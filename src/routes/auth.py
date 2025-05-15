# routes/auth.py  🔄  fully patched
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, current_app
)
from datetime import timedelta
import json
from src.utils import deactivate_room                     # keeps hallway map tidy

auth_bp = Blueprint('auth', __name__)

# ------------------------------------------------------------------
# Config helper (shared pattern across routes)
# ------------------------------------------------------------------
def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
    except Exception:
        return {}

config = load_config()
SESSION_TIMEOUT_MIN = config.get("session_timeout_minutes", 60)

# ------------------------------------------------------------------
# Global session‑timeout hook
# ------------------------------------------------------------------
@auth_bp.before_app_request
def enforce_session_timeout():
    """
    Every request marks the session as 'permanent' so Flask’s built‑in
    expiry mechanism kicks in. The lifetime is pulled from config.json.
    """
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
    from flask import render_template, request, redirect, url_for, session
    import json
    from datetime import datetime

    # Load config
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
        return redirect(url_for('passroom_view', room=current_room))

    return render_template('login.html')


# ------------------------------------------------------------------
# Admin login
# ------------------------------------------------------------------
@auth_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """
    Simple username‑password gate for the admin interface.
    •  Case‑insensitive username check
    •  Optional redirect if already logged in
    """
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
    """
    Ends the current admin session and, if this console had been
    registered as an active room/station, removes it from the list
    so students can’t keep sending passes there.
    """
    room = session.pop('admin_station', None)
    if room:
        deactivate_room(room)                             # tidy active‑room list

    session.pop('logged_in', None)
    session.pop('role', None)
    return redirect(url_for('auth.admin_login'))
