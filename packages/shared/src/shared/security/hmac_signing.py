from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac


class SignatureValidationError(ValueError):
    pass


def build_event_signature(secret: str, timestamp: str, payload: str) -> str:
    if not secret:
        raise ValueError("secret required")
    msg = f"{timestamp}.{payload}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_event_signature(
    *,
    secret: str,
    timestamp: str | None,
    payload: str,
    signature: str | None,
    max_skew_seconds: int = 300,
) -> None:
    if not timestamp or not signature:
        raise SignatureValidationError("missing signature headers")
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise SignatureValidationError("invalid signature timestamp") from exc
    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - ts) > max_skew_seconds:
        raise SignatureValidationError("signature timestamp outside allowed window")
    expected = build_event_signature(secret, timestamp, payload)
    if not hmac.compare_digest(expected, signature):
        raise SignatureValidationError("invalid signature")

