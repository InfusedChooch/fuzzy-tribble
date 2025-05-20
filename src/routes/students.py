# src/routes/students.py

from flask import Blueprint, render_template, request, redirect, url_for, session, Response
from src.models import db, Student, StudentPeriod
from src.utils import log_audit, load_config
import csv
import io

students_bp = Blueprint('students', __name__)
config = load_config()

# ------------------------------------------------------------------
@students_bp.route('/students')
def manage_students():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    students = Student.query.all()
    return render_template('students.html', students=students)

# ------------------------------------------------------------------
@students_bp.route('/students/download')
def download_students_csv():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Period', 'Room'])

    students = Student.query.all()
    for student in students:
        periods = StudentPeriod.query.filter_by(student_id=student.student_id).all()
        for sp in periods:
            writer.writerow([student.student_id, student.name, sp.period, sp.room])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=students.csv"})

# ------------------------------------------------------------------
@students_bp.route('/students/upload', methods=['POST'])
def upload_students_csv():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    file = request.files.get('csv_file')
    if not file:
        return "No file uploaded", 400

    try:
        # Clear existing data
        StudentPeriod.query.delete()
        Student.query.delete()
        db.session.commit()

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)

        student_cache = {}
        for row in reader:
            student_id = row['ID'].strip()
            name = row['Name'].strip()
            period = str(row['Period']).strip()
            room = str(row['Room']).strip()

            if student_id not in student_cache:
                student = Student(student_id=student_id, name=name)
                db.session.add(student)
                student_cache[student_id] = student
            else:
                student = student_cache[student_id]

            sp = StudentPeriod(student_id=student_id, period=period, room=room)
            db.session.add(sp)

        db.session.commit()
        log_audit("admin", "Uploaded student roster via CSV")
        return redirect(url_for('students.manage_students'))

    except Exception as e:
        return f"Upload failed: {str(e)}", 500

# ------------------------------------------------------------------
@students_bp.route('/students/add', methods=['POST'])
def add_student():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    student_id = request.form.get('id').strip()
    name = request.form.get('name').strip()
    period = request.form.get('period').strip()
    room = request.form.get('room').strip()

    try:
        student = Student.query.get(student_id)
        if not student:
            student = Student(student_id=student_id, name=name)
            db.session.add(student)

        sp = StudentPeriod(student_id=student_id, period=period, room=room)
        db.session.add(sp)
        db.session.commit()

        log_audit("admin", f"Manually added student {student_id} period {period} → {room}")
        return redirect(url_for('students.manage_students'))

    except Exception as e:
        return f"Add failed: {str(e)}", 500
