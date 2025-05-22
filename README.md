# README.md — Updated 2025-05-21

## 🧾 Overview

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

# Worklog.md — 2025-05-21

## ✅ Things Working

* Room toggling and visualization (color dots)
* Pop-up for password change (students + teachers)
* CSV export from launcher working (to `data/logs`)
* GUI tail for audit log confirmed working
* Dark mode toggle with moon button
* All pass lifecycles tested: start, swipe, return
* Launcher GUI has working config editor + route preview

## 🔍 Needs Review

* Ensure all timestamps are stored UTC or converted cleanly
* Confirm station slot config values are being pulled properly from `config.json`
* Double-check that dark mode overrides text contrast in all templates (e.g., `landing.html` vs. `admin.html`)

## 🛠️ Broken or Needs Fixing

* None observed today

## 🔜 Next Steps

* Add support for comments or notes per room (e.g., "Bathroom closed")
* Add student photo/ID card optional field (or scan QR)
* Enable per-student pass limits (daily/weekly)
* Improve teacher override interface with dropdowns
* Investigate SQLite concurrency limits for high volume swipes
* Auto-clear stale open passes via cron or periodic audit
