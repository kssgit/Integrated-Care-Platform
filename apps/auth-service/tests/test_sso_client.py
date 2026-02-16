import pytest

from auth_service.sso import SSOClient, SSOProfile, SSOProviderConfig


def _client() -> SSOClient:
    return SSOClient(
        providers={
            "google": SSOProviderConfig(
                name="google",
                client_id="client-id",
                client_secret="client-secret",
                authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
                scope="openid profile email",
            )
        }
    )


def test_build_authorize_url_contains_required_query_values() -> None:
    client = _client()
    url = client.build_authorize_url(
        "google",
        redirect_uri="http://localhost/callback",
        state="opaque-state",
    )
    assert url is not None
    assert "response_type=code" in url
    assert "client_id=client-id" in url
    assert "state=opaque-state" in url


def test_parse_google_profile() -> None:
    client = _client()
    profile = client._parse_profile(
        "google",
        {
            "sub": "google-subject-1",
            "email": "user@example.com",
            "email_verified": True,
            "name": "User One",
        },
    )
    assert isinstance(profile, SSOProfile)
    assert profile.provider_subject == "google-subject-1"
    assert profile.email == "user@example.com"
    assert profile.email_verified is True


def test_parse_naver_profile() -> None:
    client = _client()
    profile = client._parse_profile(
        "naver",
        {
            "response": {
                "id": "naver-id-1",
                "email": "user@naver.com",
                "name": "Naver User",
            }
        },
    )
    assert profile.provider == "naver"
    assert profile.provider_subject == "naver-id-1"
    assert profile.email == "user@naver.com"


@pytest.mark.asyncio
async def test_exchange_code_fails_when_provider_unconfigured() -> None:
    client = SSOClient(
        providers={
            "google": SSOProviderConfig(
                name="google",
                client_id="",
                client_secret="",
                authorize_url="",
                token_url="",
                userinfo_url="",
                scope="openid",
            )
        }
    )
    with pytest.raises(ValueError):
        await client.exchange_code_for_profile(
            "google",
            code="code",
            state="state",
            redirect_uri="http://localhost/callback",
        )
