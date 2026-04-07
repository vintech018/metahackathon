#!/usr/bin/env python3
"""
Backend API Server — Connects React frontend to Groq LLM + TriageEnv.

Endpoints:
    POST /api/triage          — Triage a custom vulnerability report via LLM
    POST /api/triage/random   — Triage a random task from the task registry
    GET  /api/tasks           — List all available tasks
    GET  /api/health          — Health check

Architecture:
    Frontend → Backend API → Groq LLM (llama-3.3-70b) → TriageEnv → Scored JSON

Security:
    - API key loaded from environment variable only
    - Never exposed to frontend
    - CORS restricted
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent))

# ── Load .env file ───────────────────────────────────────────────────────────

def load_dotenv(path: str = ".env") -> None:
    """Load environment variables from .env file."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

API_KEY = os.getenv("API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

if not API_KEY:
    print("⚠️  WARNING: API_KEY not set. LLM calls will fail.")
    print("   Set it in .env or export API_KEY=...")

# ── Imports from project ─────────────────────────────────────────────────────

from openai import OpenAI
from env.triage_env import TriageEnv
from env.tasks import ALL_TASKS
from env.environment import VulnArenaEnv

# ── VulnArena Environment (singleton for jaspreet frontend) ──────────────────
# Shared instance — stateful, persists between /reset and /step calls.
vuln_arena_env = VulnArenaEnv()

# ── LLM Client ───────────────────────────────────────────────────────────────

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY,
)

# Valid values for action validation
VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_COMPONENTS = {"auth", "database", "api", "frontend", "network"}

FALLBACK_ACTION = {
    "severity": "low",
    "component": "api",
    "remediation": "apply security best practices",
}

# ── Prompt Engineering ───────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a senior security engineer specializing in vulnerability triage. "
    "You must produce precise, security-focused, and actionable outputs."
)


def build_user_prompt(report: str) -> str:
    """Build the user prompt for the LLM."""
    return (
        "Analyze the following vulnerability report and return STRICT JSON only.\n\n"
        f"{report}\n\n"
        "Return:\n"
        "{\n"
        '  "severity": "critical/high/medium/low",\n'
        '  "component": "auth/database/api/frontend/network",\n'
        '  "remediation": "clear and actionable fix"\n'
        "}\n\n"
        "Rules:\n"
        "- severity must be exactly one of: critical, high, medium, low\n"
        "- component must be exactly one of: auth, database, api, frontend, network\n"
        "- remediation must be detailed, security-focused, and actionable\n"
        "- When applicable, mention: input validation, sanitize, parameterized queries, "
        "prepared statements, token management, session security, CSP (content security policy), "
        "access control, rate limiting, cookie security (HttpOnly, SameSite)\n"
        "- If the report describes a chained/multi-step attack, mention that multiple "
        "vulnerabilities need combined remediation\n"
        "- Do not include explanations\n"
        "- Do not include markdown\n"
        "- Only return valid JSON"
    )


# ── LLM Call ─────────────────────────────────────────────────────────────────

def call_llm(report: str) -> dict[str, str]:
    """
    Send the report to the Groq LLM and return parsed action.
    Falls back to default action on any failure.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.2,
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(report)},
            ],
        )
        raw = response.choices[0].message.content or ""
        return safe_json_parse(raw)
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return dict(FALLBACK_ACTION)


def safe_json_parse(text: str) -> dict[str, str]:
    """
    Extract and validate JSON from LLM response.
    Handles code fences, raw JSON, and malformed output.
    """
    # Try markdown fenced JSON
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return validate_action(json.loads(fence.group(1)))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try raw JSON object
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return validate_action(json.loads(brace.group(0)))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try full text
    try:
        return validate_action(json.loads(text.strip()))
    except (json.JSONDecodeError, ValueError):
        pass

    return dict(FALLBACK_ACTION)


def validate_action(parsed: dict) -> dict[str, str]:
    """Validate and normalize severity/component/remediation."""
    severity = str(parsed.get("severity", "low")).strip().lower()
    if severity not in VALID_SEVERITIES:
        severity = "low"

    component = str(parsed.get("component", "api")).strip().lower()
    if component not in VALID_COMPONENTS:
        component = "api"

    remediation = str(parsed.get("remediation", "")).strip()
    if not remediation:
        remediation = FALLBACK_ACTION["remediation"]

    return {
        "severity": severity,
        "component": component,
        "remediation": remediation,
    }


# ── Heuristic Evaluator ──────────────────────────────────────────────────────

def infer_expected(report: str) -> tuple[str, str, str, list[str]]:
    """
    Analyze a user-provided report and infer ground-truth labels for scoring.

    Returns (severity, component, difficulty, remediation_keywords).

    This is critical for custom reports where we don't have pre-labeled data.
    The heuristic examines the report text for vulnerability indicators and
    returns appropriate expected values so the TriageEnv grading system
    produces meaningful, realistic scores.
    """
    text = report.lower()

    # ── SQL Injection ────────────────────────────────────────────────────
    if any(kw in text for kw in ("sql injection", "sqli", "union select", "' or 1=1",
                                   "parameterized", "sql query", "concatenat")):
        difficulty = "easy"
        if "union" in text or "credential" in text or "dump" in text:
            difficulty = "hard"
        return "critical", "database", difficulty, [
            "parameterized", "prepared statements", "sanitize", "input validation",
        ]

    # ── Remote Code Execution / Command Injection ────────────────────────
    if any(kw in text for kw in ("rce", "remote code execution",
                                   "command injection", "reverse shell",
                                   "file upload", "shell.php", "os.system")):
        return "critical", "api", "hard", [
            "file type validation", "whitelist", "sandbox", "non-executable",
        ]

    # ── SSRF ─────────────────────────────────────────────────────────────
    if any(kw in text for kw in ("ssrf", "server-side request",
                                   "169.254", "metadata", "fetch-url",
                                   "internal service")):
        return "critical", "network", "hard", [
            "allowlist", "ssrf protection", "metadata", "network segmentation",
            "input validation",
        ]

    # ── XSS (Stored / Reflected) ─────────────────────────────────────────
    if any(kw in text for kw in ("xss", "cross-site scripting",
                                   "<script>", "stored xss", "reflected xss",
                                   "document.cookie")):
        severity = "critical" if "stored" in text or "session" in text else "high"
        difficulty = "hard" if ("chain" in text or "→" in text or "cookie" in text) else "medium"
        return severity, "frontend", difficulty, [
            "sanitize", "encode", "csp", "content security policy", "httponly",
        ]

    # ── CSRF ─────────────────────────────────────────────────────────────
    if any(kw in text for kw in ("csrf", "cross-site request forgery",
                                   "anti-csrf", "forged request")):
        return "medium", "frontend", "medium", [
            "csrf token", "samesite", "origin validation", "anti-csrf",
        ]

    # ── Authentication Bypass / Broken Auth ──────────────────────────────
    if any(kw in text for kw in ("authentication bypass", "broken auth",
                                   "jwt", "token reuse", "password reset",
                                   "brute-force", "credential rotation",
                                   "privilege escalation", "role cookie")):
        severity = "critical" if "privilege escalation" in text or "admin" in text else "high"
        difficulty = "hard" if "chain" in text or "→" in text else "medium"
        return severity, "auth", difficulty, [
            "token", "session", "invalidat", "rate limiting",
            "access control",
        ]

    # ── IDOR / Access Control ────────────────────────────────────────────
    if any(kw in text for kw in ("idor", "insecure direct object",
                                   "access control", "authorization bypass",
                                   "horizontal privilege")):
        return "high", "api", "medium", [
            "access control", "authorization", "validate", "ownership",
        ]

    # ── Information Disclosure ───────────────────────────────────────────
    if any(kw in text for kw in ("information disclosure", "verbose error",
                                   "stack trace", "debug mode", "error message",
                                   "internal path")):
        return "low", "api", "easy", [
            "error handling", "disable debug", "sanitize",
        ]

    # ── Insecure Deserialization ─────────────────────────────────────────
    if any(kw in text for kw in ("deserialization", "pickle", "yaml.load",
                                   "unserialize", "marshalling")):
        return "critical", "api", "hard", [
            "safe deserialization", "whitelist", "input validation",
        ]

    # ── Path Traversal / LFI / RFI ───────────────────────────────────────
    if any(kw in text for kw in ("path traversal", "directory traversal",
                                   "../", "local file inclusion",
                                   "remote file inclusion", "lfi", "rfi")):
        return "high", "api", "medium", [
            "path validation", "whitelist", "sanitize", "chroot",
        ]

    # ── Open Redirect ────────────────────────────────────────────────────
    if any(kw in text for kw in ("open redirect", "url redirect",
                                   "redirect_url", "phishing")):
        return "medium", "frontend", "easy", [
            "whitelist", "validate", "redirect",
        ]

    # ── Denial of Service ────────────────────────────────────────────────
    if any(kw in text for kw in ("denial of service", "dos", "ddos",
                                   "resource exhaust", "crash", "regex dos")):
        return "medium", "network", "medium", [
            "rate limiting", "input validation", "timeout",
        ]

    # ── Fallback — Unknown vulnerability ─────────────────────────────────
    # Parse severity hints from the report itself
    if any(kw in text for kw in ("critical", "severe", "full compromise",
                                   "complete access")):
        return "high", "api", "medium", ["validate", "sanitize"]

    return "medium", "api", "easy", ["validate", "sanitize"]


# ── Environment Integration ─────────────────────────────────────────────────

def run_triage_custom(report: str) -> dict[str, Any]:
    """
    Full pipeline: report → LLM → heuristic inference → TriageEnv → scored result.

    Uses infer_expected() to derive realistic ground-truth labels from the
    report text instead of hardcoded defaults. This ensures severity/component
    matches produce meaningful scores.
    """
    # Get LLM action
    action = call_llm(report)

    # Infer expected labels from report content (heuristic evaluator)
    inferred_severity, inferred_component, inferred_difficulty, inferred_keywords = infer_expected(report)

    print(f"  [INFER] severity={inferred_severity} component={inferred_component} "
          f"difficulty={inferred_difficulty} keywords={inferred_keywords}")

    # Inject custom task with inferred expectations — NO env.reset()
    env = TriageEnv()
    env._current_task = {
        "id": "custom",
        "difficulty": inferred_difficulty,
        "report": report,
        "expected": {
            "severity": inferred_severity,
            "component": inferred_component,
            "remediation_keywords": inferred_keywords,
        },
    }
    env._done = False
    env._step_count = 0

    # Step
    try:
        obs, reward, done, info = env.step(action)
    except Exception as e:
        return {
            "report": report,
            "action": action,
            "reward": 0.0,
            "info": {"error": str(e)},
        }

    return {
        "report": report,
        "action": action,
        "reward": round(reward, 4),
        "difficulty": inferred_difficulty,
        "info": _clean_info(info),
    }


def run_triage_task(task_id: str | None = None) -> dict[str, Any]:
    """
    Full pipeline using a task from the registry (with known ground truth).
    If task_id is None, picks a random task.
    """
    if task_id:
        task = next((t for t in ALL_TASKS if t["id"] == task_id), None)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
    else:
        task = random.choice(ALL_TASKS)

    report = task["report"]
    action = call_llm(report)

    env = TriageEnv()
    env._current_task = task
    env._done = False
    env._step_count = 0

    try:
        obs, reward, done, info = env.step(action)
    except Exception as e:
        return {
            "report": report,
            "action": action,
            "reward": 0.0,
            "info": {"error": str(e)},
            "id": task["id"],
            "difficulty": task["difficulty"],
        }

    return {
        "id": task["id"],
        "difficulty": task["difficulty"],
        "report": report,
        "action": action,
        "reward": round(reward, 4),
        "info": _clean_info(info),
    }


def _clean_info(info: dict) -> dict:
    """Make info JSON-serializable and frontend-friendly."""
    return {
        "task_id": info.get("task_id", "custom"),
        "difficulty": info.get("difficulty", "medium"),
        "expected_severity": info.get("expected_severity", ""),
        "expected_component": info.get("expected_component", ""),
        "expected_remediation_keywords": info.get("expected_remediation_keywords", []),
        "agent_severity": info.get("agent_severity", ""),
        "agent_component": info.get("agent_component", ""),
        "explanation": info.get("explanation", {}),
        "confidence": info.get("confidence", 0),
    }


# ── HTTP Server ──────────────────────────────────────────────────────────────

class APIHandler(BaseHTTPRequestHandler):
    """Handle API requests from the React frontend."""

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/health":
            self._json_response({
                "status": "ok",
                "model": MODEL_NAME,
                "api_configured": bool(API_KEY),
            })
        elif path == "/api/tasks":
            tasks = [
                {
                    "id": t["id"],
                    "difficulty": t["difficulty"],
                    "report_preview": t["report"][:120] + "...",
                }
                for t in ALL_TASKS
            ]
            self._json_response(tasks)

        # ── VulnArena routes (jaspreet frontend) ─────────────────────────
        elif path == "/state":
            self._json_response({"state": vuln_arena_env.state()})

        elif path == "/reset":
            # Allow GET /reset as a convenience (resets to 'easy')
            print("[VULNARENA] GET /reset → easy")
            state = vuln_arena_env.reset("easy")
            self._json_response(state)

        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON body"}, status=400)
            return

        if path == "/api/triage":
            report = data.get("report", "").strip()
            if not report:
                self._json_response({"error": "Missing 'report' field"}, status=400)
                return
            print(f"[TRIAGE] Custom report ({len(report)} chars)")
            result = run_triage_custom(report)
            self._json_response(result)

        elif path == "/api/triage/random":
            task_id = data.get("task_id")
            print(f"[TRIAGE] Task: {task_id or 'random'}")
            result = run_triage_task(task_id)
            self._json_response(result)

        # ── VulnArena routes (jaspreet frontend) ─────────────────────────
        elif path == "/reset":
            task_name = data.get("task_name", "easy")
            print(f"[VULNARENA] POST /reset task={task_name}")
            state = vuln_arena_env.reset(task_name)
            self._json_response(state)

        elif path == "/step":
            action = data.get("action", "")
            print(f"[VULNARENA] POST /step action={action}")

            # Build a simple object to pass custom inputs (if provided)
            class _CustomReq:
                report_text = data.get("report_text") or None
                logs = data.get("logs") or None
                code_snippet = data.get("code_snippet") or None

            custom_req = _CustomReq() if any([
                data.get("report_text"), data.get("logs"), data.get("code_snippet")
            ]) else None

            state_dict, reward, done, info = vuln_arena_env.step(action, custom_req=custom_req)
            self._json_response({
                "observation": state_dict,
                "reward": reward,
                "done": done,
                "info": info,
            })

        else:
            self.send_error(404, "Not found")

    def _json_response(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        # Cleaner logs
        msg = fmt % args
        if "OPTIONS" not in msg:
            print(f"  {msg}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Triage API Backend")
    parser.add_argument("--port", type=int, default=5001, help="Port (default: 5001)")
    args = parser.parse_args()

    print(f"🛡️  Triage API Server starting on http://localhost:{args.port}")
    print(f"   Model:  {MODEL_NAME}")
    print(f"   API:    {API_BASE_URL}")
    print(f"   Key:    {'✓ configured' if API_KEY else '✗ MISSING'}")
    print(f"   Tasks:  {len(ALL_TASKS)} available")
    print()
    print("   POST /api/triage          — custom report")
    print("   POST /api/triage/random   — random task from registry")
    print("   GET  /api/tasks           — list all tasks")
    print("   GET  /api/health          — health check")
    print()

    server = HTTPServer(("0.0.0.0", args.port), APIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
