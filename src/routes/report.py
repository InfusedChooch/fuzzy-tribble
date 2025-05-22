# src/routes/report.py
# Admin-side reports: weekly summary, CSV exports, and pass history view

from flask import Blueprint, render_template, session, redirect, url_for, jsonify, Response, request, make_response
from datetime import datetime
import csv
from io import StringIO

from src.models import db, Pass, User
from src.utils import log_audit, load_config, csv_response

report_bp = Blueprint('report', __name__)
config = load_config()

REPORT_DAYS = config.get("report_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
THRESHOLDS = config.get("report_time_thresholds", {"over_5": 300, "over_10": 600})


# ─────────────────────────────────────────────────────────────────────────────
# Route: Weekly Summary View (HTML)
# ─────────────────────────────────────────────────────────────────────────────
@report_bp.route('/admin_report')
def admin_report():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    report_data = []

    for student in User.query.filter_by(role="student"):
        records = Pass.query.filter_by(student_id=student.id).all()
        day_totals = {d: 0 for d in REPORT_DAYS}
        over_5 = sum(1 for r in records if (r.total_pass_time or 0) > THRESHOLDS["over_5"])
        over_10 = sum(1 for r in records if (r.total_pass_time or 0) > THRESHOLDS["over_10"])
        used_override = any(r.is_override for r in records)

        for r in records:
            dname = r.date.strftime('%A')
            if dname in day_totals:
                day_totals[dname] += r.total_pass_time or 0

        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in REPORT_DAYS)
        report_data.append({
            'student_name': student.name,
            'student_id': student.id,
            'weekly_report': weekly,
            'passes_over_5_min': over_5,
            'passes_over_10_min': over_10,
            'used_override': '✔️' if used_override else ''
        })

    return render_template('admin_report.html', report_data=report_data)


# ─────────────────────────────────────────────────────────────────────────────
# Route: Weekly Summary CSV Export
# ─────────────────────────────────────────────────────────────────────────────
@report_bp.route('/admin_report_csv')
def admin_report_csv():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Student ID', 'Weekly Report', 'Passes Over 5 Min', 'Passes Over 10 Min'])

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for student in User.query.filter_by(role="student"):
        records = Pass.query.filter_by(student_id=student.id).all()
        day_totals = {d: 0 for d in days}
        over_5 = sum(1 for r in records if (r.total_pass_time or 0) > 300)
        over_10 = sum(1 for r in records if (r.total_pass_time or 0) > 600)

        for r in records:
            if r.date.strftime('%A') in day_totals:
                day_totals[r.date.strftime('%A')] += r.total_pass_time or 0

        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in days)
        writer.writerow([student.name, student.id, weekly, over_5, over_10])

    return csv_response(output, "weekly_report")


# ─────────────────────────────────────────────────────────────────────────────
# Route: Pass History Table and Export
# ─────────────────────────────────────────────────────────────────────────────
@report_bp.route('/admin_pass_history')
def admin_pass_history():
    if not session.get('logged_in'):
        return redirect(url_for('auth.admin_login'))

    passes = Pass.query.filter(Pass.checkin_at != None).order_by(
        Pass.date.desc(), Pass.checkout_at.desc()
    ).limit(100).all()

    # CSV Export
    if request.args.get("export") == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Student", "Date", "Period", "Room Out", "Station In",
            "Station Out", "Room In", "Duration", "Hallway", "Station",
            "Note", "Override"
        ])

        for p in passes:
            logs = sorted(p.events, key=lambda l: l.timestamp)
            station_in = next((l for l in logs if l.event == "in"), None)
            station_out = next((l for l in logs if l.event == "out"), None)

            total_time = (p.checkin_at - p.checkout_at).total_seconds() if p.checkout_at and p.checkin_at else 0
            station_time = (station_out.timestamp - station_in.timestamp).total_seconds() if station_in and station_out else 0
            hallway_time = total_time - station_time if station_time else total_time

            writer.writerow([
                p.student_id,
                p.student.name if p.student else "-",
                p.date.strftime('%Y-%m-%d'),
                p.period,
                f"{p.room_out} @ {p.checkout_at.strftime('%H:%M:%S')}" if p.checkout_at else "-",
                f"{station_in.station} @ {station_in.timestamp.strftime('%H:%M:%S')}" if station_in else "-",
                f"{station_out.station} @ {station_out.timestamp.strftime('%H:%M:%S')}" if station_out else "-",
                f"{p.room_in} @ {p.checkin_at.strftime('%H:%M:%S')}" if p.checkin_at else "-",
                f"{int(total_time//60)}m {int(total_time%60)}s" if total_time else "-",
                f"{int(hallway_time//60)}m {int(hallway_time%60)}s" if hallway_time else "-",
                f"{int(station_time//60)}m {int(station_time%60)}s" if station_time else "-",
                p.note or "",
                "✔️" if p.is_override else ""
            ])

        return csv_response(output, "pass_history")

    # HTML Fallback
    rows = []
    for p in passes:
        logs = sorted(p.events, key=lambda l: l.timestamp)
        station_in = next((l for l in logs if l.event == "in"), None)
        station_out = next((l for l in logs if l.event == "out"), None)

        total_time = (p.checkin_at - p.checkout_at).total_seconds() if p.checkout_at and p.checkin_at else 0
        station_time = (station_out.timestamp - station_in.timestamp).total_seconds() if station_in and station_out else 0
        hallway_time = total_time - station_time if station_time else total_time

        rows.append({
            "id": p.student_id,
            "student": p.student.name if p.student else "-",
            "date": p.date.strftime('%Y-%m-%d'),
            "period": p.period,
            "room_out": f"{p.room_out} @ {p.checkout_at.strftime('%H:%M:%S')}" if p.checkout_at else "-",
            "station_in": f"{station_in.station} @ {station_in.timestamp.strftime('%H:%M:%S')}" if station_in else "-",
            "station_out": f"{station_out.station} @ {station_out.timestamp.strftime('%H:%M:%S')}" if station_out else "-",
            "room_in": f"{p.room_in} @ {p.checkin_at.strftime('%H:%M:%S')}" if p.checkin_at else "-",
            "duration": f"{int(total_time//60)}m {int(total_time%60)}s" if total_time else "-",
            "hallway": f"{int(hallway_time//60)}m {int(hallway_time%60)}s" if hallway_time else "-",
            "station": f"{int(station_time//60)}m {int(station_time%60)}s" if station_time else "-",
            "note": p.note or "",
            "override": "✔️" if p.is_override else ""
        })

    return render_template("admin_pass_history.html", rows=rows)
