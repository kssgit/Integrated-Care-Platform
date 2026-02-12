import pytest

from trust_safety.safe_number import InMemorySafeNumberGateway, SafeNumberRouter, mask_phone


def test_mask_phone_format() -> None:
    assert mask_phone("010-1234-5678") == "010****678"


@pytest.mark.asyncio
async def test_safe_number_router_returns_relay() -> None:
    router = SafeNumberRouter(gateway=InMemorySafeNumberGateway())
    route = await router.route("010-1234-5678", "010-1111-2222", ttl_minutes=30)

    assert route.relay_number.startswith("050-")
    assert route.masked_caller == "010****678"
    assert route.masked_callee == "010****222"


@pytest.mark.asyncio
async def test_safe_number_router_invalid_ttl_raises() -> None:
    router = SafeNumberRouter(gateway=InMemorySafeNumberGateway())
    with pytest.raises(ValueError):
        await router.route("010-1234-5678", "010-1111-2222", ttl_minutes=0)

