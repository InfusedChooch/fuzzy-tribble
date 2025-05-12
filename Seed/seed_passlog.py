import json
from datetime import datetime
from src.models import db, Pass
from src.database import create_app

app = create_app()
PASSLOG_FILE = "seed/passlog.json"

with app.app_context():
    with open(PASSLOG_FILE, "r") as f:
        passlog = json.load(f)

    for student_id, records in passlog.items():
        for entry in records:
            checkout_time = datetime.strptime(entry["CheckoutTime"], "%H:%M:%S").time()
            checkin_time = datetime.strptime(entry["CheckinTime"], "%H:%M:%S").time()
            date = datetime.strptime(entry["Date"], "%Y-%m-%d").date()

            p = Pass(
                student_id=int(student_id),
                period=entry["Period"],
                date=date,
                checkout_time=checkout_time,
                checkin_time=checkin_time,
                total_pass_time=int(entry["TotalPassTime"])
            )
            db.session.add(p)

    db.session.commit()
    print("✅ Pass data migrated from passlog.json")
