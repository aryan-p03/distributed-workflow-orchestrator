"""Abstract user repository interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.domain.auth import AuthUser


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> AuthUser | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> AuthUser | None: ...

    @abstractmethod
    def email_exists(self, email: str) -> bool: ...

    @abstractmethod
    def username_exists(self, username: str) -> bool: ...

    @abstractmethod
    def create(self, email: str, username: str, password_hash: str) -> AuthUser: ...
