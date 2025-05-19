from flask import Blueprint, render_template, session, redirect, url_for, jsonify, Response
from src.models import db, Pass, Student
from datetime import datetime
from src.utils import log_audit
import csv
import io

report_bp = Blueprint('report', __name__)


@report_bp.route('/admin_report')
def admin_report():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    report_data = []

    for student in Student.query.all():
        records = Pass.query.filter_by(student_id=student.student_id).all()
        day_totals = {d: 0 for d in days}
        over_5 = sum(1 for r in records if (r.total_pass_time or 0) > 300)
        over_10 = sum(1 for r in records if (r.total_pass_time or 0) > 600)
        used_override = any(r.is_override for r in records)

        for r in records:
            if r.date.strftime('%A') in day_totals:
                day_totals[r.date.strftime('%A')] += r.total_pass_time or 0

        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in days)
        report_data.append({
            'student_name': student.name,
            'student_id': student.student_id,
            'weekly_report': weekly,
            'passes_over_5_min': over_5,
            'passes_over_10_min': over_10,
            'used_override': '✔️' if used_override else ''
        })

    return render_template('admin_report.html', report_data=report_data)


@report_bp.route('/admin_report_csv')
def admin_report_csv():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Student ID', 'Weekly Report', 'Passes Over 5 Min', 'Passes Over 10 Min'])

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for student in Student.query.all():
        records = Pass.query.filter_by(student_id=student.student_id).all()
        day_totals = {d: 0 for d in days}
        over_5 = sum(1 for r in records if (r.total_pass_time or 0) > 300)
        over_10 = sum(1 for r in records if (r.total_pass_time or 0) > 600)

        for r in records:
            if r.date.strftime('%A') in day_totals:
                day_totals[r.date.strftime('%A')] += r.total_pass_time or 0

        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in days)
        writer.writerow([student.name, student.student_id, weekly, over_5, over_10])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=weekly_report.csv"})

@report_bp.route('/admin_pass_history')
def admin_pass_history():
    return render_template("admin_pass_history.html")  # or your real handler

