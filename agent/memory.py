"""
Memory and Reflection system for the triage agent.

Implements:
    • ReflectionMemory — stores past failures and lessons learned
    • ReflectionEngine — uses the LLM to analyze failures and generate
      improvement strategies that are fed back as context in future analyses
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.config import LLMConfig
from agent.rl import Experience


# ─────────────────────────────────────────────────────────────────────────────
#  Reflection Entry
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReflectionEntry:
    """A single reflection generated from a low-scoring attempt."""
    episode: int
    task_id: str
    original_reward: float
    expected_severity: str
    agent_severity: str
    expected_component: str
    agent_component: str
    failure_analysis: str      # LLM's analysis of what went wrong
    improvement_strategy: str  # LLM's strategy for doing better
    learned_pattern: str       # Distilled pattern/rule
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode": self.episode,
            "task_id": self.task_id,
            "original_reward": self.original_reward,
            "expected_severity": self.expected_severity,
            "agent_severity": self.agent_severity,
            "expected_component": self.expected_component,
            "agent_component": self.agent_component,
            "failure_analysis": self.failure_analysis,
            "improvement_strategy": self.improvement_strategy,
            "learned_pattern": self.learned_pattern,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReflectionEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─────────────────────────────────────────────────────────────────────────────
#  Reflection Memory
# ─────────────────────────────────────────────────────────────────────────────

class ReflectionMemory:
    """
    Persistent memory of past reflections and learned patterns.
    Used to build context for future LLM analyses.
    """

    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max_entries
        self._entries: list[ReflectionEntry] = []
        self._patterns: list[str] = []  # Distilled rules

    def add(self, entry: ReflectionEntry) -> None:
        self._entries.append(entry)
        if entry.learned_pattern:
            self._patterns.append(entry.learned_pattern)
        # Evict oldest if over capacity
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)
        if len(self._patterns) > self._max_entries:
            self._patterns.pop(0)

    def get_context_for_report(self, report: str, max_entries: int = 5) -> str:
        """
        Build a context string from relevant past reflections.
        Includes the most recent learned patterns and any task-specific lessons.
        """
        if not self._entries:
            return ""

        parts = []

        # Add distilled patterns (most valuable)
        if self._patterns:
            recent_patterns = self._patterns[-min(10, len(self._patterns)):]
            parts.append("LEARNED RULES FROM PAST MISTAKES:")
            for i, p in enumerate(recent_patterns, 1):
                parts.append(f"  {i}. {p}")

        # Add recent failure analyses (most recent first)
        recent_failures = self._entries[-min(max_entries, len(self._entries)):]
        if recent_failures:
            parts.append("\nRECENT FAILURE ANALYSES:")
            for entry in reversed(recent_failures):
                parts.append(
                    f"  - Task {entry.task_id}: Expected {entry.expected_severity}/{entry.expected_component}, "
                    f"got {entry.agent_severity}/{entry.agent_component} (reward={entry.original_reward:.2f}). "
                    f"Lesson: {entry.improvement_strategy[:200]}"
                )

        return "\n".join(parts)

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def patterns(self) -> list[str]:
        return list(self._patterns)

    def save(self, path: Path) -> None:
        data = {
            "entries": [e.to_dict() for e in self._entries],
            "patterns": self._patterns,
        }
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> None:
        if path.exists():
            data = json.loads(path.read_text())
            self._entries = [ReflectionEntry.from_dict(e) for e in data.get("entries", [])]
            self._patterns = data.get("patterns", [])

    def summary(self) -> dict[str, Any]:
        return {
            "total_reflections": len(self._entries),
            "total_patterns": len(self._patterns),
            "recent_patterns": self._patterns[-5:] if self._patterns else [],
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Reflection Engine
# ─────────────────────────────────────────────────────────────────────────────

REFLECTION_PROMPT = """\
You are a cybersecurity triage coach. An AI agent attempted to triage a \
vulnerability report but scored poorly. Analyze what went wrong and provide \
actionable feedback.

ORIGINAL REPORT:
{report}

AGENT'S DECISION:
  Severity:  {agent_severity}  (expected: {expected_severity})
  Component: {agent_component}  (expected: {expected_component})
  Remediation: {agent_remediation}

GRADING BREAKDOWN:
{grading_breakdown}

REWARD: {reward:.4f}

Respond in JSON:
{{
    "failure_analysis": "What specific mistakes did the agent make and why?",
    "improvement_strategy": "How should the agent approach similar reports in the future?",
    "learned_pattern": "A concise rule (1-2 sentences) the agent should remember for future triages"
}}"""


class ReflectionEngine:
    """
    Uses the LLM to analyze failed triage attempts and generate
    improvement strategies stored in ReflectionMemory.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._config = config or LLMConfig()
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._config.validate()
            self._client = OpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
            )
        return self._client

    def reflect(
        self,
        experience: Experience,
        memory: ReflectionMemory,
    ) -> ReflectionEntry | None:
        """
        Analyze a low-scoring experience and generate a reflection.

        Returns None if reflection fails or isn't needed.
        """
        info = experience.info

        breakdown = json.dumps(
            info.get("explanation", {}),
            indent=2,
        )

        prompt = REFLECTION_PROMPT.format(
            report=experience.report[:1000],
            agent_severity=experience.action.get("severity", "?"),
            expected_severity=info.get("expected_severity", "?"),
            agent_component=experience.action.get("component", "?"),
            expected_component=info.get("expected_component", "?"),
            agent_remediation=experience.action.get("remediation", "?")[:500],
            grading_breakdown=breakdown,
            reward=experience.reward,
        )

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._config.model,
                temperature=0.4,
                max_tokens=1024,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a security triage coach. Analyze failures "
                            "and produce actionable improvement rules."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content or ""
            # Parse JSON
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                return None

            from datetime import datetime

            entry = ReflectionEntry(
                episode=experience.episode,
                task_id=experience.task_id,
                original_reward=experience.reward,
                expected_severity=info.get("expected_severity", "?"),
                agent_severity=experience.action.get("severity", "?"),
                expected_component=info.get("expected_component", "?"),
                agent_component=experience.action.get("component", "?"),
                failure_analysis=result.get("failure_analysis", ""),
                improvement_strategy=result.get("improvement_strategy", ""),
                learned_pattern=result.get("learned_pattern", ""),
                timestamp=datetime.now().isoformat(),
            )

            memory.add(entry)
            return entry

        except Exception as e:
            print(f"[REFLECTION] Error: {e}")
            return None
