# routes/auth.py

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, current_app
)
from datetime import timedelta, datetime
import json
from sqlalchemy import select
from src.utils import deactivate_room, get_active_rooms, log_audit
from src.models import db, AuditLog, Student, StudentPeriod

auth_bp = Blueprint('auth', __name__)

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
# Helper: get current period
# ------------------------------------------------------------------
def get_current_period():
    now = datetime.now().time()
    for period, times in config.get("period_schedule", {}).items():
        start = datetime.strptime(times["start"], "%H:%M").time()
        end = datetime.strptime(times["end"], "%H:%M").time()
        if start <= now <= end:
            return str(period)
    return "N/A"

# ------------------------------------------------------------------
# Helper: get assigned room from StudentPeriod
# ------------------------------------------------------------------
def get_room(student_id, period):
    sp = db.session.scalar(select(StudentPeriod).where(
        StudentPeriod.student_id == student_id,
        StudentPeriod.period == period
    ))
    return sp.room if sp else None

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

        session['student_id'] = str(student.student_id)
        session['role'] = 'student'

        current_period = get_current_period()
        current_room = get_room(student.student_id, current_period)

        if not current_room or current_room.strip() not in get_active_rooms():
            log_audit(student.student_id, f"Attempted to access inactive room: {current_room}")
            return render_template('login.html', error=f"Room {current_room} is not accepting passes right now.")

        return redirect(url_for('core.passroom_view', room=current_room.strip()))

    return render_template('login.html')

# ------------------------------------------------------------------
# Admin login (PATCHED)
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
            log_audit("admin",f"Admin {username} logged in successfully")
            return redirect(url_for('admin.admin_view'))

        log_audit("admin", f"Failed admin login by {username}")
        return render_template('admin_login.html', error='Incorrect username or password.')

    return render_template('admin_login.html')

# ------------------------------------------------------------------
# Admin logout
# ------------------------------------------------------------------
@auth_bp.route('/admin_logout')
def admin_logout():
    room = session.pop('admin_station', None)
    if room:
        deactivate_room(room)

    if session.get("logged_in"):
        log_audit("admin", "Admin logout")

    session.pop('logged_in', None)
    session.pop('role', None)
    return redirect(url_for('auth.admin_login'))
