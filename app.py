"""Training / Bootcamp waitlist app.

Flask + SQLAlchemy. Uses Neon (Postgres) in production via DATABASE_URL and
falls back to a local SQLite file for development.
"""
import csv
import hmac
import io
import os
import re
import secrets
from datetime import datetime, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------------- config
secret = os.environ.get("SECRET_KEY")
if not secret:
    secret = secrets.token_hex(32)
    print("WARNING: SECRET_KEY not set; sessions reset on every restart.")
app.config["SECRET_KEY"] = secret


def _database_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///waitlist.db"
    # Neon/Railway hand out postgres:// or postgresql://. Use the psycopg (v3) driver.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


app.config["SQLALCHEMY_DATABASE_URI"] = _database_url()
# Neon suspends idle connections: check them before use and recycle often.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

db = SQLAlchemy(app)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
def _normalise_link(url):
    """Make 'chat.whatsapp.com/xyz' (no scheme) or a quoted value into a full https link."""
    url = (url or "").strip().strip("\"'").strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url.lstrip("/")
    return url


WHATSAPP_LINK = _normalise_link(os.environ.get("WHATSAPP_LINK", ""))
_date = os.environ.get("EVENT_DATE", "").strip()
_venue = os.environ.get("EVENT_VENUE", "").strip()
EVENT = {
    "name": os.environ.get("EVENT_NAME", "Hotspot Learning Hub"),
    "partner": os.environ.get("EVENT_PARTNER", "8Digits Komputers"),
    "program": os.environ.get("EVENT_PROGRAM", "NextGen Skill"),
    "headline": os.environ.get("EVENT_HEADLINE", "Free 3 Weeks of Impact"),
    "tagline": os.environ.get(
        "EVENT_TAGLINE",
        "Open to every student. Every level. Every department. Every college.",
    ),
    "date": _date,
    "venue": _venue,
    # The "date and venue will be communicated soon" banner shows until BOTH are set.
    "details_ready": bool(_date and _venue),
}

from content import COHOSTS, COURSES, LEGACY_COURSES, SPONSORS  # noqa: E402

COURSE_NAMES = [c["name"] for c in COURSES]
COURSE_ICONS = {**LEGACY_COURSES, **{c["name"]: c["icon"] for c in COURSES}}
LEVELS = ["100 Level", "200 Level", "300 Level", "400 Level", "500 Level", "Postgraduate"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------- model
class WaitlistEntry(db.Model):
    __tablename__ = "waitlist"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(32), nullable=False)
    institution = db.Column(db.String(160), nullable=False)
    college = db.Column(db.String(160), nullable=False)
    department = db.Column(db.String(160), nullable=False)
    level = db.Column(db.String(32), nullable=False, index=True)
    course = db.Column(db.String(80), nullable=True, index=False)
    # waiting -> invited -> registered (used in phase 2)
    status = db.Column(db.String(16), nullable=False, default="waiting", index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


def ensure_schema():
    """Add columns introduced after the first deploy (create_all never alters tables)."""
    from sqlalchemy import inspect, text
    try:
        cols = {c["name"] for c in inspect(db.engine).get_columns("waitlist")}
        if "course" not in cols:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE waitlist ADD COLUMN course VARCHAR(80)"))
    except Exception as exc:  # another worker may have added it first
        db.session.rollback()
        print("ensure_schema:", exc)


with app.app_context():
    try:
        db.create_all()
    except Exception as exc:
        host = app.config["SQLALCHEMY_DATABASE_URI"].split("@")[-1].split("/")[0]
        print("\n" + "=" * 70)
        print("Could not connect to the database (" + host + ").")
        print("Check your internet connection, DNS and VPN, and that DATABASE_URL is correct.")
        print("To work offline, leave DATABASE_URL empty in .env to use local SQLite.")
        print("=" * 70 + "\n")
        raise
    ensure_schema()


# ---------------------------------------------------------------- helpers
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["EVENT"] = EVENT
app.jinja_env.globals["COURSES"] = COURSES
app.jinja_env.globals["COHOSTS"] = COHOSTS
app.jinja_env.globals["SPONSORS"] = SPONSORS
app.jinja_env.globals["COURSE_ICONS"] = COURSE_ICONS


def check_csrf():
    sent = request.form.get("_csrf", "")
    if not sent or not hmac.compare_digest(sent, session.get("_csrf", "")):
        abort(400, "Invalid or expired form. Please go back and try again.")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def clean(value, limit):
    return re.sub(r"\s+", " ", (value or "").strip())[:limit]


def normalise_phone(raw):
    raw = (raw or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not 10 <= len(digits) <= 15:
        return None
    return ("+" if raw.startswith("+") else "") + digits


def csv_safe(value):
    """Stop spreadsheet formula injection in exported CSVs."""
    value = "" if value is None else str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def validate(form):
    data = {
        "full_name": clean(form.get("full_name"), 120),
        "email": clean(form.get("email"), 160).lower(),
        "phone": normalise_phone(form.get("phone")),
        "institution": clean(form.get("institution"), 160),
        "college": clean(form.get("college"), 160),
        "department": clean(form.get("department"), 160),
        "level": clean(form.get("level"), 32),
        "course": clean(form.get("course"), 80),
    }
    errors = []
    if len(data["full_name"]) < 3:
        errors.append("Please enter your full name.")
    if not EMAIL_RE.match(data["email"]):
        errors.append("Please enter a valid email address.")
    if not data["phone"]:
        errors.append("Please enter a valid WhatsApp number (10-15 digits).")
    for key, label in (("institution", "school"), ("college", "college or faculty"),
                       ("department", "department")):
        if not data[key]:
            errors.append(f"Please enter your {label}.")
    if data["level"] not in LEVELS:
        errors.append("Please choose your level.")
    if data["course"] not in COURSE_NAMES:
        errors.append("Please choose the course you want to join.")
    return data, errors


def wa_number(phone):
    """Digits for a wa.me link. Nigerian local numbers (080...) become 234..."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0") and len(digits) == 11:
        digits = "234" + digits[1:]
    return digits


app.jinja_env.filters["wa_number"] = wa_number


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(err):
    code = getattr(err, "code", 500)
    messages = {400: "That form expired or was invalid. Please go back and try again.",
                404: "We couldn't find that page.",
                500: "Something went wrong on our side. Please try again."}
    return render_template("error.html", code=code,
                           message=messages.get(code, "Something went wrong.")), code


# ---------------------------------------------------------------- public
@app.route("/")
def index():
    return render_template("index.html", levels=LEVELS, form={})


@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "GET":
        return redirect(url_for("index") + "#join")
    check_csrf()
    # Honeypot: real people never fill this hidden field
    if request.form.get("website"):
        return redirect(url_for("index"))

    data, errors = validate(request.form)
    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("index.html", levels=LEVELS, form=request.form), 400

    existing = WaitlistEntry.query.filter_by(email=data["email"]).first()
    if existing:
        entry, already = existing, True
    else:
        entry = WaitlistEntry(**data)
        db.session.add(entry)
        try:
            db.session.commit()
        except Exception:  # race: same email submitted twice at once
            db.session.rollback()
            entry = WaitlistEntry.query.filter_by(email=data["email"]).first()
            if entry is None:
                flash("Something went wrong. Please try again.", "error")
                return redirect(url_for("index"))
        already = existing is not None

    session["joined_id"] = entry.id
    session["already"] = already
    return redirect(url_for("success"))


@app.route("/success")
def success():
    entry_id = session.get("joined_id")
    entry = db.session.get(WaitlistEntry, entry_id) if entry_id else None
    if not entry:
        return redirect(url_for("index"))
    return render_template("success.html", entry=entry,
                           already=session.get("already", False),
                           whatsapp_link=WHATSAPP_LINK)


# ---------------------------------------------------------------- admin
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        check_csrf()
        supplied = request.form.get("password", "")
        if ADMIN_PASSWORD and hmac.compare_digest(supplied, ADMIN_PASSWORD):
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin"))
        flash("Incorrect password.", "error")
    return render_template("admin_login.html", configured=bool(ADMIN_PASSWORD))


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    check_csrf()
    session.clear()
    return redirect(url_for("index"))


def filtered_query():
    q = clean(request.args.get("q"), 100)
    level = clean(request.args.get("level"), 32)
    course = clean(request.args.get("course"), 80)
    query = WaitlistEntry.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            WaitlistEntry.full_name.ilike(like), WaitlistEntry.email.ilike(like),
            WaitlistEntry.phone.ilike(like), WaitlistEntry.institution.ilike(like),
            WaitlistEntry.college.ilike(like), WaitlistEntry.department.ilike(like),
            WaitlistEntry.course.ilike(like)))
    if level in LEVELS:
        query = query.filter(WaitlistEntry.level == level)
    if course in COURSE_NAMES or course in LEGACY_COURSES:
        query = query.filter(WaitlistEntry.course == course)
    return query, q, level, course


@app.route("/admin")
@admin_required
def admin():
    query, q, level, course = filtered_query()
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = query.order_by(WaitlistEntry.id.desc()).paginate(
        page=page, per_page=50, error_out=False)
    total = db.session.query(func.count(WaitlistEntry.id)).scalar() or 0
    by_level = dict(db.session.query(WaitlistEntry.level, func.count(WaitlistEntry.id))
                    .group_by(WaitlistEntry.level).all())
    by_course = dict(db.session.query(WaitlistEntry.course, func.count(WaitlistEntry.id))
                     .group_by(WaitlistEntry.course).all())
    course_stats = [(c["name"], c["icon"], by_course.get(c["name"], 0)) for c in COURSES]
    extras = [(n, COURSE_ICONS.get(n, "📌"), cnt) for n, cnt in by_course.items()
              if n and n not in COURSE_NAMES]
    course_stats += sorted(extras, key=lambda t: -t[2])
    course_options = COURSE_NAMES + [n for n, _, _ in extras if n in LEGACY_COURSES]
    course_max = max([n for _, _, n in course_stats] + [1])
    return render_template("admin.html", pagination=pagination, total=total,
                           by_level=by_level, levels=LEVELS, q=q, level=level,
                           course=course, course_stats=course_stats, course_options=course_options, course_max=course_max,
                           unassigned=by_course.get(None, 0))


@app.route("/admin/delete/<int:entry_id>", methods=["POST"])
@admin_required
def admin_delete(entry_id):
    check_csrf()
    entry = db.session.get(WaitlistEntry, entry_id)
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash(f"Removed {entry.full_name} from the waitlist.", "success")
    return redirect(request.referrer or url_for("admin"))


@app.route("/admin/export.csv")
@admin_required
def export_csv():
    query, _, _, _ = filtered_query()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Full name", "Email", "WhatsApp", "School", "College",
                     "Department", "Level", "Course", "Status", "Joined (UTC)"])
    for e in query.order_by(WaitlistEntry.id.asc()).all():
        writer.writerow([e.id, csv_safe(e.full_name), csv_safe(e.email), csv_safe(e.phone),
                         csv_safe(e.institution), csv_safe(e.college),
                         csv_safe(e.department), e.level, csv_safe(e.course or ""), e.status,
                         e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else ""])
    return Response(buf.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=waitlist.csv"})


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True)
