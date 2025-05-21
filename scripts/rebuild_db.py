# scripts/rebuild_db.py

import os, sys, shutil, csv
from datetime import datetime, timedelta
import pandas as pd
from werkzeug.security import generate_password_hash

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

def parse_dt(val):
    if pd.isna(val) or val == "":
        return None
    return pd.to_datetime(val, utc=True).to_pydatetime()

def rebuild_database():
    archive_existing_db()

    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Fresh database created.")

        # ---------------- users ----------------
        try:
            df = pd.read_csv(os.path.join(SEED_DIR, "users.csv"))
            df.columns = [c.strip().lower() for c in df.columns]
            required_fields = {"id", "name", "email", "role", "password"}
            if missing := (required_fields - set(df.columns)):
                raise ValueError(f"Missing columns in users.csv: {missing}")
            df["password"] = df["password"].apply(lambda raw: generate_password_hash(str(raw)))
            db.session.bulk_insert_mappings(User, df.to_dict("records"))
            print(f"✅ Loaded {len(df)} users.")
        except Exception as e:
            print(f"⚠️  users.csv load error: {e}")

        # ---------------- student_schedule ----------------
        try:
            df = pd.read_csv(os.path.join(SEED_DIR, "student_schedule.csv"))
            db.session.bulk_insert_mappings(StudentSchedule, df.to_dict("records"))
            print(f"✅ Loaded {len(df)} student schedules.")
        except Exception as e:
            print(f"⚠️  student_schedule.csv load error: {e}")

        # ---------------- teacher_schedule ----------------
        try:
            df = pd.read_csv(os.path.join(SEED_DIR, "teacher_schedule.csv"))
            db.session.bulk_insert_mappings(TeacherSchedule, df.to_dict("records"))
            print(f"✅ Loaded {len(df)} teacher schedules.")
        except Exception as e:
            print(f"⚠️  teacher_schedule.csv load error: {e}")

        # ---------------- generate student_periods from student_schedule ----------------
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
            # ---------------- passes ------------------ 
            try:
                df = pd.read_csv(os.path.join(SEED_DIR, "passes.csv"))
                df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
                df["checkout_at"] = df["checkout_at"].apply(parse_dt)
                df["checkin_at"]  = df["checkin_at"].apply(parse_dt)
                db.session.bulk_insert_mappings(Pass, df.to_dict("records"))
                print(f"✅ Loaded {len(df)} passes.")
            except FileNotFoundError:
                print("ℹ️  passes.csv not found – skipping.")
            except Exception as e:
                print(f"⚠️  passes.csv load error: {e}")

            # ------------- pass events ---------------- 
            try:
                df = pd.read_csv(os.path.join(SEED_DIR, "pass_events.csv"))
                df["timestamp"] = df["timestamp"].apply(parse_dt)
                db.session.bulk_insert_mappings(PassEvent, df.to_dict("records"))
                print(f"✅ Loaded {len(df)} pass events.")
            except FileNotFoundError:
                print("ℹ️  pass_events.csv not found – skipping.")
            except Exception as e:
                print(f"⚠️  pass_events.csv load error: {e}")

            # -------------- audit log ----------------- 
            try:
                df = pd.read_csv(os.path.join(SEED_DIR, "audit_log.csv"))
                df["time"] = df["time"].apply(parse_dt)
                db.session.bulk_insert_mappings(AuditLog, df.to_dict("records"))
                print(f"✅ Loaded {len(df)} audit entries.")
            except FileNotFoundError:
                print("ℹ️  audit_log.csv not found – skipping.")
            except Exception as e:
                print(f"⚠️  audit_log.csv load error: {e}")
        else:
            print("🧹 Clean rebuild — skipped passes, events, audit logs.")

        db.session.commit()
        print("🎉 Rebuild complete — data/hallpass.db ready.")

if __name__ == "__main__":
    rebuild_database()
