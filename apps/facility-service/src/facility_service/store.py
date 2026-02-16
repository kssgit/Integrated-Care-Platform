from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from devkit.config import load_settings
from devkit.db import AsyncDatabaseManager, Base, create_all_tables, create_schema_if_not_exists
from devkit.timezone import now_kst_iso
from sqlalchemy import Float, String, Text, func, or_, select
from sqlalchemy.orm import Mapped, mapped_column


@dataclass
class Facility:
    facility_id: str
    name: str
    district_code: str
    address: str
    lat: float
    lng: float
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=now_kst_iso)


_SETTINGS = load_settings("facility-service")
_DB_URL = _SETTINGS.DATABASE_URL
_DB_SCHEMA = "facility" if (_DB_URL and _DB_URL.startswith("postgresql")) else None


class FacilityORM(Base):
    __tablename__ = "facilities"
    __table_args__ = {"schema": _DB_SCHEMA} if _DB_SCHEMA else {}

    facility_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    district_code: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class FacilityStore:
    def __init__(self) -> None:
        self._items: dict[str, Facility] = {
            "fac-1": Facility(
                facility_id="fac-1",
                name="Jongno Care Center",
                district_code="11110",
                address="Jongno-gu, Seoul",
                lat=37.572,
                lng=126.979,
            ),
            "fac-2": Facility(
                facility_id="fac-2",
                name="Mapo Family Hub",
                district_code="11440",
                address="Mapo-gu, Seoul",
                lat=37.566,
                lng=126.901,
            ),
            "fac-3": Facility(
                facility_id="fac-3",
                name="Gangnam Senior Link",
                district_code="11680",
                address="Gangnam-gu, Seoul",
                lat=37.497,
                lng=127.028,
            ),
        }
        self._sync_log: list[dict[str, str]] = []
        self._db = AsyncDatabaseManager(_DB_URL) if _DB_URL else None
        self._orm_ready = False

    async def list_facilities(
        self,
        *,
        page: int,
        page_size: int,
        district_code: str | None = None,
    ) -> tuple[list[Facility], int]:
        if self._db is None:
            items = [item for item in self._items.values() if not district_code or item.district_code == district_code]
            total = len(items)
            start = (page - 1) * page_size
            return items[start : start + page_size], total

        await self._ensure_orm_ready()
        offset = (page - 1) * page_size

        async def _run(session):
            query = select(FacilityORM)
            count_query = select(func.count()).select_from(FacilityORM)
            if district_code:
                query = query.where(FacilityORM.district_code == district_code)
                count_query = count_query.where(FacilityORM.district_code == district_code)
            query = query.order_by(FacilityORM.facility_id).offset(offset).limit(page_size)
            rows = (await session.scalars(query)).all()
            total = int((await session.scalar(count_query)) or 0)
            return [self._to_entity(item) for item in rows], total

        return await self._db.run_with_session(_run)

    async def get_by_id(self, facility_id: str) -> Facility | None:
        if self._db is None:
            return self._items.get(facility_id)

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(FacilityORM, facility_id)
            return self._to_entity(row) if row else None

        return await self._db.run_with_session(_run)

    async def search(self, query: str, district_code: str | None = None) -> list[Facility]:
        if self._db is None:
            q = query.lower().strip()
            return [
                item
                for item in self._items.values()
                if (not district_code or item.district_code == district_code)
                and (q in item.name.lower() or q in item.address.lower())
            ]

        await self._ensure_orm_ready()
        q = f"%{query.lower().strip()}%"

        async def _run(session):
            condition = or_(
                func.lower(FacilityORM.name).like(q),
                func.lower(FacilityORM.address).like(q),
            )
            stmt = select(FacilityORM).where(condition)
            if district_code:
                stmt = stmt.where(FacilityORM.district_code == district_code)
            rows = (await session.scalars(stmt.order_by(FacilityORM.facility_id))).all()
            return [self._to_entity(item) for item in rows]

        return await self._db.run_with_session(_run)

    async def upsert(self, facility: Facility, source: str = "unknown") -> Facility:
        if self._db is None:
            self._items[facility.facility_id] = facility
            self._sync_log.append(
                {
                    "facility_id": facility.facility_id,
                    "source": source,
                    "synced_at": now_kst_iso(),
                }
            )
            return facility

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(FacilityORM, facility.facility_id)
            if row is None:
                row = FacilityORM(
                    facility_id=facility.facility_id,
                    name=facility.name,
                    district_code=facility.district_code,
                    address=facility.address,
                    lat=facility.lat,
                    lng=facility.lng,
                    metadata_json=json.dumps(facility.metadata, ensure_ascii=True),
                    updated_at=facility.updated_at,
                )
                session.add(row)
            else:
                row.name = facility.name
                row.district_code = facility.district_code
                row.address = facility.address
                row.lat = facility.lat
                row.lng = facility.lng
                row.metadata_json = json.dumps(facility.metadata, ensure_ascii=True)
                row.updated_at = facility.updated_at
            return self._to_entity(row)

        saved = await self._db.run_with_session(_run)
        self._sync_log.append(
            {
                "facility_id": facility.facility_id,
                "source": source,
                "synced_at": now_kst_iso(),
            }
        )
        return saved

    async def _ensure_orm_ready(self) -> None:
        if self._db is None or self._orm_ready:
            return

        await self._db.connect()
        if _DB_SCHEMA:
            await create_schema_if_not_exists(self._db.engine, _DB_SCHEMA)
        await create_all_tables(self._db.engine, Base.metadata)

        async def _seed_if_empty(session):
            count = int((await session.scalar(select(func.count()).select_from(FacilityORM))) or 0)
            if count > 0:
                return
            for item in self._items.values():
                session.add(
                    FacilityORM(
                        facility_id=item.facility_id,
                        name=item.name,
                        district_code=item.district_code,
                        address=item.address,
                        lat=item.lat,
                        lng=item.lng,
                        metadata_json=json.dumps(item.metadata, ensure_ascii=True),
                        updated_at=item.updated_at,
                    )
                )

        await self._db.run_with_session(_seed_if_empty)
        self._orm_ready = True

    def _to_entity(self, row: FacilityORM) -> Facility:
        try:
            metadata = json.loads(row.metadata_json) if row.metadata_json else {}
        except Exception:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return Facility(
            facility_id=row.facility_id,
            name=row.name,
            district_code=row.district_code,
            address=row.address,
            lat=row.lat,
            lng=row.lng,
            metadata=metadata,
            updated_at=row.updated_at,
        )
