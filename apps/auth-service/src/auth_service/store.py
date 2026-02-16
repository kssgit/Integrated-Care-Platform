from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import secrets
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from devkit.db import AsyncDatabaseManager, Base, create_all_tables, create_schema_if_not_exists
from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from shared.security import Role, ensure_roles

_AUTH_SCHEMA = "auth"
_PASSWORD_ALGO = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 310000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS)
    return (
        f"{_PASSWORD_ALGO}${_PASSWORD_ITERATIONS}$"
        f"{salt.hex()}$"
        f"{digest.hex()}"
    )


def verify_password(password: str, encoded: str) -> bool:
    parts = encoded.split("$")
    if len(parts) != 4 or parts[0] != _PASSWORD_ALGO:
        return hmac.compare_digest(password, encoded)
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


class UserAlreadyExistsError(RuntimeError):
    pass


@dataclass
class AuthUser:
    user_id: str
    email: str
    role: str
    auth_source: str
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class SSOLoginResult:
    user: AuthUser
    is_signup: bool
    linked_existing_account: bool


class AuthUserORM(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": _AUTH_SCHEMA}

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="guardian")
    auth_source: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuthSSOIdentityORM(Base):
    __tablename__ = "sso_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_auth_sso_provider_subject"),
        {"schema": _AUTH_SCHEMA},
    )

    identity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuthStore:
    def __init__(
        self,
        *,
        database_url: str | None,
        bootstrap_users: dict[str, dict[str, str]],
    ) -> None:
        self._bootstrap_users = bootstrap_users
        self._use_db = bool(database_url and database_url.startswith("postgresql"))
        self._db = AsyncDatabaseManager(database_url) if self._use_db and database_url else None
        self._orm_ready = False
        self._users: dict[str, dict[str, str]] = {
            email.lower(): {
                "password_hash": hash_password(values["password"]),
                "role": values["role"],
                "auth_source": "local",
            }
            for email, values in bootstrap_users.items()
        }
        self._sso_map: dict[tuple[str, str], str] = {}

    async def close(self) -> None:
        if self._db is not None:
            await self._db.disconnect()

    async def ensure_ready(self) -> None:
        await self._ensure_orm_ready()

    async def signup_local(self, *, email: str, password: str, role: str) -> AuthUser:
        normalized_email = email.lower().strip()
        normalized_role = role if ensure_roles(role, {item for item in Role}) else Role.GUARDIAN.value
        if self._db is None:
            if normalized_email in self._users:
                raise UserAlreadyExistsError("email already exists")
            self._users[normalized_email] = {
                "password_hash": hash_password(password),
                "role": normalized_role,
                "auth_source": "local",
            }
            return AuthUser(
                user_id=normalized_email,
                email=normalized_email,
                role=normalized_role,
                auth_source="local",
            )

        await self._ensure_orm_ready()

        async def _run(session):
            row = AuthUserORM(
                user_id=normalized_email,
                email=normalized_email,
                password_hash=hash_password(password),
                role=normalized_role,
                auth_source="local",
                is_active=True,
            )
            session.add(row)
            return row

        try:
            saved = await self._db.run_with_session(_run)
        except IntegrityError as exc:
            raise UserAlreadyExistsError("email already exists") from exc
        return self._to_user(saved)

    async def authenticate_local(self, *, email: str, password: str) -> AuthUser | None:
        normalized_email = email.lower().strip()
        if self._db is None:
            row = self._users.get(normalized_email)
            if not row:
                return None
            if not verify_password(password, row["password_hash"]):
                return None
            return AuthUser(
                user_id=normalized_email,
                email=normalized_email,
                role=row["role"],
                auth_source=row.get("auth_source", "local"),
            )

        await self._ensure_orm_ready()

        async def _run(session):
            query = select(AuthUserORM).where(AuthUserORM.email == normalized_email, AuthUserORM.is_active.is_(True))
            return (await session.scalars(query)).first()

        user = await self._db.run_with_session(_run)
        if user is None or not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return self._to_user(user)

    async def get_user_by_id(self, user_id: str) -> AuthUser | None:
        if self._db is None:
            row = self._users.get(user_id)
            if row is None:
                return None
            return AuthUser(
                user_id=user_id,
                email=user_id,
                role=row["role"],
                auth_source=row.get("auth_source", "local"),
            )

        await self._ensure_orm_ready()

        async def _run(session):
            return await session.get(AuthUserORM, user_id)

        row = await self._db.run_with_session(_run)
        if row is None:
            return None
        return self._to_user(row)

    async def login_with_sso(
        self,
        *,
        provider: str,
        provider_subject: str,
        email: str | None,
        role: str = "guardian",
    ) -> SSOLoginResult:
        provider_key = provider.lower().strip()
        subject_key = provider_subject.strip()
        normalized_email = email.lower().strip() if email else None
        normalized_role = role if ensure_roles(role, {item for item in Role}) else Role.GUARDIAN.value

        if self._db is None:
            existing_user_id = self._sso_map.get((provider_key, subject_key))
            if existing_user_id:
                user = self._users[existing_user_id]
                return SSOLoginResult(
                    user=AuthUser(
                        user_id=existing_user_id,
                        email=existing_user_id,
                        role=user["role"],
                        auth_source=user["auth_source"],
                    ),
                    is_signup=False,
                    linked_existing_account=False,
                )
            linked_existing = False
            if normalized_email and normalized_email in self._users:
                user_id = normalized_email
                linked_existing = True
            else:
                user_id = normalized_email or self._build_sso_user_id(provider_key, subject_key)
                self._users[user_id] = {
                    "password_hash": "",
                    "role": normalized_role,
                    "auth_source": "sso",
                }
            self._sso_map[(provider_key, subject_key)] = user_id
            row = self._users[user_id]
            return SSOLoginResult(
                user=AuthUser(user_id=user_id, email=user_id, role=row["role"], auth_source=row["auth_source"]),
                is_signup=not linked_existing,
                linked_existing_account=linked_existing,
            )

        await self._ensure_orm_ready()

        async def _run(session):
            identity_query = select(AuthSSOIdentityORM).where(
                AuthSSOIdentityORM.provider == provider_key,
                AuthSSOIdentityORM.provider_subject == subject_key,
            )
            identity = (await session.scalars(identity_query)).first()
            if identity is not None:
                user = await session.get(AuthUserORM, identity.user_id)
                identity.last_login_at = datetime.now().astimezone()
                if normalized_email:
                    identity.email = normalized_email
                if user is None:
                    raise RuntimeError("sso identity mapped user is missing")
                return SSOLoginResult(
                    user=self._to_user(user),
                    is_signup=False,
                    linked_existing_account=False,
                )

            linked_existing = False
            user: AuthUserORM | None = None
            if normalized_email:
                email_query = select(AuthUserORM).where(AuthUserORM.email == normalized_email)
                user = (await session.scalars(email_query)).first()
                if user is not None:
                    linked_existing = True

            if user is None:
                user_id = normalized_email or self._build_sso_user_id(provider_key, subject_key)
                user = AuthUserORM(
                    user_id=user_id,
                    email=normalized_email or user_id,
                    password_hash=None,
                    role=normalized_role,
                    auth_source="sso",
                    is_active=True,
                )
                session.add(user)

            identity = AuthSSOIdentityORM(
                identity_id=self._build_identity_id(provider_key, subject_key),
                provider=provider_key,
                provider_subject=subject_key,
                user_id=user.user_id,
                email=normalized_email,
                last_login_at=datetime.now().astimezone(),
            )
            session.add(identity)

            return SSOLoginResult(
                user=self._to_user(user),
                is_signup=not linked_existing,
                linked_existing_account=linked_existing,
            )

        return await self._db.run_with_session(_run)

    async def _ensure_orm_ready(self) -> None:
        if self._db is None or self._orm_ready:
            return
        await self._db.connect()
        await create_schema_if_not_exists(self._db.engine, _AUTH_SCHEMA)
        await create_all_tables(self._db.engine, Base.metadata)
        await self._seed_bootstrap_users()
        self._orm_ready = True

    async def _seed_bootstrap_users(self) -> None:
        if self._db is None:
            return

        async def _run(session):
            for email, values in self._bootstrap_users.items():
                normalized_email = email.lower()
                existing = await session.get(AuthUserORM, normalized_email)
                if existing is not None:
                    continue
                role = values["role"] if ensure_roles(values["role"], {item for item in Role}) else Role.GUARDIAN.value
                session.add(
                    AuthUserORM(
                        user_id=normalized_email,
                        email=normalized_email,
                        password_hash=hash_password(values["password"]),
                        role=role,
                        auth_source="local",
                        is_active=True,
                    )
                )

        await self._db.run_with_session(_run)

    def _to_user(self, row: AuthUserORM) -> AuthUser:
        return AuthUser(
            user_id=row.user_id,
            email=row.email,
            role=row.role,
            auth_source=row.auth_source,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def _build_sso_user_id(self, provider: str, subject: str) -> str:
        return f"sso-{uuid5(NAMESPACE_URL, f'{provider}:{subject}').hex}"

    def _build_identity_id(self, provider: str, subject: str) -> str:
        return uuid5(NAMESPACE_URL, f"identity:{provider}:{subject}").hex
