# src/utils.py
import os, json
from datetime import datetime
from src.models import db, AuditLog, ActiveRoom
from flask import make_response

AUDIT_LOG_FILE = os.path.join('data', 'logs', 'console_audit.log')

# ─── active-room helpers ────────────────────────────────────────────────
def get_active_rooms() -> set[str]:
    return {r.room for r in ActiveRoom.query.all()}

def is_station(name: str, config=None) -> bool:
    if config is None:
        config = load_config()
    return name and not name.isdigit() and name in config.get("stations", [])


def activate_room(room: str):
    if not ActiveRoom.query.get(room):
        db.session.add(ActiveRoom(room=room))
        db.session.commit()

def deactivate_room(room: str):
    rec = ActiveRoom.query.get(room)
    if rec:
        db.session.delete(rec)
        db.session.commit()

def replace_rooms(room_list: list[str]):
    ActiveRoom.query.delete()
    db.session.bulk_save_objects([ActiveRoom(room=r) for r in room_list])
    db.session.commit()

# ─── audit logger (unchanged) ───────────────────────────────────────────
def log_audit(student_id, reason):
    try:
        # Ensure only safe ASCII characters (no en dash)
        clean_reason = reason.replace("–", "-").replace("—", "-")
        line = f"[AUDIT] {student_id} - {clean_reason}"

        db.session.add(AuditLog(student_id=student_id, reason=clean_reason, time=datetime.now()))
        db.session.commit()

        print(line)
        os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    except Exception as e:
        err = f"[AUDIT ERROR] {e}"
        print(err)

        
# ─── config + period helpers ───────────────────────────────────────────────
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

def get_current_period():
    """Return the current school period based on time and active schedule."""
    from datetime import datetime
    now = datetime.now().time()
    for period, times in config.get("period_schedule", {}).items():
        start = datetime.strptime(times["start"], "%H:%M").time()
        end = datetime.strptime(times["end"], "%H:%M").time()
        if start <= now <= end:
            return period
    return "0"

def get_room(student_id, period):
    """Get assigned room for a student in a given period."""
    from src.models import StudentPeriod
    rec = StudentPeriod.query.filter_by(student_id=student_id, period=period).first()
    return rec.room if rec else None

# ─── CSV export helper ─────────────────────────────────────────────────────
from flask import make_response

def csv_response(string_io, filename="export"):
    """Convert a StringIO buffer to a Flask CSV response."""
    output = make_response(string_io.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
