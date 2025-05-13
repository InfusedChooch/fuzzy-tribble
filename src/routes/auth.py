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
