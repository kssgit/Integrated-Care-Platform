from pydantic import BaseModel, Field


class FacilityItem(BaseModel):
    id: str
    name: str
    district_code: str


class FacilityListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    district_code: str | None = None

