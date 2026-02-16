from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any


def _urlsafe_b64encode(raw: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(raw: str) -> bytes:
    import base64

    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


@dataclass(frozen=True)
class AuthTokenPayload:
    sub: str
    role: str
    exp: int
    iat: int
    typ: str
    jti: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub": self.sub,
            "role": self.role,
            "exp": self.exp,
            "iat": self.iat,
            "typ": self.typ,
            "jti": self.jti,
        }


class JWTManager:
    """HS256-only JWT utility without external dependency."""

    def __init__(self, secret: str, access_minutes: int = 15, refresh_days: int = 7) -> None:
        if not secret:
            raise ValueError("JWT secret cannot be empty")
        self._secret = secret.encode("utf-8")
        self._access_minutes = access_minutes
        self._refresh_days = refresh_days

    def issue_access_token(self, subject: str, role: str, jti: str) -> str:
        now = datetime.now(timezone.utc)
        payload = AuthTokenPayload(
            sub=subject,
            role=role,
            iat=int(now.timestamp()),
            exp=int((now + timedelta(minutes=self._access_minutes)).timestamp()),
            typ="access",
            jti=jti,
        )
        return self._encode(payload.to_dict())

    def issue_refresh_token(self, subject: str, role: str, jti: str) -> str:
        now = datetime.now(timezone.utc)
        payload = AuthTokenPayload(
            sub=subject,
            role=role,
            iat=int(now.timestamp()),
            exp=int((now + timedelta(days=self._refresh_days)).timestamp()),
            typ="refresh",
            jti=jti,
        )
        return self._encode(payload.to_dict())

    def decode(self, token: str) -> AuthTokenPayload:
        header_raw, payload_raw, sig_raw = token.split(".")
        signed = f"{header_raw}.{payload_raw}".encode("ascii")
        expected = _urlsafe_b64encode(hmac.new(self._secret, signed, hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig_raw):
            raise ValueError("invalid token signature")
        payload_obj = json.loads(_urlsafe_b64decode(payload_raw))
        exp = int(payload_obj.get("exp", 0))
        if exp <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("token expired")
        return AuthTokenPayload(
            sub=str(payload_obj.get("sub", "")),
            role=str(payload_obj.get("role", "")),
            exp=exp,
            iat=int(payload_obj.get("iat", 0)),
            typ=str(payload_obj.get("typ", "")),
            jti=str(payload_obj.get("jti", "")),
        )

    def _encode(self, payload: dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_raw = _urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_raw = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signed = f"{header_raw}.{payload_raw}".encode("ascii")
        sig = _urlsafe_b64encode(hmac.new(self._secret, signed, hashlib.sha256).digest())
        return f"{header_raw}.{payload_raw}.{sig}"

