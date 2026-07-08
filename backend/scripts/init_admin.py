"""Seed the first admin user.

Usage::

    cd backend
    uv run python scripts/init_admin.py               # default: admin / admin123
    uv run python scripts/init_admin.py admin mypass   # custom username + password

The script is idempotent — if the user already exists it just exits with a
message.
"""

import asyncio
import sys
import os

# Make sure .env is loaded before anything else
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from app.database import async_session_factory
from app.models.user import User
from app.services.auth_service import hash_password
from sqlalchemy import select


async def init_admin(
    username: str = "admin",
    password: str = "admin123",
    email: str | None = None,
) -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.username == username))
        existing = result.scalar_one_or_none()
        if existing is not None:
            if existing.is_admin:
                print(f"Admin user '{username}' already exists (is_admin=True).")
            else:
                existing.is_admin = True
                await db.commit()
                print(f"User '{username}' already existed — promoted to admin.")
            return

        user = User(
            username=username,
            hashed_password=hash_password(password),
            nickname=username,
            email=email,
            is_admin=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Admin user '{username}' created (id={user.id}, is_admin=True).")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin"
    asyncio.run(init_admin(username, password))
