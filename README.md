# Training Waitlist

Students join a waitlist, then get a button to join the WhatsApp group. Admin dashboard with search, level filter and CSV export.

## Run locally (Windows)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      (then edit .env)
python app.py
```
Open http://127.0.0.1:5000. Admin: http://127.0.0.1:5000/admin
If `DATABASE_URL` is empty, a local SQLite file is used.

## Neon
1. Create a project at neon.tech, then copy the connection string (it ends with `?sslmode=require`).
2. Put it in `.env` as `DATABASE_URL` to test locally against Neon.
Tables are created automatically on first start.

## Deploy on Railway
1. Push this folder to GitHub.
2. Railway: New Project > Deploy from GitHub repo.
3. Variables tab, add: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`, `WHATSAPP_LINK`, `EVENT_NAME`, `EVENT_TAGLINE`, `EVENT_DATE`.
4. Settings > Networking > Generate Domain.
The `Procfile` starts gunicorn. `/health` is available for health checks.

## Courses
The course list lives in `COURSES` at the top of `app.py`. Edit it to add or rename courses. Existing databases get the new `course` column automatically on startup.

## Next phase
`status` on each entry (`waiting`, `invited`, `registered`) is already in the table for the registration stage.
