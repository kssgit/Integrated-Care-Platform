from __future__ import annotations

from devkit.observability import configure_otel, configure_probe_access_log_filter
from fastapi import FastAPI, HTTPException, Query

from shared.security import validate_search_input

from search_service.schemas import SearchUpsertRequest
from search_service.store import SearchDocument, SearchStore


def success_response(data: object, meta: dict[str, object] | None = None) -> dict[str, object]:
    return {"success": True, "data": data, "meta": meta or {}}


def create_app() -> FastAPI:
    app = FastAPI(title="Search Service", version="0.1.0")
    configure_otel(service_name="search-service")
    configure_probe_access_log_filter()
    store = SearchStore()

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return success_response({"status": "ok"}, meta={})

    @app.get("/readyz")
    async def readyz() -> dict[str, object]:
        return success_response({"status": "ready"}, meta={})

    @app.get("/v1/search/facilities")
    async def search_facilities(
        query: str = Query(..., min_length=1),
        district_code: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> dict[str, object]:
        if not validate_search_input(query):
            raise HTTPException(status_code=422, detail="invalid search query")
        documents = await store.search(query, district_code=district_code, limit=limit)
        return success_response(
            [
                {
                    "id": item.document_id,
                    "name": item.name,
                    "district_code": item.district_code,
                    "address": item.address,
                }
                for item in documents
            ],
            meta={"count": len(documents)},
        )

    @app.post("/internal/search/index")
    async def upsert_index(body: SearchUpsertRequest) -> dict[str, object]:
        doc = SearchDocument(
            document_id=body.document_id,
            name=body.name,
            district_code=body.district_code,
            address=body.address,
            metadata=body.metadata,
        )
        await store.upsert_document(doc)
        return success_response({"indexed": doc.document_id}, meta={})

    return app


app = create_app()
