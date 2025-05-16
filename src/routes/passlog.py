from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for
from datetime import datetime, date
from src.models import db, Student, Pass, PassLog
from src.utils import activate_room, deactivate_room
import json, os

passlog_bp = Blueprint('passlog', __name__)

# ------------------------------------------------------------------
# Central status names — keep in sync with admin.py & main.py
# ------------------------------------------------------------------
STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"

HEARTBEAT_FILE = os.path.join('data', 'station_heartbeat.json')

# ------------------------------------------------------------------
# Config + Period helpers
# ------------------------------------------------------------------
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

def get_current_period():
    now = datetime.now().time()
    for period, times in config.get("period_schedule", {}).items():
        start = datetime.strptime(times["start"], "%H:%M").time()
        end = datetime.strptime(times["end"], "%H:%M").time()
        if start <= now <= end:
            return period
    return "N/A"

# ------------------------------------------------------------------
# Self‑service *station console* (kiosk view used by hallway stations)
# ------------------------------------------------------------------
@passlog_bp.route('/station_console', methods=['GET', 'POST'])
def station_console():
    if 'station_id' not in session:
        return "⛔ Station not set. Please launch from the admin panel.", 403

    station = session['station_id']

    # ✅ Always activate when console is opened (removed gatecheck)
    activate_room(station)

    special_stations = set(config.get('stations', ["Bathroom", "Nurse", "Library", "Office"]))
    current_period = get_current_period()
    message = ""

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        student = db.session.get(Student, student_id)

        if not student:
            message = "Invalid student ID"
        else:
            active_pass = Pass.query.filter_by(student_id=student.id, checkin_time=None).first()

            if active_pass:
                if active_pass.status == STATUS_PENDING_START:
                    message = "Your pass is waiting for approval."
                else:
                    logs_for_this_station = [l for l in active_pass.logs if l.station == station]
                    num_in = sum(1 for l in logs_for_this_station if l.event_type == "in")
                    num_out = sum(1 for l in logs_for_this_station if l.event_type == "out")
                    new_event_type = "in" if num_in <= num_out else "out"

                    last_event = PassLog.query.filter_by(pass_id=active_pass.id)\
                        .order_by(PassLog.timestamp.desc()).first()
                    if (
                        last_event and
                        last_event.event_type == "out" and
                        new_event_type == "out" and
                        (datetime.utcnow() - last_event.timestamp).total_seconds() < 30
                    ):
                        message = "Swipe already recorded."
                    else:
                        # ✅ Instant end for override/no travel
                        if (
                            new_event_type == "in" and
                            station.isdigit() and
                            station == active_pass.station and
                            not active_pass.logs
                        ):
                            active_pass.checkin_time = datetime.now().time()
                            delta = datetime.combine(date.today(), active_pass.checkin_time) - \
                                    datetime.combine(date.today(), active_pass.checkout_time)
                            active_pass.total_pass_time = int(delta.total_seconds())
                            active_pass.status = STATUS_RETURNED
                            db.session.commit()
                            message = f"{student.name}'s override pass ended at room {station}."
                        else:
                            new_log = PassLog(
                                pass_id=active_pass.id,
                                station=station,
                                timestamp=datetime.utcnow(),
                                event_type=new_event_type
                            )
                            db.session.add(new_log)

                            if (
                                new_event_type == "in" and
                                station == active_pass.station and
                                any(l.event_type == "out" for l in active_pass.logs)
                            ):
                                active_pass.checkin_time = datetime.now().time()
                                delta = datetime.combine(date.today(), active_pass.checkin_time) - \
                                        datetime.combine(date.today(), active_pass.checkout_time)
                                active_pass.total_pass_time = int(delta.total_seconds())

                                from src.routes.core import log_audit
                                log_audit(student.id, f"Pass ended by student at correct station {station}")

                                active_pass.status = STATUS_RETURNED
                            else:
                                active_pass.status = STATUS_ACTIVE

                            db.session.commit()
                            message = f"{student.name} {new_event_type} recorded at {station}."
            else:
                if station.isdigit():
                    # ✅ Enforce max passes rule
                    max_passes = config.get("passes_available", 2)
                    active_count = Pass.query.filter_by(
                        date=datetime.now().date(),
                        period=current_period,
                        station=station
                    ).filter(Pass.checkin_time == None).count()

                    if active_count >= max_passes:
                        message = f"Max passes reached for Room {station}."
                    else:
                        new_pass = Pass(
                            student_id=student.id,
                            date=datetime.now().date(),
                            period=current_period,
                            checkout_time=datetime.now().time(),
                            station=station,
                            status=STATUS_ACTIVE
                        )
                        db.session.add(new_pass)
                        db.session.commit()
                        message = f"{student.name} checked out from Room {station}."
                else:
                    message = "You don’t have an active pass to use this station."

    return render_template('station.html', station=station, passes=[], message=message)


# ------------------------------------------------------------------
# Heartbeat updater (station pings every 30s)
# ------------------------------------------------------------------
@passlog_bp.route('/station_heartbeat', methods=['POST'])
def station_heartbeat():
    if 'station_id' not in session:
        return '', 403

    station = session['station_id']
    now = datetime.utcnow().isoformat()

    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            beats = json.load(f)
    except:
        beats = {}

    beats[station] = now

    with open(HEARTBEAT_FILE, 'w') as f:
        json.dump(beats, f)

    return '', 204

# ------------------------------------------------------------------
# Close station manually (admin password)
# ------------------------------------------------------------------
@passlog_bp.route('/close_station', methods=['POST'])
def close_station():
    if 'station_id' not in session:
        return jsonify({'message': 'Station not set.'}), 403

    data = request.get_json()
    password = data.get('password', '')
    config_password = config.get('admin_password')

    if password != config_password:
        return jsonify({'message': 'Incorrect password.'}), 401

    station = session['station_id']
    deactivate_room(station)
    session.pop('station_id', None)
    return redirect(url_for('auth.login'))


# ------------------------------------------------------------------
# Public view for hallway TVs etc.
# ------------------------------------------------------------------
@passlog_bp.route('/station_view/<station_name>')
def popout_station_view(station_name):
    session['station_id'] = station_name
    return redirect(url_for('passlog.station_console'))

# ------------------------------------------------------------------
# Dropdown for setting station (station_setup.html)
# ------------------------------------------------------------------
#@passlog_bp.route('/station_setup', methods=['GET', 'POST'])
#def station_setup():
#    rooms = sorted({str(r) for r in range(100, 281)})
#    rooms.extend(config.get('stations', []))
#   rooms = sorted(set(rooms))
#
#    if request.method == 'POST':
#        selected = request.form.get('station')
#        session['station_id'] = selected
#        return redirect(url_for('passlog.station_console'))
#
 #   return render_template('station_setup.html', rooms=rooms)
