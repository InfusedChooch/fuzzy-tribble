# src/services/pass_manager.py

from datetime import datetime
from src.models import db, Pass, PassEvent
from src.utils import log_audit

STATUS_PENDING_START = "pending_start"
STATUS_ACTIVE = "active"
STATUS_PENDING_RETURN = "pending_return"
STATUS_RETURNED = "returned"

def create_pass(student_id, room, period, is_override=False):
    now = datetime.now()
    new_pass = Pass(
        student_id=student_id,
        date=now.date(),
        period=period,
        checkout_at=now,
        origin_room=room,
        is_override=is_override,
        status=STATUS_ACTIVE if is_override else STATUS_PENDING_START
    )
    db.session.add(new_pass)
    db.session.commit()
    log_audit(student_id, f"Created pass {'(override)' if is_override else ''} for room {room}")
    return new_pass


def approve_pass(pass_id):
    p = db.session.get(Pass, pass_id)
    if not p or p.status != STATUS_PENDING_START:
        return False
    p.status = STATUS_ACTIVE
    p.checkout_at = datetime.now()
    db.session.commit()
    log_audit(p.student_id, f"Approved pass {pass_id}")
    return True


def reject_pass(pass_id):
    p = db.session.get(Pass, pass_id)
    if not p or p.status != STATUS_PENDING_START:
        return False
    log_audit(p.student_id, f"Rejected pass {pass_id}")
    db.session.delete(p)
    db.session.commit()
    return True


def return_pass(pass_obj, station=None):
    now = datetime.now()
    if pass_obj.checkin_at:
        return False
    pass_obj.checkin_at = now
    pass_obj.status = STATUS_RETURNED
    if pass_obj.checkout_at:
        delta = now - pass_obj.checkout_at
        pass_obj.total_pass_time = int(delta.total_seconds())
    if station:
        pass_obj.room_in = station
    db.session.commit()
    log_audit(pass_obj.student_id, f"Returned pass {pass_obj.id} at {station or 'room'}")
    return True


def record_pass_event(pass_obj, station, event_type):
    event = PassEvent(
        pass_id=pass_obj.id,
        station=station,
        event=event_type,
        timestamp=datetime.utcnow()
    )
    db.session.add(event)
    db.session.commit()
    log_audit(pass_obj.student_id, f"{event_type.upper()} at {station}")
