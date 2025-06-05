# src/routes/core.py
# Student pass request flow, slot views, and debugging endpoints

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, date
from sqlalchemy import select

from src.models import db, User, Pass, StudentPeriod
from src.utils import (
    load_config,
    get_current_periods,
    get_room,
    get_active_rooms,
    log_audit,
    is_station
)

core_bp = Blueprint('core', __name__)
ping_bp = Blueprint('ping', __name__)

STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"

config = load_config()


# ─────────────────────────────────────────────────────────────────────────────
# Route: Student Landing Page
# ─────────────────────────────────────────────────────────────────────────────
@core_bp.route('/student')
def student_landing():
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))

    student_id = session['student_id']
    student_name = session.get('name', 'Student')
    periods = get_current_periods()
    current_period = periods[0] if periods else "0"
    room = get_room(student_id, current_period)

    return render_template(
        'landing.html',
        student_name=student_name,
        student_room=room,
        current_period=current_period
    )

# ─────────────────────────────────────────────────────────────────────────────
# Route: Student Pass History View
# ─────────────────────────────────────────────────────────────────────────────
@core_bp.route('/my_passes')
def my_passes():
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))

    student_id = session['student_id']

    passes = Pass.query.filter_by(
        student_id=student_id,
        status="returned"
    ).order_by(Pass.date.desc(), Pass.checkout_at.desc()).limit(50).all()

    rows = []
    for p in passes:
        logs = sorted(p.events, key=lambda l: l.timestamp)
        station_in = next((l for l in logs if l.event == "in"), None)
        station_out = next((l for l in logs if l.event == "out"), None)

        total_time = (p.checkin_at - p.checkout_at).total_seconds() if p.checkin_at and p.checkout_at else 0
        station_time = (station_out.timestamp - station_in.timestamp).total_seconds() if station_in and station_out else 0
        hallway_time = total_time - station_time if station_time else total_time

        rows.append({
            "date": p.date.strftime('%Y-%m-%d'),
            "period": p.period or "-",
            "room_out": p.room_out or "-",
            "station": f"{station_in.station} → {station_out.station}" if station_in and station_out else "-",
            "hallway": f"{int(hallway_time//60)}m {int(hallway_time%60)}s" if hallway_time else "-",
            "station_time": f"{int(station_time//60)}m {int(station_time%60)}s" if station_time else "-",
            "total": f"{int(total_time//60)}m {int(total_time%60)}s" if total_time else "-"
        })

    return render_template('my_passes.html', passes=rows)


# ─────────────────────────────────────────────────────────────────────────────
# Route: Passroom Entry Point (student → room)
# ─────────────────────────────────────────────────────────────────────────────
@core_bp.route('/passroom/<room>', methods=['GET', 'POST'])
def passroom_view(room):
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))

    student = db.session.get(User, session['student_id'])
    if not student or student.role != "student":
        return redirect(url_for('auth.login'))

    periods = get_current_periods()
    current_period = periods[0] if periods else "0"
    scheduled_room = get_room(student.id, current_period)

    if scheduled_room != room or room not in get_active_rooms():
        log_audit(student.id, f"Denied room access to {room}")
        session['error_msg'] = f"Room {room} is not accepting passes right now."
        return redirect(url_for('core.student_landing'))

    if request.method == 'POST':
        student_id_form = request.form.get('student_id', '').strip()
        if student_id_form != student.id:
            session['passroom_message'] = "That ID doesn't match your login."
        else:
            existing = Pass.query.filter_by(student_id=student.id, checkin_at=None).first()
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
                    origin_room=room,
                    room_in=room,
                    checkout_at=datetime.now(),
                    status=STATUS_PENDING_START
                )
                db.session.add(new_pass)
                db.session.commit()
                session['passroom_message'] = "Pass request submitted."

        return redirect(url_for('core.passroom_view', room=room))

    message = session.pop('passroom_message', '')

    passes = Pass.query.filter(
        Pass.date == datetime.now().date(),
        Pass.period.in_(periods),
        Pass.origin_room == room,
        Pass.checkin_at == None,
        Pass.is_override == False
    ).order_by(Pass.checkout_at).all()

    display_passes = []
    for p in passes:
        student_name = "-"
        if p.student_id:
            s = db.session.get(User, p.student_id)
            if s:
                student_name = s.name
        display_passes.append({
            "student_name": student_name,
            "status": p.status
        })

    while len(display_passes) < config.get("passes_available", 3):
        display_passes.append({"student_name": None, "status": "free"})

    return render_template(
        "passreq.html",
        room=room,
        current_period=current_period,
        school_name=config.get("school_name", "TJMS"),
        passes=display_passes,
        message=message,
        session=session
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route: JSON View of Active Slots (used on student dashboard)
# ─────────────────────────────────────────────────────────────────────────────
@core_bp.route('/student_slot_view')
def student_slot_view():
    station_slots = config.get("station_slots", 3)
    class_slots = config.get("passes_available", 2)

    student_id = session.get("student_id")
    periods = get_current_periods()
    current_period = periods[0] if periods else "0"
    current_room = get_room(student_id, current_period)
    active_rooms = get_active_rooms()
    today = date.today()

    data = []
    for room in sorted(active_rooms):
        if not is_station(room, config) and room != current_room:
            continue

        slots = station_slots if is_station(room, config) else class_slots
        taken = Pass.query.filter_by(room_in=room, status="active", date=today).count()
        pending = Pass.query.filter_by(room_in=room, status="pending_start", date=today).count()
        used = taken + pending
        free = max(slots - used, 0)

        data.append({
            "room": room,
            "free": free,
            "taken": taken,
            "pending": pending,
            "active": True,
            "type": "station" if is_station(room, config) else "classroom",
            "is_current": (room == current_room)
        })

    return jsonify(data)


# ─────────────────────────────────────────────────────────────────────────────
# Debug Endpoints
# ─────────────────────────────────────────────────────────────────────────────
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
@core_bp.route('/debug/active_rooms')
def debug_rooms():
    return jsonify(sorted(list(get_active_rooms())))

@core_bp.route('/debug_students')
def debug_students():
    students = User.query.all()
    return jsonify([{ "id": s.id, "type": str(type(s.id)) } for s in students])

@core_bp.route("/debug_audit")
def debug_audit():
    log_audit("999", "Simulated audit for testing")
    return "✅ Audit triggered", 200

@core_bp.route('/debug_session')
def debug_session():
    if not session:
        return "<p>No session data found.</p>"
    return "<h2>Session Data</h2><ul>" + "".join(
        f"<li><strong>{k}</strong>: {v}</li>" for k, v in session.items()
    ) + "</ul>"


# ─────────────────────────────────────────────────────────────────────────────
# Health Check Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@ping_bp.route('/ping')
def ping():
    return "pong", 200

