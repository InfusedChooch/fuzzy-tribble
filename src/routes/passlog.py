from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for
from datetime import datetime, date
from src.models import db, Student, Pass, PassLog
import json

passlog_bp = Blueprint('passlog', __name__)

# ------------------------------------------------------------------
# Central status names — keep in sync with admin.py & main.py
# ------------------------------------------------------------------
STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
    except Exception:
        return {}

config = load_config()


def get_current_period():
    """Return the period key (e.g. "3") that matches the current time."""
    now = datetime.now().time()
    for period, times in config.get("period_schedule", {}).items():
        start = datetime.strptime(times["start"], "%H:%M").time()
        end = datetime.strptime(times["end"], "%H:%M").time()
        if start <= now <= end:
            return period
    return "N/A"

# ------------------------------------------------------------------
# Station *log* endpoint — adds IN / OUT events to an existing pass
# ------------------------------------------------------------------
@passlog_bp.route('/station_log', methods=['POST'])
def station_log():
    if 'station_id' not in session:
        return jsonify({'message': 'Station not logged in'}), 403

    student_id = request.form.get('student_id', '').strip()
    event_type = request.form.get('event_type', 'in')
    if event_type not in {"in", "out"}:
        return jsonify({'message': 'Invalid event type'}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({'message': 'Invalid student ID'})

    active_pass = Pass.query.filter_by(student_id=student.id, checkin_time=None).first()
    if not active_pass:
        return jsonify({'message': 'No active pass found'})

    # Auto‑close if returning to origin room *and* logging an "in" event
    if event_type == "in" and session['station_id'] == active_pass.station:
        active_pass.checkin_time = datetime.now().time()
        delta = datetime.combine(date.today(), active_pass.checkin_time) - \
                datetime.combine(date.today(), active_pass.checkout_time)
        active_pass.total_pass_time = int(delta.total_seconds())
        active_pass.status = STATUS_RETURNED
        db.session.commit()
        return jsonify({'message': f'Pass ended at {session["station_id"]} for {student.name}.'})

    # Otherwise just log the station event
    new_log = PassLog(
        pass_id   = active_pass.id,
        station   = session['station_id'],
        timestamp = datetime.utcnow(),
        event_type= event_type
    )
    db.session.add(new_log)
    db.session.commit()

    return jsonify({'message': f'{event_type.title()} logged at {session["station_id"]} for {student.name}.'})

# ------------------------------------------------------------------
# Self‑service *station console* (kiosk view used by hallway stations)
# ------------------------------------------------------------------
@passlog_bp.route('/station_console', methods=['GET', 'POST'])
def station_console():
    """Kiosk UI that lets a student scan in/out at Bathroom, Nurse, etc."""
    if 'station_id' not in session:
        return redirect(url_for('passlog.station_setup'))

    station = session['station_id']
    special_stations = set(config.get('stations', ["Bathroom", "Nurse", "Library", "Office"]))
    current_period = get_current_period()
    message = ""

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        student = Student.query.get(student_id)

        if not student:
            message = "Invalid student ID"
        else:
            # Student must already have an ACTIVE pass that originated from their room
            existing = Pass.query.filter_by(student_id=student.id, checkin_time=None).first()
            if not existing:
                message = "You don’t have an active pass to use this station."
            else:
                # Toggle between OUT and IN events
                last_event_out = PassLog.query.filter_by(pass_id=existing.id, event_type="out").order_by(PassLog.timestamp.desc()).first()
                if last_event_out and (datetime.utcnow() - last_event_out.timestamp).total_seconds() < 30:
                    # Prevent duplicate scans in quick succession
                    message = "Swipe already recorded."
                else:
                    new_event_type = "in" if station == existing.station else "out"
                    session['event_type'] = new_event_type  # for debug / testing
                    new_log = PassLog(
                        pass_id   = existing.id,
                        station   = station,
                        timestamp = datetime.utcnow(),
                        event_type= new_event_type
                    )
                    db.session.add(new_log)

                    # Auto‑close if returning to origin room
                    if new_event_type == "in" and station == existing.station:
                        existing.checkin_time = datetime.now().time()
                        delta = datetime.combine(date.today(), existing.checkin_time) - \
                                datetime.combine(date.today(), existing.checkout_time)
                        existing.total_pass_time = int(delta.total_seconds())
                        existing.status = STATUS_RETURNED
                    else:
                        existing.status = STATUS_ACTIVE  # stays active while travelling

                    db.session.commit()
                    message = f"{student.name} {new_event_type} recorded at {station}."

    # Display passes from this room currently out
    passes = Pass.query.filter_by(checkin_time=None).all()
    out = []
    for p in passes:
        stu = p.student
        if not stu:
            continue
        # Only show passes whose destination is _this_ station (room) OR this station is the origin room
        if p.station == station or station in special_stations:
            out.append({
                "student_name": stu.name,
                "status": p.status,
                "room": p.station
            })

    return render_template('station.html', station=station, passes=out, message=message)

# ------------------------------------------------------------------
# Station selector (set station_id in session for this browser)
# ------------------------------------------------------------------
@passlog_bp.route('/station_setup', methods=['GET', 'POST'])
def station_setup():
    rooms = sorted({str(r) for r in range(100, 131)})  # e.g. 100‑130 plus config stations
    rooms.extend(config.get('stations', []))
    rooms = sorted(set(rooms))

    if request.method == 'POST':
        selected = request.form.get('station')
        session['station_id'] = selected
        return redirect(url_for('passlog.station_console'))

    return render_template('station_setup.html', rooms=rooms)

# ------------------------------------------------------------------
# Public view for hallway TVs etc.
# ------------------------------------------------------------------
@passlog_bp.route('/station_view/<station_name>')
def popout_station_view(station_name):
    session['station_id'] = station_name
    return redirect(url_for('passlog.station_console'))
