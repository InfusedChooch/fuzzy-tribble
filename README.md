# 🏢 Hall Pass Tracker (v0.7.5)

A Flask-based digital hall pass system for managing student movement across rooms and stations.
Built for educational environments with student-facing kiosks, admin tools, logging, schedule flexibility, and GUI control.

Now includes a robust room manager UI, interactive launcher, and dynamic station visualization.

---

## 🚀 Features (v0.7.5)

### ✅ Student Features

* Login using Student ID
* Request pass from scheduled room
* Return when finished
* Sign in/out of hallway stations (Bathroom, Nurse, etc.)
* Auto-end pass when returning to original room
* Auto-end override pass if returning to assigned room with no logs
* Configurable max passes per room (via config)
* Visual status of room slots (free/pending/taken)
* Real-time kiosk bubble updates

### ✅ Admin Features

* Secure login with configurable username/password
* Create override passes manually
* Monitor all pending/active passes in real-time
* Approve/reject requests via dashboard
* Manually end any pass
* Add/edit notes to open passes
* Room Manager UI with:

  * Toggle room/station active state
  * View current occupancy (dots with tooltips)
  * Rename, reset, view stats, or copy popout link
  * Delete room or "Close All" from UI
* View 50 most recent returns with full timestamps
* Weekly pass summaries per student
* Export pass and audit logs to CSV
* Upload/download student rosters (CSV)

### 🔹 GUI Launcher (Updated)

* Launch server via WSGI or `main.py`
* Stream stdout/stderr to console
* Route preview browser for all endpoints
* Config editor tab (colors, pass limit, reset time)
* Day schedule selector (`regular`, `half_day`, `delayed`)
* Export current DB to CSVs + JSON logs
* Rebuild/reset DB from seed files
* Tail audit log (`console_audit.log`)

---

## 📁 Project File Tree

```plaintext
📁 /
├── launcher.py            — GUI launcher (Tkinter)
├── main.py / wsgi.py      — App entrypoints
├── requirements.txt       — Python deps
├── README.md / Worklog.md — Docs + TODOs

📁 data/
├── config.json            — App config (theme, slots, schedule)
├── hallpass.db            — SQLite database
├── station_heartbeat.json — Last station swipes
└── logs/                  — Exports + audit trail

📁 scripts/
├── masterlist.csv         — Initial student-period room mappings
├── build_student_periods.py — Splits masterlist into rosters
└── rebuild_db.py          — DB from seed files

📁 Seed/
├── audit_log.csv / passes.csv / pass_events.csv
├── students.csv / student_periods.csv
└── masterlist.csv         — Source student schedule

📁 src/
├── __init__.py / database.py / models.py
├── utils.py               — config, audit, CSV response
├── services/
│   └── pass_manager.py    — Pass logic engine
└── routes/
    ├── admin.py           — Dashboard, pass admin, room manager
    ├── auth.py            — Login/logout (student/admin)
    ├── core.py            — Student-facing pass flow
    ├── passlog.py         — Kiosk logic + station interactions
    ├── report.py          — Weekly reports + CSVs
    └── students.py        — Roster upload/download/add

📁 static/
├── student_upload_template.csv
├── css/
│   └── style.css          — Global theming
├── images/
│   ├── icon.png
│   └── school_logo.png
└── js/
    ├── admin.js           — Pass tables, timers, actions
    ├── index.js           — Student bubbles + live clock
    └── rooms.js           — Room Manager interface

📁 templates/
├── *.html (admin, index, login, station, summary, etc.)
```

---

## 🌐 App Logic Map

```plaintext
🖥️ launcher.py
 ├── Launches main.py / wsgi.py
 ├── Edits config.json
 ├── Displays audit logs, routes, rebuild tools

🔗 main.py / wsgi.py → src/__init__.py
 └── Registers all Flask routes

📂 src/routes/
 ├── auth.py       — Handles login/session
 ├── core.py       — Student check-in/request flow
 ├── passlog.py    — Station IN/OUT logic
 ├── admin.py      — Pass dashboard, room controls
 ├── report.py     — Summary exports + weekly data
 └── students.py   — CSV upload/download/add

🧬 pass_manager.py
 └── create, approve, return, record event — core pass lifecycle

🛠️ utils.py
 ├── get_current_period, get_room
 ├── load_config, log_audit
 └── csv_response for export endpoints

📄 templates/
 └── Jinja2 views tied to route rendering

📁 static/js/
 ├── admin.js — live timers, pass actions, collapse
 ├── index.js — student view, clock, period
 └── rooms.js — Room Manager (rename, reset, stats, delete)

🫒 Worklog.md — Daily dev notes and tasks
```

---

## 🤪 Testing Checklist

### Student Flow

* ✅ Login with ID → get routed to assigned room
* ✅ Request pass → see pending status
* ✅ Admin approves → see active
* ✅ Swipe into station → status log updates
* ✅ Return to origin → auto-close + audit

### Admin Flow

* ✅ Login → dashboard loads open + returned passes
* ✅ Approve/reject buttons work
* ✅ Room Manager shows status dots + actions
* ✅ Override passes work (manual checkout)
* ✅ CSVs download correctly
* ✅ Room Manager triple-dot menu works (rename, reset, delete, copy link)

---

## 🔄 Recent Improvements (v0.7.5)

* ✅ Room bubbles now show live **occupied**, **pending**, and **free** states
* ✅ Triple-dot menu for room manager actions (rename, stats, reset, delete, link)
* ✅ `Close All Rooms` button in Room Manager
* ✅ Station IN resets room-in bubble to green when leaving
* ✅ Launcher export saves `students`, `passes`, `audit`, and `events` to `/data/logs/`
* ✅ Audit log stream visible in GUI console
* ✅ Kiosk window size/position is remembered per room
* ✅ Refactored `/admin_rooms` logic with centralized config handling
* ✅ `passroom_view` now strictly enforces period/room match

---

## 🛠 Setup Instructions

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate       # or venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the GUI launcher
python launcher.py
```

Alternatively:

```bash
# Run manually:
python main.py
# or
waitress-serve --port=5000 wsgi:app
```

---

## 😂 Pass Status Lifecycle

```plaintext
→ Login (student ID)
→ Request pass → pending_start
→ Admin approves → active
→ Swipe into station
→ Return to origin → pending_return
→ Admin approves → returned
```

---

## 💼 License

MIT — Free to use, adapt, and deploy for educational institutions.
