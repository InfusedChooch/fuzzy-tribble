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

from src.models import db, AuditLog, User

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
from werkzeug.security import check_password_hash
from sqlalchemy import func

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if session.get("logged_in"):
        return redirect(url_for('admin.admin_view'))

    if request.method == 'POST':
        user_input = request.form.get('user', '').strip()
        password = request.form.get('password', '').strip()
        admin_username = config.get("admin_username", "admin")

        # 🔐 Admin case
        if user_input.lower() == admin_username.lower():
            if password == config.get("admin_password"):
                session['logged_in'] = True
                session['role'] = 'admin'
                log_audit("admin", f"Admin {user_input} logged in successfully")
                return redirect(url_for('admin.admin_view'))
            else:
                log_audit("admin", f"Failed admin login by {user_input}")
                return render_template('login.html', error="Incorrect admin password.")

        # 🔐 User case (email or ID)
        user = None
        if "@" in user_input:
            user = User.query.filter(func.lower(User.email) == user_input.lower()).first()
        else:
            user = db.session.get(User, user_input)

        if not user:
            return render_template('login.html', error="ID or Email not recognized.")

        # ✅ Check password from DB
        if not check_password_hash(user.password, password):
            return render_template('login.html', error="Incorrect password.")

        session['student_id'] = str(user.id)
        session['role'] = user.role

        if user.role == "student":
            current_period = get_current_period()
            current_room = get_room(user.id, current_period)
            if not current_room or current_room.strip() not in get_active_rooms():
                log_audit(user.id, f"Attempted to access inactive room: {current_room}")
                return render_template('login.html', error=f"Room {current_room} is not accepting passes right now.")
            return redirect(url_for('core.passroom_view', room=current_room.strip()))

        # 🔁 Redirect teachers or other roles to future dashboard (placeholder for now)
        return render_template('login.html', error="Non-student login not yet implemented.")

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
