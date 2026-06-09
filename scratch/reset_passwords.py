import sys
sys.path.append('/Users/krishnagarg/smartonboard-main/backend')
from db.session import SessionLocal
from models.user import User
from core.security import hash_password

db = SessionLocal()
try:
    users = db.query(User).all()
    hashed_pwd = hash_password("Password123!")
    for u in users:
        u.password_hash = hashed_pwd
        print(f"Resetting password_hash for: {u.email}")
    db.commit()
    print("Passwords successfully reset to 'Password123!'")
except Exception as e:
    db.rollback()
    print(f"Error resetting passwords: {e}")
finally:
    db.close()
