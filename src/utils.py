import json
import os
from src.models import db, AuditLog
from datetime import datetime

ACTIVE_ROOMS_FILE = os.path.join('data', 'active_rooms.json')
AUDIT_LOG_FILE = os.path.join('data', 'logs', 'console_audit.log')  # ✅ new

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

def log_audit(student_id, reason):
    try:
        log = AuditLog(student_id=student_id, reason=reason, time=datetime.now())
        db.session.add(log)
        db.session.commit()
        line = f"[AUDIT] {student_id} - {reason}"
        print(line)
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(line + "\n")  # ✅ file-based echo for launcher console
    except Exception as e:
        err = f"[AUDIT ERROR] {e}"
        print(err)
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(err + "\n")
