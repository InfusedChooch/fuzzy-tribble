# 🏢 Hall Pass Tracker (v0.6+ GUI Launcher Edition)

A Flask-based digital hall pass system for managing student movement across rooms and stations.
Built for school use with student-facing kiosks and a robust admin panel for live monitoring, overrides, logs, and reports.
Now includes a GUI launcher with route preview, log streaming, and dynamic server startup.

---

## 🚀 Features (v0.6)

### ✅ Student Features

* Login using Student ID
* Request pass from scheduled room
* Request return when finished
* Sign in/out of hallway stations (Bathroom, Nurse, Library, Office)
* Auto-end pass when returning to original room station

### ✅ Admin Features

* Secure login with editable username & password
* Create override passes
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
* Open live station kiosk from admin panel
* Assign current browser’s station ID (room or fixed station)
* Upload/download student roster (CSV w/ JSON schedules)

### 🔹 GUI Launcher (NEW)

* Launch server via WSGI or `main.py`
* Live popout console with server stdout/stderr
* Clickable Local and LAN server links
* Auto-discovers all routes and groups by file
* Embedded browser preview for all GET routes
* Uses `static/images/school_logo.png` as app/taskbar icon

---

## 📂 File Structure

```
hall_pass_app/
├── launcher.py              # GUI launcher
├── main.py                 # App entry and background thread
├── wsgi.py                 # WSGI server hook
├── config.json             # Admin credentials, stations, schedule
├── /data/                  # JSON files for heartbeat, active rooms
├── /src/
│   ├── models.py           # SQLAlchemy models
│   ├── utils.py            # Periods and room activation
│   └── routes/
│       ├── auth.py         # Login/logout/session timeout
│       ├── admin.py        # Admin dashboard + reporting
│       ├── students.py     # Roster upload/download
│       ├── passlog.py      # Station IN/OUT logic
│       ├── report.py       # Weekly and final CSV exports
│       └── core.py         # Student-facing routes (index/passroom/debug)
├── /templates/
│   ├── login.html
│   ├── admin.html
│   ├── index.html
│   ├── station.html
│   └── station_setup.html
└── /static/
    ├── css/style.css
    └── js/
        ├── index.js
        └── admin.js
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

## 🧪 Pass Lifecycle

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
* Launch kiosk mode or view station live

---

## 🔄 What's New in v0.6

* ✨ GUI Launcher
* ↺ Live server console
* 🔗 Clickable route list with preview
* 🔍 Auto route discovery by file
* 🎨 Custom window/taskbar icon

---

## 💼 License

MIT — Free to use, modify, and deploy in educational settings.
