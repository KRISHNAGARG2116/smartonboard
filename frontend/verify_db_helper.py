import sys
import argparse
from sqlalchemy import select
# Add backend to path
sys.path.append("../backend")
from db.session import SessionLocal, tenant_context
from models import User, Company

def verify_user(email):
    db = SessionLocal()
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.email_verified = True
            db.add(user)
            db.commit()
            print(f"SUCCESS: Marked {email} as verified.")
        else:
            print(f"ERROR: User {email} not found.")
    db.close()

def cleanup_user(email):
    db = SessionLocal()
    with tenant_context(auth_mode="true"):
        user = db.scalar(select(User).where(User.email == email))
        if user:
            company_id = user.company_id
            db.delete(user)
            db.commit()
            print(f"SUCCESS: Deleted user {email}.")
            if company_id:
                company = db.scalar(select(Company).where(Company.id == company_id))
                if company:
                    db.delete(company)
                    db.commit()
                    print(f"SUCCESS: Deleted company {company.name}.")
        else:
            print(f"User {email} already cleaned up or not found.")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", type=str)
    parser.add_argument("--cleanup", type=str)
    args = parser.parse_args()
    
    if args.verify:
        verify_user(args.verify)
    elif args.cleanup:
        cleanup_user(args.cleanup)
