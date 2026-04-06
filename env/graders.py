"""
Deterministic grading system for the Bug Bounty Triage environment.

Base scoring breakdown:
    Severity match   → 0.4  (exact, case-insensitive)
    Component match  → 0.3  (exact after synonym normalization, case-insensitive)
    Remediation KWs  → 0.3  (combined: keyword match × 0.5 + quality heuristic × 0.5)

Advanced signals (additive, capped):
    CVSS-style risk bonus  → up to +0.3  (high_impact, no_auth, data_exfil)
    Attack chain bonus     → up to +0.1  (chained vulns with matching remediation)

Difficulty-based reward scaling:
    easy   → reward × 1.0
    medium → reward × 1.2
    hard   → reward × 1.5

Final reward is always capped at 1.0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from env.actions import normalize_component, normalize_severity

if TYPE_CHECKING:
    from env.actions import TriageAction
    from env.tasks import ExpectedOutput


# ── Weight constants ──────────────────────────────────────────────────────────
W_SEVERITY: float = 0.4
W_COMPONENT: float = 0.3
W_REMEDIATION: float = 0.3

# ── Difficulty multipliers ────────────────────────────────────────────────────
DIFFICULTY_MULTIPLIERS: dict[str, float] = {
    "easy": 1.0,
    "medium": 1.2,
    "hard": 1.5,
}


def _score_severity(action_severity: str, expected_severity: str) -> float:
    """Return 1.0 if severities match (case-insensitive), else 0.0."""
    return 1.0 if normalize_severity(action_severity) == normalize_severity(expected_severity) else 0.0


def _score_component(action_component: str, expected_component: str) -> float:
    """Return 1.0 if components match after synonym normalization, else 0.0."""
    return 1.0 if normalize_component(action_component) == normalize_component(expected_component) else 0.0


def _score_remediation(remediation_text: str, expected_keywords: list[str]) -> float:
    """
    Return the proportion of expected keywords found in the remediation text.

    Matching is case-insensitive.  Each keyword is checked as a substring of
    the full remediation text so that the agent doesn't need to match exact
    phrasing — e.g. "use parameterized queries" matches keyword "parameterized".
    """
    if not expected_keywords:
        return 1.0  # No keywords expected → full credit

    text_lower = remediation_text.lower()
    matches = sum(1 for kw in expected_keywords if kw.lower() in text_lower)
    return matches / len(expected_keywords)


# ── Advanced scoring helpers ──────────────────────────────────────────────────

def infer_risk_signals(report: str) -> dict[str, bool]:
    """
    Detect CVSS-style risk signals from the vulnerability report text.

    Returns a dict of boolean flags:
        high_impact       – RCE, account takeover, or admin access mentioned
        no_auth_required  – exploit needs no authentication
        user_interaction  – exploit requires victim interaction
        data_exfiltration – report mentions data / credential theft
    """
    text = report.lower()
    return {
        "high_impact": any(kw in text for kw in ("rce", "account takeover", "admin access")),
        "no_auth_required": any(kw in text for kw in ("unauthenticated", "no authentication")),
        "user_interaction": any(kw in text for kw in ("victim", "click")),
        "data_exfiltration": any(kw in text for kw in ("data", "credentials", "exfiltrate")),
    }


def bonus_score(report: str) -> float:
    """
    Compute a CVSS-style bonus from report risk signals.

    Scoring:
        high_impact       → +0.1
        no_auth_required  → +0.1
        data_exfiltration → +0.1

    Capped at 0.3.  ``user_interaction`` is detected but does not
    contribute bonus points (it indicates *lower* exploitability).
    """
    signals = infer_risk_signals(report)
    score = 0.0
    if signals["high_impact"]:
        score += 0.1
    if signals["no_auth_required"]:
        score += 0.1
    if signals["data_exfiltration"]:
        score += 0.1
    return min(score, 0.3)


def remediation_quality(text: str) -> float:
    """
    Heuristic quality score for the remediation text.

    Awards partial credit for mentioning security-relevant concepts:
        +0.2  if "validate" or "sanitize"
        +0.2  if "token", "cookie", or "session"
        +0.2  if "csp" or "security policy"

    Capped at 0.3 (not 0.6) to keep it as a supplementary signal.
    """
    t = text.lower()
    score = 0.0
    if "validate" in t or "sanitize" in t:
        score += 0.2
    if "token" in t or "cookie" in t or "session" in t:
        score += 0.2
    if "csp" in t or "security policy" in t:
        score += 0.2
    return min(score, 0.3)


def detect_chain(report: str) -> bool:
    """
    Return True if the report describes a chained / multi-step attack.

    Detection heuristics:
        • contains "chain" or "→"
        • OR  ("xss" AND "cookie")
        • OR  ("ssrf" AND "metadata")
    """
    t = report.lower()
    if "chain" in t or "→" in t:
        return True
    if "xss" in t and "cookie" in t:
        return True
    if "ssrf" in t and "metadata" in t:
        return True
    return False


def _chain_bonus(report: str, remediation: str) -> float:
    """
    Return +0.1 if the report is a chained attack AND the agent's
    remediation acknowledges the multi-step nature.
    """
    if not detect_chain(report):
        return 0.0
    rem = remediation.lower()
    if any(kw in rem for kw in ("multiple", "combined", "chain")):
        return 0.1
    return 0.0


def _combined_remediation_score(
    remediation_text: str,
    expected_keywords: list[str],
) -> float:
    """
    Combined remediation score: 50 % keyword match + 50 % quality heuristic.
    """
    kw_score = _score_remediation(remediation_text, expected_keywords)
    qual_score = remediation_quality(remediation_text)
    return kw_score * 0.5 + qual_score * 0.5


# ── Primary grading functions ─────────────────────────────────────────────────

def grade_detailed(
    action: "TriageAction",
    expected: "ExpectedOutput",
    report: str = "",
) -> dict[str, float]:
    """
    Compute a full scoring breakdown and return individual components.

    Returns
    -------
    dict with keys:
        severity_score, component_score, remediation_score,
        bonus_score, chain_bonus, total
    """
    sev = _score_severity(action.severity, expected["severity"])
    comp = _score_component(action.component, expected["component"])
    rem = _combined_remediation_score(action.remediation, expected["remediation_keywords"])
    bonus = bonus_score(report)
    chain = _chain_bonus(report, action.remediation)

    raw_total = (
        W_SEVERITY * sev
        + W_COMPONENT * comp
        + W_REMEDIATION * rem
        + bonus
        + chain
    )

    return {
        "severity_score": round(W_SEVERITY * sev, 4),
        "component_score": round(W_COMPONENT * comp, 4),
        "remediation_score": round(W_REMEDIATION * rem, 4),
        "bonus_score": round(bonus + chain, 4),
        "total": round(min(raw_total, 1.0), 4),
    }


def grade(action: "TriageAction", expected: "ExpectedOutput", report: str = "") -> float:
    """
    Compute a deterministic reward in [0.0, 1.0] for the agent's triage action.

    Parameters
    ----------
    action : TriageAction
        The agent's submitted triage decision.
    expected : ExpectedOutput
        The ground-truth labels for the current task.
    report : str
        The original vulnerability report text (used for advanced signals).

    Returns
    -------
    float
        Weighted score between 0.0 and 1.0.
    """
    return grade_detailed(action, expected, report)["total"]


def grade_with_difficulty(
    action: "TriageAction",
    expected: "ExpectedOutput",
    difficulty: str,
    report: str = "",
) -> float:
    """
    Grade the action and apply difficulty-based reward scaling.

    The raw grade is multiplied by the difficulty multiplier:
        easy   → ×1.0
        medium → ×1.2
        hard   → ×1.5

    The scaled reward is capped at 1.0 to comply with OpenEnv expectations.

    Parameters
    ----------
    action : TriageAction
        The agent's submitted triage decision.
    expected : ExpectedOutput
        The ground-truth labels for the current task.
    difficulty : str
        The task difficulty tier.
    report : str
        The original vulnerability report text (used for advanced signals).

    Returns
    -------
    float
        Scaled reward.
    """
    raw = grade(action, expected, report)
    multiplier = DIFFICULTY_MULTIPLIERS.get(difficulty.lower(), 1.0)
    return round(min(raw * multiplier, 1.0), 4)


def grade_with_difficulty_detailed(
    action: "TriageAction",
    expected: "ExpectedOutput",
    difficulty: str,
    report: str = "",
) -> dict[str, float]:
    """
    Full detailed grade with difficulty scaling.

    Returns the same breakdown as ``grade_detailed`` plus a ``scaled_total``
    key that applies the difficulty multiplier (capped at 1.0).
    """
    details = grade_detailed(action, expected, report)
    multiplier = DIFFICULTY_MULTIPLIERS.get(difficulty.lower(), 1.0)
    details["scaled_total"] = round(min(details["total"] * multiplier, 1.0), 4)
    return details
