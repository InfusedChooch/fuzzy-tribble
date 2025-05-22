# README.md — Updated 2025-05-21

## 📜 Overview

TJMS Hall Pass Tracker is a student check-in/out web application for managing hallway usage. Built using Flask, SQLite, and JS/HTML/CSS, it supports Admin, Teacher, and Student logins, station swiping, and visual dashboards.

Key features include:

* Admin-controlled room/station activation
* Dark mode and mobile-friendly interface
* Automatic pass validation and kiosk station logging
* Teacher and student schedules
* Live and historical reports
* CSV import/export and full database rebuild tools

---

## 📁 File Tree

```
launcher.py
LICENSE
main.py
README.md
Worklog.md
wsgi.py

📁 data/
├── config.json
├── hallpass.db
├── logs/
│   ├── 20250521_active_rooms.csv
│   ├── 20250521_audit_log.csv
│   ├── 20250521_passes.csv
│   ├── 20250521_passlog.json
│   ├── 20250521_pass_events.csv
│   ├── 20250521_student_periods.csv
│   ├── 20250521_users.csv
│   └── console_audit.log

📁 scripts/
├── build_student_periods.py
├── masterlist.csv
└── rebuild_db.py

📁 Seed/
├── student_schedule.csv
├── teacher_schedule.csv
└── users.csv

📁 src/
├── database.py
├── models.py
├── utils.py
├── __init__.py
├── routes/
│   ├── admin.py
│   ├── auth.py
│   ├── core.py
│   ├── passlog.py
│   ├── report.py
│   └── students.py
└── services/
    └── pass_manager.py

📁 static/
├── css/
│   └── style.css
├── csv/
│   ├── active_rooms_template.csv
│   ├── audit_log_template.csv
│   ├── passes_template.csv
│   ├── pass_events_template.csv
│   ├── student_periods_template.csv
│   ├── student_schedule_template.csv
│   ├── teacher_schedule_template.csv
│   └── users_template.csv
├── images/
│   ├── icon.png
│   └── school_logo.png
└── js/
    ├── admin.js
    ├── index.js
    ├── rooms.js
    └── theme.js

📁 templates/
├── admin.html
├── admin_pass_history.html
├── admin_report.html
├── admin_rooms.html
├── admin_weekly_summary.html
├── landing.html
├── login.html
├── passreq.html
├── station.html
└── students.html
```

---

## 🔁 Updated Features as of 2025-05-21

* ✅ **Dark Mode** fully integrated with toggle button (moon emoji)
* ✅ **Student landing page** (`landing.html`) added with personalized greeting, pass dots, and clock
* ✅ **Student and Teacher password change** supported via pop-up (not page redirect)
* ✅ **Export-to-CSV** added for all core tables via GUI launcher
* ✅ **Teacher schedule enforcement**: limited classroom control to teacher schedule
* ✅ **Room manager updated**: no hard deletes on toggle; "Close All" button added
* ✅ **Audit log tails to GUI**
* ✅ **JS timers** to track active pass durations
* ✅ **Admin launcher GUI** now merges rebuild/export/settings/tools in a tabbed layout

---

## 📄 Refactor Summary — May 2025 Cleanup

All major backend files under `src/routes/`, `src/utils.py`, `src/models.py`, and `src/services/` were cleaned and standardized:

* 🧹 Replaced all `"""docstrings"""` with `#` comments for consistency
* 🧩 Grouped code by logical sections with `# ──` dividers
* 📌 Added file-path + purpose comment at the top of each file
* 🔧 Reordered functions for clarity and consistency
* 🗃️ Improved inline comments and removed unused imports
* 🔐 Ensured session, role, and ID checks are clearly marked
* 📤 CSV export functions moved to use `csv_response()` helper

Refactored files:

* `scripts/build_student_periods.py`
* `scripts/rebuild_db.py`
* `src/utils.py`
* `src/models.py`
* `src/services/pass_manager.py`
* `src/routes/admin.py`
* `src/routes/auth.py`
* `src/routes/core.py`
* `src/routes/passlog.py`
* `src/routes/report.py`
* `src/routes/students.py`

🎨 Updated Frontend & Styling (May 2025)
✅ JavaScript Changes
admin.js
✅ Split logic into well-labeled sections: Init, Pass Actions, Popups, and Station Tools

✅ Added greeting message (Welcome X or Good morning X)

✅ Added preloadAndOpenSchedule() call for teachers needing schedule setup

✅ Modular pass row rendering and time tracking (updateTimers)

✅ Improved popup positioning and style consistency

✅ Refactored teacher popup to include period mapping

index.js
✅ Student landing page JS extracted to its own file

✅ Draws current room status visually using colored dots

✅ Displays current period and synced clock

✅ Supports inline password update via modal popup

rooms.js
✅ Dynamically fetches room list and statuses

✅ Admin UI includes color-coded dots: 🟥 taken, 🟦 pending, 🟩 free

✅ Room actions available: rename, reset, stats, delete

✅ closeAllRooms() utility added

theme.js
✅ Supports persistent dark mode with localStorage

✅ Conditionally shows ⚙️ Settings button for teacher/admin

✅ Adds compact floating button UI (🌓 + ⚙️)

🎨 CSS (style.css) Enhancements
✅ Full support for light/dark theme via :root + .dark variables

✅ Improved form and table accessibility

✅ Dot indicators styled for pass slots and room status

✅ Button and input hover feedback harmonized

✅ Visual consistency across all modals, popups, and tables

✅ Styled .custom-clock for prominent time display
