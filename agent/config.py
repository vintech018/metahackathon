"""
Configuration for the AI Vulnerability Triage Agent.

Centralizes all knobs: model settings, RL hyperparameters, file paths,
and prompt templates.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LLMConfig:
    """OpenAI-compatible LLM settings."""
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 2048
    api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Export it as an environment variable or pass it directly."
            )


@dataclass(frozen=True)
class RLConfig:
    """Reinforcement learning hyperparameters."""
    # Experience replay
    buffer_capacity: int = 500
    min_buffer_for_reflection: int = 5

    # Exploration
    epsilon_start: float = 0.3      # Initial exploration rate
    epsilon_end: float = 0.05       # Final exploration rate
    epsilon_decay_episodes: int = 50 # Episodes to decay over

    # Reward thresholds
    low_reward_threshold: float = 0.6   # Trigger reflection below this
    high_reward_threshold: float = 0.9  # Consider "mastered"

    # Training
    max_episodes: int = 100
    reflection_every_n: int = 5    # Reflect every N episodes


@dataclass(frozen=True)
class AgentConfig:
    """Top-level agent configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    rl: RLConfig = field(default_factory=RLConfig)

    # Persistence
    data_dir: Path = Path("agent_data")
    experience_file: str = "experience_buffer.json"
    memory_file: str = "reflection_memory.json"
    metrics_file: str = "training_metrics.json"

    # Environment
    use_extended_tasks: bool = True
    use_difficulty_scaling: bool = True
    debug: bool = False

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
