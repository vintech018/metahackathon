#!/usr/bin/env python3
"""
inference.py — OpenEnv-compatible inference script for Bug Bounty Vulnerability Triage.

Runs a single-step triage episode:
    1. Resets the TriageEnv to get a vulnerability report
    2. Sends the report to an LLM for multi-step analysis
    3. Submits the structured action to the environment
    4. Prints exactly 3 log lines in strict OpenEnv format

Usage:
    python inference.py

Environment variables:
    API_BASE_URL  — OpenAI-compatible API base URL
    MODEL_NAME    — Model identifier (e.g., gpt-4o-mini)
    API_KEY       — API key (falls back to HF_TOKEN if not set)
"""

import json
import os
import re
import sys

from pathlib import Path

from openai import OpenAI

from env.triage_env import TriageEnv
from file_parser import extract_text


# ── Load .env ─────────────────────────────────────────────────────────────────

def _load_dotenv(path: str = ".env") -> None:
    """Load environment variables from .env file if it exists."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────────────────

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "llama-3.3-70b-versatile")
API_KEY = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN", "")

FALLBACK_ACTION = {
    "severity": "low",
    "component": "api",
    "remediation": "apply security best practices",
}

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_COMPONENTS = {"auth", "database", "api", "frontend", "network"}


# ─────────────────────────────────────────────────────────────────────────────
#  Prompt Construction
# ─────────────────────────────────────────────────────────────────────────────

def _is_code_input(text: str) -> bool:
    """Heuristic: detect if the input looks like source code rather than a report."""
    code_indicators = [
        "def ", "class ", "import ",           # Python
        "public ", "private ", "void ",          # Java
        "function ", "const ", "var ",            # JS/general
        "SELECT ", "INSERT ", "UPDATE ",          # SQL fragments
    ]
    return any(indicator in text for indicator in code_indicators)


def build_prompt(report: str) -> tuple[str, str]:
    """
    Build the system and user prompts for the LLM.

    Detects whether the input is a vulnerability report or source code
    and adjusts the prompt accordingly.

    Parameters
    ----------
    report : str
        Raw vulnerability report text or extracted source code.

    Returns
    -------
    tuple[str, str]
        (system_prompt, user_prompt)
    """
    system_prompt = (
        "You are a senior security engineer performing bug bounty triage. "
        "You may receive either a vulnerability report or source code "
        "containing vulnerabilities. "
        "Analyze the input carefully and produce accurate, "
        "security-focused decisions."
    )

    # ── Determine input type and build context-aware header ────────────
    is_code = _is_code_input(report)

    if is_code:
        input_header = (
            "Analyze the following source code for security vulnerabilities.\n"
            "Look for vulnerabilities such as SQL injection, XSS, "
            "insecure authentication, unsafe file handling, "
            "command injection, path traversal, and insecure deserialization.\n\n"
            "SOURCE CODE:\n"
        )
    else:
        input_header = (
            "Analyze the following vulnerability report and provide a triage decision.\n\n"
            "VULNERABILITY REPORT:\n"
        )

    user_prompt = (
        f"{input_header}"
        f"{report}\n\n"
        "INSTRUCTIONS:\n"
        "1. Determine the severity: exactly one of critical, high, medium, or low.\n"
        "   - critical: RCE, full authentication bypass, mass data breach, infrastructure compromise\n"
        "   - high: significant data exposure, privilege escalation, stored XSS with session hijack\n"
        "   - medium: limited data exposure, CSRF, open redirect, moderate impact vulnerabilities\n"
        "   - low: information disclosure, minor issues, theoretical attacks with mitigations in place\n\n"
        "2. Identify the primary affected component: exactly one of auth, database, api, frontend, or network.\n"
        "   - auth: authentication, authorization, session management, JWT, OAuth, password reset, login bypass\n"
        "   - database: SQL injection, data storage, query manipulation, NoSQL injection\n"
        "   - api: REST/GraphQL endpoints, server-side logic, file upload, IDOR on API endpoints\n"
        "   - frontend: XSS (reflected/stored), CSRF, client-side rendering, output encoding issues\n"
        "   - network: SSRF, DNS rebinding, infrastructure, cloud metadata, network segmentation\n\n"
        "3. Provide detailed, actionable remediation that addresses ALL vulnerabilities mentioned.\n"
        "   Your remediation MUST be comprehensive and security-focused. Include specific technical fixes.\n"
        "   When applicable, mention: input validation, sanitize user input, output encoding, "
        "parameterized queries, prepared statements, token management, session security, "
        "CSP (content security policy), access control, rate limiting, RBAC, "
        "cookie security (HttpOnly, Secure, SameSite flags), "
        "URL allowlisting, network segmentation, and other relevant controls.\n"
        "   If the report describes a chained or multiple-step attack, explicitly mention that "
        "multiple vulnerabilities need to be addressed in a combined remediation approach, "
        "acknowledging the chain of attacks.\n\n"
        "RESPOND WITH ONLY A SINGLE JSON OBJECT — no explanations, no markdown, no extra text:\n"
        '{"severity": "...", "component": "...", "remediation": "..."}\n'
    )

    return system_prompt, user_prompt


# ─────────────────────────────────────────────────────────────────────────────
#  LLM Interaction
# ─────────────────────────────────────────────────────────────────────────────

def get_model_action(client: OpenAI, system_prompt: str, user_prompt: str) -> str:
    """
    Call the LLM and return the raw response text.

    Parameters
    ----------
    client : OpenAI
        Initialized OpenAI client.
    system_prompt : str
        System-level instruction.
    user_prompt : str
        User-level prompt with the vulnerability report.

    Returns
    -------
    str
        Raw text response from the model.
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.2,
        max_tokens=300,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────────────────────
#  JSON Parsing
# ─────────────────────────────────────────────────────────────────────────────

def safe_json_parse(text: str) -> dict:
    """
    Safely extract and validate a triage action from LLM output.

    Handles:
        - Raw JSON responses
        - JSON wrapped in markdown code fences
        - Missing or invalid fields (falls back to defaults)

    Parameters
    ----------
    text : str
        Raw text from the LLM.

    Returns
    -------
    dict
        Validated action dict with keys: severity, component, remediation.
    """
    # Attempt 1: Try to find JSON within markdown code fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1))
            return _validate_action(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

    # Attempt 2: Try to extract raw JSON object
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            parsed = json.loads(brace_match.group(0))
            return _validate_action(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

    # Attempt 3: Try full text as JSON
    try:
        parsed = json.loads(text.strip())
        return _validate_action(parsed)
    except (json.JSONDecodeError, ValueError):
        pass

    # All parsing failed — return fallback
    return dict(FALLBACK_ACTION)


def _validate_action(parsed: dict) -> dict:
    """
    Validate and normalize parsed action fields.

    Ensures severity and component are valid canonical values.
    Falls back to defaults for any missing or invalid field.
    """
    # Extract and normalize severity
    severity = str(parsed.get("severity", "low")).strip().lower()
    if severity not in VALID_SEVERITIES:
        severity = FALLBACK_ACTION["severity"]

    # Extract and normalize component
    component = str(parsed.get("component", "api")).strip().lower()
    if component not in VALID_COMPONENTS:
        component = FALLBACK_ACTION["component"]

    # Extract remediation text
    remediation = str(parsed.get("remediation", "")).strip()
    if not remediation:
        remediation = FALLBACK_ACTION["remediation"]

    return {
        "severity": severity,
        "component": component,
        "remediation": remediation,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Main Execution Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    Full OpenEnv-compatible execution pipeline.

    1. Initialize environment and OpenAI client
    2. Reset environment to get a vulnerability report
    3. Build prompt and query the LLM
    4. Parse response into a structured action
    5. Submit action to environment
    6. Print exactly 3 log lines in strict OpenEnv format
    """
    # ── Initialize ────────────────────────────────────────────────────────
    env = TriageEnv()
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # ── Reset environment ─────────────────────────────────────────────────
    obs = env.reset()
    task_id = obs.task_id

    # ── File input handling ───────────────────────────────────────────────
    input_file = os.getenv("INPUT_FILE")
    file_text = ""
    if input_file and os.path.isfile(input_file):
        file_text = extract_text(input_file)

    # Use file content if available, otherwise fall back to observation
    report = file_text if file_text else obs.report

    # ── Log: START ────────────────────────────────────────────────────────
    print(f"[START] task={task_id} env=TriageEnv model={MODEL_NAME}")

    # ── Get action from LLM ──────────────────────────────────────────────
    action_dict = None
    error_msg = None

    try:
        system_prompt, user_prompt = build_prompt(report)
        raw_response = get_model_action(client, system_prompt, user_prompt)
        action_dict = safe_json_parse(raw_response)
    except Exception as e:
        error_msg = str(e)
        action_dict = dict(FALLBACK_ACTION)

    # ── Submit action to environment ─────────────────────────────────────
    reward = 0.0
    done = False

    try:
        obs_next, reward, done, info = env.step(action_dict)
    except Exception as e:
        error_msg = str(e)
        done = True

    # ── Format values for logging ────────────────────────────────────────
    action_json = json.dumps(action_dict, separators=(",", ":"))
    reward_fmt = f"{reward:.2f}"
    done_str = "true" if done else "false"
    error_str = error_msg if error_msg else "null"
    score = reward
    success = score >= 0.6
    success_str = "true" if success else "false"

    # ── Log: STEP ─────────────────────────────────────────────────────────
    print(f"[STEP] step=1 action={action_json} reward={reward_fmt} done={done_str} error={error_str}")

    # ── Log: END ──────────────────────────────────────────────────────────
    print(f"[END] success={success_str} steps=1 score={reward_fmt} rewards={reward_fmt}")


if __name__ == "__main__":
    main()
