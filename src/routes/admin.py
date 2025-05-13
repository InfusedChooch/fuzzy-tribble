# src/routes/admin.py
# ------------------------------------------------------------------
# Admin‑side routes: live dashboard, weekly summary, archive & exports
# ------------------------------------------------------------------
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, Response
)
from datetime import datetime, date
from src.models import db, Pass, Student, AuditLog        # AuditLog kept for future use
import json, csv, io
from src.utils import activate_room, get_active_rooms

admin_bp = Blueprint('admin', __name__)

# ──────────────────────────────────────────────────────────────────
# Unified status constants (keep in sync across the app)
# ──────────────────────────────────────────────────────────────────
STATUS_PENDING_START  = "pending_start"
STATUS_PENDING_RETURN = "pending_return"
STATUS_ACTIVE         = "active"
STATUS_RETURNED       = "returned"

# ──────────────────────────────────────────────────────────────────
# Config helper
# ──────────────────────────────────────────────────────────────────
def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
    except Exception:
        return {}

config       = load_config()
active_rooms = get_active_rooms()
DAYS         = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# =================================================================
# MAIN ADMIN DASHBOARD  – Pending / Active + Weekly Summary
# =================================================================
@admin_bp.route('/admin')
def admin_view():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    open_passes = Pass.query.filter(Pass.checkin_time == None).all()

    pending_starts, pending_returns, active = [], [], []
    for p in open_passes:
        rec = {
            "id"        : p.id,
            "student"   : p.student.name,
            "student_id": p.student.id,
            "period"    : p.period,
            "room"      : p.station,
            "station"   : p.station,
            "time_out"  : p.checkout_time.strftime("%H:%M:%S") if p.checkout_time else "—",
            "note"      : p.note or "",
            "override"  : "✔️" if p.is_override else "",
            "status"    : p.status
        }
        if p.status == STATUS_PENDING_START:
            pending_starts.append(rec)
        elif p.status == STATUS_PENDING_RETURN:
            pending_returns.append(rec)
        else:
            active.append(rec)

    # Weekly report
    report_data = []
    for stu in Student.query.all():
        records       = Pass.query.filter_by(student_id=stu.id).all()
        day_totals    = {d: 0 for d in DAYS}
        over_5        = sum(1 for r in records if (r.total_pass_time or 0) > 300)
        over_10       = sum(1 for r in records if (r.total_pass_time or 0) > 600)
        used_override = any(r.is_override for r in records)

        for r in records:
            dname = r.date.strftime('%A')
            if dname in day_totals:
                day_totals[dname] += r.total_pass_time or 0

        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in DAYS)
        report_data.append({
            "student_name"      : stu.name,
            "student_id"        : stu.id,
            "weekly_report"     : weekly,
            "passes_over_5_min" : over_5,
            "passes_over_10_min": over_10,
            "used_override"     : "✔️" if used_override else ""
        })

    # Patch: build station list for popout dropdown
    station_rooms = config.get("stations", []) + [str(r) for r in range(100, 131)]

    return render_template(
        "admin.html",
        admin_station   = session.get("admin_station", "—"),
        active_rooms    = active_rooms,
        pending_starts  = pending_starts,
        pending_returns = pending_returns,
        active          = active,
        report_data     = report_data,
        station_rooms   = sorted(station_rooms)
    )


# =================================================================
# JSON feed for admin.js (live timer table)
# =================================================================
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
            "id"          : p.id,
            "student_name": p.student.name,
            "student_id"  : p.student.id,
            "period"      : p.period,
            "room"        : p.station,
            "station"     : p.station,
            "checkout"    : p.checkout_time.strftime('%H:%M:%S') if p.checkout_time else None,
            "elapsed"     : elapsed,
            "status"      : p.status,
            "note"        : p.note or "",
            "is_override" : p.is_override
        })

    return jsonify(response)
# =================================================================
# MANUALLY CREATE / OVERRIDE PASS
# =================================================================
@admin_bp.route('/admin_create_pass', methods=['POST'])
def admin_create_pass():
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    data       = request.get_json()
    student_id = data.get('student_id')
    student    = Student.query.get(student_id)

    if not student:
        return jsonify({'message': 'Student not found.'})

    if Pass.query.filter_by(student_id=student.id, checkin_time=None).first():
        return jsonify({'message': 'Student already has an active pass.'})

    override_pass = Pass(
        student_id   = student.id,
        date         = date.today(),
        period       = data.get('period'),
        checkout_time= datetime.now().time(),
        station      = data.get('room', '').strip() or "OVERRIDE",
        is_override  = True,
        status       = STATUS_ACTIVE
    )
    db.session.add(override_pass)
    db.session.commit()
    return jsonify({'message': f'Override pass created for {student.name}.'})

# =================================================================
# QUICK APPROVE / REJECT (pending start)
# =================================================================
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

# =================================================================
# ADMIN QUICK END PASS
# =================================================================
@admin_bp.route('/admin_checkin/<int:pass_id>', methods=['POST'])
def admin_checkin(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = Pass.query.get(pass_id)
    if not p or p.checkin_time:
        return jsonify({'message': 'Pass already ended or not found.'})

    p.checkin_time = datetime.now().time()
    delta          = datetime.combine(date.today(), p.checkin_time) - \
                     datetime.combine(date.today(), p.checkout_time)
    p.total_pass_time = int(delta.total_seconds())
    p.status          = STATUS_RETURNED
    db.session.commit()
    return jsonify({'message': f'Pass {p.id} checked in.'})

# =================================================================
# ADD / UPDATE NOTE ON CURRENT OPEN PASS
# =================================================================
@admin_bp.route('/admin_add_note/<student_id>', methods=['POST'])
def admin_add_note(student_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    note = request.get_json().get('note', '').strip()

    p = Pass.query.filter(
        Pass.student_id == student_id,
        Pass.checkin_time == None,
        Pass.status.in_([STATUS_ACTIVE, STATUS_PENDING_RETURN])
    ).order_by(Pass.checkout_time.desc()).first()

    if not p:
        return jsonify({'message': 'No active pass found.'})

    p.note = note
    db.session.commit()
    return jsonify({'message': 'Note saved.'})

# =================================================================
# SET THIS BROWSER’S STATION LABEL  (reuse station_setup.html)
# =================================================================
@admin_bp.route('/admin_station', methods=['GET', 'POST'])
def set_station():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    if request.method == 'POST':
        station = request.form.get('station').strip()
        session['admin_station'] = station
        activate_room(station)
        return redirect(url_for('admin.admin_view'))

    rooms = sorted({str(r) for r in range(100, 131)} | set(config.get('stations', [])))
    return render_template('station_setup.html', rooms=rooms)

# =================================================================
# LIVE ARCHIVE  – last 100 returned passes
# =================================================================
@admin_bp.route('/admin_pass_history')
def admin_pass_history():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    rows = []
    for p in Pass.query.filter_by(status=STATUS_RETURNED).order_by(
            Pass.date.desc(), Pass.checkout_time.desc()).limit(100):
        logs = sorted(p.logs, key=lambda l: l.timestamp)
        station_in  = next((l for l in logs if l.event_type == "in"),  None)
        station_out = next((l for l in logs if l.event_type == "out"), None)

        rows.append({
            "student"    : p.student.name,
            "date"       : p.date.strftime('%Y-%m-%d'),
            "period"     : p.period,
            "room_out"   : f"{p.station} @ {p.checkout_time.strftime('%H:%M:%S')}",
            "station_in" : f"{station_in.station} @ {station_in.timestamp.strftime('%H:%M:%S')}"  if station_in  else "—",
            "station_out": f"{station_out.station} @ {station_out.timestamp.strftime('%H:%M:%S')}" if station_out else "—",
            "room_in"    : f"{p.station} @ {p.checkin_time.strftime('%H:%M:%S')}" if p.checkin_time else "—",
            "duration"   : f"{p.total_pass_time//60}m {p.total_pass_time%60}s" if p.total_pass_time else "—",
            "note"       : (p.note or "") + (" ✅" if p.is_override else "")
        })

    return render_template('admin_pass_history.html', rows=rows)

# =================================================================
# FINAL CSV EXPORT  – only completed passes
# =================================================================
@admin_bp.route('/admin_export_final')
def export_final_report():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Date", "Period", "RoomOUT+TimeOUT",
        "Station+TimeIN", "Station+TimeOUT", "RoomOUT+TimeIN"
    ])

    for p in Pass.query.filter_by(status=STATUS_RETURNED).all():
        logs = sorted(p.logs, key=lambda l: l.timestamp)
        station_in  = next((l for l in logs if l.event_type == "in"),  None)
        station_out = next((l for l in logs if l.event_type == "out"), None)

        writer.writerow([
            p.student.id,
            p.date.strftime('%Y-%m-%d'),
            p.period,
            f"{p.station} @ {p.checkout_time.strftime('%H:%M:%S')}",
            f"{station_in.station} @ {station_in.timestamp.strftime('%H:%M:%S')}"  if station_in  else "—",
            f"{station_out.station} @ {station_out.timestamp.strftime('%H:%M:%S')}" if station_out else "—",
            f"{p.station} @ {p.checkin_time.strftime('%H:%M:%S')}" if p.checkin_time else "—"
        ])

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=final_pass_report.csv'}
    )

# =================================================================
# RED‑DOT COUNTER FOR NAV BAR (admin.js)
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
