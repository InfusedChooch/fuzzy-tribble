# 🏢 Hall Pass Tracker (v0.7)

A Flask-based digital hall pass system for managing student movement across rooms and stations.
Built for school use with student-facing kiosks and a robust admin panel for live monitoring, overrides, logs, and reports.
Now includes a GUI launcher with route preview, log streaming, dynamic server startup, **editable config**, and **schedule type switching**.

---

## 🚀 Features (v0.7)

### ✅ Student Features

* Login using Student ID
* Request pass from scheduled room
* Request return when finished
* Sign in/out of hallway stations (Bathroom, Nurse, Library, Office)
* Auto-end pass when returning to original room station
* Auto-end override pass with no logs if checking into assigned room
* Enforced max passes per room (from config)

### ✅ Admin Features

* Secure login with editable username & password
* Create override passes with room/period inputs
* Monitor all pending/active passes live (auto-refresh every 5 sec)
* Approve/reject pass requests from a unified pending list
* End any active pass manually
* Add/update notes on any open pass
* View 50 most recent returned passes with detailed timestamps:

  * Room Out + Time
  * Station In + Out + Duration
  * Room In + Time
  * Hallway vs Station Time
* Access weekly summary with pass stats and override tracking
* Export final logs and weekly summary to CSV
* ✨ Launch live kiosk via dropdown: `/station_view/<station>`
* Upload/download student roster (CSV w/ JSON schedules)

### 🔹 GUI Launcher (Updated)

* Launch server via WSGI or `main.py`
* Live popout console with server stdout/stderr
* Clickable Local and LAN server links
* Auto-discovers all routes and groups by file
* Embedded browser preview for all GET routes
* Uses `static/images/school_logo.png` as app/taskbar icon
* Edit config settings live (including theme, max pass time, passes available)
* Switch between `regular`, `half_day`, and `delayed` schedules
* Rebuild/reset database and export current logs

---

## 📂 File Structure

```
launcher.py
LICENSE
list_files.py
main.py
Paths.md
README.md
requirements.txt
venvinstructions.txt
wsgi.py

data/
├── active_rooms.json
├── config.json
├── hallpass.db
├── station_heartbeat.json
└── logs/
    ├── 20250515_audit.json
    ├── 20250515_auditlog.json
    ├── 20250515_masterlist.csv

Old/
└── app.py

scripts/
└── rebuild_db.py

Seed/
├── auditlog.json
├── masterlist.csv
└── passlog.json

src/
├── __init__.py
├── database.py
├── models.py
├── utils.py
└── routes/
    ├── admin.py
    ├── auth.py
    ├── core.py
    ├── passlog.py
    ├── report.py
    └── students.py

static/
├── student_upload_template.csv
├── css/
│   └── style.css
├── images/
│   ├── icon.png
│   └── school_logo.png
└── js/
    ├── admin.js
    └── index.js

templates/
├── admin.html
├── admin_login.html
├── admin_pass_history.html
├── admin_report.html
├── admin_weekly_summary.html
├── index.html
├── login.html
├── station.html
└── students.html
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

Or run manually:

```bash
python main.py
# or
waitress-serve --port=5000 wsgi:app
```

---

## 🥺 Pass Lifecycle

1. **Student login** ➔ redirect to scheduled room
2. **Request pass** ➔ marked `pending_start`
3. **Admin approves** ➔ pass becomes `active`
4. **Student logs station IN/OUT**
5. **Student clicks return** ➔ `pending_return`
6. **Admin approves** ➔ pass marked `returned` with logs

---

## 💪 Testing Tips

### Students

* Log in and verify assigned room access
* Request pass and visit a kiosk
* Return to original room

### Admins

* Use `/admin_login` to access dashboard
* Test overrides and notes
* View history and export CSVs
* Open kiosk station via "Pop Out Station" (dropdown in admin panel)
* Switch day types (top left dropdown)
* Test config editing via launcher

---

## ♻ What's New in v0.7

* ✨ **Full pass logging with station in/out & elapsed time**
* ✨ **Launcher supports config editing + day switching**
* ✨ **Route preview & link tester in launcher**
* 🖊️ Admin can now manually check-in/return passes
* 🖊️ Override passes end instantly if no station logs are made
* ✅ Students auto-routed only if room is active
* 📊 Exported logs show station time, hallway time, notes, override
* ⏰ Admin panel now shows real-time durations
* 📲 `/ping` route for server health monitoring
* 💡 Pass status tags: `pending_start`, `active`, `pending_return`, `returned`

---

## 💼 License

MIT — Free to use, modify, and deploy in educational settings.
