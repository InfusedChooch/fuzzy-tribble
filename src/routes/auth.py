# routes/auth.py

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, current_app
)
from datetime import timedelta
import json
from src.utils import deactivate_room                     # keeps hallway map tidy
from src.models import db, AuditLog
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# ------------------------------------------------------------------
# Central audit logger
# ------------------------------------------------------------------
def log_audit(student_id, reason):
    log = AuditLog(student_id=student_id, reason=reason, time=datetime.now())
    db.session.add(log)
    db.session.commit()

# ------------------------------------------------------------------
# Config helper
# ------------------------------------------------------------------
def load_config():
    try:
        with open('data/config.json') as f:
            config = json.load(f)
            active = config.get("active_schedule", "regular")
            config["period_schedule"] = config.get("schedule_variants", {}).get(active, {})
            return config
    except Exception:
        return {}

config = load_config()
SESSION_TIMEOUT_MIN = config.get("session_timeout_minutes", 60)

# ------------------------------------------------------------------
# Global session‑timeout hook
# ------------------------------------------------------------------
@auth_bp.before_app_request
def enforce_session_timeout():
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(
        minutes=SESSION_TIMEOUT_MIN
    )

# ------------------------------------------------------------------
# Login
# ------------------------------------------------------------------
@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    from src.models import db, Student
    from src.utils import get_active_rooms
    import json
    from datetime import datetime

    try:
        with open('data/config.json') as f:
            config = json.load(f)
    except:
        config = {}

    def get_current_period():
        now = datetime.now().time()
        for period, times in config.get("period_schedule", {}).items():
            start = datetime.strptime(times["start"], "%H:%M").time()
            end = datetime.strptime(times["end"], "%H:%M").time()
            if start <= now <= end:
                return str(period)
        return "N/A"

    if session.get("logged_in"):
        return redirect(url_for('admin.admin_view'))

    if request.method == 'POST':
        user = request.form['user'].strip()
        admin_username = config.get("admin_username", "admin")

        if user.lower() == admin_username.lower():
            return redirect(url_for('auth.admin_login'))

        student = db.session.get(Student, user)
        if not student:
            return render_template('login.html', error="ID not recognized.")

        session['student_id'] = str(student.id)
        session['role'] = 'student'

        current_period = get_current_period()
        current_room = student.schedule.get(current_period)
        if current_room not in get_active_rooms():
            return render_template('login.html', error=f"Room {current_room} is not accepting passes right now.")
        return redirect(url_for('core.passroom_view', room=current_room))

    return render_template('login.html')


# ------------------------------------------------------------------
# Admin login
# ------------------------------------------------------------------
@auth_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if session.get("logged_in"):
        return redirect(url_for('admin.admin_view'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()

        if (
            username == config.get('admin_username', '').lower()
            and password == config.get('admin_password')
        ):
            session['logged_in'] = True
            session['role'] = 'admin'
            return redirect(url_for('admin.set_station'))

        log_audit(username, "Failed admin login attempt.")
        return render_template(
            'admin_login.html',
            error='Incorrect username or password.'
        )

    return render_template('admin_login.html')


# ------------------------------------------------------------------
# Admin logout
# ------------------------------------------------------------------
@auth_bp.route('/admin_logout')
def admin_logout():
    room = session.pop('admin_station', None)
    if room:
        deactivate_room(room)

    session.pop('logged_in', None)
    session.pop('role', None)
    return redirect(url_for('auth.admin_login'))
