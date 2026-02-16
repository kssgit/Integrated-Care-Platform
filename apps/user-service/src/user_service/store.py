from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from devkit.db import AsyncDatabaseManager, Base, create_all_tables, create_schema_if_not_exists
from devkit.timezone import now_kst_iso
from sqlalchemy import Boolean, DateTime, JSON, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from user_service.models import UserPreference, UserRecord

_USER_SCHEMA = "user"
_INTEGRATION_SCHEMA = "integration"


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": _USER_SCHEMA}

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    auth_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    auth_source: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    phone_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserPreferenceORM(Base):
    __tablename__ = "preferences"
    __table_args__ = {"schema": _USER_SCHEMA}

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preferred_language: Mapped[str] = mapped_column(String(16), nullable=False, default="ko")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLogORM(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": _INTEGRATION_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserStore:
    def __init__(self, database_url: str | None = None) -> None:
        self._users: dict[str, UserRecord] = {}
        self._preferences: dict[str, UserPreference] = {}
        self._audit_logs: list[dict[str, Any]] = []
        self._db = AsyncDatabaseManager(database_url) if database_url else None
        self._orm_ready = False

    async def ensure_ready(self) -> None:
        await self._ensure_orm_ready()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.disconnect()

    async def create_user(self, user: UserRecord) -> UserRecord:
        if self._db is None:
            self._users[user.user_id] = user
            return user

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(UserORM, user.user_id)
            if row is None:
                row = UserORM(
                    user_id=user.user_id,
                    email=user.email,
                    role=user.role,
                    auth_user_id=user.auth_user_id,
                    auth_source=user.auth_source,
                    status=user.status,
                    phone_encrypted=user.phone_encrypted,
                    phone_hash=user.phone_hash,
                    profile_data=user.profile_data,
                    deleted_at=self._parse_dt(user.deleted_at),
                    created_at=self._parse_dt(user.created_at) or datetime.now().astimezone(),
                    updated_at=self._parse_dt(user.updated_at) or datetime.now().astimezone(),
                )
                session.add(row)
            else:
                row.email = user.email
                row.role = user.role
                row.auth_user_id = user.auth_user_id
                row.auth_source = user.auth_source
                row.status = user.status
                row.phone_encrypted = user.phone_encrypted
                row.phone_hash = user.phone_hash
                row.profile_data = user.profile_data
                row.deleted_at = self._parse_dt(user.deleted_at)
                row.updated_at = datetime.now().astimezone()
            return self._to_user_record(row)

        return await self._db.run_with_session(_run)

    async def ensure_user(
        self,
        *,
        user_id: str,
        email: str,
        role: str,
        auth_user_id: str | None = None,
        auth_source: str = "local",
        profile_data: dict[str, Any] | None = None,
    ) -> tuple[UserRecord, bool]:
        existing = await self.get_user(user_id)
        if existing is not None:
            return existing, False
        created = await self.create_user(
            UserRecord(
                user_id=user_id,
                email=email.lower(),
                role=role,
                auth_user_id=auth_user_id or user_id,
                auth_source=auth_source,
                status="active",
                profile_data=profile_data or {},
            )
        )
        return created, True

    async def get_user(self, user_id: str) -> UserRecord | None:
        if self._db is None:
            return self._users.get(user_id)

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(UserORM, user_id)
            if row is None:
                return None
            return self._to_user_record(row)

        return await self._db.run_with_session(_run)

    async def update_user(self, user_id: str, updates: dict[str, Any]) -> UserRecord | None:
        if self._db is None:
            user = self._users.get(user_id)
            if not user:
                return None
            for key, value in updates.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            user.updated_at = now_kst_iso()
            return user

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(UserORM, user_id)
            if row is None:
                return None
            for key in (
                "email",
                "role",
                "auth_user_id",
                "auth_source",
                "status",
                "phone_encrypted",
                "phone_hash",
                "profile_data",
            ):
                if key in updates and updates[key] is not None:
                    setattr(row, key, updates[key])
            if "deleted_at" in updates:
                row.deleted_at = self._parse_dt(updates["deleted_at"])
            row.updated_at = datetime.now().astimezone()
            return self._to_user_record(row)

        return await self._db.run_with_session(_run)

    async def soft_delete_user(self, user_id: str) -> bool:
        if self._db is None:
            user = self._users.get(user_id)
            if not user:
                return False
            now = now_kst_iso()
            user.deleted_at = now
            user.updated_at = now
            return True

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(UserORM, user_id)
            if row is None:
                return False
            now = datetime.now().astimezone()
            row.deleted_at = now
            row.updated_at = now
            return True

        return await self._db.run_with_session(_run)

    async def set_preference(self, preference: UserPreference) -> UserPreference:
        if self._db is None:
            self._preferences[preference.user_id] = preference
            return preference

        await self._ensure_orm_ready()
        now = datetime.now().astimezone()

        async def _run(session):
            row = await session.get(UserPreferenceORM, preference.user_id)
            extra_payload = {
                "care_type": preference.care_type,
                "location_lat": preference.location_lat,
                "location_lng": preference.location_lng,
                "search_radius_km": preference.search_radius_km,
                "notification_settings": preference.notification_settings,
            }
            notification_enabled = bool(preference.notification_settings.get("enabled", True))
            preferred_language = str(preference.notification_settings.get("preferred_language", "ko"))
            if row is None:
                row = UserPreferenceORM(
                    user_id=preference.user_id,
                    notification_enabled=notification_enabled,
                    preferred_language=preferred_language,
                    extra=extra_payload,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.notification_enabled = notification_enabled
                row.preferred_language = preferred_language
                row.extra = extra_payload
                row.updated_at = now
            return self._to_preference(row)

        return await self._db.run_with_session(_run)

    async def get_preference(self, user_id: str) -> UserPreference | None:
        if self._db is None:
            return self._preferences.get(user_id)

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(UserPreferenceORM, user_id)
            if row is None:
                return None
            return self._to_preference(row)

        return await self._db.run_with_session(_run)

    async def add_audit_log(
        self,
        *,
        actor_user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str,
    ) -> None:
        if self._db is None:
            self._audit_logs.append(
                {
                    "actor_user_id": actor_user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "ip_address": ip_address,
                    "accessed_at": now_kst_iso(),
                }
            )
            return

        await self._ensure_orm_ready()

        async def _run(session):
            session.add(
                AuditLogORM(
                    actor_user_id=actor_user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    ip_address=ip_address,
                    payload={},
                    created_at=datetime.now().astimezone(),
                )
            )

        await self._db.run_with_session(_run)

    async def snapshot(self) -> dict[str, Any]:
        if self._db is None:
            return {
                "users": [asdict(item) for item in self._users.values()],
                "preferences": [asdict(item) for item in self._preferences.values()],
                "audit_logs": list(self._audit_logs),
            }

        await self._ensure_orm_ready()

        async def _run(session):
            users = [self._to_user_record(row).__dict__ for row in (await session.scalars(select(UserORM))).all()]
            prefs = [self._to_preference(row).__dict__ for row in (await session.scalars(select(UserPreferenceORM))).all()]
            audits = []
            for row in (await session.scalars(select(AuditLogORM))).all():
                audits.append(
                    {
                        "actor_user_id": row.actor_user_id,
                        "resource_type": row.resource_type,
                        "resource_id": row.resource_id,
                        "action": row.action,
                        "ip_address": row.ip_address,
                        "accessed_at": row.created_at.isoformat() if row.created_at else None,
                    }
                )
            return {"users": users, "preferences": prefs, "audit_logs": audits}

        return await self._db.run_with_session(_run)

    async def _ensure_orm_ready(self) -> None:
        if self._db is None or self._orm_ready:
            return
        await self._db.connect()
        await create_schema_if_not_exists(self._db.engine, _USER_SCHEMA)
        await create_schema_if_not_exists(self._db.engine, _INTEGRATION_SCHEMA)
        await create_all_tables(self._db.engine, Base.metadata)
        self._orm_ready = True

    def _to_user_record(self, row: UserORM) -> UserRecord:
        return UserRecord(
            user_id=row.user_id,
            email=row.email,
            role=row.role,
            auth_user_id=row.auth_user_id,
            auth_source=row.auth_source,
            status=row.status,
            phone_encrypted=row.phone_encrypted,
            phone_hash=row.phone_hash,
            profile_data=row.profile_data or {},
            deleted_at=row.deleted_at.isoformat() if row.deleted_at else None,
            created_at=row.created_at.isoformat() if row.created_at else now_kst_iso(),
            updated_at=row.updated_at.isoformat() if row.updated_at else now_kst_iso(),
        )

    def _to_preference(self, row: UserPreferenceORM) -> UserPreference:
        extra = row.extra or {}
        if not isinstance(extra, dict):
            extra = {}
        settings = extra.get("notification_settings", {})
        if not isinstance(settings, dict):
            settings = {}
        settings.setdefault("enabled", row.notification_enabled)
        settings.setdefault("preferred_language", row.preferred_language)
        return UserPreference(
            user_id=row.user_id,
            care_type=str(extra.get("care_type", "senior")),
            location_lat=extra.get("location_lat"),
            location_lng=extra.get("location_lng"),
            search_radius_km=int(extra.get("search_radius_km", 5)),
            notification_settings=settings,
        )

    def _parse_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
