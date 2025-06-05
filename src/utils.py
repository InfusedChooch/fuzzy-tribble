# src/utils.py
# Shared utility functions: config loader, audit logger, room/session helpers, and CSV response tools

import os, json
from datetime import datetime
from flask import make_response
from src.models import db, AuditLog, ActiveRoom

# ─────────────────────────────────────────────────────────────────────────────
# Globals
# ─────────────────────────────────────────────────────────────────────────────
AUDIT_LOG_FILE = os.path.join('data', 'logs', 'console_audit.log')


# ─────────────────────────────────────────────────────────────────────────────
# Active Room Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Return all currently active room names.
def get_active_rooms() -> set[str]:
    return {r.room for r in ActiveRoom.query.all()}

# Determine if a room name refers to a station (non-digit and in config).
def is_station(name: str, config=None) -> bool:
    if config is None:
        config = load_config()
    return name and not name.isdigit() and name in config.get("stations", [])

# Mark a room as active (if not already).
def activate_room(room: str):
    if not ActiveRoom.query.get(room):
        db.session.add(ActiveRoom(room=room))
        db.session.commit()

# Remove a room from active status.
def deactivate_room(room: str):
    rec = ActiveRoom.query.get(room)
    if rec:
        db.session.delete(rec)
        db.session.commit()

# Reset all active rooms to a new list.
def replace_rooms(room_list: list[str]):
    ActiveRoom.query.delete()
    db.session.bulk_save_objects([ActiveRoom(room=r) for r in room_list])
    db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Audit Logger
# ─────────────────────────────────────────────────────────────────────────────

# Write an audit log entry to the DB and to a local log file.
def log_audit(student_id, reason):
    try:
        clean_reason = reason.replace("–", "-").replace("—", "-")
        line = f"[AUDIT] {student_id} - {clean_reason}"

        db.session.add(AuditLog(student_id=student_id, reason=clean_reason, time=datetime.now()))
        db.session.commit()

        print(line)
        os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    except Exception as e:
        print(f"[AUDIT ERROR] {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Config + Period Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Load config file from /data/config.json with resolved schedule variant.
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

# Return a list of all periods currently active (based on time window).
def get_current_periods():
    now = datetime.now().time()
    matches = []

    for period, times in config.get("period_schedule", {}).items():
        try:
            start = datetime.strptime(times["start"], "%H:%M").time()
            end = datetime.strptime(times["end"], "%H:%M").time()
            if start <= now <= end:
                matches.append(period)
        except Exception as e:
            print(f"[WARN] Skipping period {period} due to bad time format: {e}")

    return matches

# Get the room a student is assigned to during a specific period.
def get_room(student_id, period):
    from src.models import StudentPeriod
    rec = StudentPeriod.query.filter_by(student_id=student_id, period=period).first()
    return rec.room if rec else None

# Copy StudentSchedule entries into normalized StudentPeriod rows.
def sync_student_schedule_to_periods():
    from src.models import StudentSchedule, StudentPeriod

    StudentPeriod.query.delete()

    all_scheds = StudentSchedule.query.all()
    for sched in all_scheds:
        for key, val in vars(sched).items():
            if key.startswith("period_") and val:
                period = key.replace("period_", "").replace("_", "/")
                db.session.add(StudentPeriod(student_id=sched.student_id, period=period, room=val))
    db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# CSV Export Helper
# ─────────────────────────────────────────────────────────────────────────────

# Wrap a StringIO buffer as a downloadable CSV response.
def csv_response(string_io, filename="export"):
    output = make_response(string_io.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

