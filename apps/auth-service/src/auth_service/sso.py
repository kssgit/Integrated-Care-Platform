from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


@dataclass(frozen=True)
class SSOProfile:
    provider: str
    provider_subject: str
    email: str | None
    email_verified: bool
    name: str | None


@dataclass(frozen=True)
class SSOProviderConfig:
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str

    @property
    def is_configured(self) -> bool:
        return bool(
            self.client_id
            and self.client_secret
            and self.authorize_url
            and self.token_url
            and self.userinfo_url
        )


@dataclass(frozen=True)
class SSOTokenResponse:
    access_token: str


class SSOClient:
    def __init__(self, providers: dict[str, SSOProviderConfig], timeout_seconds: float = 8.0) -> None:
        self._providers = providers
        self._timeout_seconds = timeout_seconds

    def supported_providers(self) -> set[str]:
        return set(self._providers.keys())

    def get_provider(self, provider: str) -> SSOProviderConfig | None:
        return self._providers.get(provider.lower().strip())

    def build_authorize_url(self, provider: str, *, redirect_uri: str, state: str) -> str | None:
        conf = self.get_provider(provider)
        if conf is None or not conf.is_configured:
            return None
        query = urlencode(
            {
                "response_type": "code",
                "client_id": conf.client_id,
                "redirect_uri": redirect_uri,
                "scope": conf.scope,
                "state": state,
            }
        )
        return f"{conf.authorize_url}?{query}"

    async def exchange_code_for_profile(
        self,
        provider: str,
        *,
        code: str,
        state: str,
        redirect_uri: str,
    ) -> SSOProfile:
        conf = self.get_provider(provider)
        if conf is None:
            raise ValueError("unsupported provider")
        if not conf.is_configured:
            raise ValueError("sso provider is not configured")

        token = await self._exchange_code_for_token(conf, code=code, state=state, redirect_uri=redirect_uri)
        userinfo = await self._fetch_userinfo(conf, access_token=token.access_token)
        return self._parse_profile(conf.name, userinfo)

    async def _exchange_code_for_token(
        self,
        conf: SSOProviderConfig,
        *,
        code: str,
        state: str,
        redirect_uri: str,
    ) -> SSOTokenResponse:
        body = {
            "grant_type": "authorization_code",
            "client_id": conf.client_id,
            "client_secret": conf.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if conf.name == "naver":
            body["state"] = state

        payload = await self._request_json(
            method="POST",
            url=conf.token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        access_token = str(payload.get("access_token", "")).strip()
        if not access_token:
            raise ValueError("missing access_token from sso provider")
        return SSOTokenResponse(access_token=access_token)

    async def _fetch_userinfo(self, conf: SSOProviderConfig, *, access_token: str) -> dict:
        payload = await self._request_json(
            method="GET",
            url=conf.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not isinstance(payload, dict):
            raise ValueError("invalid userinfo payload")
        return payload

    async def _request_json(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> dict:
        attempts = 3
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.request(method=method, url=url, headers=headers, data=data)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("response payload is not an object")
                return payload
            except Exception:
                if attempt == attempts - 1:
                    raise
                await asyncio.sleep(0.25 * (2**attempt))
        raise RuntimeError("unreachable")

    def _parse_profile(self, provider: str, payload: dict) -> SSOProfile:
        provider_key = provider.lower()
        if provider_key == "google":
            subject = str(payload.get("sub", "")).strip()
            if not subject:
                raise ValueError("google sub is required")
            email = str(payload.get("email", "")).strip() or None
            email_verified = bool(payload.get("email_verified", False))
            name = str(payload.get("name", "")).strip() or None
            return SSOProfile(
                provider="google",
                provider_subject=subject,
                email=email,
                email_verified=email_verified,
                name=name,
            )

        if provider_key == "naver":
            raw = payload.get("response", payload)
            if not isinstance(raw, dict):
                raise ValueError("naver profile response is invalid")
            subject = str(raw.get("id", "")).strip()
            if not subject:
                raise ValueError("naver id is required")
            email = str(raw.get("email", "")).strip() or None
            name = str(raw.get("name", "")).strip() or None
            return SSOProfile(
                provider="naver",
                provider_subject=subject,
                email=email,
                email_verified=bool(email),
                name=name,
            )

        raise ValueError("unsupported provider")


def create_sso_client_from_env() -> SSOClient:
    providers: dict[str, SSOProviderConfig] = {}
    for provider in [item.strip().lower() for item in os.getenv("AUTH_SSO_PROVIDERS", "google,naver").split(",")]:
        if not provider:
            continue
        providers[provider] = SSOProviderConfig(
            name=provider,
            client_id=os.getenv(f"AUTH_SSO_{provider.upper()}_CLIENT_ID", "").strip(),
            client_secret=os.getenv(f"AUTH_SSO_{provider.upper()}_CLIENT_SECRET", "").strip(),
            authorize_url=os.getenv(f"AUTH_SSO_{provider.upper()}_AUTHORIZE_URL", "").strip(),
            token_url=os.getenv(f"AUTH_SSO_{provider.upper()}_TOKEN_URL", "").strip(),
            userinfo_url=os.getenv(f"AUTH_SSO_{provider.upper()}_USERINFO_URL", "").strip(),
            scope=os.getenv(f"AUTH_SSO_{provider.upper()}_SCOPE", "openid profile email").strip(),
        )
    return SSOClient(providers)
