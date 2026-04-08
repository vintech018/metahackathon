"""Compatibility export for validators that import server.environment."""

from app.environment import VulnerabilityTaskEnv

SupportTriageEnv = VulnerabilityTaskEnv

__all__ = ["VulnerabilityTaskEnv", "SupportTriageEnv"]
