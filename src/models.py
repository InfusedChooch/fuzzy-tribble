# src/models.py
# SQLAlchemy ORM models for users, schedules, passes, logs, and active rooms

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

# ─────────────────────────────────────────────────────────────────────────────
# Active Room Tracker
# ─────────────────────────────────────────────────────────────────────────────
class ActiveRoom(db.Model):
    __tablename__ = "active_rooms"

    room  = db.Column(db.String(20), primary_key=True)  # e.g. "115", "Bathroom"
    added = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Users Table
# ─────────────────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id       = db.Column(db.String, primary_key=True)  # login ID
    name     = db.Column(db.String, nullable=False)
    email    = db.Column(db.String, unique=True, nullable=False)
    role     = db.Column(db.String, nullable=False)  # "student", "teacher"
    password = db.Column(db.String, nullable=False)

    # Related records (for students)
    passes   = db.relationship("Pass", backref="student", lazy=True, foreign_keys='Pass.student_id')
    audits   = db.relationship("AuditLog", backref="student", lazy=True, foreign_keys='AuditLog.student_id')
    periods  = db.relationship("StudentPeriod", backref="student", lazy=True, foreign_keys='StudentPeriod.student_id')

    def check_password(self, raw_password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, raw_password)


# ─────────────────────────────────────────────────────────────────────────────
# Student & Teacher Schedule Tables
# ─────────────────────────────────────────────────────────────────────────────
class TeacherSchedule(db.Model):
    __tablename__ = "teacher_schedule"

    teacher_id = db.Column(db.String, db.ForeignKey("users.id"), primary_key=True)

    # Schedule entries for each period
    period_0 = db.Column(db.String(10))
    period_1 = db.Column(db.String(10))
    period_2 = db.Column(db.String(10))
    period_3 = db.Column(db.String(10))
    period_4_5 = db.Column(db.String(10))
    period_5_6 = db.Column(db.String(10))
    period_6_7 = db.Column(db.String(10))
    period_7_8 = db.Column(db.String(10))
    period_9 = db.Column(db.String(10))
    period_10 = db.Column(db.String(10))
    period_11 = db.Column(db.String(10))
    period_12 = db.Column(db.String(10))

    teacher = db.relationship("User", backref="teacher_schedule", lazy=True)


class StudentSchedule(db.Model):
    __tablename__ = "student_schedule"

    student_id = db.Column(db.String, db.ForeignKey("users.id"), primary_key=True)

    period_0 = db.Column(db.String(10))
    period_1 = db.Column(db.String(10))
    period_2 = db.Column(db.String(10))
    period_3 = db.Column(db.String(10))
    period_4_5 = db.Column(db.String(10))
    period_5_6 = db.Column(db.String(10))
    period_6_7 = db.Column(db.String(10))
    period_7_8 = db.Column(db.String(10))
    period_9 = db.Column(db.String(10))
    period_10 = db.Column(db.String(10))
    period_11 = db.Column(db.String(10))
    period_12 = db.Column(db.String(10))

    student = db.relationship("User", backref="schedule", lazy=True)


class StudentPeriod(db.Model):
    __tablename__ = "student_periods"

    student_id = db.Column(db.String, db.ForeignKey("users.id"), primary_key=True)
    period     = db.Column(db.String(10), primary_key=True)
    room       = db.Column(db.String(10), nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# Hall Pass Records
# ─────────────────────────────────────────────────────────────────────────────
class Pass(db.Model):
    __tablename__ = "passes"

    id          = db.Column(db.Integer, primary_key=True)
    date        = db.Column(db.Date, default=func.current_date())
    student_id  = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)

    checkout_at     = db.Column(db.DateTime(timezone=True), nullable=False)
    checkin_at      = db.Column(db.DateTime(timezone=True))
    period          = db.Column(db.String(10))
    origin_room     = db.Column(db.String(10), nullable=False)  # main room (where pass starts)
    room_out        = db.synonym("origin_room")
    room_in         = db.Column(db.String(10))  # where the student ends up
    is_override     = db.Column(db.Boolean, default=False)
    note            = db.Column(db.Text)
    status          = db.Column(db.String, default="pending_start", nullable=False)
    total_pass_time = db.Column(db.Integer)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending_start','active','pending_return','returned')"
        ),
        db.UniqueConstraint(
            "student_id", "checkin_at", name="uq_student_one_open_pass"
        ),
    )

    # Legacy support — alias origin_room as .station
    @property
    def station(self):
        return self.origin_room

    @station.setter
    def station(self, val):
        self.origin_room = val

    # Helpers for legacy time-only fields
    @property
    def checkout_time(self):
        return self.checkout_at.time() if self.checkout_at else None

    @checkout_time.setter
    def checkout_time(self, t):
        if t is None:
            self.checkout_at = None
        else:
            self.checkout_at = datetime.combine(datetime.utcnow().date(), t)

    @property
    def checkin_time(self):
        return self.checkin_at.time() if self.checkin_at else None

    @checkin_time.setter
    def checkin_time(self, t):
        if t is None:
            self.checkin_at = None
        else:
            self.checkin_at = datetime.combine(datetime.utcnow().date(), t)


# ─────────────────────────────────────────────────────────────────────────────
# Swipe Log (PassEvent)
# ─────────────────────────────────────────────────────────────────────────────
class PassEvent(db.Model):
    __tablename__ = "pass_events"

    id        = db.Column(db.Integer, primary_key=True)
    pass_id   = db.Column(db.Integer, db.ForeignKey("passes.id", ondelete="CASCADE"), nullable=False)
    station   = db.Column(db.String(50), nullable=False)  # Where the swipe happened
    event     = db.Column(db.String(20), nullable=False)  # "in" or "out"
    timestamp = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    pass_ref = db.relationship("Pass", backref="events")


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log Table
# ─────────────────────────────────────────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String, db.ForeignKey("users.id"))
    time       = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    reason     = db.Column(db.String(255), nullable=False)
