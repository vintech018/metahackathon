"""Typed models for the Phase 2 vulnerability triage compatibility layer."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VulnerabilityComponent(str, Enum):
    AUTH = "auth"
    DATABASE = "database"
    API = "api"
    FRONTEND = "frontend"
    NETWORK = "network"


class Observation(BaseModel):
    ticket_id: str
    subject: str
    body: str
    sender_email: str
    created_at: str
    attachments: list[str] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)
    step_number: int = 0
    task_id: str = ""
    tickets_remaining: int = 0
    tickets_completed: int = 0


class Action(BaseModel):
    severity: VulnerabilitySeverity
    component: VulnerabilityComponent
    remediation: str = Field(min_length=1)


class Reward(BaseModel):
    total: float = Field(..., ge=0.0, le=1.0)
    severity_score: float = Field(0.0, ge=0.0, le=1.0)
    component_score: float = Field(0.0, ge=0.0, le=1.0)
    remediation_score: float = Field(0.0, ge=0.0, le=1.0)
    bonus_score: float = Field(0.0, ge=0.0, le=1.0)
    feedback: str = ""


class StepResult(BaseModel):
    observation: Observation | None
    reward: Reward
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)


class ResetResult(BaseModel):
    observation: Observation
    info: dict[str, Any] = Field(default_factory=dict)


class EnvironmentState(BaseModel):
    task_id: str
    current_ticket_index: int
    total_tickets: int
    cumulative_reward: float
    step_count: int
    done: bool
    scores_per_ticket: list[float]
    task_score: float
