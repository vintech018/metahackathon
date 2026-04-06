"""
Bug Bounty Vulnerability Triage — OpenEnv Environment.

A single-step, deterministic environment where an AI agent must:
    1. Classify vulnerability severity  (Critical / High / Medium / Low)
    2. Identify the affected component   (Auth / Database / API / Frontend / Network)
    3. Suggest remediation steps

Compatible with the OpenEnv interface:
    reset()           → TriageObservation
    step(action)      → (TriageObservation, float, bool, dict)
    state()           → dict

IMPORTANT — Synchronous Environment:
    This environment is synchronous.  Inference scripts should NOT use
    'await' when calling step() or reset().  All methods return plain
    values, not coroutines.
"""

from __future__ import annotations

import random
from typing import Any

from env.actions import TriageAction
from env.graders import grade, grade_detailed, grade_with_difficulty, grade_with_difficulty_detailed
from env.observations import TriageObservation
from env.tasks import ALL_TASKS, Task


class TriageEnv:
    """
    OpenEnv-compatible environment for vulnerability report triage.

    Parameters
    ----------
    seed : int | None
        Optional random seed for reproducibility.
    debug : bool
        When True, prints diagnostic information during reset/step.
    use_difficulty_scaling : bool
        When True, applies difficulty-based reward multipliers.
    """

    def __init__(
        self,
        seed: int | None = None,
        debug: bool = False,
        use_difficulty_scaling: bool = True,
    ) -> None:
        self._rng = random.Random(seed)
        self._debug = debug
        self._use_difficulty_scaling = use_difficulty_scaling

        # Internal state
        self._current_task: Task | None = None
        self._step_count: int = 0
        self._done: bool = False
        self._last_reward: float | None = None

    # ── OpenEnv interface ─────────────────────────────────────────────────────

    def reset(self) -> TriageObservation:
        """
        Reset the environment and select a new task at random.

        Returns
        -------
        TriageObservation
            The initial observation containing the vulnerability report.
        """
        self._current_task = self._rng.choice(ALL_TASKS)
        self._step_count = 0
        self._done = False
        self._last_reward = None

        if self._debug:
            print(
                f"[DEBUG] reset() → selected task '{self._current_task['id']}' "
                f"(difficulty={self._current_task['difficulty']})"
            )

        return self._make_observation()

    def step(
        self,
        action: TriageAction | dict[str, str],
    ) -> tuple[TriageObservation, float, bool, dict[str, Any]]:
        """
        Execute one step in the environment.

        Parameters
        ----------
        action : TriageAction | dict
            The agent's triage decision.  Accepts either a TriageAction
            instance or a plain dict that will be coerced into one.

        Returns
        -------
        tuple[TriageObservation, float, bool, dict]
            (observation, reward, done, info)

        Raises
        ------
        RuntimeError
            If called before reset() or after the episode is already done.
        """
        if self._current_task is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        if self._done:
            raise RuntimeError(
                "Episode already finished. Call reset() to start a new episode."
            )

        # Coerce dict → TriageAction if needed
        if isinstance(action, dict):
            action = TriageAction(**action)

        expected = self._current_task["expected"]
        difficulty = self._current_task["difficulty"]
        report_text = self._current_task["report"]

        # Compute detailed scoring breakdown
        if self._use_difficulty_scaling:
            details = grade_with_difficulty_detailed(action, expected, difficulty, report_text)
            reward = details["scaled_total"]
        else:
            details = grade_detailed(action, expected, report_text)
            reward = details["total"]

        self._step_count += 1
        self._done = True
        self._last_reward = reward

        # Build info dict with explainability
        info: dict[str, Any] = {
            "task_id": self._current_task["id"],
            "difficulty": difficulty,
            "raw_reward": details["total"],
            "scaled_reward": reward,
            "expected_severity": expected["severity"],
            "expected_component": expected["component"],
            "expected_remediation_keywords": expected["remediation_keywords"],
            "agent_severity": action.severity,
            "agent_component": action.component,
            "explanation": {
                "severity_score": details["severity_score"],
                "component_score": details["component_score"],
                "remediation_score": details["remediation_score"],
                "bonus_score": details["bonus_score"],
            },
            "confidence": round(reward, 2),
        }

        if self._debug:
            print(f"[DEBUG] step() -> reward={reward}, done={self._done}")
            print(f"[DEBUG]   expected: severity={expected['severity']}, component={expected['component']}")
            print(f"[DEBUG]   received: severity={action.severity}, component={action.component}")
            print(f"[DEBUG]   explanation: {info['explanation']}")

        observation = self._make_observation()
        return observation, reward, self._done, info

    def state(self) -> dict[str, Any]:
        """
        Return the current internal state of the environment.

        Returns
        -------
        dict
            Contains the current task details, step count, and done flag.
        """
        return {
            "current_task": self._current_task,
            "step_count": self._step_count,
            "done": self._done,
            "last_reward": self._last_reward,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_observation(self) -> TriageObservation:
        """Construct a TriageObservation from the current task."""
        assert self._current_task is not None
        return TriageObservation(
            report=self._current_task["report"],
            task_id=self._current_task["id"],
            difficulty=self._current_task["difficulty"],
            step_count=self._step_count,
        )

    # ── Convenience ───────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        task_id = self._current_task["id"] if self._current_task else "None"
        return (
            f"TriageEnv(task={task_id}, step={self._step_count}, done={self._done})"
        )
