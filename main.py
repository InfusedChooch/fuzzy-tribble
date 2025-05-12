# main.py
from flask import render_template, request, jsonify
from datetime import datetime
from src import create_app
from src.models import db, Student, Pass, AuditLog
import json

app = create_app()

# Load configuration
def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
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


@app.route('/')
def index():
    current_period = get_current_period()
    active_passes = Pass.query.filter_by(checkin_time=None).order_by(Pass.checkout_time).all()
    return render_template(
        'index.html',
        passes=active_passes,
        current_period=current_period,
        school_name=config.get('school_name', 'School'),
        theme_color=config.get('theme_color', '#4a90e2'),
        logo_url="/static/images/school_logo.png"
    )


@app.route('/check', methods=['POST'])
def check():
    student_id = request.form.get('student_id', '').strip()
    student = Student.query.get(student_id)

    if not student:
        db.session.add(AuditLog(student_id=None, reason=f"Invalid ID: {student_id}"))
        db.session.commit()
        return jsonify({'message': 'Invalid ID number.'})

    current_period = get_current_period()

    if str(student.period) != str(current_period):
        db.session.add(AuditLog(
            student_id=student.id,
            reason=f"Invalid period: tried {current_period}, expected {student.period}"
        ))
        db.session.commit()
        return jsonify({'message': f'You cannot leave during this period (current: {current_period}).'})

    active_pass = Pass.query.filter_by(student_id=student.id, checkin_time=None).first()
    if active_pass:
        active_pass.checkin_time = datetime.now().time()
        delta = datetime.combine(datetime.today(), active_pass.checkin_time) - datetime.combine(datetime.today(), active_pass.checkout_time)
        active_pass.total_pass_time = int(delta.total_seconds())
        db.session.commit()
        return jsonify({'message': 'Returned successfully.'})

    max_passes = config.get('passes_available', 3)
    active_count = Pass.query.filter_by(checkin_time=None).count()
    if active_count >= max_passes:
        return jsonify({'message': 'No passes available right now.'})

    new_pass = Pass(
        student_id=student.id,
        date=datetime.now().date(),
        period=current_period,
        checkout_time=datetime.now().time(),
    )
    db.session.add(new_pass)
    db.session.commit()
    return jsonify({'message': f'Pass checked out for {student.name}.'})


@app.route('/passes')
def get_pass_slots():
    max_passes = config.get('passes_available', 3)
    active = Pass.query.filter_by(checkin_time=None, is_override=False).order_by(Pass.checkout_time).all()

    slots = []
    for i in range(max_passes):
        if i < len(active):
            p = active[i]
            slots.append({
                'status': 'in use',
                'pass_id': p.id,
                'student_id': p.student_id,
                'student_name': p.student.name if p.student else 'Unknown',
                'time_out': p.checkout_time.strftime('%H:%M:%S')
            })
        else:
            slots.append({
                'status': 'free',
                'pass_id': str(i + 1),
                'student_id': None,
                'student_name': None,
                'time_out': None
            })
    return jsonify(slots)


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

@app.route('/test')
def test():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=config.get("debug_mode", True))
