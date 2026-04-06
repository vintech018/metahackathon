#!/usr/bin/env python3
"""
Dashboard runner — start the explainability web dashboard.

Usage:
    python run_dashboard.py
    python run_dashboard.py --port 9090
    python run_dashboard.py --data-dir agent_data
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent.dashboard import run_dashboard


def main():
    parser = argparse.ArgumentParser(description="Launch the Triage Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--data-dir", type=str, default="agent_data", help="Agent data directory")
    args = parser.parse_args()

    run_dashboard(port=args.port, data_dir=args.data_dir)


if __name__ == "__main__":
    main()
