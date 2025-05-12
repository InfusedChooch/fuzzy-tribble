import json
from datetime import datetime
from src.models import db, AuditLog
from src.database import create_app

app = create_app()
AUDITLOG_FILE = "see/auditlog.json"

with app.app_context():
    with open(AUDITLOG_FILE, "r") as f:
        audits = json.load(f)

    for entry in audits:
        try:
            log = AuditLog(
                student_id=int(entry.get("student_id")) if entry.get("student_id").isdigit() else None,
                time=datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S"),
                reason=entry["reason"]
            )
            db.session.add(log)
        except Exception as e:
            print(f"❌ Skipped entry due to error: {e} — {entry}")

    db.session.commit()
    print("✅ Audit log imported from auditlog.json")
