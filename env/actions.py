"""Action space definitions for the Bug Bounty Triage environment."""

from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Literal


# ── Jaspreet's Action Enum (VulnArena pipeline actions) ──────────────────────

class Action(str, Enum):
    ANALYZE_REPORT = "analyze_report"
    ANALYZE_LOGS = "analyze_logs"
    INSPECT_CODE = "inspect_code"
    EXTRACT_VULNERABILITY = "extract_vulnerability"
    ESTIMATE_SEVERITY = "estimate_severity"
    IDENTIFY_COMPONENT = "identify_component"
    SIMULATE_ATTACK = "simulate_attack"
    CHAIN_VULNERABILITIES = "chain_vulnerabilities"
    SUGGEST_FIX = "suggest_fix"
    VALIDATE_FIX = "validate_fix"


# ── Vaibhav's TriageAction (OpenEnv structured output) ───────────────────────

VALID_SEVERITIES: set[str] = {"critical", "high", "medium", "low"}

VALID_COMPONENTS: set[str] = {"auth", "database", "api", "frontend", "network"}

# Synonym map – keys are common aliases, values are canonical component names.
COMPONENT_SYNONYMS: dict[str, str] = {
    "authentication": "auth",
    "login": "auth",
    "authz": "auth",
    "authn": "auth",
    "db": "database",
    "sql": "database",
    "datastore": "database",
    "rest": "api",
    "graphql": "api",
    "endpoint": "api",
    "ui": "frontend",
    "client": "frontend",
    "web": "frontend",
    "browser": "frontend",
    "net": "network",
    "infra": "network",
    "infrastructure": "network",
    "server": "network",
    "ssrf": "network",
    "backend": "api",
    "server-side": "api",
    "application server": "api",
}


def normalize_component(value: str) -> str:
    """Resolve a component string to its canonical form using synonyms."""
    lowered = value.strip().lower()
    if lowered in VALID_COMPONENTS:
        return lowered
    return COMPONENT_SYNONYMS.get(lowered, lowered)


def normalize_severity(value: str) -> str:
    """Normalize severity to lowercase canonical form."""
    return value.strip().lower()


class TriageAction(BaseModel):
    """
    An agent's triage decision for a vulnerability report.

    Attributes:
        severity:    One of critical / high / medium / low.
        component:   Affected system component (auth / database / api / frontend / network).
        remediation: Free-text remediation recommendation.
    """

    severity: str
    component: str
    remediation: str

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        normalized = normalize_severity(v)
        if normalized not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{v}'. Must be one of: {sorted(VALID_SEVERITIES)}"
            )
        return normalized

    @field_validator("component")
    @classmethod
    def validate_component(cls, v: str) -> str:
        normalized = normalize_component(v)
        if normalized not in VALID_COMPONENTS:
            raise ValueError(
                f"Invalid component '{v}'. Must be one of (or synonym of): {sorted(VALID_COMPONENTS)}"
            )
        return normalized

    @field_validator("remediation")
    @classmethod
    def validate_remediation(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Remediation text must not be empty.")
        return stripped
