from __future__ import annotations


def success_response(data: object, meta: dict[str, object] | None = None) -> dict[str, object]:
    return {"success": True, "data": data, "meta": meta or {}}


def error_response(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}
