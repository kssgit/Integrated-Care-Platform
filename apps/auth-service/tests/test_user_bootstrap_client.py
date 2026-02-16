import pytest

from auth_service.user_bootstrap_client import UserBootstrapClient


@pytest.mark.asyncio
async def test_bootstrap_client_disabled_without_config() -> None:
    client = UserBootstrapClient(base_url=None, internal_token="")
    await client.ensure_user(user_id="u1", email="u1@example.com", role="guardian", profile_data={})

