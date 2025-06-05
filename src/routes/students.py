# src/routes/students.py
# Admin routes to view, upload, download, and add student schedules

from flask import Blueprint, render_template, request, redirect, url_for, session, Response
from src.models import db, User, StudentPeriod
from src.utils import log_audit, load_config
import csv
import io
from werkzeug.security import generate_password_hash

students_bp = Blueprint('students', __name__)
config = load_config()


# ─────────────────────────────────────────────────────────────────────────────
# Route: Manage Students Page
# ─────────────────────────────────────────────────────────────────────────────
@students_bp.route('/students')
def manage_students():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    students = User.query.filter_by(role="student").all()
    return render_template('students.html', students=students)


# ─────────────────────────────────────────────────────────────────────────────
# Route: Download Student Schedule CSV
# ─────────────────────────────────────────────────────────────────────────────
@students_bp.route('/students/download')
def download_students_csv():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    from src.models import StudentSchedule

    output = io.StringIO()
    writer = csv.writer(output)

    period_fields = [
        "period_0", "period_1", "period_2", "period_3", "period_4_5",
        "period_5_6", "period_6_7", "period_7_8", "period_9",
        "period_10", "period_11", "period_12"
    ]
    writer.writerow(['ID', 'Name'] + period_fields)

    students = User.query.filter_by(role="student").all()
    for student in students:
        sched = StudentSchedule.query.get(student.id)
        if sched:
            row = [student.id, student.name] + [
                getattr(sched, field, "") or "" for field in period_fields
            ]
            writer.writerow(row)

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=students_schedule.csv"
    })


# ─────────────────────────────────────────────────────────────────────────────
# Route: Upload Student Schedule CSV
# ─────────────────────────────────────────────────────────────────────────────
@students_bp.route('/students/upload', methods=['POST'])
def upload_students_csv():
    if not session.get('logged_in') or session.get('role') != "admin":
        return redirect(url_for('auth.login'))

    file = request.files.get('csv_file')
    if not file:
        return "No file uploaded", 400

    try:
        from src.models import StudentSchedule, StudentPeriod

        StudentSchedule.query.delete()
        StudentPeriod.query.delete()
        User.query.filter_by(role="student").delete()
        db.session.commit()

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)

        for row in reader:
            student_id = row['ID'].strip()
            name = row['Name'].strip()
            email = f"{student_id}@school.org"
            password = generate_password_hash(student_id)

            student = User(
                id=student_id,
                name=name,
                email=email,
                role="student",
                password=password
            )
            db.session.add(student)

            sched = StudentSchedule(student_id=student_id)
            for key in row:
                if key.startswith("period_"):
                    setattr(sched, key, row[key].strip())
            db.session.add(sched)

        db.session.commit()

        # Sync to StudentPeriod
        all_scheds = StudentSchedule.query.all()
        for sched in all_scheds:
            for key, val in vars(sched).items():
                if key.startswith("period_") and val:
                    period = key.replace("period_", "").replace("_", "/")
                    db.session.add(StudentPeriod(student_id=sched.student_id, period=period, room=val))
        db.session.commit()

        log_audit("admin", "Uploaded student roster and synced schedules")
        return redirect(url_for('students.manage_students'))

    except Exception as e:
        return f"Upload failed: {str(e)}", 500


# ─────────────────────────────────────────────────────────────────────────────
# Route: Manually Add a Student Period
# ─────────────────────────────────────────────────────────────────────────────
@students_bp.route('/students/add', methods=['POST'])
def add_student():
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    student_id = request.form.get('id').strip()
    name = request.form.get('name').strip()
    period = request.form.get('period').strip()
    room = request.form.get('room').strip()

    try:
        student = User.query.get(student_id)
        if not student:
            email = f"{student_id}@school.org"
            password = generate_password_hash(student_id)
            student = User(
                id=student_id,
                name=name,
                email=email,
                role="student",
                password=password
            )
            db.session.add(student)

        sp = StudentPeriod(student_id=student_id, period=period, room=room)
        db.session.add(sp)
        db.session.commit()

        log_audit("admin", f"Manually added student {student_id} period {period} → {room}")
        return redirect(url_for('students.manage_students'))

    except Exception as e:
        return f"Add failed: {str(e)}", 500

