"""Dev-only startup seed: ensures a default super admin exists so the frontend
has something to log in with on a fresh database. Run via `python -m app.seed`
(wired into `entrypoint.sh` after migrations). No-ops if `default_admin_email`
is blank or a user with that email already exists.
"""

import asyncio
import uuid
from datetime import datetime, timezone

import app.models_registry  # noqa: F401 -- registers all tables before use
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.modules.users.domain.entities import UserEntity
from app.modules.users.infrastructure.repository import SqlAlchemyUserRepository
from app.shared.enums import Role

settings = get_settings()


async def seed_default_admin() -> None:
    if not settings.default_admin_email or not settings.default_admin_password:
        print("[seed] DEFAULT_ADMIN_EMAIL/PASSWORD not set, skipping admin seed.")
        return

    async with async_session_factory() as session:
        repository = SqlAlchemyUserRepository(session)
        existing = await repository.get_by_email(settings.default_admin_email)
        if existing is not None:
            print(f"[seed] Admin {settings.default_admin_email} already exists, skipping.")
            return

        now = datetime.now(timezone.utc)
        admin = UserEntity(
            id=uuid.uuid4(),
            name=settings.default_admin_name,
            email=settings.default_admin_email,
            password_hash=hash_password(settings.default_admin_password),
            cpf=None,
            phone=None,
            role=Role.SUPER_ADMIN,
            project_id=None,
            department_id=None,
            avatar_url=None,
            active=True,
            first_access=False,
            created_at=now,
            updated_at=now,
        )
        await repository.create(admin)
        print(f"[seed] Created default admin: {settings.default_admin_email}")


if __name__ == "__main__":
    asyncio.run(seed_default_admin())
