import csv
from src.models import db, Student
from src.database import create_app

app = create_app()

# Path to your masterlist.csv
CSV_FILE = "seed/masterlist.csv"

with app.app_context():
    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            student = Student(
                id=int(row['ID']),
                name=row['Name'],
                course=row.get('Course', ''),
                period=str(row['Period'])
            )
            db.session.merge(student)  # merge avoids duplicate keys
        db.session.commit()
    print("✅ Students imported from masterlist.csv")
