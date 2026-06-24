import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from db.session import SessionLocal, tenant_context
from models import User

email = "cand_steep_1782333529206@example.com"
db = SessionLocal()
try:
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == email))
        if user:
            print(f"FOUND USER: id={user.id}, email={user.email}, role={user.role}, is_active={user.is_active}")
        else:
            print("USER NOT FOUND")
            # Let's list the last 5 users
            users = db.scalars(select(User).order_by(User.id.desc()).limit(5)).all()
            for u in users:
                print(f"LAST USER: id={u.id}, email={u.email}, role={u.role}")
finally:
    db.close()
