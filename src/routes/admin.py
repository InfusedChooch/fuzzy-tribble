# src/routes/admin.py
# ------------------------------------------------------------------
# Admin‑side routes: live dashboard, weekly summary, archive & exports
# ------------------------------------------------------------------

from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, Response
)
from datetime import datetime, date
from src.models import db, Pass, Student, AuditLog
from src.utils import activate_room, get_active_rooms, log_audit
import json, csv, io

admin_bp = Blueprint('admin', __name__)

STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"

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

# =================================================================
@admin_bp.route('/admin')
def admin_view():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    open_passes = Pass.query.filter(
        Pass.status.in_([STATUS_ACTIVE, STATUS_PENDING_START, STATUS_PENDING_RETURN]),
        Pass.checkin_at == None
    ).all()

    pending_starts, pending_returns, active = [], [], []

    for p in open_passes:
        rec = {
            "id": p.id,
            "student": p.student.name,
            "student_id": p.student.student_id,
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
        logs = sorted(p.logs, key=lambda l: l.timestamp)
        station_in = next((l for l in logs if l.event == "in"), None)
        station_out = next((l for l in logs if l.event == "out"), None)

        total_time = (p.checkin_at - p.checkout_at).total_seconds() if p.checkin_at and p.checkout_at else 0
        station_time = (station_out.timestamp - station_in.timestamp).total_seconds() if station_in and station_out else 0
        hallway_time = total_time - station_time if station_time else total_time

        recent_returns_data.append({
            "id": p.student.student_id,
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

    return render_template(
        "admin.html",
        pending_starts=pending_starts,
        pending_returns=pending_returns,
        active=active,
        recent_returns=recent_returns_data,
        active_rooms=get_active_rooms(),
        admin_station=session.get("station_id", ""),
        config_stations=config.get("stations", [])
    )

# =================================================================
@admin_bp.route('/admin_passes')
def admin_passes():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    open_passes = Pass.query.filter(
        Pass.checkin_at == None,
        Pass.status == STATUS_ACTIVE
    ).all()

    now = datetime.now()
    response = []

    for p in open_passes:
        logs = sorted(p.logs, key=lambda l: l.timestamp)
        station_out = next((l for l in logs if l.event == "out"), None)
        station_in  = next((l for l in reversed(logs) if l.event == "in"), None)

        elapsed_secs = int((now - p.checkout_at).total_seconds()) if p.checkout_at else 0
        station_time = int((station_out.timestamp - station_in.timestamp).total_seconds()) if station_in and station_out else 0
        hallway_time = elapsed_secs - station_time if station_time else elapsed_secs

        response.append({
            "pass_id": p.id,
            "student_name": p.student.name,
            "student_id": p.student.student_id,
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

# (⚠️ PATCHING REMAINING ROUTES NEXT — let me know if you'd like the full patched file or just the rest)


# =================================================================
# MANUALLY CREATE / OVERRIDE PASS

@admin_bp.route('/admin_create_pass', methods=['POST'])
def admin_create_pass():
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    student_id = data.get('student_id')
    period = data.get('period')
    room_out = data.get('room', '').strip() or "OVERRIDE"

    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({'message': 'Student not found.'})

    if Pass.query.filter_by(student_id=student.student_id, checkin_at=None).first():
        return jsonify({'message': 'Student already has an active pass.'})

    override_pass = Pass(
        student_id    = student.student_id,
        date          = date.today(),
        period        = period,
        checkout_at   = datetime.now(),
        room_out      = room_out,
        is_override   = True,
        status        = STATUS_ACTIVE
    )
    db.session.add(override_pass)
    db.session.commit()
    log_audit(student.student_id, f"Admin created override pass for Room {room_out}")
    return jsonify({'message': f'Override pass created for {student.name} leaving {room_out}.'})

# =================================================================
@admin_bp.route('/admin/approve/<int:pass_id>', methods=['POST'])
def admin_approve_pass(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = db.session.get(Pass, pass_id)
    if not p or p.status != STATUS_PENDING_START:
        return jsonify({'message': 'Pass not pending or not found.'})

    p.status = STATUS_ACTIVE
    p.checkout_at = datetime.now()
    db.session.commit()
    log_audit(p.student_id, f"Admin approved pass {pass_id}")
    return jsonify({'message': f'Pass {pass_id} approved.'})

@admin_bp.route('/admin/reject/<int:pass_id>', methods=['POST'])
def admin_reject_pass(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = db.session.get(Pass, pass_id)
    if not p or p.status != STATUS_PENDING_START:
        return jsonify({'message': 'Pass not pending or not found.'})

    db.session.delete(p)
    db.session.commit()
    log_audit(p.student_id, f"Admin rejected pass {pass_id}")
    return jsonify({'message': f'Pass {pass_id} rejected.'})

# =================================================================
@admin_bp.route('/admin_checkin/<int:pass_id>', methods=['POST'])
def admin_checkin(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = db.session.get(Pass, pass_id)
    if not p or p.checkin_at:
        return jsonify({'message': 'Invalid or already returned pass'})

    now = datetime.now()
    p.checkin_at = now
    p.status = STATUS_RETURNED

    if p.checkout_at:
        delta = now - p.checkout_at
        p.total_pass_time = int(delta.total_seconds())

    db.session.commit()
    log_audit(p.student_id, f"Admin marked pass {pass_id} as returned")
    return jsonify({'message': f'Pass {pass_id} marked as returned.'})

# =================================================================
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

# =================================================================
@admin_bp.route('/admin_weekly_summary')
def admin_weekly_summary():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    report_data = []

    for stu in Student.query.all():
        records = Pass.query.filter_by(student_id=stu.student_id).all()
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
            "student_name"      : stu.name,
            "student_id"        : stu.student_id,
            "weekly_report"     : weekly,
            "passes_over_5_min" : over_5,
            "passes_over_10_min": over_10,
            "used_override"     : "✔️" if used_override else ""
        })

    return render_template('admin_weekly_summary.html', report_data=report_data)

# =================================================================
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

    pending = Pass.query.filter(
        Pass.status.in_([STATUS_PENDING_START, STATUS_PENDING_RETURN]),
        Pass.checkin_at == None
    ).all()

    results = []
    for p in pending:
        results.append({
            "pass_id": p.id,
            "student_id": p.student_id,
            "student_name": p.student.name if p.student else "—",
            "room": p.origin_room,
            "time": p.checkout_at.strftime("%H:%M:%S") if p.checkout_at else "—",
            "status": p.status
        })

    return jsonify(results)

# =================================================================
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
    

    
