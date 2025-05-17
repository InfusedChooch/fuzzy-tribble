import json
import os
from src.models import db, AuditLog
from datetime import datetime

ACTIVE_ROOMS_FILE = os.path.join('data', 'active_rooms.json')

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
        print(f"[AUDIT]{student_id} - {reason}")
    except Exception as e:
        print(f"[AUDIT ERROR] {e}")