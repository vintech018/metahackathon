"""Validator-facing multi-ticket environment for Phase 2 compatibility."""

from __future__ import annotations

import copy
from typing import Any

from app.models import Action, EnvironmentState, Observation, ResetResult, Reward, StepResult
from tasks.graders import grade
from tasks.task_definitions import TASKS


class VulnerabilityTaskEnv:
    """Compatibility environment that exposes task_easy/task_medium/task_hard."""

    def __init__(self) -> None:
        self._task_id = "task_easy"
        self._tickets: list[dict[str, Any]] = []
        self._current_index = 0
        self._step_count = 0
        self._cumulative_reward = 0.0
        self._scores_per_ticket: list[float] = []
        self._done = False

    def reset(self, task_id: str = "task_easy") -> ResetResult:
        if task_id not in TASKS:
            raise ValueError(f"Unknown task_id '{task_id}'. Valid task IDs: {list(TASKS.keys())}")

        task = TASKS[task_id]
        self._task_id = task_id
        self._tickets = copy.deepcopy(task["tickets"])
        self._current_index = 0
        self._step_count = 0
        self._cumulative_reward = 0.0
        self._scores_per_ticket = []
        self._done = False

        return ResetResult(
            observation=self._make_observation(),
            info={
                "task_id": task_id,
                "task_name": task["name"],
                "difficulty": task["difficulty"],
                "total_tickets": len(self._tickets),
                "description": task["description"],
            },
        )

    def step(self, action: Action) -> StepResult:
        if self._done:
            return StepResult(
                observation=None,
                reward=Reward(
                    total=0.05,
                    severity_score=0.0,
                    component_score=0.0,
                    remediation_score=0.0,
                    bonus_score=0.0,
                    feedback="Episode already done. Call reset().",
                ),
                done=True,
                info={"warning": "Episode already done. Call reset()."},
            )

        current_ticket = self._tickets[self._current_index]
        ground_truth = current_ticket["_ground_truth"]
        reward = grade(action, ground_truth, self._task_id)

        self._scores_per_ticket.append(reward.total)
        self._cumulative_reward += reward.total
        self._step_count += 1
        self._current_index += 1
        self._done = self._current_index >= len(self._tickets)

        task_score = self._cumulative_reward / len(self._tickets) if self._tickets else 0.0

        info: dict[str, Any] = {
            "ticket_id": current_ticket["id"],
            "step": self._step_count,
            "ground_truth": ground_truth,
        }
        if self._done:
            info["task_score"] = round(task_score, 4)
            info["scores_per_ticket"] = self._scores_per_ticket
            info["message"] = "Episode complete."

        return StepResult(
            observation=None if self._done else self._make_observation(),
            reward=reward,
            done=self._done,
            info=info,
        )

    def state(self) -> EnvironmentState:
        task_score = self._cumulative_reward / len(self._tickets) if self._tickets else 0.0
        return EnvironmentState(
            task_id=self._task_id,
            current_ticket_index=self._current_index,
            total_tickets=len(self._tickets),
            cumulative_reward=round(self._cumulative_reward, 4),
            step_count=self._step_count,
            done=self._done,
            scores_per_ticket=self._scores_per_ticket,
            task_score=round(task_score, 4),
        )

    def _make_observation(self) -> Observation:
        ticket = self._tickets[self._current_index]
        return Observation(
            ticket_id=ticket["id"],
            subject=ticket["subject"],
            body=ticket["body"],
            sender_email=ticket["sender_email"],
            created_at=ticket["created_at"],
            attachments=ticket.get("attachments", []),
            history=[],
            step_number=self._step_count,
            task_id=self._task_id,
            tickets_remaining=len(self._tickets) - self._current_index,
            tickets_completed=self._current_index,
        )
