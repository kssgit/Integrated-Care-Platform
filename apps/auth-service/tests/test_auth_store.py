import pytest

from auth_service.store import AuthStore, UserAlreadyExistsError


@pytest.mark.asyncio
async def test_local_signup_and_authenticate_in_memory() -> None:
    store = AuthStore(database_url=None, bootstrap_users={})
    user = await store.signup_local(email="user@example.com", password="password123", role="guardian")
    assert user.user_id == "user@example.com"

    auth_user = await store.authenticate_local(email="user@example.com", password="password123")
    assert auth_user is not None
    assert auth_user.role == "guardian"


@pytest.mark.asyncio
async def test_duplicate_signup_raises_error_in_memory() -> None:
    store = AuthStore(database_url=None, bootstrap_users={})
    await store.signup_local(email="dup@example.com", password="password123", role="guardian")
    with pytest.raises(UserAlreadyExistsError):
        await store.signup_local(email="dup@example.com", password="password123", role="guardian")


@pytest.mark.asyncio
async def test_sso_links_existing_email_account_in_memory() -> None:
    store = AuthStore(database_url=None, bootstrap_users={})
    await store.signup_local(email="linked@example.com", password="password123", role="guardian")
    result = await store.login_with_sso(
        provider="google",
        provider_subject="google-sub-001",
        email="linked@example.com",
        role="guardian",
    )
    assert result.user.user_id == "linked@example.com"
    assert result.linked_existing_account is True
    assert result.is_signup is False
