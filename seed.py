"""Load dummy sample students (safe, fake data). Run once: python seed.py"""
import database as db

SAMPLE = [
    {"name": "Aarav Sharma", "date_of_birth": "2004-03-14", "email": "aarav@example.com", "phone": "+91 9000000001", "course": "Python", "enrollment_date": "2024-07-01"},
    {"name": "Diya Patel", "date_of_birth": "2006-08-22", "email": "diya@example.com", "course": "Data Science", "enrollment_date": "2024-07-01"},
    {"name": "Rohan Mehta", "date_of_birth": "2005-01-30", "phone": "+91 9000000003", "course": "Python", "enrollment_date": "2024-08-10"},
    {"name": "Isha Verma", "date_of_birth": "2007-11-05", "email": "isha@example.com", "course": "Web Development", "enrollment_date": "2025-01-15"},
    {"name": "Kabir Singh", "date_of_birth": "2003-06-18", "email": "kabir@example.com", "course": "Data Science", "enrollment_date": "2023-07-01"},
    {"name": "Meera Nair", "date_of_birth": "2006-02-09", "email": "meera@example.com", "course": "Python", "enrollment_date": "2024-09-05"},
]

if __name__ == "__main__":
    db.init_db()
    if db.count_students() > 0:
        print("Database already has students; skipping seed.")
    else:
        for s in SAMPLE:
            db.create_student(s)
        print(f"Inserted {len(SAMPLE)} dummy students into {db.db_path()}")
