from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any

from devkit.db import AsyncDatabaseManager, Base
from devkit.timezone import now_kst_iso
from sqlalchemy import Integer, String, Text, select, text
from sqlalchemy.orm import Mapped, mapped_column


@dataclass
class FacilityPatchAuditRecord:
    facility_id: str
    actor_user_id: str
    reason: str
    applied_fields: list[str]
    patch: dict[str, Any]
    created_at: str


@dataclass
class PipelineRunAuditRecord:
    action: str
    dag_id: str
    dag_run_id: str
    state: str
    provider: str | None
    conf: dict[str, Any]
    requested_by: str
    created_at: str


class FacilityPatchAuditORM(Base):
    __tablename__ = "facility_patch_audit"
    __table_args__ = {"schema": "admin"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    applied_fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    patch_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class PipelineRunAuditORM(Base):
    __tablename__ = "pipeline_run_audit"
    __table_args__ = {"schema": "admin"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    dag_id: Mapped[str] = mapped_column(String(255), nullable=False)
    dag_run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=True)
    conf_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class AdminStore:
    def __init__(self, dsn: str | None) -> None:
        self._dsn = dsn
        self._db = AsyncDatabaseManager(dsn) if dsn else None
        self._orm_ready = False

    async def close(self) -> None:
        if self._db is not None:
            await self._db.disconnect()

    async def patch_facility(
        self,
        *,
        facility_id: str,
        patch: dict[str, Any],
        reason: str,
        actor_user_id: str,
    ) -> tuple[dict[str, Any], FacilityPatchAuditRecord]:
        if self._db is None:
            raise RuntimeError("DATABASE_URL is required for admin operations")
        await self._ensure_orm_ready()

        facility_table = '"facility".facilities'
        now = now_kst_iso()

        async def _run(session):
            row = (
                await session.execute(
                    text(
                        f"SELECT facility_id, name, district_code, address, lat, lng, metadata_json, updated_at "
                        f"FROM {facility_table} WHERE facility_id = :facility_id"
                    ),
                    {"facility_id": facility_id},
                )
            ).mappings().first()
            if row is None:
                return None

            applied_fields: list[str] = []
            updates: dict[str, Any] = {}

            for field in ("name", "address", "lat", "lng"):
                if field in patch:
                    updates[field] = patch[field]
                    applied_fields.append(field)

            if "metadata" in patch:
                updates["metadata_json"] = json.dumps(patch["metadata"], ensure_ascii=True)
                applied_fields.append("metadata")

            if updates:
                updates["updated_at"] = now
                set_clause = ", ".join(f"{key} = :{key}" for key in updates.keys())
                await session.execute(
                    text(f"UPDATE {facility_table} SET {set_clause} WHERE facility_id = :facility_id"),
                    {"facility_id": facility_id, **updates},
                )

            refreshed = (
                await session.execute(
                    text(
                        f"SELECT facility_id, name, district_code, address, lat, lng, metadata_json, updated_at "
                        f"FROM {facility_table} WHERE facility_id = :facility_id"
                    ),
                    {"facility_id": facility_id},
                )
            ).mappings().one()

            patch_audit = FacilityPatchAuditORM(
                facility_id=facility_id,
                actor_user_id=actor_user_id,
                reason=reason,
                applied_fields_json=json.dumps(applied_fields, ensure_ascii=True),
                patch_json=json.dumps(patch, ensure_ascii=True),
                created_at=now,
            )
            session.add(patch_audit)

            metadata_obj = {}
            try:
                metadata_obj = json.loads(refreshed["metadata_json"] or "{}")
            except Exception:
                metadata_obj = {}

            return {
                "facility": {
                    "facility_id": refreshed["facility_id"],
                    "name": refreshed["name"],
                    "district_code": refreshed["district_code"],
                    "address": refreshed["address"],
                    "lat": float(refreshed["lat"]),
                    "lng": float(refreshed["lng"]),
                    "metadata": metadata_obj if isinstance(metadata_obj, dict) else {},
                    "updated_at": refreshed["updated_at"],
                },
                "audit": FacilityPatchAuditRecord(
                    facility_id=facility_id,
                    actor_user_id=actor_user_id,
                    reason=reason,
                    applied_fields=applied_fields,
                    patch=patch,
                    created_at=now,
                ),
            }

        result = await self._db.run_with_session(_run)
        if result is None:
            raise LookupError("facility not found")
        return result["facility"], result["audit"]

    async def list_facility_patch_audit(self, facility_id: str) -> list[FacilityPatchAuditRecord]:
        if self._db is None:
            raise RuntimeError("DATABASE_URL is required for admin operations")
        await self._ensure_orm_ready()

        async def _run(session):
            stmt = (
                select(FacilityPatchAuditORM)
                .where(FacilityPatchAuditORM.facility_id == facility_id)
                .order_by(FacilityPatchAuditORM.id.desc())
            )
            rows = (await session.scalars(stmt)).all()
            return [
                FacilityPatchAuditRecord(
                    facility_id=row.facility_id,
                    actor_user_id=row.actor_user_id,
                    reason=row.reason,
                    applied_fields=json.loads(row.applied_fields_json or "[]"),
                    patch=json.loads(row.patch_json or "{}"),
                    created_at=row.created_at,
                )
                for row in rows
            ]

        return await self._db.run_with_session(_run)

    async def add_pipeline_run_audit(
        self,
        *,
        action: str,
        dag_id: str,
        dag_run_id: str,
        state: str,
        provider: str | None,
        conf: dict[str, Any],
        requested_by: str,
    ) -> PipelineRunAuditRecord:
        if self._db is None:
            raise RuntimeError("DATABASE_URL is required for admin operations")
        await self._ensure_orm_ready()
        now = now_kst_iso()

        async def _run(session):
            row = PipelineRunAuditORM(
                action=action,
                dag_id=dag_id,
                dag_run_id=dag_run_id,
                state=state,
                provider=provider,
                conf_json=json.dumps(conf, ensure_ascii=True),
                requested_by=requested_by,
                created_at=now,
            )
            session.add(row)
            return PipelineRunAuditRecord(
                action=action,
                dag_id=dag_id,
                dag_run_id=dag_run_id,
                state=state,
                provider=provider,
                conf=conf,
                requested_by=requested_by,
                created_at=now,
            )

        return await self._db.run_with_session(_run)

    async def list_pipeline_run_audit(
        self,
        *,
        status: str | None,
        provider: str | None,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> list[PipelineRunAuditRecord]:
        if self._db is None:
            raise RuntimeError("DATABASE_URL is required for admin operations")
        await self._ensure_orm_ready()

        async def _run(session):
            stmt = select(PipelineRunAuditORM)
            if status:
                stmt = stmt.where(PipelineRunAuditORM.state == status)
            if provider:
                stmt = stmt.where(PipelineRunAuditORM.provider == provider)
            if from_at:
                stmt = stmt.where(PipelineRunAuditORM.created_at >= from_at.isoformat())
            if to_at:
                stmt = stmt.where(PipelineRunAuditORM.created_at <= to_at.isoformat())
            stmt = stmt.order_by(PipelineRunAuditORM.id.desc())
            rows = (await session.scalars(stmt)).all()
            output: list[PipelineRunAuditRecord] = []
            for row in rows:
                try:
                    conf = json.loads(row.conf_json or "{}")
                except Exception:
                    conf = {}
                output.append(
                    PipelineRunAuditRecord(
                        action=row.action,
                        dag_id=row.dag_id,
                        dag_run_id=row.dag_run_id,
                        state=row.state,
                        provider=row.provider,
                        conf=conf if isinstance(conf, dict) else {},
                        requested_by=row.requested_by,
                        created_at=row.created_at,
                    )
                )
            return output

        return await self._db.run_with_session(_run)

    async def _ensure_orm_ready(self) -> None:
        if self._db is None or self._orm_ready:
            return
        await self._db.connect()
        self._orm_ready = True
