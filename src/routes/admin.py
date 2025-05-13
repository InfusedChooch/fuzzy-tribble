from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app, Response
from datetime import datetime, date, time
from src.models import db, Pass, Student, AuditLog
import json, csv, io
from src.utils import activate_room, get_active_rooms

admin_bp = Blueprint('admin', __name__)

# --- Pass‑status constants (single source of truth) ---------------
STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"
# ------------------------------------------------------------------

def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
    except Exception:
        return {}

config = load_config()
active_rooms = get_active_rooms()

# ------------------------------------------------------------------
# MAIN ADMIN DASHBOARD
# ------------------------------------------------------------------
@admin_bp.route('/admin')
def admin_view():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    open_passes = Pass.query.filter(Pass.checkin_time == None).all()

    pending_starts, pending_returns, active = [], [], []
    for p in open_passes:
        record = {
            "id": p.id,
            "student": p.student.name,
            "student_id": p.student.id,
            "period": p.period,
            "room": p.station,
            "station": p.station,
            "checkout": p.checkout_time.strftime("%H:%M:%S") if p.checkout_time else "—",
            "status": p.status
        }
        if p.status == STATUS_PENDING_START:
            pending_starts.append(record)
        elif p.status == STATUS_PENDING_RETURN:
            pending_returns.append(record)
        elif p.status == STATUS_ACTIVE:
            active.append(record)

    return render_template(
        "admin.html",
        active_rooms=active_rooms,
        pending_starts=pending_starts,
        pending_returns=pending_returns,
        active=active
    )

# ------------------------------------------------------------------
# JSON feed consumed by admin.js (includes running timer)
# ------------------------------------------------------------------
@admin_bp.route('/admin_passes')
def admin_passes():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    open_passes = Pass.query.filter(Pass.checkin_time == None).all()
    response = []
    now = datetime.now()

    for p in open_passes:
        elapsed = None
        if p.checkout_time:
            delta = datetime.combine(date.today(), now.time()) - \
                    datetime.combine(date.today(), p.checkout_time)
            elapsed = f"{delta.seconds // 60}m {delta.seconds % 60}s"

        response.append({
            'id'           : p.id,
            'student_name' : p.student.name,
            'student_id'   : p.student.id,
            'period'       : p.period,
            'room'         : p.station,
            'station'      : p.station,
            'checkout'     : p.checkout_time.strftime("%H:%M:%S") if p.checkout_time else "—",
            'elapsed'      : elapsed,
            'status'       : p.status,
        })

    return jsonify(response)

# ------------------------------------------------------------------
# MANUALLY CREATE (OVERRIDE) PASS
# ------------------------------------------------------------------
@admin_bp.route('/admin_create_pass', methods=['POST'])
def admin_create_pass():
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    student_id = data.get('student_id')
    student = Student.query.get(student_id)

    if not student:
        return jsonify({'message': 'Student not found.'})

    existing_pass = Pass.query.filter_by(student_id=student.id, checkin_time=None).first()
    if existing_pass:
        return jsonify({'message': 'Student already has an active pass.'})

    override_pass = Pass(
        student_id=student.id,
        date=date.today(),
        period=data.get('period'),
        checkout_time=datetime.now().time(),
        station=data.get('room').strip(),
        is_override=True,
        status=STATUS_ACTIVE,
    )
    db.session.add(override_pass)
    db.session.commit()
    return jsonify({'message': f'Override pass created for {student.name}.'})

# ------------------------------------------------------------------
# ONE‑CLICK APPROVE / REJECT (PENDING‑START)
# ------------------------------------------------------------------
@admin_bp.route('/admin/approve/<int:pass_id>', methods=['POST'])
def admin_approve_pass(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = Pass.query.get(pass_id)
    if not p or p.status != STATUS_PENDING_START:
        return jsonify({'message': 'Pass not pending or not found.'})
    p.status = STATUS_ACTIVE
    db.session.commit()
    return jsonify({'message': f'Pass {pass_id} approved.'})

@admin_bp.route('/admin/reject/<int:pass_id>', methods=['POST'])
def admin_reject_pass(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = Pass.query.get(pass_id)
    if not p or p.status != STATUS_PENDING_START:
        return jsonify({'message': 'Pass not pending or not found.'})
    db.session.delete(p)
    db.session.commit()
    return jsonify({'message': f'Pass {pass_id} rejected.'})

# ------------------------------------------------------------------
# QUICK END PASS (ADMIN OVERRIDE)
# ------------------------------------------------------------------
@admin_bp.route('/admin_checkin/<int:pass_id>', methods=['POST'])
def admin_checkin(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = Pass.query.get(pass_id)
    if not p or p.checkin_time:
        return jsonify({'message': 'Pass already ended or not found.'})

    p.checkin_time = datetime.now().time()
    delta = datetime.combine(datetime.today(), p.checkin_time) - \
            datetime.combine(datetime.today(), p.checkout_time)
    p.total_pass_time = int(delta.total_seconds())
    p.status = STATUS_RETURNED
    db.session.commit()
    return jsonify({'message': f'Pass {p.id} checked in.'})

# ------------------------------------------------------------------
# ADD / UPDATE NOTE ON MOST RECENT OPEN PASS
# ------------------------------------------------------------------
@admin_bp.route('/admin_add_note/<student_id>', methods=['POST'])
def admin_add_note(student_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    note = data.get('note')

    p = Pass.query.filter(
        Pass.student_id == student_id,
        Pass.checkin_time == None,
        Pass.status.in_([STATUS_ACTIVE, STATUS_PENDING_RETURN])
    ).order_by(Pass.checkout_time.desc()).first()

    if p:
        p.note = note
        db.session.commit()
        return jsonify({'message': 'Note saved.'})

    return jsonify({'message': 'No active pass found.'})

# ------------------------------------------------------------------
# OPTIONAL — SET THIS CONSOLE’S STATION LABEL
# ------------------------------------------------------------------
@admin_bp.route('/admin_station', methods=['GET', 'POST'])
def set_station():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    if request.method == 'POST':
        station = request.form.get('station').strip()
        session['admin_station'] = station
        activate_room(station)        # mark this room “active” for live map
        return redirect(url_for('admin.admin_view'))

    return render_template('admin_station_setup.html')


# ------------------------------------------------------------------
# Pass History
# ------------------------------------------------------------------
@admin_bp.route('/admin_pass_history')
def admin_pass_history():
    passes = Pass.query.order_by(Pass.date.desc(), Pass.checkout_time.desc()).limit(100).all()
    return render_template('admin_pass_history.html', passes=passes)


# ------------------------------------------------------------------
# FINAL CSV EXPORT (ONLY COMPLETED PASSES)
# ------------------------------------------------------------------
@admin_bp.route('/admin_export_final')
def export_final_report():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Period", "RoomOUT+TimeOUT",
                     "Station+TimeIN", "Station+TimeOUT", "RoomOUT+TimeIN"])

    passes = Pass.query.filter(Pass.status == STATUS_RETURNED).all()

    for p in passes:
        student = p.student
        room_out_time = f"{p.station} @ {p.checkout_time.strftime('%H:%M:%S')}" if p.room else "—"

        # Pull first “in” and first “out” station logs if you’re tracking those
        logs = sorted(p.logs, key=lambda l: l.timestamp)
        station_in_log  = next((l for l in logs if l.event_type == "in"),  None)
        station_out_log = next((l for l in logs if l.event_type == "out"), None)

        station_in  = f"{station_in_log.station} @ {station_in_log.timestamp.strftime('%H:%M:%S')}" if station_in_log else "—"
        station_out = f"{station_out_log.station} @ {station_out_log.timestamp.strftime('%H:%M:%S')}" if station_out_log else "—"

        room_in_time = "—"
        if p.checkin_time:
            room_in_time = f"{p.station} @ {p.checkin_time.strftime('%H:%M:%S')}"

        writer.writerow([
            student.id,
            p.date.strftime('%Y-%m-%d'),
            p.period,
            room_out_time,
            station_in,
            station_out,
            room_in_time
        ])

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=final_pass_report.csv'}
    )

# ------------------------------------------------------------------
# RED‑DOT COUNTER FOR NAV BAR
# ------------------------------------------------------------------
@admin_bp.route('/admin_pending_count')
def admin_pending_count():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    start_count  = Pass.query.filter_by(status=STATUS_PENDING_START).count()
    return_count = Pass.query.filter_by(status=STATUS_PENDING_RETURN).count()

    return jsonify({
        'pending_start': start_count,
        'pending_return': return_count
    })
