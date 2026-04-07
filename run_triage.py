#!/usr/bin/env python3
"""
Single-report inference — triage a vulnerability report without training.

Usage:
    python run_triage.py                           # interactive mode
    python run_triage.py --report "SQL injection found in login..."
    python run_triage.py --file report.txt
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent.config import AgentConfig, LLMConfig
from agent.triage_agent import TriageAgent

SAMPLE_REPORTS = [
    (
        "SQL Injection in User Search\n"
        "The /api/v2/search endpoint concatenates user input directly into SQL queries. "
        "Sending ' UNION SELECT * FROM credentials -- in the search field returns "
        "all stored credentials including hashed passwords and API keys. "
        "No authentication is required to access the search endpoint."
    ),
    (
        "CRITICAL: Our production Kubernetes cluster has an exposed dashboard at "
        "/k8s-dashboard with default credentials (admin/admin). Anyone on the "
        "internet can access it and deploy arbitrary containers, view secrets, "
        "and access all namespace resources. The dashboard is exposed through "
        "an Ingress controller without any authentication middleware."
    ),
    (
        "hey found something kinda weird... when i upload a profile pic on ur "
        "site, if i change the file extension to .svg and put javascript in it, "
        "the script runs when anyone views my profile. managed to grab session "
        "cookies with it. also noticed the upload endpoint doesn't check file "
        "size so i could probably DOS the server by uploading huge files lol"
    ),
]


def main():
    parser = argparse.ArgumentParser(description="Triage a single vulnerability report")
    parser.add_argument("--report", type=str, help="Report text to analyze")
    parser.add_argument("--file", type=str, help="File containing the report")
    parser.add_argument("--model", type=str, default=None, help="Groq model (default: read from MODEL_NAME env var)")
    parser.add_argument("--sample", type=int, choices=[1, 2, 3], help="Use a sample report (1-3)")

    args = parser.parse_args()

    # Determine report text
    if args.file:
        report = Path(args.file).read_text()
    elif args.report:
        report = args.report
    elif args.sample:
        report = SAMPLE_REPORTS[args.sample - 1]
    else:
        # Interactive mode
        print("🛡️  AI Vulnerability Triage — Single Report Mode")
        print("=" * 60)
        print("\nPaste your vulnerability report (press Ctrl+D or Ctrl+Z when done):\n")
        try:
            report = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nAborted.")
            return

    if not report.strip():
        print("Error: Empty report. Please provide a vulnerability report.")
        return

    config = AgentConfig(llm=LLMConfig(model=args.model))
    agent = TriageAgent(config)
    agent.triage_single(report, verbose=True)


if __name__ == "__main__":
    main()
