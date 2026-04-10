from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from services.common.config import Settings
from services.common.models import UserAccount, UserSessionRecord
from services.retriever.repositories.chat_repository import ChatRepository
from services.retriever.schemas.auth import AdminUserRead, AuthLoginResponse, AuthMeResponse, CurrentUserRead, PasswordChangeResponse


DEFAULT_PASSWORD = "Passw0rd!"
SUPPORTED_ROLES = {"admin", "user", "student"}


@dataclass(slots=True)
class AuthContext:
    user: UserAccount
    session: UserSessionRecord
    token: str
    refreshed_token: str | None = None


class AuthManager:
    def __init__(self, *, repository: ChatRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self.password_hasher = PasswordHasher()

    def bootstrap_users(self) -> None:
        users_path = Path(self.settings.users_file)
        if not users_path.exists():
            return
        payload = json.loads(users_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("users.json must contain an array")
        active_usernames: set[str] = set()
        fallback_user_id: int | None = None
        default_hash = self.hash_password(DEFAULT_PASSWORD)
        for item in payload:
            username = str(item["username"]).strip()
            displayname = str(item["displayname"]).strip()
            role = str(item["role"]).strip().lower()
            if role not in SUPPORTED_ROLES:
                raise ValueError(f"Unsupported role in users.json for {username}: {role}")
            active_usernames.add(username)
            user = self.repository.upsert_bootstrap_user(
                username=username,
                displayname=displayname,
                role=role,
                password_hash=default_hash,
            )
            if self.verify_password(DEFAULT_PASSWORD, user.password_hash) and not user.force_password_change:
                updated = self.repository.update_user(user.id, force_password_change=True)
                if updated is not None:
                    user = updated
            if fallback_user_id is None and user.status == "active":
                fallback_user_id = user.id
        self.repository.deactivate_users_not_in(active_usernames)
        if fallback_user_id is not None:
            self.repository.assign_orphaned_records_to_user(fallback_user_id)

    def hash_password(self, password: str) -> str:
        return self.password_hasher.hash(f"{password}{self.settings.password_salt}")

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return self.password_hasher.verify(password_hash, f"{password}{self.settings.password_salt}")
        except VerifyMismatchError:
            return False

    def login(self, username: str, password: str) -> AuthLoginResponse:
        user = self.repository.get_user_by_username(username.strip())
        if user is None or user.status != "active":
            raise PermissionError("Invalid username or password")
        if not self.verify_password(password, user.password_hash):
            raise PermissionError("Invalid username or password")
        token, session = self._issue_session(user)
        return AuthLoginResponse(
            token=token,
            expires_at=session.expires_at,
            max_expires_at=session.max_expires_at,
            user=self._map_current_user(user),
        )

    def authenticate_token(self, token: str) -> AuthContext:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as error:
            raise PermissionError("Invalid or expired session") from error
        session_id = str(payload.get("sid") or "").strip()
        user_id = int(payload.get("sub") or 0)
        if not session_id or user_id <= 0:
            raise PermissionError("Invalid or expired session")
        session = self.repository.get_user_session(session_id)
        user = self.repository.get_user_by_id(user_id)
        now = datetime.now(UTC)
        if session is None or user is None or user.status != "active":
            raise PermissionError("Invalid or expired session")
        if session.revoked_at is not None or now >= session.max_expires_at or now >= session.expires_at:
            raise PermissionError("Invalid or expired session")
        refreshed_token: str | None = None
        if now >= session.last_refreshed_at + timedelta(minutes=self.settings.jwt_refresh_threshold_minutes):
            new_expiry = min(now + timedelta(minutes=self.settings.jwt_expiration_minutes), session.max_expires_at)
            session = self.repository.refresh_user_session(
                session.id,
                last_refreshed_at=now,
                last_activity_at=now,
                expires_at=new_expiry,
            ) or session
            refreshed_token = self._encode_token(user, session)
        else:
            session = self.repository.update_user_session_activity(session.id, last_activity_at=now) or session
        return AuthContext(user=user, session=session, token=token, refreshed_token=refreshed_token)

    def logout(self, session_id: str) -> None:
        self.repository.revoke_user_session(session_id, revoked_at=datetime.now(UTC))

    def change_password(
        self,
        *,
        auth: AuthContext,
        current_password: str | None,
        new_password: str,
        confirm_password: str,
    ) -> PasswordChangeResponse:
        if not new_password.strip():
            raise ValueError("New password cannot be empty")
        if new_password != confirm_password:
            raise ValueError("New password and confirmation do not match")
        if not auth.user.force_password_change:
            if not current_password or not self.verify_password(current_password, auth.user.password_hash):
                raise PermissionError("Current password is incorrect")
        updated = self.repository.update_user(
            auth.user.id,
            password_hash=self.hash_password(new_password),
            force_password_change=False,
        )
        assert updated is not None
        self.repository.revoke_all_user_sessions(updated.id, revoked_at=datetime.now(UTC))
        token, session = self._issue_session(updated)
        return PasswordChangeResponse(
            token=token,
            user=self._map_current_user(updated),
            expires_at=session.expires_at,
            max_expires_at=session.max_expires_at,
        )

    def me(self, auth: AuthContext) -> AuthMeResponse:
        return AuthMeResponse(
            user=self._map_current_user(auth.user),
            expires_at=auth.session.expires_at,
            max_expires_at=auth.session.max_expires_at,
        )

    def require_admin(self, auth: AuthContext) -> None:
        if auth.user.role != "admin":
            raise PermissionError("Admin access required")

    def list_users(self) -> list[AdminUserRead]:
        return [self._map_admin_user(user) for user in self.repository.list_users()]

    def create_user(self, *, username: str, displayname: str, role: str) -> AdminUserRead:
        normalized_role = role.strip().lower()
        if normalized_role not in SUPPORTED_ROLES:
            raise ValueError("Unsupported role")
        if self.repository.get_user_by_username(username.strip()) is not None:
            raise ValueError("Username already exists")
        user = self.repository.create_user(
            username=username.strip(),
            displayname=displayname.strip(),
            role=normalized_role,
            password_hash=self.hash_password(DEFAULT_PASSWORD),
            status="active",
            force_password_change=True,
        )
        return self._map_admin_user(user)

    def update_user(self, user_id: int, **fields: object) -> AdminUserRead | None:
        user = self.repository.update_user(user_id, **fields)
        if user is None:
            return None
        return self._map_admin_user(user)

    def delete_user(self, *, actor: AuthContext, user_id: int) -> AdminUserRead | None:
        if actor.user.id == user_id:
            raise ValueError("Admin cannot delete own account")
        user = self.repository.delete_user(user_id)
        if user is None:
            return None
        return self._map_admin_user(user)

    def _issue_session(self, user: UserAccount) -> tuple[str, UserSessionRecord]:
        now = datetime.now(UTC)
        expiry = now + timedelta(minutes=self.settings.jwt_expiration_minutes)
        max_expiry = now + timedelta(minutes=self.settings.jwt_max_lifetime_minutes)
        session = self.repository.create_user_session(
            session_id=str(uuid.uuid4()),
            user_id=user.id,
            issued_at=now,
            last_refreshed_at=now,
            last_activity_at=now,
            expires_at=expiry,
            max_expires_at=max_expiry,
        )
        return self._encode_token(user, session), session

    def _encode_token(self, user: UserAccount, session: UserSessionRecord) -> str:
        return jwt.encode(
            {
                "sub": str(user.id),
                "sid": session.id,
                "username": user.username,
                "role": user.role,
                "exp": int(session.expires_at.timestamp()),
                "iat": int(session.issued_at.timestamp()),
            },
            self.settings.jwt_secret,
            algorithm="HS256",
        )

    def _map_current_user(self, user: UserAccount) -> CurrentUserRead:
        return CurrentUserRead(
            id=user.id,
            username=user.username,
            displayname=user.displayname,
            role=user.role,
            status=user.status,
            force_password_change=user.force_password_change,
        )

    def _map_admin_user(self, user: UserAccount) -> AdminUserRead:
        return AdminUserRead(
            id=user.id,
            username=user.username,
            displayname=user.displayname,
            role=user.role,
            status=user.status,
            force_password_change=user.force_password_change,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
