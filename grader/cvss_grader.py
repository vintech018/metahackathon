"""Legacy grader used by the original task modules in ``tasks/``."""

from __future__ import annotations

from difflib import SequenceMatcher


STRICT_MIN_SCORE = 0.05
STRICT_MAX_SCORE = 0.95


def _normalize(value) -> str:
    return str(value or "").strip().lower()


def _sequence_similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _list_overlap(actual: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    actual_set = {_normalize(item) for item in actual if _normalize(item)}
    expected_set = {_normalize(item) for item in expected if _normalize(item)}
    if not expected_set:
        return 1.0
    return len(actual_set & expected_set) / len(expected_set)


def _to_strict_unit_interval(raw_score: float) -> float:
    bounded = max(0.0, min(1.0, raw_score))
    if bounded <= 0.0:
        return STRICT_MIN_SCORE
    if bounded >= 1.0:
        return STRICT_MAX_SCORE
    return round(bounded, 4)


def calculate_final_score(obs, ground_truth):
    """Return a deterministic score strictly inside the open interval ``(0, 1)``."""
    weights = {
        "vulnerability": 0.2,
        "severity": 0.2,
        "component": 0.2,
        "exploit_chain": 0.2,
        "fix": 0.2,
    }

    score = 0.0

    if _normalize(obs.identified_vulnerability) == _normalize(
        ground_truth.get("vulnerability_type")
    ):
        score += weights["vulnerability"]

    if _normalize(obs.severity) == _normalize(ground_truth.get("severity")):
        score += weights["severity"]

    score += weights["component"] * _sequence_similarity(
        _normalize(obs.component),
        _normalize(ground_truth.get("component")),
    )

    score += weights["exploit_chain"] * _list_overlap(
        list(getattr(obs, "exploit_chain", []) or []),
        list(ground_truth.get("exploit_chain", []) or []),
    )

    score += weights["fix"] * _sequence_similarity(
        _normalize(obs.fix_suggestion),
        _normalize(ground_truth.get("correct_fix")),
    )

    return _to_strict_unit_interval(score)
