from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
from src.models import db, Pass, Student, AuditLog
import json

admin_bp = Blueprint('admin', __name__)

def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
    except Exception:
        return {}

config = load_config()


@admin_bp.route('/admin')
def admin_view():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    # Recent audit logs
    audit_log = AuditLog.query.order_by(AuditLog.time.desc()).limit(5).all()

    # Weekly summary stats
    students = Student.query.all()
    summary = []
    for student in students:
        passes = Pass.query.filter_by(student_id=student.id).all()
        total = sum(p.total_pass_time or 0 for p in passes)
        count = len(passes)
        avg = total // count if count else 0
        over_5 = sum(1 for p in passes if (p.total_pass_time or 0) > 300)
        summary.append({
            'student_name': student.name,
            'student_id': student.id,
            'total_time': f"{total // 60}m {total % 60}s",
            'total_passes': count,
            'avg_time': f"{avg // 60}m {avg % 60}s",
            'passes_over_5_min': over_5
        })

    # Recent 10 completed passes
    recent_passes = Pass.query.filter(Pass.checkin_time.isnot(None))\
        .order_by(Pass.date.desc(), Pass.checkout_time.desc()).limit(10).all()

    return render_template(
        'admin.html',
        weekly_summary=summary,
        audit_log=audit_log,
        recent_passes=recent_passes
    )


@admin_bp.route('/admin_passes')
def admin_passes():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    active = Pass.query.filter_by(checkin_time=None).order_by(Pass.checkout_time).all()
    return jsonify([
        {
            'pass_id': p.id,
            'student_id': p.student_id,
            'student_name': p.student.name if p.student else 'Unknown',
            'time_out': p.checkout_time.strftime('%H:%M:%S'),
            'is_override': p.is_override
        } for p in active
    ])


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
        return jsonify({'message': 'Student already has a pass.'})

    override_pass = Pass(
        student_id=student.id,
        date=datetime.now().date(),
        period="Override",
        checkout_time=datetime.now().time(),
        is_override=True
    )
    db.session.add(override_pass)
    db.session.commit()
    return jsonify({'message': f'Override pass created for {student.name}.'})


@admin_bp.route('/admin_checkin/<int:pass_id>', methods=['POST'])
def admin_checkin(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    p = Pass.query.get(pass_id)
    if not p or p.checkin_time:
        return jsonify({'message': 'Pass already closed or not found.'})

    p.checkin_time = datetime.now().time()
    delta = datetime.combine(datetime.today(), p.checkin_time) - datetime.combine(datetime.today(), p.checkout_time)
    p.total_pass_time = int(delta.total_seconds())
    db.session.commit()
    return jsonify({'message': f'Pass {p.id} checked in.'})


@admin_bp.route('/admin_add_note/<student_id>', methods=['POST'])
def admin_add_note(student_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    note = data.get('note')
    p = Pass.query.filter_by(student_id=student_id, checkin_time=None).order_by(Pass.checkout_time.desc()).first()

    if p:
        p.note = note
        db.session.commit()
        return jsonify({'message': 'Note saved.'})

    return jsonify({'message': 'No active pass found.'})


@admin_bp.route('/admin_change_password', methods=['POST'])
def admin_change_password():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    current = data.get("current_password")
    new = data.get("new_password")
    confirm = data.get("confirm_password")

    if current != config.get("admin_password"):
        return jsonify({'success': False, 'message': 'Current password incorrect.'})
    if new != confirm:
        return jsonify({'success': False, 'message': 'New passwords do not match.'})

    config["admin_password"] = new
    with open("data/config.json", "w") as f:
        json.dump(config, f, indent=4)

    return jsonify({'success': True, 'message': 'Password updated successfully.'})

@admin_bp.route('/admin_pass_history')
def admin_pass_history():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    # Fetch most recent 100 checked-in passes
    history = Pass.query.filter(Pass.checkin_time.isnot(None)).order_by(Pass.date.desc(), Pass.checkout_time.desc()).limit(100).all()

    return render_template('admin_pass_history.html', history=history)
