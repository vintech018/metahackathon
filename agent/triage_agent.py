"""
Triage Agent — Main orchestrator combining LLM reasoning, RL, and memory.

This is the central controller that:
    1. Takes a vulnerability report from TriageEnv
    2. Queries reflection memory for relevant past lessons
    3. Runs the multi-step LLM reasoning pipeline
    4. Submits the action to the environment
    5. Stores the experience in the replay buffer
    6. Triggers reflection on low-scoring episodes
    7. Tracks metrics across the entire training run
"""

from __future__ import annotations

import random
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent.config import AgentConfig
from agent.memory import ReflectionEngine, ReflectionMemory
from agent.reasoning import LLMReasoningEngine, ReasoningTrace
from agent.rl import (
    EpsilonScheduler,
    EpisodeMetrics,
    Experience,
    ExperienceBuffer,
    MetricsTracker,
)
from env.actions import VALID_COMPONENTS, VALID_SEVERITIES
from env.triage_env import TriageEnv

console = Console()


class TriageAgent:
    """
    Self-improving AI triage agent with hybrid LLM + RL architecture.

    Architecture:
        ┌────────────────────────────────────────────┐
        │              TriageAgent                    │
        │  ┌──────────┐  ┌───────────┐  ┌─────────┐ │
        │  │ LLM      │  │ RL Policy │  │ Memory  │ │
        │  │ Reasoning │←→│ (ε-greedy)│←→│ System  │ │
        │  │ Engine    │  │           │  │         │ │
        │  └──────────┘  └───────────┘  └─────────┘ │
        │       ↕                            ↕       │
        │  ┌──────────┐            ┌──────────────┐  │
        │  │ TriageEnv│            │ Reflection   │  │
        │  │          │            │ Engine       │  │
        │  └──────────┘            └──────────────┘  │
        └────────────────────────────────────────────┘
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        self._config = config or AgentConfig()
        self._config.ensure_data_dir()

        # Core components
        self._reasoning = LLMReasoningEngine(self._config.llm)
        self._buffer = ExperienceBuffer(self._config.rl.buffer_capacity)
        self._memory = ReflectionMemory()
        self._reflection_engine = ReflectionEngine(self._config.llm)
        self._epsilon = EpsilonScheduler(
            start=self._config.rl.epsilon_start,
            end=self._config.rl.epsilon_end,
            decay_episodes=self._config.rl.epsilon_decay_episodes,
        )
        self._metrics = MetricsTracker()

        # Environment
        if self._config.use_extended_tasks:
            self._env = self._create_extended_env()
        else:
            self._env = TriageEnv(
                debug=self._config.debug,
                use_difficulty_scaling=self._config.use_difficulty_scaling,
            )

        # State
        self._current_episode = 0

        # Load persisted data
        self._load_state()

    def _create_extended_env(self) -> TriageEnv:
        """Create env with extended task set by monkey-patching."""
        import env.tasks as tasks_module
        from env.tasks_extended import ALL_TASKS_EXTENDED

        original_tasks = tasks_module.ALL_TASKS
        tasks_module.ALL_TASKS = ALL_TASKS_EXTENDED

        env = TriageEnv(
            debug=self._config.debug,
            use_difficulty_scaling=self._config.use_difficulty_scaling,
        )

        # Restore original to not affect other imports
        tasks_module.ALL_TASKS = original_tasks

        # Store extended tasks directly on env for use
        env._extended_tasks = ALL_TASKS_EXTENDED
        return env

    def _random_action(self) -> dict[str, str]:
        """Generate a random exploration action."""
        return {
            "severity": random.choice(list(VALID_SEVERITIES)),
            "component": random.choice(list(VALID_COMPONENTS)),
            "remediation": "Apply standard security best practices including input validation, output encoding, proper authentication, and defense-in-depth measures.",
        }

    # ── Core Loop ──────────────────────────────────────────────────────────

    def run_episode(self, verbose: bool = True) -> EpisodeMetrics:
        """
        Run a single triage episode:
        1. Reset env → get report
        2. Decide explore vs. exploit
        3. If exploit: run multi-step LLM reasoning
        4. Submit action → get reward
        5. Store experience
        6. Maybe reflect
        """
        self._current_episode += 1
        episode = self._current_episode

        # Use extended tasks if available
        if hasattr(self._env, "_extended_tasks"):
            from env.tasks_extended import ALL_TASKS_EXTENDED
            self._env._current_task = random.choice(ALL_TASKS_EXTENDED)
            self._env._step_count = 0
            self._env._done = False
            self._env._last_reward = None
            obs = self._env._make_observation()
        else:
            obs = self._env.reset()

        report = obs.report
        task_id = obs.task_id
        difficulty = obs.difficulty

        eps = self._epsilon.get_epsilon(episode)
        is_exploration = self._epsilon.should_explore(episode)

        trace: ReasoningTrace | None = None
        tokens_used = 0

        if is_exploration:
            action = self._random_action()
            reasoning_summary = "[EXPLORATION] Random action"
            reasoning_steps = 0

            if verbose:
                console.print(
                    f"[bold yellow]Episode {episode}[/] | Task: {task_id} | "
                    f"[yellow]EXPLORING (ε={eps:.3f})[/yellow]"
                )
        else:
            # Get reflection context from memory
            reflection_ctx = self._memory.get_context_for_report(report)

            # Run multi-step reasoning
            trace = self._reasoning.analyze(report, reflection_ctx)
            action = trace.final_action
            reasoning_summary = trace.summary()
            reasoning_steps = 4
            tokens_used = trace.total_tokens_used

            if verbose:
                console.print(
                    f"[bold cyan]Episode {episode}[/] | Task: {task_id} | "
                    f"[cyan]EXPLOITING (ε={eps:.3f})[/cyan]"
                )
                console.print(f"  Reasoning: {reasoning_summary}")

        # Submit to environment
        obs_next, reward, done, info = self._env.step(action)

        # Track correctness
        severity_correct = action.get("severity") == info.get("expected_severity")
        component_correct = action.get("component") == info.get("expected_component")

        if verbose:
            reward_color = "green" if reward >= 0.8 else "yellow" if reward >= 0.5 else "red"
            console.print(
                f"  Reward: [{reward_color}]{reward:.4f}[/{reward_color}] | "
                f"Severity: {'✓' if severity_correct else '✗'} | "
                f"Component: {'✓' if component_correct else '✗'}"
            )

        # Store experience
        exp = Experience(
            episode=episode,
            task_id=task_id,
            difficulty=difficulty,
            report=report,
            action=action,
            reward=reward,
            info=info,
            reasoning_summary=reasoning_summary,
        )
        self._buffer.add(exp)

        # Maybe reflect on low-scoring episodes
        reflection_triggered = False
        if (
            reward < self._config.rl.low_reward_threshold
            and not is_exploration
            and episode % self._config.rl.reflection_every_n == 0
        ):
            reflection_triggered = True
            if verbose:
                console.print("  [magenta]→ Triggering reflection...[/magenta]")
            reflection = self._reflection_engine.reflect(exp, self._memory)
            if reflection and verbose:
                console.print(
                    f"  [magenta]  Pattern learned: {reflection.learned_pattern}[/magenta]"
                )

        # Track metrics
        metrics = EpisodeMetrics(
            episode=episode,
            task_id=task_id,
            difficulty=difficulty,
            reward=reward,
            epsilon=eps,
            was_exploration=is_exploration,
            severity_correct=severity_correct,
            component_correct=component_correct,
            reasoning_steps=reasoning_steps,
            tokens_used=tokens_used,
            reflection_triggered=reflection_triggered,
        )
        self._metrics.add(metrics)

        return metrics

    def train(self, episodes: int | None = None, verbose: bool = True) -> dict[str, Any]:
        """
        Run a full training loop.

        Parameters
        ----------
        episodes : int
            Number of episodes to train. Defaults to config.rl.max_episodes.
        verbose : bool
            Whether to print progress.

        Returns
        -------
        dict
            Training summary including metrics and buffer stats.
        """
        n_episodes = episodes or self._config.rl.max_episodes

        if verbose:
            console.print(Panel(
                f"[bold]Starting Training: {n_episodes} episodes[/bold]\n"
                f"Model: {self._config.llm.model} | "
                f"Extended Tasks: {self._config.use_extended_tasks}\n"
                f"ε: {self._config.rl.epsilon_start:.2f} → {self._config.rl.epsilon_end:.2f} "
                f"over {self._config.rl.epsilon_decay_episodes} episodes",
                title="🛡️ AI Vulnerability Triage Agent",
                border_style="cyan",
            ))

        for i in range(n_episodes):
            self.run_episode(verbose=verbose)

            # Periodic summary
            if verbose and (i + 1) % 10 == 0:
                avg = self._metrics.get_running_average(10)
                acc = self._metrics.get_accuracy(10)
                console.print(
                    f"\n[bold]── Checkpoint (Episode {self._current_episode}) ──[/bold]"
                )
                console.print(
                    f"  Running Avg Reward: {avg:.4f} | "
                    f"Severity Acc: {acc['severity']:.0%} | "
                    f"Component Acc: {acc['component']:.0%}"
                )
                console.print(
                    f"  Buffer: {self._buffer.size} | "
                    f"Reflections: {self._memory.size} | "
                    f"Patterns: {len(self._memory.patterns)}\n"
                )

            # Save state periodically
            if (i + 1) % 25 == 0:
                self._save_state()

        # Final save
        self._save_state()

        summary = self.get_summary()

        if verbose:
            self._print_summary(summary)

        return summary

    def triage_single(self, report: str, verbose: bool = True) -> dict[str, Any]:
        """
        Triage a single vulnerability report (inference mode, no RL).

        Returns
        -------
        dict
            Contains action, reasoning trace, and explanation.
        """
        reflection_ctx = self._memory.get_context_for_report(report)
        trace = self._reasoning.analyze(report, reflection_ctx)

        result = {
            "action": trace.final_action,
            "reasoning": trace.to_dict(),
            "reasoning_summary": trace.summary(),
            "tokens_used": trace.total_tokens_used,
        }

        if verbose:
            self._print_triage_result(result)

        return result

    # ── Reporting ──────────────────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive training summary."""
        return {
            "training": self._metrics.summary(),
            "buffer": self._buffer.stats(),
            "memory": self._memory.summary(),
            "tokens_total": self._reasoning.total_tokens,
        }

    def get_episode_history(self) -> list[dict[str, Any]]:
        """Return full episode history for dashboard."""
        return [m.to_dict() for m in self._metrics.all_episodes]

    def get_experience_history(self) -> list[dict[str, Any]]:
        """Return experience buffer for dashboard."""
        return [e.to_dict() for e in self._buffer]

    def _print_summary(self, summary: dict[str, Any]) -> None:
        """Print a rich formatted training summary."""
        console.print("\n")
        console.print(Panel(
            "[bold green]Training Complete[/bold green]",
            border_style="green",
        ))

        # Training metrics table
        table = Table(title="Training Metrics", border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        training = summary["training"]
        table.add_row("Total Episodes", str(training["total_episodes"]))
        table.add_row("Mean Reward", f"{training['mean_reward']:.4f}")
        table.add_row("Best Reward", f"{training['best_reward']:.4f}")
        table.add_row("Final 10 Avg", f"{training['final_10_avg']:.4f}")
        table.add_row("Severity Accuracy", f"{training['accuracy']['severity']:.1%}")
        table.add_row("Component Accuracy", f"{training['accuracy']['component']:.1%}")
        table.add_row("Total Tokens", f"{training['total_tokens']:,}")
        table.add_row("Exploration %", f"{training['exploration_pct']}%")

        console.print(table)

        # Memory summary
        mem = summary["memory"]
        console.print(f"\n[bold]Reflection Memory:[/bold] {mem['total_reflections']} entries, {mem['total_patterns']} patterns")
        if mem["recent_patterns"]:
            console.print("[bold]Recent Learned Patterns:[/bold]")
            for p in mem["recent_patterns"]:
                console.print(f"  • {p}")

    def _print_triage_result(self, result: dict[str, Any]) -> None:
        """Print a rich formatted triage result."""
        action = result["action"]
        reasoning = result["reasoning"]

        severity_colors = {
            "critical": "red",
            "high": "dark_orange",
            "medium": "yellow",
            "low": "green",
        }
        sev_color = severity_colors.get(action["severity"], "white")

        console.print(Panel(
            f"[bold {sev_color}]Severity: {action['severity'].upper()}[/bold {sev_color}]\n"
            f"[bold]Component: {action['component']}[/bold]\n\n"
            f"[bold]Remediation:[/bold]\n{action['remediation']}\n\n"
            f"[dim]Tokens used: {result['tokens_used']}[/dim]",
            title="🛡️ Triage Decision",
            border_style=sev_color,
        ))

        # Show reasoning steps
        if reasoning.get("step1_vuln_identification"):
            step1 = reasoning["step1_vuln_identification"]
            console.print(f"\n[bold]Step 1 — Vulnerability:[/bold] {step1.get('primary_vulnerability', '?')}")
            console.print(f"  Confidence: {step1.get('confidence', '?')}")

        if reasoning.get("step2_impact_assessment"):
            step2 = reasoning["step2_impact_assessment"]
            console.print(f"\n[bold]Step 2 — Impact:[/bold]")
            console.print(f"  Blast radius: {step2.get('blast_radius', '?')}")
            console.print(f"  Exploitability: {step2.get('exploitability', '?')}")

        if reasoning.get("step3_severity_component"):
            step3 = reasoning["step3_severity_component"]
            console.print(f"\n[bold]Step 3 — Classification:[/bold]")
            console.print(f"  CVSS Estimate: {step3.get('cvss_estimate', '?')}")
            console.print(f"  Justification: {step3.get('severity_justification', '?')}")

    # ── Persistence ────────────────────────────────────────────────────────

    def _save_state(self) -> None:
        """Persist all agent state to disk."""
        d = self._config.data_dir
        self._buffer.save(d / self._config.experience_file)
        self._memory.save(d / self._config.memory_file)
        self._metrics.save(d / self._config.metrics_file)

    def _load_state(self) -> None:
        """Load persisted state from disk."""
        d = self._config.data_dir
        self._buffer.load(d / self._config.experience_file)
        self._memory.load(d / self._config.memory_file)
        self._metrics.load(d / self._config.metrics_file)

        # Restore episode counter
        if self._metrics.all_episodes:
            self._current_episode = max(m.episode for m in self._metrics.all_episodes)
