"""
One-time setup: creates the database, a default admin account, and loads
all the skill roadmaps — all in a single command.

Run this ONCE, before starting the server:
    python setup.py

Then start the server normally:
    python app.py
"""

from app import app, db, User
from seed_data import seed

with app.app_context():
    db.create_all()

    if not User.query.filter_by(role="admin").first():
        admin = User(name="Admin", email="admin@skillpath.com", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Created admin login -> email: admin@skillpath.com  password: admin123")
    else:
        print("Admin account already exists — skipping.")

seed()

print("\nSetup complete. Now run:  python app.py")
