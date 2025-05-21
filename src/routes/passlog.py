# src/routes/passlog.py

from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for
from datetime import datetime
import json, os

from src.models import db, User, Pass, PassEvent
from src.utils import (
    activate_room, deactivate_room, get_current_periods,
    load_config, log_audit, get_active_rooms, is_station
)
from src.services import pass_manager

passlog_bp = Blueprint('passlog', __name__)

STATUS_PENDING_START  = pass_manager.STATUS_PENDING_START
STATUS_PENDING_RETURN = pass_manager.STATUS_PENDING_RETURN
STATUS_ACTIVE         = pass_manager.STATUS_ACTIVE
STATUS_RETURNED       = pass_manager.STATUS_RETURNED

HEARTBEAT_FILE = os.path.join('data', 'station_heartbeat.json')
config = load_config()

# ------------------------------------------------------------------
@passlog_bp.route('/station_console', methods=['GET', 'POST'])
def station_console():
    if 'station_id' not in session:
        return "⛔ Station not set. Please launch from the admin panel.", 403

    station = session['station_id']
    activate_room(station)

    current_period = get_current_periods()
    message = ""

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        student = db.session.get(User, student_id)

        if not student or student.role != "student":
            message = "Unauthorized user or invalid ID"
        else:
            active_pass = Pass.query.filter_by(student_id=student.id, checkin_at=None).first()

            if active_pass:
                if active_pass.status == STATUS_PENDING_START:
                    message = "Your pass is waiting for approval."
                else:
                    logs_for_station = [l for l in active_pass.events if l.station == station]
                    num_in = sum(1 for l in logs_for_station if l.event == "in")
                    num_out = sum(1 for l in logs_for_station if l.event == "out")
                    new_event = "in" if num_in <= num_out else "out"

                    last_event = db.session.query(PassEvent).filter_by(pass_id=active_pass.id)\
                        .order_by(PassEvent.timestamp.desc()).first()

                    if (
                        last_event and
                        last_event.station == station and
                        last_event.event == "out" and
                        new_event == "in" and
                        (datetime.utcnow() - last_event.timestamp).total_seconds() < 30
                    ):
                        message = "Already swiped out - wait a moment before re-entering."
                    else:
                        # ✅ Only set room_in if it's a real station, not a classroom
                        if (
                            new_event == "in" and
                            not active_pass.room_in and
                            is_station(station, config=config) and
                            station != active_pass.origin_room
                        ):
                            active_pass.room_in = station
                            db.session.commit()

                        pass_manager.record_pass_event(active_pass, station, new_event)

                        # 🛠️ Clear room_in if swiping out of a real return station
                        if new_event == "out" and active_pass.room_in == station:
                            active_pass.room_in = None
                            db.session.commit()

                        # ✅ Return to origin room, regardless of prior OUT logs
                        if new_event == "in" and station == active_pass.origin_room:
                            if not active_pass.room_in:
                                active_pass.room_in = station
                            pass_manager.return_pass(active_pass, station=station)
                            message = f"{student.name}'s pass ended at {station}."
                        else:
                            active_pass.status = STATUS_ACTIVE
                            db.session.commit()
                            message = f"{student.name} {new_event} recorded at {station}."
            else:
                # 🟢 Self-checkout logic for classrooms
                if not is_station(station):
                    max_passes = config.get("passes_available", 2)
                    periods = get_current_periods()
                    active_count = Pass.query.filter(
                        Pass.date == datetime.now().date(),
                        Pass.period.in_(periods),
                        Pass.origin_room == station,
                        Pass.checkin_at == None
                    ).count()


                    if active_count >= max_passes:
                        message = f"Max passes reached for Room {station}."
                    else:
                        new_pass = Pass(
                            student_id=student.id,
                            date=datetime.now().date(),
                            period=current_period,
                            checkout_at=datetime.now(),
                            origin_room=station,
                            status=STATUS_ACTIVE
                        )
                        db.session.add(new_pass)
                        db.session.commit()
                        log_audit(student.id, f"Checked out from classroom {station}")
                        message = f"{student.name} checked out from Room {station}."
                else:
                    message = "You don’t have an active pass to use this station."

    return render_template('station.html', station=station, passes=[], message=message)

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
@passlog_bp.route('/station_view/<station_name>')
def popout_station_view(station_name):
    session['station_id'] = station_name
    return redirect(url_for('passlog.station_console'))
