from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SearchDocument:
    document_id: str
    name: str
    district_code: str
    address: str
    metadata: dict[str, Any]


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

    async def search(self, keyword: str, district_code: str | None = None, limit: int = 20) -> list[SearchDocument]:
        q = keyword.lower().strip()
        matched = [
            doc
            for doc in self._docs.values()
            if (not district_code or doc.district_code == district_code)
            and (q in doc.name.lower() or q in doc.address.lower())
        ]
        return matched[:limit]

    async def upsert_document(self, doc: SearchDocument) -> None:
        self._docs[doc.document_id] = doc

