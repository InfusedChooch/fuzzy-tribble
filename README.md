# Hall Pass Tracker (v0.5)

A Flask-based digital hall pass system for managing student movement across rooms and stations. Built for school use with student-facing kiosks and a robust admin panel for live monitoring, overrides, logs, and reports.

---

## 🔧 Features (v0.5)

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

---

## 🛠 Station & Room Behavior

* Stations like Bathroom/Nurse/Library are "fixed" and appear in a dropdown
* All other numeric rooms (e.g., 101, 202) must be typed manually when opening a station
* Station logs track IN → OUT events and automatically end the pass if returning to the original room
* Total pass time = room checkout → check-in
* Station time = difference between IN and OUT logs
* Hallway time = total pass time – station time

---

## 🧪 Pass Lifecycle (Request Flow)

1. **Student login** ➔ redirect to their scheduled room
2. **Request pass** ➔ mark as `pending_start`
3. **Admin approves** ➔ pass becomes `active`
4. **Student visits station** ➔ IN/OUT log created
5. **Student clicks return** ➔ becomes `pending_return`
6. **Admin approves** ➔ pass marked `returned` with timestamps + stats

---

## 📂 Folder Structure

```
hall_pass_app/
├── main.py                 # App entry and login routes
├── config.json             # Admin credentials, station list, period schedule
├── /data/                  # JSON files for heartbeat, active rooms
├── /src/
│   ├── models.py           # SQLAlchemy models
│   └── routes/
│       ├── admin.py        # Admin dashboard + reporting
│       ├── auth.py         # Login/logout/session timeout
│       ├── students.py     # Roster upload/download
│       ├── passlog.py      # Station IN/OUT logic
│       └── report.py       # Weekly and final CSV exports
├── /templates/             # HTML views
│   ├── index.html          # Student room view
│   ├── admin.html          # Admin dashboard
│   ├── login.html          # Initial login page
│   ├── station.html        # Kiosk view (station_console)
│   ├── station_setup.html  # Pick station for device
│   └── others…
└── /static/
    ├── css/style.css       # Styling
    └── js/
        ├── index.js        # Student grid logic
        └── admin.js        # Live updates & admin actions
```

---

## ⚙️ Setup Instructions

### 1. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the App

```bash
python main.py
```

Visit `http://localhost:5000` to log in as a student or admin.

---

## 🧪 Testing Tips

### Student

* Log in as a student → check if assigned room is open
* Request pass and return
* Visit `/station_setup` to configure kiosk → test log IN/OUT

### Admin

* Log in via `/admin_login`
* Approve/deny requests
* Use override tool
* View recent pass history
* Export reports

---

## ✅ Recent Upgrades (v0.5)

* 🔁 Unified pending/active view with live auto-refresh
* 🕒 Full pass lifecycle with IN/OUT timestamps and durations
* 🧠 Room return auto-checkin and completion tracking
* 📃 Final CSV export: ID, Name, Room Out/In, Station In/Out, Time
* 📝 Notes persist through refresh
* 📊 Weekly reports track override usage + long passes

---

## 📜 License

MIT — Use, adapt, and deploy freely in your school or district.
