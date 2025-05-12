# Hall Pass Tracker (v0.4)

A Flask-based digital hall pass system for managing student movement in schools. Designed for classroom use with student-facing check-in and admin-facing monitoring and reporting.

---

## 🔧 Features (v0.4)

### ✅ Student Features

* Sign in/out of hall passes using Student ID
* Passes tracked by period with time and duration
* Destinations/stations (e.g., Bathroom, Nurse) logged per visit

### ✅ Admin Features

* Password-protected login
* Create override passes (e.g., send a student out directly)
* View active passes, timer, duration, notes
* See most recent station log timeline per student
* Edit admin password in-panel
* View recent pass history (last 10 returned)
* Weekly reports with time summaries and CSV export
* Add/remove students via CSV upload or individual form
* Set up stations via dropdown on kiosk devices (no password required)

---

## 💡 How Station Logging Works

1. Admin defines list of stations in `config.json`
2. A kiosk (student terminal) visits `/station_setup`
3. The user picks a station (e.g., "Bathroom"), stored in session
4. Students type in ID and log each station visit during their pass
5. Admin sees the timeline of stations visited for each pass

---

## 📂 Folder Structure

```
hall_pass_app/
├── main.py                 # Launches the app
├── config.json             # Admin credentials, station list, period schedule
├── /data/                  # SQLite DB and CSV files
├── /src/
│   ├── __init__.py
│   ├── models.py
│   └── routes/
│       ├── admin.py
│       ├── auth.py
│       ├── students.py
│       ├── report.py
│       └── passlog.py
├── /templates/
│   ├── index.html
│   ├── admin.html
│   ├── admin_login.html
│   ├── students.html
│   ├── admin_report.html
│   ├── station.html
│   └── station_setup.html
├── /static/
│   ├── css/style.css
│   ├── js/index.js
│   └── js/admin.js
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

Visit `http://localhost:5000` to access the student or admin login page.

---

## 🧪 Test Student Workflow

1. Visit `/`
2. Enter a valid student ID
3. Take a pass → log stations using kiosk `/station_console`

---

## 🧪 Test Admin Workflow

1. Visit `/admin_login`
2. Use the credentials in `config.json`
3. Create override passes, view active logs, export reports, etc.

---

## 🚀 Next Steps for v0.5

* [ ] Add live auto-refresh for admin panel
* [ ] Track and report pass frequency by student
* [ ] Audit CSV export
* [ ] Role-based admin access (teacher vs main office)
* [ ] Graphs/charts of weekly data
* [ ] Optional kiosk PIN/QR login (instead of dropdown)
* [ ] Package as `.exe` or Docker container

---

## 📜 License

MIT — modify freely and adapt to your school needs.
