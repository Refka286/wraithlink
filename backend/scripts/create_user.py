import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.security import hash_password
from app.database import SessionLocal
from app.models.enums import UserRole
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description="Create an AegisPen user account.")
    parser.add_argument("email")
    parser.add_argument("password")
    parser.add_argument("--role", choices=[role.value for role in UserRole], default=UserRole.reader.value)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).one_or_none()
        if existing is not None:
            print(f"user '{args.email}' already exists")
            return

        user = User(
            email=args.email,
            hashed_password=hash_password(args.password),
            role=UserRole(args.role),
        )
        db.add(user)
        db.commit()
        print(f"created user '{args.email}' with role '{args.role}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
