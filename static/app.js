(function () {
  "use strict";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* header shadow on scroll */
  var bar = document.querySelector(".topbar");
  function onScroll() { if (bar) bar.classList.toggle("scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  /* scroll reveal */
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    reveals.forEach(function (el) { io.observe(el); });
  } else { reveals.forEach(function (el) { el.classList.add("in"); }); }

  /* count-up numbers */
  document.querySelectorAll("[data-count]").forEach(function (el) {
    var target = parseInt(el.getAttribute("data-count"), 10) || 0;
    if (reduce || target < 2) { el.textContent = target; return; }
    var start = null, dur = 1100;
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });

  /* button ripple */
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".btn");
    if (!btn || reduce) return;
    var r = btn.getBoundingClientRect(), size = Math.max(r.width, r.height);
    var s = document.createElement("span");
    s.className = "ripple";
    s.style.cssText = "width:" + size + "px;height:" + size + "px;left:" + (ev.clientX - r.left - size / 2) +
      "px;top:" + (ev.clientY - r.top - size / 2) + "px";
    btn.appendChild(s); setTimeout(function () { s.remove(); }, 650);
  });

  /* dismiss flash messages */
  document.querySelectorAll(".flash").forEach(function (f) {
    f.addEventListener("click", function () { f.remove(); });
  });

  /* confirm dialogs for destructive forms */
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) { if (!window.confirm(f.getAttribute("data-confirm"))) e.preventDefault(); });
  });

  /* waitlist form: inline validation + loading state */
  var form = document.getElementById("join-form");
  if (form) {
    var rules = {
      full_name: function (v) { return v.trim().length >= 3 || "Please enter your full name."; },
      email: function (v) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.trim()) || "Enter a valid email address."; },
      phone: function (v) { var d = v.replace(/\D/g, ""); return (d.length >= 10 && d.length <= 15) || "Enter a valid WhatsApp number."; },
      institution: function (v) { return v.trim().length > 0 || "Enter your school."; },
      college: function (v) { return v.trim().length > 0 || "Enter your college or faculty."; },
      department: function (v) { return v.trim().length > 0 || "Enter your department."; },
      level: function (v) { return v !== "" || "Choose your level."; }
    };
    function check(input) {
      var rule = rules[input.name]; if (!rule) return true;
      var res = rule(input.value), err = input.parentNode.querySelector(".field-error");
      if (!err) { err = document.createElement("span"); err.className = "field-error"; input.parentNode.appendChild(err); }
      var ok = res === true;
      input.setAttribute("aria-invalid", ok ? "false" : "true");
      input.classList.toggle("ok", ok);
      err.textContent = ok ? "" : res;
      return ok;
    }
    form.querySelectorAll("input,select").forEach(function (i) {
      i.addEventListener("blur", function () { if (i.value !== "" || i.dataset.touched) check(i); i.dataset.touched = "1"; });
      i.addEventListener("input", function () { if (i.getAttribute("aria-invalid") === "true") check(i); });
    });
    var courseGroup = document.getElementById("course-group"), courseErr = document.getElementById("course-error");
    function courseChosen(report) {
      var ok = !!form.querySelector("input[name=course]:checked");
      if (courseGroup) courseGroup.classList.toggle("invalid", !ok && report);
      if (courseErr) courseErr.textContent = ok || !report ? "" : "Please choose a course to continue.";
      if (!ok && report && courseGroup) courseGroup.scrollIntoView({ behavior: "smooth", block: "center" });
      return ok;
    }
    form.querySelectorAll("input[name=course]").forEach(function (r) {
      r.addEventListener("change", function () { courseChosen(false); });
    });
    form.addEventListener("submit", function (e) {
      var firstBad = null;
      form.querySelectorAll("input,select").forEach(function (i) { if (!check(i) && !firstBad) firstBad = i; });
      if (firstBad) { e.preventDefault(); firstBad.focus(); return; }
      if (!courseChosen(true)) { e.preventDefault(); return; }
      var b = form.querySelector("button[type=submit]");
      b.disabled = true; b.innerHTML = '<span class="spinner"></span> Joining...';
    });
  }

  /* share button */
  var share = document.getElementById("share-btn");
  if (share) {
    share.addEventListener("click", function () {
      var data = { title: document.title, text: share.getAttribute("data-text"), url: share.getAttribute("data-url") };
      if (navigator.share) { navigator.share(data).catch(function () {}); return; }
      if (navigator.clipboard) {
        navigator.clipboard.writeText(data.url).then(function () {
          var old = share.textContent; share.textContent = "Link copied!";
          setTimeout(function () { share.textContent = old; }, 1800);
        });
      } else { window.prompt("Copy this link:", data.url); }
    });
  }

  /* confetti (success page) */
  var cv = document.getElementById("confetti");
  if (cv && !reduce) {
    var ctx = cv.getContext("2d"), W, H, parts = [], colors = ["#ef5f18", "#ff8a3d", "#271b67", "#3a2d86", "#25d366", "#ffd166"];
    function size() { W = cv.width = window.innerWidth; H = cv.height = window.innerHeight; }
    size(); window.addEventListener("resize", size);
    for (var i = 0; i < 140; i++) {
      parts.push({ x: Math.random() * W, y: -20 - Math.random() * H * 0.6, w: 6 + Math.random() * 7, h: 8 + Math.random() * 8,
        c: colors[(Math.random() * colors.length) | 0], vy: 2 + Math.random() * 3.5, vx: -1.5 + Math.random() * 3,
        rot: Math.random() * 6, vr: -0.2 + Math.random() * 0.4 });
    }
    var t0 = performance.now();
    (function frame(now) {
      ctx.clearRect(0, 0, W, H); var alive = false;
      parts.forEach(function (p) {
        p.x += p.vx; p.y += p.vy; p.rot += p.vr;
        if (p.y < H + 30) alive = true;
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.fillStyle = p.c; ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); ctx.restore();
      });
      if (alive && now - t0 < 7000) requestAnimationFrame(frame); else ctx.clearRect(0, 0, W, H);
    })(t0);
  }
})();
