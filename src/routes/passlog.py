from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for
from src.models import db, Student, Pass, PassLog
from datetime import datetime

passlog_bp = Blueprint('passlog', __name__)


@passlog_bp.route('/station_login', methods=['GET', 'POST'])
def station_login():
    if request.method == 'POST':
        station = request.form.get('station')
        password = request.form.get('password')

        # Replace this with a config lookup or per-station auth in future
        if password == 'stationpass':
            session['station_id'] = station
            return jsonify({'message': f'Station "{station}" logged in.'})

        return jsonify({'message': 'Invalid password'}), 401

    # Quick HTML form for login
    return render_template_string('''
        <h2>Station Login</h2>
        <form method="POST">
          <label>Station Name:</label>
          <input name="station" required>
          <label>Password:</label>
          <input type="password" name="password" required>
          <button type="submit">Login</button>
        </form>
    ''')


@passlog_bp.route('/station_log', methods=['POST'])
def station_log():
    if 'station_id' not in session:
        return jsonify({'message': 'Station not logged in'}), 403

    student_id = request.form.get('student_id')
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'message': 'Invalid student ID'})

    active_pass = Pass.query.filter_by(student_id=student.id, checkin_time=None).first()
    if not active_pass:
        return jsonify({'message': 'No active pass found'})

    new_log = PassLog(
        pass_id=active_pass.id,
        station=session['station_id'],
        timestamp=datetime.utcnow()
    )
    db.session.add(new_log)
    db.session.commit()

    return jsonify({'message': f'Visit to {session["station_id"]} logged for {student.name}.'})

@passlog_bp.route('/station_console')
def station_console():
    if 'station_id' not in session:
        return redirect(url_for('passlog.station_login'))

    return render_template('station.html', station_name=session['station_id'])

@passlog_bp.route('/station_setup', methods=['GET', 'POST'])
def station_setup():
    from src.routes.auth import load_config  # or import from wherever you defined it
    config = load_config()
    stations = config.get("stations", [])

    if request.method == 'POST':
        selected = request.form.get('station')
        session['station_id'] = selected
        return redirect(url_for('passlog.station_console'))

    return render_template('station_setup.html', stations=stations)
