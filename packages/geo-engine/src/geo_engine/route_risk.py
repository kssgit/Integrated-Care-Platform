from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteRiskFactors:
    traffic_level: float
    incident_count: int
    weather_severity: float
    vulnerable_zone_overlap: float


def calculate_route_risk_score(
    factors: RouteRiskFactors,
    golden_time_score: float | None = None,
) -> float:
    _validate_ratio("traffic_level", factors.traffic_level)
    _validate_ratio("weather_severity", factors.weather_severity)
    _validate_ratio("vulnerable_zone_overlap", factors.vulnerable_zone_overlap)
    if factors.incident_count < 0:
        raise ValueError("incident_count must be >= 0")
    incident_ratio = min(1.0, factors.incident_count / 10.0)
    base_score = (
        factors.traffic_level * 35.0
        + incident_ratio * 25.0
        + factors.weather_severity * 20.0
        + factors.vulnerable_zone_overlap * 20.0
    )
    penalty = 0.0 if golden_time_score is None else _golden_time_penalty(golden_time_score)
    return round(min(100.0, base_score + penalty), 2)


def classify_route_risk(score: float) -> str:
    if score < 0 or score > 100:
        raise ValueError("score must be between 0 and 100")
    if score < 30:
        return "LOW"
    if score < 60:
        return "MEDIUM"
    if score < 80:
        return "HIGH"
    return "CRITICAL"


def _validate_ratio(field: str, value: float) -> None:
    if value < 0 or value > 1:
        raise ValueError(f"{field} must be between 0 and 1")


def _golden_time_penalty(golden_time_score: float) -> float:
    if golden_time_score < 0 or golden_time_score > 100:
        raise ValueError("golden_time_score must be between 0 and 100")
    return ((100.0 - golden_time_score) / 100.0) * 20.0
