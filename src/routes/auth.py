# src/routes/auth.py
# Handles login, logout, session enforcement, and user password change

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, current_app, jsonify
)
from datetime import timedelta
import json
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func
from sqlalchemy.orm import class_mapper

from src.models import db, AuditLog, User, TeacherSchedule
from src.utils import (
    deactivate_room,
    get_active_rooms,
    get_current_periods,
    get_room,
    log_audit,
    load_config
)

auth_bp = Blueprint('auth', __name__)
config = load_config()
SESSION_TIMEOUT_MIN = config.get("session_timeout_minutes", 60)


# ─────────────────────────────────────────────────────────────────────────────
# Global Session Timeout Enforcer
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.before_app_request
def enforce_session_timeout():
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(
        minutes=SESSION_TIMEOUT_MIN
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route: Login (Admin, Student, Teacher)
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    session.clear()  # Clear any residual session data

    if session.get("logged_in"):
        return redirect(url_for('admin.admin_view'))

    if request.method == 'POST':
        user_input = request.form.get('user', '').strip()
        password = request.form.get('password', '').strip()
        admin_username = config.get("admin_username", "admin")

        # Admin login case
        if user_input.lower() == admin_username.lower():
            if password == config.get("admin_password"):
                session.clear()
                session['logged_in'] = True
                session['role'] = 'admin'
                session['name'] = 'Admin'
                log_audit("admin", f"Admin {user_input} logged in successfully")
                return redirect(url_for('admin.admin_view'))
            else:
                log_audit("admin", f"Failed admin login by {user_input}")
                return render_template('login.html', error="Incorrect admin password.")

        # User login case
        user = None
        if "@" in user_input:
            user = User.query.filter(func.lower(User.email) == user_input.lower()).first()
        else:
            user = db.session.get(User, user_input)

        if not user:
            return render_template('login.html', error="ID or Email not recognized.")
        if not check_password_hash(user.password, password):
            return render_template('login.html', error="Incorrect password.")

        # Valid login — create session
        session.clear()
        session['name'] = user.name
        session['role'] = user.role

        if user.role == "student":
            session['student_id'] = str(user.id)
            return redirect(url_for('core.student_landing'))

        elif user.role == "teacher":
            session['teacher_id'] = str(user.id)

            # Ensure teacher schedule exists
            schedule = TeacherSchedule.query.filter_by(teacher_id=user.id).first()
            if not schedule:
                schedule = TeacherSchedule(teacher_id=user.id)
                db.session.add(schedule)
                db.session.commit()

            # Pull list of non-empty room assignments
            period_cols = [c.key for c in class_mapper(TeacherSchedule).columns if c.key.startswith("period_")]
            rooms = set()
            for col in period_cols:
                val = getattr(schedule, col)
                if val:
                    rooms.add(val.strip())

            session['teacher_rooms'] = list(rooms)
            session['logged_in'] = True
            log_audit(user.id, "Teacher logged in successfully")
            return redirect(url_for('admin.admin_view'))

    # GET fallback or failed POST
    return render_template('login.html')


# ─────────────────────────────────────────────────────────────────────────────
# Route: Student/Teacher Password Change
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/change_password', methods=['POST'])
def change_user_password():
    user_id = session.get('student_id') or session.get('teacher_id')
    if not user_id:
        return jsonify({ "success": False, "message": "Not logged in" }), 403

    user = db.session.get(User, user_id)
    data = request.get_json()
    current = data.get("current_password", "")
    new = data.get("new_password", "")
    confirm = data.get("confirm_password", "")

    if not check_password_hash(user.password, current):
        return jsonify({ "success": False, "message": "Incorrect current password" })

    if new != confirm:
        return jsonify({ "success": False, "message": "Passwords do not match" })

    user.password = generate_password_hash(new)
    db.session.commit()
    return jsonify({ "success": True, "message": "Password changed successfully" })


# ─────────────────────────────────────────────────────────────────────────────
# Route: Logout (Admin, Teacher, Student)
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    role = session.get("role")
    user_id = session.get("student_id") or session.get("teacher_id") or "unknown"

    if role == "admin":
        room = session.pop('admin_station', None)
        if room:
            deactivate_room(room)
        log_audit("admin", "Admin logout")
    else:
        safe_role = role.capitalize() if role else "User"
        log_audit(user_id, f"{safe_role} logout")

    session.clear()
    return redirect(url_for('auth.login'))

