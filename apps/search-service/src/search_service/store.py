from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from devkit.config import load_settings
from devkit.db import AsyncDatabaseManager, Base, create_all_tables, create_schema_if_not_exists
from sqlalchemy import String, Text, func, or_, select
from sqlalchemy.orm import Mapped, mapped_column


@dataclass
class SearchDocument:
    document_id: str
    name: str
    district_code: str
    address: str
    metadata: dict[str, Any]


_SETTINGS = load_settings("search-service")
_DB_URL = _SETTINGS.DATABASE_URL
_DB_SCHEMA = "search" if (_DB_URL and _DB_URL.startswith("postgresql")) else None


class SearchDocumentORM(Base):
    __tablename__ = "search_documents"
    __table_args__ = {"schema": _DB_SCHEMA} if _DB_SCHEMA else {}

    document_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    district_code: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class SearchStore:
    def __init__(self) -> None:
        self._docs: dict[str, SearchDocument] = {
            "fac-1": SearchDocument(
                document_id="fac-1",
                name="Jongno Care Center",
                district_code="11110",
                address="Jongno-gu, Seoul",
                metadata={},
            ),
            "fac-2": SearchDocument(
                document_id="fac-2",
                name="Mapo Family Hub",
                district_code="11440",
                address="Mapo-gu, Seoul",
                metadata={},
            ),
            "fac-3": SearchDocument(
                document_id="fac-3",
                name="Gangnam Senior Link",
                district_code="11680",
                address="Gangnam-gu, Seoul",
                metadata={},
            ),
        }
        self._db = AsyncDatabaseManager(_DB_URL) if _DB_URL else None
        self._orm_ready = False

    async def search(self, keyword: str, district_code: str | None = None, limit: int = 20) -> list[SearchDocument]:
        if self._db is None:
            q = keyword.lower().strip()
            matched = [
                doc
                for doc in self._docs.values()
                if (not district_code or doc.district_code == district_code)
                and (q in doc.name.lower() or q in doc.address.lower())
            ]
            return matched[:limit]

        await self._ensure_orm_ready()
        q = f"%{keyword.lower().strip()}%"

        async def _run(session):
            condition = or_(
                func.lower(SearchDocumentORM.name).like(q),
                func.lower(SearchDocumentORM.address).like(q),
            )
            stmt = select(SearchDocumentORM).where(condition)
            if district_code:
                stmt = stmt.where(SearchDocumentORM.district_code == district_code)
            stmt = stmt.order_by(SearchDocumentORM.document_id).limit(limit)
            rows = (await session.scalars(stmt)).all()
            return [self._to_entity(row) for row in rows]

        return await self._db.run_with_session(_run)

    async def upsert_document(self, doc: SearchDocument) -> None:
        if self._db is None:
            self._docs[doc.document_id] = doc
            return

        await self._ensure_orm_ready()

        async def _run(session):
            row = await session.get(SearchDocumentORM, doc.document_id)
            if row is None:
                session.add(
                    SearchDocumentORM(
                        document_id=doc.document_id,
                        name=doc.name,
                        district_code=doc.district_code,
                        address=doc.address,
                        metadata_json=json.dumps(doc.metadata, ensure_ascii=True),
                    )
                )
            else:
                row.name = doc.name
                row.district_code = doc.district_code
                row.address = doc.address
                row.metadata_json = json.dumps(doc.metadata, ensure_ascii=True)

        await self._db.run_with_session(_run)

    async def _ensure_orm_ready(self) -> None:
        if self._db is None or self._orm_ready:
            return

        await self._db.connect()
        if _DB_SCHEMA:
            await create_schema_if_not_exists(self._db.engine, _DB_SCHEMA)
        await create_all_tables(self._db.engine, Base.metadata)

        async def _seed_if_empty(session):
            count = int((await session.scalar(select(func.count()).select_from(SearchDocumentORM))) or 0)
            if count > 0:
                return
            for item in self._docs.values():
                session.add(
                    SearchDocumentORM(
                        document_id=item.document_id,
                        name=item.name,
                        district_code=item.district_code,
                        address=item.address,
                        metadata_json=json.dumps(item.metadata, ensure_ascii=True),
                    )
                )

        await self._db.run_with_session(_seed_if_empty)
        self._orm_ready = True

    def _to_entity(self, row: SearchDocumentORM) -> SearchDocument:
        try:
            metadata = json.loads(row.metadata_json) if row.metadata_json else {}
        except Exception:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return SearchDocument(
            document_id=row.document_id,
            name=row.name,
            district_code=row.district_code,
            address=row.address,
            metadata=metadata,
        )
