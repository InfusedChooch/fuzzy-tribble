# src/utils.py
from flask import make_response
import json
import os
from datetime import datetime
from src.models import db, AuditLog, StudentPeriod

ACTIVE_ROOMS_FILE = os.path.join('data', 'active_rooms.json')
AUDIT_LOG_FILE = os.path.join('data', 'logs', 'console_audit.log')
CONFIG_FILE = os.path.join('data', 'config.json')

def csv_response(output, base_filename):
    output.seek(0)
    today = datetime.now().strftime("%Y-%m-%d")
    response = make_response(output.read())
    response.headers["Content-Disposition"] = f"attachment; filename={base_filename}_{today}.csv"
    response.headers["Content-Type"] = "text/csv"
    return response
# ─── Room Management ────────────────────────────────────────────────

def get_active_rooms():
    try:
        with open(ACTIVE_ROOMS_FILE) as f:
            return set(json.load(f))
    except:
        return set()

def activate_room(room):
    rooms = get_active_rooms()
    rooms.add(room)
    with open(ACTIVE_ROOMS_FILE, 'w') as f:
        json.dump(sorted(rooms), f)

def deactivate_room(room):
    rooms = get_active_rooms()
    rooms.discard(room)
    with open(ACTIVE_ROOMS_FILE, 'w') as f:
        json.dump(sorted(rooms), f)


# ─── Logging ────────────────────────────────────────────────────────

def log_audit(student_id, reason):
    try:
        log = AuditLog(student_id=student_id, reason=reason, time=datetime.now())
        db.session.add(log)
        db.session.commit()
        line = f"[AUDIT] {student_id} - {reason}"
        print(line)
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        err = f"[AUDIT ERROR] {e}"
        print(err)
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(err + "\n")


# ─── Config Management ──────────────────────────────────────────────

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            active = config.get("active_schedule", "regular")
            config["period_schedule"] = config.get("schedule_variants", {}).get(active, {})
            return config
    except Exception:
        return {}


# ─── Period / Schedule Helpers ──────────────────────────────────────

def get_current_period():
    config = load_config()
    now = datetime.now().time()
    for period, times in config.get("period_schedule", {}).items():
        start = datetime.strptime(times["start"], "%H:%M").time()
        end = datetime.strptime(times["end"], "%H:%M").time()
        if start <= now <= end:
            return str(period)
    return "N/A"


def get_room(student_id, period):
    sp = db.session.query(StudentPeriod).filter_by(
        student_id=student_id,
        period=period
    ).first()
    return sp.room if sp else None
