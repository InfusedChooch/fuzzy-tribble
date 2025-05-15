from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# --- Student Table ---
class Student(db.Model):
    __tablename__ = 'students'
    id       = db.Column(db.String, primary_key=True)           # ⬅ ID as string
    name     = db.Column(db.String(100), nullable=False)
    schedule = db.Column(db.JSON, nullable=True)                # ⬅ Schedule JSON

    passes = db.relationship('Pass', backref='student', lazy=True)
    audits = db.relationship('AuditLog', backref='student', lazy=True)


# --- Pass Table ---
class Pass(db.Model):
    __tablename__ = 'passes'
    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.String, db.ForeignKey('students.id'), nullable=False)
    date             = db.Column(db.Date, default=datetime.utcnow)
    period           = db.Column(db.String(10))
    checkout_time    = db.Column(db.Time)
    checkin_time     = db.Column(db.Time)
    station           = db.Column(db.String(50), nullable=True)  # (intentional typo kept)
    total_pass_time  = db.Column(db.Integer)
    note             = db.Column(db.Text)
    is_override      = db.Column(db.Boolean, default=False)
    status           = db.Column(db.String, default="pending")


# --- Audit Log Table ---
class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String, db.ForeignKey('students.id'), nullable=True)
    time       = db.Column(db.DateTime, default=datetime.utcnow)
    reason     = db.Column(db.String(255), nullable=False)


# --- Pass Log Table ---
class PassLog(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    pass_id     = db.Column(db.Integer, db.ForeignKey('passes.id'), nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    station     = db.Column(db.String(50), nullable=False)
    event_type  = db.Column(db.String(20), nullable=False)

    pass_ref = db.relationship("Pass", backref="logs")
