"""Auth application service: register, login, current-user validation, logout."""

from __future__ import annotations

from backend.domain.auth import (
    AuthError,
    AuthUser,
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)
from backend.infrastructure.repositories.user_repository import UserRepository


class AuthService:
    """Orchestrates auth use-cases against a :class:`UserRepository`."""

    def __init__(
        self,
        repo: UserRepository,
        jwt_secret: str,
        jwt_expires_seconds: int = 3600,
    ) -> None:
        self._repo = repo
        self._jwt_secret = jwt_secret
        self._jwt_expires_seconds = jwt_expires_seconds

    def register(self, email: str, username: str, password: str) -> AuthUser:
        """Create a new user and return the persisted :class:`AuthUser`.

        Raises :class:`AuthError` if *email* or *username* is already taken.
        """
        if self._repo.email_exists(email):
            raise AuthError("Email is already registered")
        if self._repo.username_exists(username):
            raise AuthError("Username is already taken")

        password_hash = hash_password(password)
        return self._repo.create(email=email, username=username, password_hash=password_hash)

    def login(self, email: str, password: str) -> str:
        """Validate credentials and return a signed JWT access token.

        Raises :class:`AuthError` if the credentials are invalid.
        """
        user = self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")

        return issue_token(
            user_id=user.id,
            secret=self._jwt_secret,
            expires_seconds=self._jwt_expires_seconds,
        )

    def get_current_user(self, token: str) -> AuthUser:
        """Decode *token* and return the corresponding :class:`AuthUser`.

        Raises :class:`TokenError` for invalid/expired tokens, or
        :class:`AuthError` if the encoded user no longer exists.
        """
        user_id = verify_token(token, self._jwt_secret)
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise AuthError("User not found")
        return user

    def logout(self, token: str) -> None:  # noqa: ARG002
        """Signal logout.

        JWT tokens are stateless; client-side discards the token to invalidate it.
        This method is a no-op server-side but provides a stable interface for
        future token blocklist support if needed.
        """
