# scripts/build_student_periods.py
"""
Create student_periods.csv from masterlist.csv

Assumes masterlist.csv header is either:
    ID,Name,Schedule          – OR –
    student_id,name,schedule

Writes:
    - student_periods.csv with: student_id,period,room
    - student_list.csv with:    student_id,name
"""

import csv, json, os, sys
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "Seed"
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"

def build_periods():
    src  = SCRIPT_DIR / "masterlist.csv"
    out_periods = SEED_DIR / "student_periods.csv"
    out_list    = SEED_DIR / "students.csv"

    if not src.exists():
        sys.exit("❌ masterlist.csv not found")

    with src.open(newline="") as f_src, \
         out_periods.open("w", newline="") as f_periods, \
         out_list.open("w", newline="") as f_list:

        reader   = csv.DictReader(f_src)
        writer_p = csv.writer(f_periods)
        writer_s = csv.writer(f_list)

        writer_p.writerow(["student_id", "period", "room"])
        writer_s.writerow(["student_id", "name"])

        for row in reader:
            # normalise column names
            sid   = row.get("student_id") or row.get("ID")
            name  = row.get("name")       or row.get("Name")
            blob  = row.get("schedule")   or row.get("Schedule") or "{}"

            # write name list
            writer_s.writerow([sid.strip(), name.strip()])

            # parse and write period data
            try:
                sched = json.loads(blob)
            except json.JSONDecodeError:
                print(f"⚠️  bad JSON for student {sid}; skipping")
                continue

            for period, room in sched.items():
                writer_p.writerow([sid.strip(), str(period), room.strip()])

    print(f"✅ student_periods.csv written → {out_periods}")
    print(f"✅ student_list.csv written    → {out_list}")

if __name__ == "__main__":
    build_periods()
