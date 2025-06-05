#!/usr/bin/env python3
# scripts/build_student_periods.py
# Splits masterlist.csv into users.csv, student_schedule.csv, and teacher_schedule.csv.

import csv, json, sys
from pathlib import Path

# ─── Setup Paths ─────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
SEED_DIR    = ROOT / "Seed"
SCRIPT_DIR  = Path(__file__).resolve().parent

DEFAULT_ML  = SEED_DIR / "masterlist.csv"
FALLBACK_ML = SCRIPT_DIR / "masterlist.csv"

USERS_CSV         = SEED_DIR / "users.csv"
STUDENT_SCHED_CSV = SEED_DIR / "student_schedule.csv"
TEACHER_SCHED_CSV = SEED_DIR / "teacher_schedule.csv"

PERIOD_LIST = ["0", "1", "2", "3", "4/5", "5/6", "6/7", "7/8", "9", "10", "11", "12"]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def safe_field(p):
    return f"period_{p.replace('/', '_')}"

# ─── Main Execution ──────────────────────────────────────────────────────────
def main():
    masterlist = DEFAULT_ML if DEFAULT_ML.exists() else FALLBACK_ML
    if not masterlist.exists():
        sys.exit("❌ masterlist.csv not found in Seed or local directory.")
    print(f"📄 Using: {masterlist.relative_to(ROOT)}")

    with (
        masterlist.open(newline="", encoding="utf-8") as src,
        USERS_CSV.open("w", newline="", encoding="utf-8") as f_users,
        STUDENT_SCHED_CSV.open("w", newline="", encoding="utf-8") as f_stu_sched,
        TEACHER_SCHED_CSV.open("w", newline="", encoding="utf-8") as f_tea_sched,
    ):
        reader  = csv.DictReader(src)
        w_user  = csv.writer(f_users)
        w_stu   = csv.writer(f_stu_sched)
        w_tea   = csv.writer(f_tea_sched)

        user_header   = ["id", "name", "email", "role", "password"]
        sched_header  = ["student_id"] + [safe_field(p) for p in PERIOD_LIST]

        w_user.writerow(user_header)
        w_stu.writerow(sched_header)
        w_tea.writerow(["teacher_id"] + [safe_field(p) for p in PERIOD_LIST])

        for raw_row in reader:
            row = {
                (k.strip().lower() if k else ""): (v or "").strip()
                for k, v in raw_row.items() if k
            }

            sid   = row.get("student_id") or row.get("id")
            name  = row.get("name")
            email = row.get("email") or f"{sid}@example.org"
            role  = row.get("role", "student").lower()
            blob  = row.get("schedule", "")

            if not sid or not name:
                print(f"⚠️  Skipping row with missing ID/Name → {raw_row}")
                continue

            w_user.writerow([sid, name, email, role, sid])  # password = ID

            if role == "student":
                try:
                    sched = json.loads(blob) if blob.strip().startswith("{") else {}
                except json.JSONDecodeError:
                    print(f"⚠️  Bad schedule JSON for {sid}; skipping")
                    sched = {}

                out = [sid] + [sched.get(p, "") for p in PERIOD_LIST]
                w_stu.writerow(out)
            else:
                w_tea.writerow([sid] + [""] * len(PERIOD_LIST))

    print(f"✅ Wrote: {USERS_CSV.relative_to(ROOT)}")
    print(f"✅ Wrote: {STUDENT_SCHED_CSV.relative_to(ROOT)}")
    print(f"✅ Wrote: {TEACHER_SCHED_CSV.relative_to(ROOT)}")

if __name__ == "__main__":
    main()

