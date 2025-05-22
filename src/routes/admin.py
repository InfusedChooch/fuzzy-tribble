# src/routes/admin.py
# Admin‑side routes: dashboard views, pass management, room controls, and reports

from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, Response
)
from datetime import datetime, date
import json, csv, io

from src.models import db, Pass, User, StudentPeriod
from src.utils import (
    activate_room, deactivate_room, get_active_rooms, get_current_periods,
    log_audit, is_station
)
from src.services import pass_manager

admin_bp = Blueprint('admin', __name__)

STATUS_PENDING_START  = pass_manager.STATUS_PENDING_START
STATUS_PENDING_RETURN = pass_manager.STATUS_PENDING_RETURN
STATUS_ACTIVE         = pass_manager.STATUS_ACTIVE
STATUS_RETURNED       = pass_manager.STATUS_RETURNED

# ─────────────────────────────────────────────────────────────────────────────
# Config Load/Save
# ─────────────────────────────────────────────────────────────────────────────
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

def save_config(cfg: dict):
    with open('data/config.json', 'w') as f:
        json.dump(cfg, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard View
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin')
def admin_view():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    open_passes = Pass.query.filter(
        Pass.status.in_([STATUS_ACTIVE, STATUS_PENDING_START, STATUS_PENDING_RETURN]),
        Pass.checkin_at == None
    ).all()

    pending_starts, pending_returns, active = [], [], []
    for p in open_passes:
        rec = {
            "id": p.id,
            "student": p.student.name,
            "student_id": p.student.id,
            "room": p.room_out,
            "time_out": p.checkout_at.strftime('%H:%M:%S') if p.checkout_at else '-',
            "note": p.note or "",
            "override": "✔️" if p.is_override else "",
            "status": p.status
        }
        if p.status == STATUS_PENDING_START:
            pending_starts.append(rec)
        elif p.status == STATUS_PENDING_RETURN:
            pending_returns.append(rec)
        else:
            active.append(rec)

    recent_returns = Pass.query.filter_by(status=STATUS_RETURNED).order_by(
        Pass.date.desc(), Pass.checkout_at.desc()
    ).limit(5).all()

    recent_returns_data = []
    for p in recent_returns:
        logs = sorted(p.events, key=lambda l: l.timestamp)
        station_in = next((l for l in logs if l.event == "in"), None)
        station_out = next((l for l in logs if l.event == "out"), None)

        total_time = (p.checkin_at - p.checkout_at).total_seconds() if p.checkin_at and p.checkout_at else 0
        station_time = (station_out.timestamp - station_in.timestamp).total_seconds() if station_in and station_out else 0
        hallway_time = total_time - station_time if station_time else total_time

        recent_returns_data.append({
            "id": p.student.id,
            "student_name": p.student.name,
            "date": p.date.strftime('%Y-%m-%d'),
            "period": p.period,
            "room_out": f"{p.room_out} @ {p.checkout_at.strftime('%H:%M:%S')}" if p.checkout_at else "-",
            "station_in": f"{station_in.station} @ {station_in.timestamp.strftime('%H:%M:%S')}" if station_in else "-",
            "station_out": f"{station_out.station} @ {station_out.timestamp.strftime('%H:%M:%S')}" if station_out else "-",
            "room_in": f"{p.room_in} @ {p.checkin_at.strftime('%H:%M:%S')}" if p.checkin_at else "-",
            "elapsed": f"{int(total_time//60)}m {int(total_time%60)}s" if total_time else "-",
            "hallway_time": f"{int(hallway_time//60)}m {int(hallway_time%60)}s" if hallway_time else "-",
            "station_time": f"{int(station_time//60)}m {int(station_time%60)}s" if station_time else "-",
            "note": p.note or "",
            "override": "✔️" if p.is_override else ""
        })

    needs_setup = False
    if session.get("role") == "teacher":
        from src.models import TeacherSchedule
        sched = TeacherSchedule.query.filter_by(teacher_id=session.get("teacher_id")).first()
        if not sched or not any(getattr(sched, f"period_{i}", None) for i in range(13)):
            needs_setup = True

    return render_template(
        "admin.html",
        pending_starts=pending_starts,
        pending_returns=pending_returns,
        active=active,
        recent_returns=recent_returns_data,
        active_rooms=get_active_rooms(),
        admin_station=session.get("station_id", ""),
        config_stations=config.get("stations", []),
        needs_schedule_setup=needs_setup
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route Set: Pass Management (approve, create, checkin, notes)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin_passes')
def admin_passes():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    query = Pass.query.filter(Pass.checkin_at == None, Pass.status == STATUS_ACTIVE)
    if session.get("role") == "teacher":
        allowed_rooms = session.get("teacher_rooms", [])
        query = query.filter(Pass.origin_room.in_(allowed_rooms))

    open_passes = query.all()
    now = datetime.now()
    response = []

    for p in open_passes:
        logs = sorted(p.events, key=lambda l: l.timestamp)
        station_out = next((l for l in logs if l.event == "out"), None)
        station_in  = next((l for l in reversed(logs) if l.event == "in"), None)
        elapsed_secs = int((now - p.checkout_at).total_seconds()) if p.checkout_at else 0
        station_time = int((station_out.timestamp - station_in.timestamp).total_seconds()) if station_in and station_out else 0
        hallway_time = elapsed_secs - station_time if station_time else elapsed_secs

        response.append({
            "pass_id": p.id,
            "student_name": p.student.name,
            "student_id": p.student.id,
            "date": p.date.strftime('%Y-%m-%d'),
            "period": p.period,
            "room_time": f"{p.room_out} @ {p.checkout_at.strftime('%H:%M:%S')}" if p.checkout_at else "-",
            "station_out": f"{station_out.station} @ {station_out.timestamp.strftime('%H:%M:%S')}" if station_out else "-",
            "station_in": f"{station_in.station} @ {station_in.timestamp.strftime('%H:%M:%S')}" if station_in else "-",
            "room_in": f"{p.room_in} @ {p.checkin_at.strftime('%H:%M:%S')}" if p.checkin_at else "-",
            "elapsed": f"{elapsed_secs//60}m {elapsed_secs%60}s",
            "hallway_time": f"{hallway_time//60}m {hallway_time%60}s" if hallway_time else "-",
            "station_time": f"{station_time//60}m {station_time%60}s" if station_time else "-",
            "note": p.note or "",
            "is_override": p.is_override,
            "status": p.status
        })

    return jsonify(response)

# ─────────────────────────────────────────────────────────────────────────────
# Route: Create Override Pass (Admin/Teacher)
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_create_pass', methods=['POST'])
def admin_create_pass():
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    student_id = data.get('student_id')
    period = data.get('period')
    room_out = data.get('room', '').strip() or "OVERRIDE"

    student = db.session.get(User, student_id)
    if not student:
        return jsonify({'message': 'User not found.'})

    if Pass.query.filter_by(student_id=student.id, checkin_at=None).first():
        return jsonify({'message': 'User already has an active pass.'})

    room_in = None
    if session.get("role") == "teacher":
        teacher_id = session.get("teacher_id", session.get("user_id"))
        if not period:
            current_periods = get_current_periods()
            period = current_periods[0] if current_periods else "0"

        from src.models import TeacherSchedule
        ts = TeacherSchedule.query.filter_by(teacher_id=teacher_id).first()
        if ts:
            safe_period = f"period_{period.replace('/', '_')}"
            room_in = getattr(ts, safe_period, None)

    if not room_in and room_out.isdigit():
        room_in = room_out

    new_pass = Pass(
        student_id=student.id,
        date=datetime.now().date(),
        period=period,
        origin_room=room_out,
        room_in=room_in,
        checkout_at=datetime.now(),
        is_override=True,
        status=STATUS_PENDING_START
    )
    db.session.add(new_pass)
    db.session.commit()
    log_audit("admin", f"Created override pass for {student.name} from {room_out} returning to {room_in or 'None'}")
    return jsonify({'message': f'Override pass created for {student.name} leaving {room_out}.'})


# ─────────────────────────────────────────────────────────────────────────────
# Route: Approve or Reject a Pass
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin/approve/<int:pass_id>', methods=['POST'])
def admin_approve_pass(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    success = pass_manager.approve_pass(pass_id)
    return jsonify({'message': f'Pass {pass_id} approved.' if success else 'Pass not pending or not found.'})


@admin_bp.route('/admin/reject/<int:pass_id>', methods=['POST'])
def admin_reject_pass(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    success = pass_manager.reject_pass(pass_id)
    return jsonify({'message': f'Pass {pass_id} rejected.' if success else 'Pass not pending or not found.'})


# ─────────────────────────────────────────────────────────────────────────────
# Route: Manual Checkin
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_checkin/<int:pass_id>', methods=['POST'])
def admin_checkin(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = db.session.get(Pass, pass_id)
    if not p or p.checkin_at:
        return jsonify({'message': 'Invalid or already returned pass'})

    if not p.room_in:
        p.room_in = p.origin_room

    success = pass_manager.return_pass(p)
    return jsonify({'message': f'Pass {pass_id} marked as returned.' if success else 'Return failed'})


# ─────────────────────────────────────────────────────────────────────────────
# Route: Add Note to Active Pass
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_add_note/<student_id>', methods=['POST'])
def admin_add_note(student_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    note = request.get_json().get('note', '').strip()
    p = Pass.query.filter(
        Pass.student_id == student_id,
        Pass.checkin_at == None,
        Pass.status.in_([STATUS_ACTIVE, STATUS_PENDING_RETURN])
    ).order_by(Pass.checkout_at.desc()).first()

    if not p:
        return jsonify({'message': 'No active pass found.'})

    p.note = note
    db.session.commit()
    log_audit(student_id, "Note updated on active pass.")
    return jsonify({'message': 'Note saved.'})


# ─────────────────────────────────────────────────────────────────────────────
# Route: Weekly Summary Table (HTML)
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_weekly_summary', methods=['GET'])
def admin_weekly_summary():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    selected_student = request.args.get("student")
    selected_room = request.args.get("room")
    all_students = User.query.filter_by(role="student").order_by(User.name).all()
    all_rooms = sorted(set(p.origin_room for p in Pass.query.all() if p.origin_room))

    # Filter by student
    if selected_student:
        students = [User.query.get(selected_student)]
    else:
        students = all_students

    report_data = []

    for stu in students:
        records = Pass.query.filter_by(student_id=stu.id).all()
        if selected_room:
            records = [r for r in records if r.origin_room == selected_room]

        day_totals = {d: 0 for d in DAYS}
        over_5 = sum(1 for r in records if (r.total_pass_time or 0) > 300)
        over_10 = sum(1 for r in records if (r.total_pass_time or 0) > 600)
        used_override = any(r.is_override for r in records)

        for r in records:
            dname = r.date.strftime('%A')
            if dname in day_totals:
                day_totals[dname] += r.total_pass_time or 0

        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in DAYS)
        report_data.append({
            "student_name": stu.name,
            "student_id": stu.id,
            "weekly_report": weekly,
            "passes_over_5_min": over_5,
            "passes_over_10_min": over_10,
            "used_override": "✔️" if used_override else ""
        })

    return render_template(
        'admin_weekly_summary.html',
        report_data=report_data,
        all_students=all_students,
        all_rooms=all_rooms,
        selected_student=selected_student,
        selected_room=selected_room
    )

# ─────────────────────────────────────────────────────────────────────────────
# Route: Room Manager UI Page
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_rooms_ui')
def admin_rooms_ui():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    return render_template('admin_rooms.html')


# ─────────────────────────────────────────────────────────────────────────────
# Route: Admin Room API (GET/POST/PATCH/DELETE)
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_rooms', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def admin_rooms():
    if not session.get('logged_in'):
        return jsonify({'error': 'unauthorized'}), 403

    config = load_config()
    passes_available = config.get("passes_available", 3)
    default_station_slots = config.get("station_slots", 3)
    config.setdefault("rooms", [])
    config.setdefault("stations", [])

    role = session.get("role")
    teacher_rooms = session.get("teacher_rooms", [])

    # GET: Return all rooms with slot info
    if request.method == 'GET':
        configured_rooms = set(config["rooms"])
        configured_stations = set(config["stations"])
        active_room_set = get_active_rooms()
        room_set = configured_rooms | configured_stations | active_room_set
        periods = get_current_periods()
        today = datetime.now().date()

        data = []
        for room in sorted(room_set):
            is_active = room in active_room_set
            a_station = is_station(room, config=config)

            if a_station:
                pending = 0
                taken = Pass.query.filter(Pass.room_in == room, Pass.status == STATUS_ACTIVE).count()
                free = max(default_station_slots - taken, 0)
            else:
                pending = Pass.query.filter(
                    Pass.origin_room == room,
                    Pass.period.in_(periods),
                    Pass.date == today,
                    Pass.status == STATUS_PENDING_START
                ).count()
                taken = Pass.query.filter(
                    Pass.origin_room == room,
                    Pass.period.in_(periods),
                    Pass.date == today,
                    Pass.status == STATUS_ACTIVE
                ).count()
                free = max(passes_available - pending - taken, 0)

            checked_in = Pass.query.filter_by(room_in=room, status=STATUS_ACTIVE).count()

            data.append({
                "room": room,
                "type": "station" if a_station else "room",
                "active": is_active,
                "free": free,
                "pending": pending,
                "taken": taken,
                "checked_in": checked_in
            })

        return jsonify(data)

    # All other methods require a valid room
    payload = request.get_json(force=True)
    room = payload.get("room", "").strip()
    if not room:
        return jsonify({'error': 'missing room'}), 400

    if role == "teacher":
        if not is_station(room, config=config) and room not in teacher_rooms:
            return jsonify({'error': 'Not authorized for this room'}), 403

    if request.method == 'POST':
        activate_room(room)
        if room.isdigit():
            if room not in config["rooms"]:
                config["rooms"].append(room)
        else:
            if room not in config["stations"]:
                config["stations"].append(room)
        save_config(config)
        log_audit("admin", f"Activated room {room}")
        return '', 204

    if request.method == 'PATCH':
        if payload.get("active"):
            activate_room(room)
            log_audit("admin", f"Activated room {room}")
        else:
            deactivate_room(room)
            log_audit("admin", f"Deactivated room {room}")
        return '', 204

    if request.method == 'DELETE':
        if role != "admin":
            return jsonify({'error': 'Only admins can delete rooms'}), 403
        deactivate_room(room)
        config["rooms"] = [r for r in config["rooms"] if r != room]
        config["stations"] = [r for r in config["stations"] if r != room]
        save_config(config)
        log_audit("admin", f"Removed room {room}")
        return '', 204


# ─────────────────────────────────────────────────────────────────────────────
# Route: Rename Room
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_rooms/rename', methods=['POST'])
def rename_room():
    data = request.get_json(force=True)
    old = data.get('old')
    new = data.get('new')

    if not old or not new:
        return jsonify({'error': 'Missing room name'}), 400

    from src.models import ActiveRoom
    rec = ActiveRoom.query.get(old)
    if rec:
        db.session.delete(rec)
        db.session.commit()
        db.session.add(ActiveRoom(room=new.strip()))
        db.session.commit()
        log_audit("admin", f'Renamed room "{old}" → "{new}"')
        return '', 204
    return jsonify({'error': 'Room not found'}), 404


# ─────────────────────────────────────────────────────────────────────────────
# Route: Room Stats Summary
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_rooms/stats/<room>')
def room_stats(room):
    today = datetime.now().date()
    passes_today = Pass.query.filter_by(origin_room=room, date=today).all()
    stats = {
        "room": room,
        "count_today": len(passes_today),
        "active": sum(1 for p in passes_today if p.status in {
            STATUS_ACTIVE, STATUS_PENDING_START, STATUS_PENDING_RETURN
        })
    }
    return jsonify(stats)


# ─────────────────────────────────────────────────────────────────────────────
# Route: Pending Pass Count + Detail for Admin Panel
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_pending_count')
def admin_pending_count():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    start_count  = Pass.query.filter_by(status=STATUS_PENDING_START).count()
    return_count = Pass.query.filter_by(status=STATUS_PENDING_RETURN).count()

    return jsonify({
        "pending_start" : start_count,
        "pending_return": return_count
    })


@admin_bp.route('/admin_pending_passes')
def admin_pending_passes():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    query = Pass.query.filter(
        Pass.status.in_([STATUS_PENDING_START, STATUS_PENDING_RETURN]),
        Pass.checkin_at == None
    )

    if session.get("role") == "teacher":
        allowed_rooms = session.get("teacher_rooms", [])
        query = query.filter(Pass.origin_room.in_(allowed_rooms))

    pending = query.all()

    results = []
    for p in pending:
        results.append({
            "pass_id": p.id,
            "student_id": p.student_id,
            "student_name": p.student.name if p.student else "-",
            "room": p.origin_room,
            "time": p.checkout_at.strftime("%H:%M:%S") if p.checkout_at else "-",
            "status": p.status
        })

    return jsonify(results)


# ─────────────────────────────────────────────────────────────────────────────
# Route: Admin Password Change
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/admin_change_password', methods=['POST'])
def admin_change_password():
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json()
    current = data.get('current_password', '').strip()
    new = data.get('new_password', '').strip()
    confirm = data.get('confirm_password', '').strip()

    try:
        with open('data/config.json', 'r') as f:
            config = json.load(f)

        if current != config.get('admin_password'):
            return jsonify({"success": False, "message": "Current password incorrect."})
        if not new:
            return jsonify({"success": False, "message": "New password cannot be empty."})
        if new != confirm:
            return jsonify({"success": False, "message": "Passwords do not match."})

        config['admin_password'] = new
        with open('data/config.json', 'w') as f:
            json.dump(config, f, indent=2)

        return jsonify({"success": True, "message": "Password changed successfully."})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})


# ─────────────────────────────────────────────────────────────────────────────
# Route: Teacher Schedule Setup
# ─────────────────────────────────────────────────────────────────────────────
@admin_bp.route('/setup_schedule', methods=['POST'])
def setup_schedule():
    if session.get("role") != "teacher":
        return jsonify({"success": False, "message": "Only teachers may edit their schedule."}), 403

    from src.models import TeacherSchedule
    teacher_id = session.get("teacher_id")
    if not teacher_id:
        return jsonify({"success": False, "message": "Missing teacher ID."}), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Invalid data format."}), 400

    schedule = TeacherSchedule.query.filter_by(teacher_id=teacher_id).first()
    if not schedule:
        schedule = TeacherSchedule(teacher_id=teacher_id)
        db.session.add(schedule)

    for key, val in data.items():
        if key.startswith("period_"):
            setattr(schedule, key, val.strip() if val else None)

    db.session.commit()
    log_audit(teacher_id, "Updated their schedule via popup")
    return jsonify({"success": True, "message": "Schedule updated."})


@admin_bp.route('/admin/teacher_schedule')
def get_teacher_schedule():
    if session.get("role") != "teacher":
        return jsonify({"error": "unauthorized"}), 403

    from src.models import TeacherSchedule
    from sqlalchemy.inspection import inspect

    sched = TeacherSchedule.query.filter_by(teacher_id=session["teacher_id"]).first()
    if not sched:
        return jsonify({})

    return jsonify({
        attr.key: getattr(sched, attr.key) or ""
        for attr in inspect(sched).mapper.column_attrs
        if attr.key.startswith("period_")
    })
