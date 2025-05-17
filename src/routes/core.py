# src/routes/core.py

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, date
from src.models import db, Student, Pass
from src.utils import get_active_rooms, log_audit
import json, os

core_bp = Blueprint('core', __name__)
ping_bp = Blueprint('ping', __name__)

STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"

# Load config
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

# Period helper
def get_current_period():
    now = datetime.now().time()
    for period, times in config.get("period_schedule", {}).items():
        start = datetime.strptime(times["start"], "%H:%M").time()
        end   = datetime.strptime(times["end"], "%H:%M").time()
        if start <= now <= end:
            return str(period)
    return "N/A"

#Audit Log
def log_audit(student_id, reason):
    from src.models import db, AuditLog
    from datetime import datetime
    log = AuditLog(student_id=student_id, reason=reason, time=datetime.now())
    db.session.add(log)
    db.session.commit()

@core_bp.route('/index')
def index():
    if 'student_id' not in session:
        return redirect(url_for('core.login'))

    student = db.session.get(Student, session['student_id'])
    current_period = get_current_period()
    current_room = student.schedule.get(current_period)

    # Optional debug statements
    #print("DEBUG - Period:", current_period)
    #print("DEBUG - 1Room from schedule:", repr(current_room))
    #print("DEBUG - Active rooms:", get_active_rooms())

    if not current_room or current_room.strip() not in get_active_rooms():
        return render_template("login.html", error=f"Room {current_room} is not accepting passes right now.")

    return redirect(url_for('core.passroom_view', room=current_room.strip()))


@core_bp.route('/passroom/<room>', methods=['GET', 'POST'])
def passroom_view(room):
    if 'student_id' not in session:
        return redirect(url_for('core.login'))

    student = db.session.get(Student, session['student_id'])
    current_period = get_current_period()
    scheduled_room = student.schedule.get(current_period)

    if scheduled_room != room:
        return render_template('login.html', error=f"You are not scheduled for Room {room} this period.")
    log_audit(student.id, f"Attempted to access inactive room: {room}")
    if room not in get_active_rooms():
        return render_template('login.html', error=f"Room {room} is not active right now.")

    if request.method == 'POST':
        student_id_form = request.form.get('student_id', '').strip()
        if student_id_form != student.id:
            session['passroom_message'] = "That ID doesn't match your login."
        else:
            existing = Pass.query.filter_by(student_id=student.id, checkin_time=None).first()
            if existing:
                if existing.status == STATUS_ACTIVE:
                    existing.status = STATUS_PENDING_RETURN
                    db.session.commit()
                    session['passroom_message'] = "Return request submitted."
                else:
                    session['passroom_message'] = "You already have a pending pass."
            else:
                new_pass = Pass(
                    student_id=student.id,
                    date=datetime.now().date(),
                    period=current_period,
                    station=room,
                    checkout_time=datetime.now().time(),
                    status=STATUS_PENDING_START
                )
                db.session.add(new_pass)
                db.session.commit()
                session['passroom_message'] = "Pass request submitted."
        return redirect(url_for('core.passroom_view', room=room))

    message = session.pop('passroom_message', '')

    passes = Pass.query.filter_by(
        date=datetime.now().date(),
        period=current_period,
        station=room
    ).filter(
        Pass.checkin_time == None,
        Pass.is_override == False  # 🔁 Ignore override passes for display limit
    ).order_by(Pass.checkout_time).all()

    display_passes = [{
        "student_name": p.student.name if p.student else None,
        "status": p.status
    } for p in passes]

    passes_available = config.get("passes_available", 3)
    while len(display_passes) < passes_available:
        display_passes.append({"student_name": None, "status": "free"})

    return render_template(
        "index.html",
        room=room,
        current_period=current_period,
        school_name=config.get("school_name", "TJMS"),
        passes=display_passes,
        message=message,
        session=session
    )

@core_bp.route('/check', methods=['POST'])
def deprecated_check():
    return jsonify({'message': 'This endpoint is no longer in use.'}), 410

@core_bp.route('/debug_period')
def debug_period():
    now = datetime.now().time()
    matches = []
    for period, times in config.get("period_schedule", {}).items():
        start = datetime.strptime(times["start"], "%H:%M").time()
        end = datetime.strptime(times["end"], "%H:%M").time()
        matches.append({
            "period": period,
            "start": str(start),
            "end": str(end),
            "now": str(now),
            "match": start <= now <= end
        })
    return jsonify(matches)

@core_bp.route('/debug_rooms')
def debug_rooms():
    return jsonify(sorted(list(get_active_rooms())))

@core_bp.route('/debug/active_rooms')
def debug_active_rooms():
    return jsonify(sorted(list(get_active_rooms())))

@core_bp.route('/debug_students')
def debug_students():
    students = Student.query.all()
    return jsonify([{ "id": s.id, "type": str(type(s.id)) } for s in students])

@core_bp.route("/debug_audit")
def debug_audit():
    from src.utils import log_audit
    log_audit("999", "Simulated audit for testing")
    return "✅ Audit triggered", 200


@ping_bp.route('/ping')
def ping():
    return "pong", 200
