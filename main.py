# main.py – unified status flows and fixes while preserving original routes
from flask import render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, date, timedelta, timezone
from src import create_app
from src.models import db, Student, Pass, AuditLog
import json, os, time
from src.utils import get_active_rooms
from threading import Thread

app = create_app()

# Unified status constants
STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"

# Load config
def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
    except:
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

# Cleanup inactive rooms thread
def cleanup_inactive_rooms(interval=60, timeout=120):
    heartbeat_path = 'data/station_heartbeat.json'
    active_path = 'data/active_rooms.json'

    while True:
        now = datetime.now(timezone.utc)
        try:
            with open(heartbeat_path, 'r') as f:
                beats = json.load(f)
        except:
            beats = {}

        try:
            with open(active_path, 'r') as f:
                active = set(json.load(f))
        except:
            active = set()

        to_remove = set()
        for station, stamp in beats.items():
            try:
                last_seen = datetime.fromisoformat(stamp)
                if (now - last_seen).total_seconds() > timeout:
                    to_remove.add(station)
            except:
                continue

        if to_remove:
            updated = active - to_remove
            with open(active_path, 'w') as f:
                json.dump(sorted(updated), f)

        time.sleep(interval)

# Start cleanup thread
Thread(target=cleanup_inactive_rooms, daemon=True).start()

# ------------------------------------------------------------------
# LOGIN ROUTE
# ------------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
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
# REDIRECT TO CURRENT ROOM
# ------------------------------------------------------------------
@app.route('/index')
def index():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student = db.session.get(Student, session['student_id'])
    current_period = get_current_period()
    current_room = student.schedule.get(current_period)
    if current_room not in get_active_rooms():
        return render_template("login.html", error=f"Room {current_room} is not accepting passes right now.")
    return redirect(url_for('passroom_view', room=current_room))

# ------------------------------------------------------------------
# ROOM VIEW FOR STUDENTS
# ------------------------------------------------------------------
@app.route('/passroom/<room>', methods=['GET', 'POST'])
def passroom_view(room):
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student = db.session.get(Student, session['student_id'])
    current_period = get_current_period()
    scheduled_room = student.schedule.get(current_period)

    if scheduled_room != room:
        return render_template('login.html', error=f"You are not scheduled for Room {room} this period.")

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
        return redirect(url_for('passroom_view', room=room))

    message = session.pop('passroom_message', '')

    passes = Pass.query.filter_by(
        date=datetime.now().date(),
        period=current_period,
        station=room
    ).filter(Pass.checkin_time == None).order_by(Pass.checkout_time).all()

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

# ------------------------------------------------------------------
# DEPRECATED
# ------------------------------------------------------------------
@app.route('/check', methods=['POST'])
def deprecated_check():
    return jsonify({'message': 'This endpoint is no longer in use.'}), 410

# ------------------------------------------------------------------
# DEBUG
# ------------------------------------------------------------------
@app.route('/debug_period')
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

@app.route('/debug_rooms')
def debug_rooms():
    return jsonify(sorted(list(get_active_rooms())))

@app.route('/debug/active_rooms')
def debug_active_rooms():
    from src.utils import get_active_rooms
    return jsonify(sorted(list(get_active_rooms())))


@app.route('/debug_students')
def debug_students():
    students = Student.query.all()
    return jsonify([{ "id": s.id, "type": str(type(s.id)) } for s in students])

# ------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=config.get("debug_mode", True))
