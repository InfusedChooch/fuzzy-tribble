#!/usr/bin/env python3
"""
Split Seed/masterlist.csv →  Seed/users.csv  +  Seed/student_periods.csv

• Accepts headers in ANY case:  student_id / ID / id   and   Name / name
• Adds a 'role' column (default 'student') and raw-ID password.
• Teachers (role ≠ student) go only to users.csv.

Run:
    python scripts/build_student_periods.py
"""

import csv, json, sys
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[1]
SEED_DIR   = ROOT / "Seed"
MASTERLIST = SEED_DIR / "masterlist.csv"

USERS_CSV   = SEED_DIR / "users.csv"
PERIODS_CSV = SEED_DIR / "student_periods.csv"


def main() -> None:
    if not MASTERLIST.exists():
        sys.exit(f"❌ masterlist.csv not found at {MASTERLIST}")

    with (
        MASTERLIST.open(newline="", encoding="utf-8") as src,
        USERS_CSV.open("w", newline="", encoding="utf-8") as f_users,
        PERIODS_CSV.open("w", newline="", encoding="utf-8") as f_periods,
    ):
        reader  = csv.DictReader(src)
        w_user  = csv.writer(f_users)
        w_per   = csv.writer(f_periods)

        # headers expected by rebuild_db.py
        w_user.writerow(["id", "name", "email", "role", "password"])
        w_per.writerow(["student_id", "period", "room"])

        for raw_row in reader:
            # ---------- lower-case every key once ----------
            row = {k.strip().lower(): (v or "").strip() for k, v in raw_row.items()}

            sid   = row.get("student_id") or row.get("id")
            name  = row.get("name")
            email = row.get("email") or f"{sid}@example.org"
            role  = row.get("role", "student").lower()
            blob  = row.get("schedule", "{}")

            if not sid or not name:
                print(f"⚠️  Skipping row with missing ID/Name → {raw_row}")
                continue

            # ---------- users.csv ----------
            w_user.writerow([sid, name, email, role, sid])  # raw ID = default password

            # ---------- student_periods.csv (students only) ----------
            if role != "student":
                continue

            try:
                sched = json.loads(blob) if blob else {}
            except json.JSONDecodeError:
                print(f"⚠️  Bad JSON schedule for {sid}; skipping periods")
                continue

            for period, room in sched.items():
                if period and room:
                    w_per.writerow([sid, str(period), str(room)])

    print(f"✅ Wrote {USERS_CSV.relative_to(ROOT)}")
    print(f"✅ Wrote {PERIODS_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
