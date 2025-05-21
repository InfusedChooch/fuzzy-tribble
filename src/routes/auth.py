# src/routes/auth.py

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, current_app
)
from datetime import timedelta
import json

from src.utils import (
    deactivate_room,
    get_active_rooms,
    get_current_period,
    get_room,
    log_audit,
    load_config  # ✅ moved from local to utils
)

from src.models import db, AuditLog, Student

auth_bp = Blueprint('auth', __name__)

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
            log_audit("admin", f"Admin {username} logged in successfully")
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
    return redirect(url_for('auth.login'))
