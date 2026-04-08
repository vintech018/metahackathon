"""Phase 2 graders for the validator-facing task registry."""

from __future__ import annotations

from typing import Any

from app.models import Action, Reward
from env.actions import normalize_component, normalize_severity


STRICT_MIN_SCORE = 0.05
STRICT_MAX_SCORE = 0.95

TASK_WEIGHTS = {
    "task_easy": {"severity": 0.45, "component": 0.30, "remediation": 0.25},
    "task_medium": {"severity": 0.40, "component": 0.30, "remediation": 0.30},
    "task_hard": {"severity": 0.35, "component": 0.25, "remediation": 0.40},
}


def _strict_open_interval(score: float) -> float:
    bounded = max(0.0, min(1.0, score))
    if bounded <= 0.0:
        return STRICT_MIN_SCORE
    if bounded >= 1.0:
        return STRICT_MAX_SCORE
    return round(bounded, 4)


def _score_severity(predicted: str, truth: str) -> float:
    return 1.0 if normalize_severity(predicted) == normalize_severity(truth) else 0.0


def _score_component(predicted: str, truth: str) -> float:
    return 1.0 if normalize_component(predicted) == normalize_component(truth) else 0.0


def _score_remediation(remediation: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    lowered = remediation.lower()
    matches = sum(1 for keyword in keywords if keyword.lower() in lowered)
    return matches / len(keywords)


def _feedback(
    severity_score: float,
    component_score: float,
    remediation_score: float,
    ground_truth: dict[str, Any],
) -> str:
    issues: list[str] = []
    if severity_score < 1.0:
        issues.append(f"severity should be {ground_truth['severity']}")
    if component_score < 1.0:
        issues.append(f"component should be {ground_truth['component']}")
    if remediation_score < 0.8:
        issues.append("remediation should cover more expected security controls")
    return "Perfect triage!" if not issues else "Issues: " + "; ".join(issues)


def grade(action: Action | dict[str, Any], ground_truth: dict[str, Any], task_id: str) -> Reward:
    if isinstance(action, dict):
        action = Action(**action)

    weights = TASK_WEIGHTS.get(task_id, TASK_WEIGHTS["task_easy"])
    severity_score = _score_severity(action.severity.value, ground_truth["severity"])
    component_score = _score_component(action.component.value, ground_truth["component"])
    remediation_score = _score_remediation(
        action.remediation,
        list(ground_truth.get("remediation_keywords", [])),
    )

    raw_total = (
        weights["severity"] * severity_score
        + weights["component"] * component_score
        + weights["remediation"] * remediation_score
    )
    total = _strict_open_interval(raw_total)

    return Reward(
        total=total,
        severity_score=round(severity_score, 4),
        component_score=round(component_score, 4),
        remediation_score=round(remediation_score, 4),
        bonus_score=0.0,
        feedback=_feedback(
            severity_score,
            component_score,
            remediation_score,
            ground_truth,
        ),
    )
