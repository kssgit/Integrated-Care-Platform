import pytest

from geo_engine.route_risk import RouteRiskFactors, calculate_route_risk_score, classify_route_risk


def test_route_risk_score_within_range() -> None:
    factors = RouteRiskFactors(
        traffic_level=0.7,
        incident_count=3,
        weather_severity=0.4,
        vulnerable_zone_overlap=0.2,
    )
    score = calculate_route_risk_score(factors, golden_time_score=80)
    assert 0 <= score <= 100


def test_route_risk_classification_levels() -> None:
    assert classify_route_risk(10) == "LOW"
    assert classify_route_risk(40) == "MEDIUM"
    assert classify_route_risk(70) == "HIGH"
    assert classify_route_risk(90) == "CRITICAL"


def test_route_risk_rejects_invalid_ratio() -> None:
    factors = RouteRiskFactors(
        traffic_level=1.2,
        incident_count=1,
        weather_severity=0.3,
        vulnerable_zone_overlap=0.2,
    )
    with pytest.raises(ValueError):
        calculate_route_risk_score(factors)
