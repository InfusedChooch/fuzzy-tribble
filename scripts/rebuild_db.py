# scripts/rebuild_db.py
# Rebuilds the database from CSV seed files; optionally loads logs and passes in full mode.

import os, sys, shutil, csv
from datetime import datetime, timedelta
import pandas as pd
from werkzeug.security import generate_password_hash

# ─── Path Setup ─────────────────────────────────────────────────────────────
ROOT_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.database import create_app
from src.models   import db, User, StudentSchedule, TeacherSchedule, StudentPeriod, Pass, PassEvent, AuditLog

SEED_DIR  = os.path.join(ROOT_DIR, "Seed")
DATA_DIR  = os.path.join(ROOT_DIR, "data")
DB_FILE   = os.path.join(DATA_DIR, "hallpass.db")
PURGE_DIR = os.path.join(DATA_DIR, "purge")
os.makedirs(PURGE_DIR, exist_ok=True)

FULL_MODE = "--full" in sys.argv

# ─── Archive Old Database ───────────────────────────────────────────────────
def archive_existing_db():
    if not os.path.isfile(DB_FILE):
        print("ℹ️  No existing hallpass.db to archive.")
        return
    cutoff = datetime.now() - timedelta(days=7)
    for fname in os.listdir(PURGE_DIR):
        if fname.endswith(".db"):
            fpath = os.path.join(PURGE_DIR, fname)
            try:
                if datetime.fromtimestamp(os.path.getmtime(fpath)) < cutoff:
                    os.remove(fpath)
            except Exception:
                pass
    tag  = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(DB_FILE, os.path.join(PURGE_DIR, f"{tag}_hallpass.db"))
    print(f"🗃️  Archived previous DB → purge/{tag}_hallpass.db")

# ─── Helpers ────────────────────────────────────────────────────────────────
def parse_dt(val):
    if pd.isna(val) or val == "":
        return None
    return pd.to_datetime(val, utc=True).to_pydatetime()

# ─── Main Routine ───────────────────────────────────────────────────────────
def rebuild_database():
    archive_existing_db()
    app = create_app()

    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Fresh database created.")

        # Load Users
        try:
            df = pd.read_csv(os.path.join(SEED_DIR, "users.csv"))
            df.columns = [c.strip().lower() for c in df.columns]
            required = {"id", "name", "email", "role", "password"}
            if missing := (required - set(df.columns)):
                raise ValueError(f"Missing columns in users.csv: {missing}")
            df["password"] = df["password"].apply(lambda raw: generate_password_hash(str(raw)))
            db.session.bulk_insert_mappings(User, df.to_dict("records"))
            print(f"✅ Loaded {len(df)} users.")
        except Exception as e:
            print(f"⚠️  users.csv load error: {e}")

        # Load Schedules
        for fname, model, label in [
            ("student_schedule.csv", StudentSchedule, "student schedules"),
            ("teacher_schedule.csv", TeacherSchedule, "teacher schedules")
        ]:
            try:
                df = pd.read_csv(os.path.join(SEED_DIR, fname))
                db.session.bulk_insert_mappings(model, df.to_dict("records"))
                print(f"✅ Loaded {len(df)} {label}.")
            except Exception as e:
                print(f"⚠️  {fname} load error: {e}")

        # Derive StudentPeriod from StudentSchedule
        try:
            all_scheds = StudentSchedule.query.all()
            count = 0
            for sched in all_scheds:
                for key, val in vars(sched).items():
                    if key.startswith("period_") and val:
                        period = key.replace("period_", "").replace("_", "/")
                        db.session.add(StudentPeriod(student_id=sched.student_id, period=period, room=val))
                        count += 1
            db.session.commit()
            print(f"✅ Generated {count} student-period rows from StudentSchedule.")
        except Exception as e:
            print(f"⚠️  Error generating student_periods: {e}")

        if FULL_MODE:
            # Optional: Load pass records and logs
            for fname, model, parse_map, label in [
                ("passes.csv", Pass, {"date": "date", "checkout_at": "datetime", "checkin_at": "datetime"}, "passes"),
                ("pass_events.csv", PassEvent, {"timestamp": "datetime"}, "pass events"),
                ("audit_log.csv", AuditLog, {"time": "datetime"}, "audit entries")
            ]:
                try:
                    df = pd.read_csv(os.path.join(SEED_DIR, fname))
                    for col, ptype in parse_map.items():
                        if ptype == "date":
                            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
                        else:
                            df[col] = df[col].apply(parse_dt)
                    db.session.bulk_insert_mappings(model, df.to_dict("records"))
                    print(f"✅ Loaded {len(df)} {label}.")
                except FileNotFoundError:
                    print(f"ℹ️  {fname} not found – skipping.")
                except Exception as e:
                    print(f"⚠️  {fname} load error: {e}")
        else:
            print("🧹 Clean rebuild — skipped passes, events, audit logs.")

        db.session.commit()
        print("🎉 Rebuild complete — data/hallpass.db ready.")

if __name__ == "__main__":
    rebuild_database()

