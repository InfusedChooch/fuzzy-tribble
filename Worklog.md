# 📓 Project Work Log — Hall Pass Tracker

This file serves as a living changelog and task board for ongoing development, testing, and maintenance.

---

## ✅ Things Working

- 🧠 Pass lifecycle (request ➝ approve ➝ return) with accurate state tracking
- 👨‍🏫 Admin dashboard with real-time pass monitoring and timer updates
- 🗂️ Pass note functionality via dashboard
- 📋 Student login and scheduled room routing
- 🧾 Full pass audit logging with `console_audit.log` and DB write
- 🔐 Admin login and password change flow
- 📅 Schedule switching (`regular`, `half_day`, `delayed`) from launcher
- 🔄 Launcher GUI with:
  - WSGI or main.py launch
  - Console output
  - Config editor
  - Day type switch
  - Route preview
- 📊 Reports: weekly summary, pass history, CSV export
- 🧪 `/ping`, `/debug_period`, `/debug_rooms` working
- 📦 Database rebuild from seed files (with masterlist splitter)

---

## 🧐 Things Needing a Look

- 📎 Route `/request_pass` appears referenced in `index.js` but not routed in `core.py` — confirm if deprecated or missing
- 🧩 Confirm redundant code in `stop_server()` (defined twice in `launcher.py`)
- ⚠️ Determine consistency between pass creation logic in `core.py` vs. `passlog.py` vs. `admin_create_pass`
- 📦 Improve error messaging on student upload (e.g. bad CSV formatting or missing fields)
- 🔁 Multiple tab refresh intervals in `admin.js` — evaluate performance cost for long-term use
- 📁 Confirm consistent use of `student_id` casing across form submissions and database lookups

---

## ❌ Things Broken or Inconsistent

- 🛑 `Stop Server` in launcher does not terminate `main.py` cleanly if run outside the same shell
- 🧵 Audit log tailer sometimes throws file-handle errors if `console_audit.log` does not exist on launch
- ⚙️ `launch_server()` assumes `waitress-serve` is in path — may fail silently if not found
- 🧾 Error handling on station double-swipe within 30 seconds needs testing across multiple station types
- 🗃️ Exported DB CSVs sometimes mismatch headers due to renamed DB columns (e.g., `origin_room` vs. `room_out`)
- 🔁 `student.schedule[...]` logic in some routes was replaced by `get_room()` but may still be referenced

---

## ⏭️ Next Steps

- [ ] 🔁 Refactor and unify pass creation logic (core/admin/passlog)
- [ ] 🛠️ Add `/request_pass` route or remove it from frontend
- [ ] 🔒 Migrate passwords to hashed storage (currently plaintext in config.json)
- [ ] 🔍 Add `/status` route for station health
- [ ] 📆 Allow custom bell schedule override per day (via calendar config)
- [ ] 📤 Email/notification hooks on override or excessive passes
- [ ] 📦 Exportable full student profile (pass history + summary)
- [ ] 💡 Add dark mode / UI theme toggle to launcher


### File Index
launcher.py (CustomTkinter)
LICENSE
main.py
README.md
requirements.txt
venvinstructions.txt
Worklog.md
wsgi.py
data\active_rooms.json
data\config.json
data\hallpass.db
data\station_heartbeat.json
data\logs\20250520_audit_log.csv
data\logs\20250520_passes.csv
data\logs\20250520_passlog.json
data\logs\20250520_pass_events.csv
data\logs\20250520_students.csv
data\logs\20250520_student_periods.csv
data\logs\console_audit.log
scripts\build_student_periods.py
scripts\masterlist.csv
scripts\rebuild_db.py
Seed\audit_log.csv
Seed\masterlist.csv
Seed\passes.csv
Seed\pass_events.csv
Seed\students.csv
Seed\student_periods.csv
src\database.py
src\models.py
src\utils.py
src\__init__.py
src\routes\admin.py
src\routes\auth.py
src\routes\core.py
src\routes\passlog.py
src\routes\report.py
src\routes\students.py
src\services\pass_manager.py
static\student_upload_template.csv
static\css\style.css
static\images\icon.png
static\images\school_logo.png
static\js\admin.js
static\js\index.js
static\js\rooms.js
templates\admin.html
templates\admin_login.html
templates\admin_pass_history.html
templates\admin_report.html
templates\admin_rooms.html
templates\admin_weekly_summary.html
templates\index.html
templates\login.html
templates\station.html
templates\students.html

