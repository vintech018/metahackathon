"""
Reinforcement Learning components for the triage agent.

Implements:
    • ExperienceBuffer — replay buffer storing (state, action, reward, info)
    • EpsilonScheduler — ε-greedy exploration decay
    • RLPolicy — wraps the LLM with exploration/exploitation and reward tracking
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.config import RLConfig


# ─────────────────────────────────────────────────────────────────────────────
#  Experience Tuple
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Experience:
    """A single (state, action, reward, info) transition."""
    episode: int
    task_id: str
    difficulty: str
    report: str                  # state (observation)
    action: dict[str, str]       # agent's triage decision
    reward: float                # scalar reward from environment
    info: dict[str, Any]         # grading breakdown
    reasoning_summary: str = ""  # human-readable reasoning trace

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode": self.episode,
            "task_id": self.task_id,
            "difficulty": self.difficulty,
            "report": self.report[:300] + "..." if len(self.report) > 300 else self.report,
            "action": self.action,
            "reward": self.reward,
            "info": {
                k: v for k, v in self.info.items()
                if k not in ("expected_remediation_keywords",)
            },
            "reasoning_summary": self.reasoning_summary,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Experience":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─────────────────────────────────────────────────────────────────────────────
#  Experience Buffer (Replay Buffer)
# ─────────────────────────────────────────────────────────────────────────────

class ExperienceBuffer:
    """
    Fixed-capacity replay buffer for storing triage experiences.
    Supports filtering, statistics, and persistence.
    """

    def __init__(self, capacity: int = 500) -> None:
        self._capacity = capacity
        self._buffer: list[Experience] = []

    def add(self, exp: Experience) -> None:
        """Add an experience, evicting oldest if at capacity."""
        self._buffer.append(exp)
        if len(self._buffer) > self._capacity:
            self._buffer.pop(0)

    def sample(self, n: int) -> list[Experience]:
        """Sample n random experiences."""
        return random.sample(self._buffer, min(n, len(self._buffer)))

    def get_low_reward(self, threshold: float = 0.6) -> list[Experience]:
        """Return all experiences below reward threshold."""
        return [e for e in self._buffer if e.reward < threshold]

    def get_by_task(self, task_id: str) -> list[Experience]:
        """Return all experiences for a specific task."""
        return [e for e in self._buffer if e.task_id == task_id]

    def get_recent(self, n: int = 10) -> list[Experience]:
        """Return the N most recent experiences."""
        return self._buffer[-n:]

    @property
    def size(self) -> int:
        return len(self._buffer)

    def stats(self) -> dict[str, Any]:
        """Compute aggregate statistics over the buffer."""
        if not self._buffer:
            return {"count": 0}

        rewards = [e.reward for e in self._buffer]
        by_difficulty: dict[str, list[float]] = {}
        by_task: dict[str, list[float]] = {}

        for e in self._buffer:
            by_difficulty.setdefault(e.difficulty, []).append(e.reward)
            by_task.setdefault(e.task_id, []).append(e.reward)

        return {
            "count": len(self._buffer),
            "mean_reward": round(sum(rewards) / len(rewards), 4),
            "min_reward": round(min(rewards), 4),
            "max_reward": round(max(rewards), 4),
            "std_reward": round(
                math.sqrt(sum((r - sum(rewards) / len(rewards)) ** 2 for r in rewards) / len(rewards)),
                4,
            ),
            "by_difficulty": {
                d: round(sum(rs) / len(rs), 4) for d, rs in by_difficulty.items()
            },
            "by_task": {
                t: round(sum(rs) / len(rs), 4) for t, rs in by_task.items()
            },
            "low_reward_count": len([r for r in rewards if r < 0.6]),
            "high_reward_count": len([r for r in rewards if r >= 0.9]),
        }

    def save(self, path: Path) -> None:
        """Persist buffer to JSON file."""
        data = [e.to_dict() for e in self._buffer]
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> None:
        """Load buffer from JSON file."""
        if path.exists():
            data = json.loads(path.read_text())
            self._buffer = [Experience.from_dict(d) for d in data]

    def __len__(self) -> int:
        return len(self._buffer)

    def __iter__(self):
        return iter(self._buffer)


# ─────────────────────────────────────────────────────────────────────────────
#  Epsilon Scheduler
# ─────────────────────────────────────────────────────────────────────────────

class EpsilonScheduler:
    """
    Linear epsilon decay for exploration/exploitation balance.

    Starts at epsilon_start and linearly decays to epsilon_end
    over decay_episodes, then stays at epsilon_end.
    """

    def __init__(
        self,
        start: float = 0.3,
        end: float = 0.05,
        decay_episodes: int = 50,
    ) -> None:
        self._start = start
        self._end = end
        self._decay_episodes = decay_episodes

    def get_epsilon(self, episode: int) -> float:
        """Return epsilon for the given episode."""
        if episode >= self._decay_episodes:
            return self._end
        progress = episode / self._decay_episodes
        return self._start + (self._end - self._start) * progress

    def should_explore(self, episode: int) -> bool:
        """Return True if the agent should explore (random action)."""
        return random.random() < self.get_epsilon(episode)


# ─────────────────────────────────────────────────────────────────────────────
#  Training Metrics
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EpisodeMetrics:
    """Metrics for a single training episode."""
    episode: int
    task_id: str
    difficulty: str
    reward: float
    epsilon: float
    was_exploration: bool
    severity_correct: bool
    component_correct: bool
    reasoning_steps: int
    tokens_used: int
    reflection_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode": self.episode,
            "task_id": self.task_id,
            "difficulty": self.difficulty,
            "reward": self.reward,
            "epsilon": round(self.epsilon, 4),
            "was_exploration": self.was_exploration,
            "severity_correct": self.severity_correct,
            "component_correct": self.component_correct,
            "reasoning_steps": self.reasoning_steps,
            "tokens_used": self.tokens_used,
            "reflection_triggered": self.reflection_triggered,
        }


class MetricsTracker:
    """Tracks and persists training metrics across episodes."""

    def __init__(self) -> None:
        self._episodes: list[EpisodeMetrics] = []

    def add(self, metrics: EpisodeMetrics) -> None:
        self._episodes.append(metrics)

    def get_running_average(self, window: int = 10) -> float:
        """Compute running average reward over last `window` episodes."""
        if not self._episodes:
            return 0.0
        recent = self._episodes[-window:]
        return sum(m.reward for m in recent) / len(recent)

    def get_accuracy(self, window: int = 10) -> dict[str, float]:
        """Compute severity and component accuracy over last `window` episodes."""
        recent = self._episodes[-window:]
        if not recent:
            return {"severity": 0.0, "component": 0.0}
        return {
            "severity": sum(1 for m in recent if m.severity_correct) / len(recent),
            "component": sum(1 for m in recent if m.component_correct) / len(recent),
        }

    def summary(self) -> dict[str, Any]:
        """Full training summary."""
        if not self._episodes:
            return {"total_episodes": 0}

        rewards = [m.reward for m in self._episodes]
        return {
            "total_episodes": len(self._episodes),
            "mean_reward": round(sum(rewards) / len(rewards), 4),
            "best_reward": round(max(rewards), 4),
            "worst_reward": round(min(rewards), 4),
            "final_10_avg": round(self.get_running_average(10), 4),
            "accuracy": self.get_accuracy(len(self._episodes)),
            "total_tokens": sum(m.tokens_used for m in self._episodes),
            "exploration_pct": round(
                sum(1 for m in self._episodes if m.was_exploration) / len(self._episodes) * 100,
                1,
            ),
        }

    def save(self, path: Path) -> None:
        data = [m.to_dict() for m in self._episodes]
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> None:
        if path.exists():
            data = json.loads(path.read_text())
            self._episodes = [
                EpisodeMetrics(**{k: v for k, v in d.items() if k in EpisodeMetrics.__dataclass_fields__})
                for d in data
            ]

    @property
    def all_episodes(self) -> list[EpisodeMetrics]:
        return self._episodes
