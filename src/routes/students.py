from flask import Blueprint, render_template, request, redirect, url_for, session, Response
from src.models import db, Student
import csv
import io
import json

students_bp = Blueprint('students', __name__)

@students_bp.route('/students')
def manage_students():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    students = Student.query.all()
    return render_template('students.html', students=students)

@students_bp.route('/students/download')
def download_students_csv():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Schedule'])  # ✅ updated header

    for student in Student.query.all():
        schedule_json = json.dumps(student.schedule or {})
        writer.writerow([student.id, student.name, schedule_json])  # ✅ write schedule

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=students.csv"})

@students_bp.route('/students/upload', methods=['POST'])
def upload_students_csv():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    file = request.files.get('csv_file')
    if not file:
        return "No file uploaded", 400

    try:
        Student.query.delete()
        db.session.commit()

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        for row in reader:
            schedule = json.loads(row['Schedule'])
            new_student = Student(
                id=row['ID'].strip(),
                name=row['Name'].strip(),
                schedule=schedule
            )
            db.session.add(new_student)

        db.session.commit()
        return redirect(url_for('students.manage_students'))

    except Exception as e:
        return f"Upload failed: {str(e)}", 500

@students_bp.route('/students/add', methods=['POST'])
def add_student():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    student_id = request.form.get('id')
    name = request.form.get('name')
    schedule_raw = request.form.get('schedule')  # NEW FIELD

    if Student.query.get(student_id):
        return "Student with this ID already exists", 400

    try:
        schedule = json.loads(schedule_raw)
    except Exception:
        return "Invalid schedule format. Please use JSON.", 400

    new_student = Student(
        id=student_id,
        name=name,
        schedule=schedule
    )
    db.session.add(new_student)
    db.session.commit()

    return redirect(url_for('students.manage_students'))
