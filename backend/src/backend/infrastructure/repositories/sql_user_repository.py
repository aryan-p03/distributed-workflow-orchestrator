"""SQLAlchemy-backed user repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.auth import AuthUser
from backend.infrastructure.db.models import User
from backend.infrastructure.repositories.user_repository import UserRepository


def _to_auth_user(row: User) -> AuthUser:
    return AuthUser(
        id=row.id,
        email=row.email,
        username=row.username,
        password_hash=row.password_hash,
        created_at=row.created_at,
    )


class SqlUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> AuthUser | None:
        row = self._session.get(User, user_id)
        return _to_auth_user(row) if row is not None else None

    def get_by_email(self, email: str) -> AuthUser | None:
        row = self._session.query(User).filter_by(email=email).first()
        return _to_auth_user(row) if row is not None else None

    def email_exists(self, email: str) -> bool:
        return self._session.query(User).filter_by(email=email).count() > 0

    def username_exists(self, username: str) -> bool:
        return self._session.query(User).filter_by(username=username).count() > 0

    def create(self, email: str, username: str, password_hash: str) -> AuthUser:
        row = User(email=email, username=username, password_hash=password_hash)
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return _to_auth_user(row)
