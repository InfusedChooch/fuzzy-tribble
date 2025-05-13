# scripts/rebuild_db.py

import os, sys, json
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import create_app
from src.models import db, Student, Pass, AuditLog, PassLog

app = create_app()

def rebuild_database():
    db_path = os.path.join("src", "data", "hallpass.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️  Old database deleted.")

    with app.app_context():
        db.create_all()
        print("✅ New database created.")

        # --- Load students ---
        try:
            df = pd.read_csv("seed/masterlist.csv")
            for _, row in df.iterrows():
                schedule = json.loads(row['Schedule'])
                student_id = str(row['ID']).strip()  # ✅ force string ID
                print(f"Adding student: {student_id} - {row['Name']}")

                student = Student(id=student_id, name=row['Name'], schedule=schedule)
                db.session.add(student)
            print(f"✅ Loaded {len(df)} students.")
        except Exception as e:
            print(f"⚠️ Error loading students: {e}")

        # --- Load audit logs ---
        try:
            with open("seed/auditlog.json") as f:
                audit_data = json.load(f)
                for entry in audit_data:
                    log = AuditLog(
                        student_id = str(entry.get("student_id")),
                        reason     = entry.get("reason"),
                        time       = datetime.fromisoformat(entry["time"])
                    )
                    db.session.add(log)
                print(f"✅ Loaded {len(audit_data)} audit logs.")
        except Exception as e:
            print(f"⚠️ Error loading audit logs: {e}")

        # --- Load pass logs ---
        try:
            with open("seed/passlog.json") as f:
                pass_data = json.load(f)
                for entry in pass_data:
                    print("Loading pass entry:", entry.get("id", "N/A"))

                    p = Pass(
                        id              = entry["id"],
                        student_id      = str(entry["student_id"]),  # ✅ ensure string
                        date            = datetime.fromisoformat(entry["date"]).date(),
                        period          = entry["period"],
                        checkout_time   = datetime.strptime(entry["checkout_time"], "%H:%M:%S").time(),
                        checkin_time    = datetime.strptime(entry["checkin_time"], "%H:%M:%S").time() if entry.get("checkin_time") else None,
                        station          = entry.get("station"),
                        total_pass_time = entry.get("total_pass_time", 0),
                        note            = entry.get("note"),
                        is_override     = entry.get("is_override", False),
                        status          = entry.get("status", "returned")
                    )
                    db.session.add(p)

                    logs = entry.get("logs") or []
                    if isinstance(logs, str):
                        print(f"⚠️ Skipping malformed logs in pass ID {entry['id']}: expected list, got string.")
                        continue

                    for log in logs:
                        pl = PassLog(
                            pass_id    = entry["id"],
                            station    = log["station"],
                            event_type = log["event_type"],
                            timestamp  = datetime.fromisoformat(log["timestamp"])
                        )
                        db.session.add(pl)

                print(f"✅ Loaded {len(pass_data)} passes and logs.")
        except Exception as e:
            print(f"⚠️ Error loading passes: {e}")

        db.session.commit()
        print("🎉 Database seed complete.")

if __name__ == "__main__":
    rebuild_database()
