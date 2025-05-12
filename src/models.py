from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy instance (to be initialized in app factory later)
db = SQLAlchemy()

# --- Student Table ---
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    period = db.Column(db.String(10), nullable=False)
    course = db.Column(db.String(100), nullable=True)

    passes = db.relationship('Pass', backref='student', lazy=True)
    audits = db.relationship('AuditLog', backref='student', lazy=True)

# --- Pass Table ---
class Pass(db.Model):
    __tablename__ = 'passes'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    period = db.Column(db.String(10))
    checkout_time = db.Column(db.Time)
    checkin_time = db.Column(db.Time)
    sation = db.Column(db.String(50), nullable=True)
    total_pass_time = db.Column(db.Integer)  # stored as seconds
    note = db.Column(db.Text)
    is_override = db.Column(db.Boolean, default=False)


# --- Audit Log Table ---
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.String(255), nullable=False)


class PassLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pass_id = db.Column(db.Integer, db.ForeignKey('passes.id'), nullable=False)  # <-- fix here
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    station = db.Column(db.String(50), nullable=False)

    pass_ref = db.relationship("Pass", backref="logs")

