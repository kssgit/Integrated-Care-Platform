from api.event_parking_monitor import ParkingAlertConfig, ParkingAlertPolicy


def test_parking_alert_policy_threshold() -> None:
    policy = ParkingAlertPolicy(
        ParkingAlertConfig(threshold=3, window_seconds=60, cooldown_seconds=60)
    )

    assert policy.add_event(100.0) is False
    assert policy.add_event(110.0) is False
    assert policy.add_event(120.0) is True
    assert policy.add_event(125.0) is False


def test_parking_alert_policy_window_prunes_old_events() -> None:
    policy = ParkingAlertPolicy(
        ParkingAlertConfig(threshold=2, window_seconds=10, cooldown_seconds=10)
    )

    assert policy.add_event(100.0) is False
    assert policy.add_event(200.0) is False
    assert policy.event_count() == 1


def test_parking_alert_policy_realerts_after_cooldown() -> None:
    policy = ParkingAlertPolicy(
        ParkingAlertConfig(threshold=2, window_seconds=120, cooldown_seconds=30)
    )

    assert policy.add_event(100.0) is False
    assert policy.add_event(110.0) is True
    assert policy.add_event(120.0) is False
    assert policy.add_event(141.0) is True
