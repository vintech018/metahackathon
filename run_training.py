#!/usr/bin/env python3
"""
Training runner — launch the AI vulnerability triage agent for training.

Usage:
    python run_training.py --episodes 20
    python run_training.py --episodes 50 --model gpt-4o
    python run_training.py --episodes 10 --no-extended

Environment:
    OPENAI_API_KEY must be set.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from agent.config import AgentConfig, LLMConfig, RLConfig
from agent.triage_agent import TriageAgent


def main():
    parser = argparse.ArgumentParser(
        description="Train the AI Vulnerability Triage Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--episodes", type=int, default=20,
        help="Number of training episodes (default: 20)",
    )
    parser.add_argument(
        "--model", type=str, default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.3,
        help="LLM temperature (default: 0.3)",
    )
    parser.add_argument(
        "--no-extended", action="store_true",
        help="Use only original tasks (no extended noisy/multi-vuln set)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug output from the environment",
    )
    parser.add_argument(
        "--data-dir", type=str, default="agent_data",
        help="Directory for persisted agent state (default: agent_data)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-episode output",
    )

    args = parser.parse_args()

    config = AgentConfig(
        llm=LLMConfig(
            model=args.model,
            temperature=args.temperature,
        ),
        rl=RLConfig(
            max_episodes=args.episodes,
        ),
        data_dir=Path(args.data_dir),
        use_extended_tasks=not args.no_extended,
        debug=args.debug,
    )

    agent = TriageAgent(config)
    summary = agent.train(episodes=args.episodes, verbose=not args.quiet)

    print("\n✅ Training complete!")
    print(f"   Data saved to: {args.data_dir}/")
    print(f"   Launch dashboard: python run_dashboard.py")

    return summary


if __name__ == "__main__":
    main()
