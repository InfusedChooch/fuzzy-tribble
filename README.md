# 🏢 Hall Pass Tracker (v0.7)

A Flask-based digital hall pass system for managing student movement across rooms and stations.
Built for educational environments with student-facing kiosks, admin tools, logging, schedule flexibility, and GUI control.
Now includes a desktop GUI launcher with full config editing, audit visibility, and real-time route preview.

---

## 🚀 Features (v0.7)

### ✅ Student Features

* Login using Student ID
* Request pass from scheduled room
* Return when finished
* Sign in/out of hallway stations (Bathroom, Nurse, etc.)
* Auto-end pass when returning to original room
* Auto-end override pass if returning to assigned room with no logs
* Configurable max passes per room (via config)

### ✅ Admin Features

* Secure login with configurable username/password
* Create override passes manually
* Monitor all pending/active passes in real-time
* Approve/reject requests via dashboard
* Manually end any pass
* Add/edit notes to open passes
* View 50 most recent returns with full timestamps:

  * Room Out, Station In/Out, Room In
  * Duration: total, hallway, station
* View/export weekly pass summary per student
* Export full pass and audit logs to CSV
* Launch station kiosk from dropdown selector
* Upload/download student rosters (CSV)

### 🔹 GUI Launcher (Updated)

* Launch server via WSGI or `main.py`
* Stream live stdout/stderr to GUI console
* Local + LAN route links
* Embedded browser to preview all GET routes
* Editable config: color theme, pass limits, reset time
* Switch between `regular`, `half_day`, and `delayed` schedules
* Export logs or rebuild/reset DB from seed files
* Tail live audit log (`console_audit.log`)

---

## 📁 Project File Index

```plaintext
.
├── file_paths.md
├── launcher.py
├── LICENSE
├── list_files.py
├── main.py
├── README.md
├── requirements.txt
├── venvinstructions.txt
├── Worklog.md
├── wsgi.py
├── data
│   ├── config.json
│   ├── hallpass.db
│   ├── station_heartbeat.json
│   └── logs
│       └── console_audit.log
├── scripts
│   ├── build_student_periods.py
│   ├── masterlist.csv
│   └── rebuild_db.py
├── Seed
│   ├── audit_log.csv
│   ├── masterlist.csv
│   ├── passes.csv
│   ├── pass_events.csv
│   ├── students.csv
│   └── student_periods.csv
├── src
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   ├── utils.py
│   ├── routes
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── core.py
│   │   ├── passlog.py
│   │   ├── report.py
│   │   └── students.py
│   └── services
│       └── pass_manager.py
├── static
│   ├── student_upload_template.csv
│   ├── css
│   │   └── style.css
│   ├── images
│   │   ├── icon.png
│   │   └── school_logo.png
│   └── js
│       ├── admin.js
│       ├── index.js
│       └── rooms.js
└── templates
    ├── admin.html
    ├── admin_login.html
    ├── admin_pass_history.html
    ├── admin_report.html
    ├── admin_rooms.html
    ├── admin_weekly_summary.html
    ├── index.html
    ├── login.html
    ├── station.html
    └── students.html

```

---

## 🌐 Project Logic Tree (Simplified)

```plaintext
🖥️ launcher.py — GUI launcher
  ├── scripts/*.py — DB rebuild, student splitter
  ├── data/config.json — editable in launcher
  ├── data/logs/*.csv — exported reports
  └── wsgi.py / main.py — launches Flask app (Waitress / direct)

🧩 main.py / wsgi.py — App entrypoints
  └── src/__init__.py — creates and configures the Flask app
      ├── src/routes/*.py — defines all route blueprints
      ├── src/models.py — database schema (Students, Passes, Logs)
      ├── src/utils.py — shared helpers (config, periods, logging)
      └── src/services/pass_manager.py — core pass lifecycle logic

🌐 src/routes/*.py — Flask API + HTML endpoints
  ├── admin.py — dashboards, room control, exports, pass admin
  ├── auth.py — login/logout + session auth
  ├── core.py — student passroom check-in/request logic
  ├── passlog.py — kiosk station IN/OUT swipes, heartbeat
  ├── report.py — admin reports (CSV/HTML)
  └── students.py — upload/download student schedule

🧠 src/services/pass_manager.py — Pass lifecycle functions
  ├── create_pass(), approve_pass(), return_pass(), record_pass_event()
  └── Used directly by admin.py and passlog.py

🛠️ src/utils.py — General utilities
  ├── get_current_period(), get_room(), log_audit(), load_config()
  └── Also includes CSV export response wrapper

📄 templates/*.html — Jinja2 HTML templates
  ├── admin.html, login.html, index.html, station.html, etc.
  └── Used via render_template() in routes

📁 static/js/*.js — JavaScript logic
  ├── index.js — student display, clock, period sync
  ├── admin.js — dashboard tables, notes, pass controls
  └── rooms.js — room manager UI (toggle, rename, stats, reset)

📁 data/ — Runtime data
  ├── config.json — full configuration (editable)
  ├── station_heartbeat.json — last check-in timestamps
  ├── hallpass.db — SQLite database (auto-rebuilt)
  └── logs/ — audit log + CSV/JSON exports

📁 scripts/ — Admin helper scripts
  ├── build_student_periods.py — splits masterlist.csv into students.csv and student_periods.csv
  ├── masterlist.csv — source input
  └── rebuild_db.py — resets the DB from /Seed data

📁 Seed/ — Initial seed data
  └── CSVs for students, passes, logs (used by rebuild_db)

🧾 Worklog.md — Dev notes and project TODOs

```

---

## 🚧 Setup Instructions

### 1. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Run the Launcher

```bash
python launcher.py
```

Or manually:

```bash
python main.py
# or
waitress-serve --port=5000 wsgi:app
```

---

## 🥺 Pass Lifecycle

1. Student login ➔ redirect to room view
2. Request pass ➔ status = `pending_start`
3. Admin approves ➔ status = `active`
4. Student uses station(s)
5. Click return ➔ status = `pending_return`
6. Admin approves ➔ pass marked `returned`

---

## 💪 Testing Tips

### Student Testing

* Login and verify room access
* Request a pass and swipe into a kiosk
* Return pass and check audit trail

### Admin Testing

* Login via `/admin_login`
* Approve/reject passes and add notes
* View history and export CSVs
* Launch station view via dropdown
* Switch day type via launcher
* Edit and save config in GUI

---

## ♻ What's New in v0.7

* ✨ Full logging: station in/out, durations
* ✨ GUI: config editor + day schedule switching
* ✨ Route preview browser inside launcher
* 🖊️ Manual pass return by admin
* 🖊️ Auto-end override pass with no logs
* ✅ Students only route if room is active
* 📊 CSVs now include notes + override indicators
* ⏰ Admin panel shows live timers
* 📲 `/ping` health endpoint for WSGI
* 💡 Tags: `pending_start`, `active`, `pending_return`, `returned`

---

## 💼 License

MIT — Free to use and modify in educational environments.
