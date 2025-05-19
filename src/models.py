from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

# ---------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------
class Student(db.Model):
    __tablename__ = "students"

    student_id       = db.Column(db.String, primary_key=True)           # student ID
    name     = db.Column(db.String(100), nullable=False)

    # relationships
    passes   = db.relationship("Pass",        backref="student", lazy=True)
    audits   = db.relationship("AuditLog",    backref="student", lazy=True)
    periods  = db.relationship("StudentPeriod", backref="student", lazy=True)


class StudentPeriod(db.Model):
    """
    Normalised class schedule – one row per period.
    """
    __tablename__ = "student_periods"

    student_id = db.Column(
        db.String, db.ForeignKey("students.student_id"), primary_key=True
    )
    period     = db.Column(db.String(10), primary_key=True)
    room       = db.Column(db.String(10), nullable=False)

# ---------------------------------------------------------------------
# Passes
# ---------------------------------------------------------------------
class Pass(db.Model):
    __tablename__ = "passes"

    id          = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=func.current_date())
    student_id  = db.Column(db.String, db.ForeignKey("students.student_id"), nullable=False)

    # using full-timestamp columns going forward
    checkout_at = db.Column(db.DateTime(timezone=True), nullable=False)
    checkin_at  = db.Column(db.DateTime(timezone=True))
    period        = db.Column(db.String(10))
    origin_room   = db.Column(db.String(10), nullable=False)   # real column
    room_out = db.synonym("origin_room")
    room_in     = db.Column(db.String(10))
    is_override   = db.Column(db.Boolean, default=False)
    note          = db.Column(db.Text)
    status        = db.Column(
        db.String,
        default="pending_start",
        nullable=False
    )
    total_pass_time = db.Column(db.Integer)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending_start','active','pending_return','returned')"
        ),
        db.UniqueConstraint(
            "student_id", "checkin_at", name="uq_student_one_open_pass"
        ),
    )

    # -----------------------------------------------------------------
    # Back-compat shims
    # -----------------------------------------------------------------
    @property
    def station(self):
        """Alias for old code that still expects .station."""
        return self.origin_room

    @station.setter
    def station(self, val):
        self.origin_room = val

    # Legacy time-only helpers (checkout_time / checkin_time)
    @property
    def checkout_time(self):
        return self.checkout_at.time() if self.checkout_at else None

    @checkout_time.setter
    def checkout_time(self, t):
        """
        Accepts a datetime.time and stores a full timestamp today.
        """
        if t is None:
            self.checkout_at = None
        else:
            self.checkout_at = datetime.combine(
                datetime.utcnow().date(), t
            )

    @property
    def checkin_time(self):
        return self.checkin_at.time() if self.checkin_at else None

    @checkin_time.setter
    def checkin_time(self, t):
        if t is None:
            self.checkin_at = None
        else:
            self.checkin_at = datetime.combine(
                datetime.utcnow().date(), t
            )

# ---------------------------------------------------------------------
# Station swipe logs  (new preferred name)
# ---------------------------------------------------------------------
class PassEvent(db.Model):
    """
    Each IN / OUT swipe recorded by a kiosk.
    """
    __tablename__ = "pass_events"

    id        = db.Column(db.Integer, primary_key=True)
    pass_id   = db.Column(
        db.Integer,
        db.ForeignKey("passes.id", ondelete="CASCADE"),
        nullable=False
    )
    station   = db.Column(db.String(50), nullable=False)
    event     = db.Column(db.String(20), nullable=False)          # 'in' / 'out'
    timestamp = db.Column(db.DateTime(timezone=True),
                          default=datetime.utcnow)

    pass_ref = db.relationship("Pass", backref="events")

# ---------------------------------------------------------------------
# Legacy swipe logs  (routes/passlog.py still imports PassLog)
# ---------------------------------------------------------------------
class PassLog(db.Model):
    """
    Thin wrapper around the same idea as PassEvent.
    Left here only so existing imports keep working.
    """
    __tablename__ = "pass_log"

    id        = db.Column(db.Integer, primary_key=True)
    pass_id   = db.Column(
        db.Integer,
        db.ForeignKey("passes.id", ondelete="CASCADE"),
        nullable=False
    )
    station   = db.Column(db.String(50), nullable=False)
    event     = db.Column(db.String(20), nullable=False)          # 'in' / 'out'
    timestamp = db.Column(db.DateTime(timezone=True),
                          default=datetime.utcnow)

    pass_ref = db.relationship("Pass", backref="logs")

    # backward-compat alias
    @property
    def event_type(self):
        return self.event

    @event_type.setter
    def event_type(self, value):
        self.event = value

# ---------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String, db.ForeignKey("students.student_id"))
    time       = db.Column(db.DateTime(timezone=True),
                           default=datetime.utcnow)
    reason     = db.Column(db.String(255), nullable=False)