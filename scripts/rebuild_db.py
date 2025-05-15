import os
import sys
import json
import shutil
import pandas as pd
from datetime import datetime, timedelta

# ✅ Set project root and fix path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

print("sys.path:", sys.path)  # Debugging help

from src.database import create_app
from src.models import db, Student, Pass, AuditLog, PassLog


# ──────────────────────────── paths ──────────────────────────────
ROOT_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEED_DIR  = os.path.join(ROOT_DIR, "Seed")
DATA_DIR  = os.path.join(ROOT_DIR, "data")
DB_FILE   = os.path.join(DATA_DIR, "hallpass.db")
PURGE_DIR = os.path.join(DATA_DIR, "purge")
os.makedirs(PURGE_DIR, exist_ok=True)

# allow `import src.*`
sys.path.insert(0, ROOT_DIR)

from src.database import create_app        # <-- your app factory
from src.models   import db, Student, Pass, AuditLog, PassLog

# ────────────────────── helper: archive and purge ────────────────
def archive_existing_db():
    if not os.path.isfile(DB_FILE):
        print("ℹ️  No existing hallpass.db to archive.")
        return

    # purge backups older than 7 days
    cutoff = datetime.now() - timedelta(days=7)
    for fname in os.listdir(PURGE_DIR):
        if fname.endswith(".db"):
            fpath = os.path.join(PURGE_DIR, fname)
            try:
                if datetime.fromtimestamp(os.path.getmtime(fpath)) < cutoff:
                    os.remove(fpath)
                    print(f"🗑️  Removed old backup {fname}")
            except Exception as e:
                print(f"⚠️  Could not delete {fname}: {e}")

    # move current DB → purge/YYYYMMDD_hallpass.db
    tag  = datetime.now().strftime("%Y%m%d")
    dest = os.path.join(PURGE_DIR, f"{tag}_hallpass.db")
    try:
        shutil.move(DB_FILE, dest)
        print(f"🗃️  Archived previous DB → {dest}")
    except PermissionError:
        print("❌ hallpass.db is in use. Close all apps using it and rerun.")
        sys.exit(1)

# ──────────────────────── main rebuild ───────────────────────────
def rebuild_database():
    archive_existing_db()

    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Fresh database created.")

        # ---------- students ----------
        try:
            df = pd.read_csv(os.path.join(SEED_DIR, "masterlist.csv"))
            for _, row in df.iterrows():
                db.session.add(Student(
                    id       = str(row["ID"]).strip(),
                    name     = row["Name"],
                    schedule = json.loads(row["Schedule"])
                ))
            print(f"✅ Loaded {len(df)} students.")
        except Exception as e:
            print(f"⚠️  Student load error: {e}")

        # ---------- audit logs ----------
        try:
            with open(os.path.join(SEED_DIR, "auditlog.json")) as f:
                audits = json.load(f)
            for a in audits:
                db.session.add(AuditLog(
                    student_id = str(a.get("student_id")),
                    reason     = a["reason"],
                    time       = datetime.fromisoformat(a["time"])
                ))
            print(f"✅ Loaded {len(audits)} audit entries.")
        except Exception as e:
            print(f"⚠️  Audit‑log load error: {e}")

        # ---------- passes + logs ----------
        try:
            with open(os.path.join(SEED_DIR, "passlog.json")) as f:
                grouped = json.load(f)
            pcount = 0
            for stu_id, plist in grouped.items():
                for p in plist:
                    db.session.add(Pass(
                        id              = p["id"],
                        student_id      = stu_id,
                        date            = datetime.fromisoformat(p["date"]).date(),
                        period          = p["period"],
                        checkout_time   = datetime.strptime(p["checkout_time"], "%H:%M:%S").time(),
                        checkin_time    = datetime.strptime(p["checkin_time"], "%H:%M:%S").time() \
                                            if p.get("checkin_time") else None,
                        station         = p.get("station"),
                        total_pass_time = p.get("total_pass_time", 0),
                        note            = p.get("note"),
                        is_override     = p.get("is_override", False),
                        status          = p.get("status", "returned")
                    ))
                    for log in p.get("logs", []):
                        db.session.add(PassLog(
                            pass_id    = p["id"],
                            station    = log["station"],
                            event_type = log["event_type"],
                            timestamp  = datetime.fromisoformat(log["timestamp"])
                        ))
                    pcount += 1
            print(f"✅ Loaded {pcount} passes.")
        except Exception as e:
            print(f"⚠️  Pass‑log load error: {e}")

        db.session.commit()
        print("🎉 Rebuild complete — data/hallpass.db ready.")

if __name__ == "__main__":
    rebuild_database()
