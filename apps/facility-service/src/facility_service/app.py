from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from shared.security import validate_search_input

from facility_service.schemas import FacilityUpsertRequest
from facility_service.store import Facility, FacilityStore


def success_response(data: object, meta: dict[str, object] | None = None) -> dict[str, object]:
    return {"success": True, "data": data, "meta": meta or {}}


def create_app() -> FastAPI:
    app = FastAPI(title="Facility Service", version="0.1.0")
    store = FacilityStore()

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return success_response({"status": "ok"}, meta={})

    @app.get("/readyz")
    async def readyz() -> dict[str, object]:
        return success_response({"status": "ready"}, meta={})

    @app.get("/v1/facilities")
    async def list_facilities(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        district_code: str | None = None,
    ) -> dict[str, object]:
        items, total = await store.list_facilities(page=page, page_size=page_size, district_code=district_code)
        data = [
            {
                "id": item.facility_id,
                "name": item.name,
                "district_code": item.district_code,
                "address": item.address,
                "lat": item.lat,
                "lng": item.lng,
            }
            for item in items
        ]
        return success_response(data, meta={"page": page, "page_size": page_size, "total": total})

    @app.get("/v1/facilities/search")
    async def search_facilities(query: str = Query(..., min_length=1), district_code: str | None = None) -> dict[str, object]:
        if not validate_search_input(query):
            raise HTTPException(status_code=422, detail="invalid search query")
        items = await store.search(query, district_code=district_code)
        return success_response(
            [
                {"id": item.facility_id, "name": item.name, "district_code": item.district_code}
                for item in items
            ],
            meta={"count": len(items)},
        )

    @app.get("/v1/facilities/{facility_id}")
    async def get_facility(facility_id: str) -> dict[str, object]:
        item = await store.get_by_id(facility_id)
        if not item:
            raise HTTPException(status_code=404, detail="facility not found")
        return success_response(
            {
                "id": item.facility_id,
                "name": item.name,
                "district_code": item.district_code,
                "address": item.address,
                "lat": item.lat,
                "lng": item.lng,
                "metadata": item.metadata,
            },
            meta={},
        )

    @app.post("/internal/facilities/upsert")
    async def upsert_facility(body: FacilityUpsertRequest) -> dict[str, object]:
        facility = Facility(
            facility_id=body.facility_id,
            name=body.name,
            district_code=body.district_code,
            address=body.address,
            lat=body.lat,
            lng=body.lng,
            metadata=body.metadata,
        )
        saved = await store.upsert(facility, source=body.source)
        return success_response({"facility_id": saved.facility_id, "updated_at": saved.updated_at}, meta={})

    return app


app = create_app()
