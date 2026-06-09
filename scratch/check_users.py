import sys
sys.path.append('/Users/krishnagarg/smartonboard-main/backend')
from db.session import SessionLocal
from models.user import User

db = SessionLocal()
try:
    users = db.query(User).all()
    print(f"Found {len(users)} users in database:")
    for u in users:
        print(f"Email: {u.email}, Role: {u.role}")
finally:
    db.close()
