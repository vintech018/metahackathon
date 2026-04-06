"""Observation space definitions for the Bug Bounty Triage environment."""

from pydantic import BaseModel
from typing import Literal


class TriageObservation(BaseModel):
    """
    The observation returned to the agent after reset() or step().

    Attributes:
        report:      The raw vulnerability report text the agent must triage.
        task_id:     Unique identifier for the current task.
        difficulty:  Difficulty tier of the task (easy / medium / hard).
        step_count:  Number of steps taken so far in the current episode.
    """

    report: str
    task_id: str
    difficulty: Literal["easy", "medium", "hard"]
    step_count: int = 0
