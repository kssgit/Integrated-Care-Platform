from pydantic import BaseModel, Field


class SafeNumberRouteRequest(BaseModel):
    caller_phone: str
    callee_phone: str
    ttl_minutes: int = Field(default=30, ge=1, le=720)

