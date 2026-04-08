#!/usr/bin/env python3
"""
Deployment backend for the VulnArena AI demo.

This server powers two public-facing experiences:
1. The multi-step VulnArena environment used by the React frontend.
2. Optional report triage endpoints that call an OpenAI-compatible model.

The deployed demo is intentionally defensive:
- frontend assets are served by the same process as the API
- each browser session gets an isolated environment instance
- large request bodies are rejected early
- expensive endpoints are rate limited
- the app still works without external model credentials by falling back to
  deterministic heuristics
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from openai import OpenAI
from pydantic import BaseModel, Field


APP_ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

# Ensure project root is importable for local package-style imports.
sys.path.insert(0, str(APP_ROOT))

from env.environment import VulnArenaEnv
from env.tasks import ALL_TASKS
from env.triage_env import TriageEnv


def load_dotenv(path: str = ".env") -> None:
    """Load environment variables from a local .env file if it exists."""
    env_path = APP_ROOT / path
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv()


API_KEY = os.getenv("API_KEY", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile").strip()

LLM_ENABLED = all((API_KEY, API_BASE_URL, MODEL_NAME))
TRIAGE_API_ENABLED = os.getenv("ENABLE_PUBLIC_TRIAGE_API", "false").lower() in {
    "1",
    "true",
    "yes",
}
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "131072"))
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))
GENERAL_RATE_LIMIT = int(os.getenv("GENERAL_RATE_LIMIT", "120"))
GENERAL_RATE_WINDOW_SECONDS = int(os.getenv("GENERAL_RATE_WINDOW_SECONDS", "300"))
EXPENSIVE_RATE_LIMIT = int(os.getenv("EXPENSIVE_RATE_LIMIT", "8"))
EXPENSIVE_RATE_WINDOW_SECONDS = int(os.getenv("EXPENSIVE_RATE_WINDOW_SECONDS", "600"))
SESSION_COOKIE = "vulnarena_session"

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
extra_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL) if LLM_ENABLED else None


VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_COMPONENTS = {"auth", "database", "api", "frontend", "network"}

FALLBACK_ACTION = {
    "severity": "low",
    "component": "api",
    "remediation": "Apply input validation and security best practices.",
}

SYSTEM_PROMPT = (
    "You are a senior security engineer specializing in vulnerability triage. "
    "Produce precise, security-focused, and actionable JSON only."
)


SESSION_LOCK = threading.Lock()
SESSIONS: dict[str, dict[str, Any]] = {}
RATE_LIMIT_LOCK = threading.Lock()
RATE_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)


class ResetRequest(BaseModel):
    task_name: str = "easy"


class StepRequest(BaseModel):
    action: str
    report_text: str | None = None
    logs: list[str] | None = None
    code_snippet: str | None = None


class TriageRequest(BaseModel):
    report: str = Field(min_length=1, max_length=16000)


class RandomTriageRequest(BaseModel):
    task_id: str | None = Field(default=None, max_length=128)


app = FastAPI(title="VulnArena AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*DEFAULT_ALLOWED_ORIGINS, *extra_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def _now() -> float:
    return time.monotonic()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(subject: str, bucket: str, limit: int, window_seconds: int) -> None:
    key = (bucket, subject)
    current = _now()
    with RATE_LIMIT_LOCK:
        q = RATE_BUCKETS[key]
        while q and current - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {bucket}. Please wait and try again.",
            )
        q.append(current)


def _prune_sessions_locked() -> None:
    cutoff = time.time() - SESSION_TTL_SECONDS
    expired = [sid for sid, data in SESSIONS.items() if data["last_seen"] < cutoff]
    for sid in expired:
        del SESSIONS[sid]


def _get_session_env(request: Request) -> tuple[str, VulnArenaEnv, bool]:
    session_id = request.cookies.get(SESSION_COOKIE, "")
    created = False

    with SESSION_LOCK:
        _prune_sessions_locked()
        if not re.fullmatch(r"[0-9a-f]{32}", session_id):
            session_id = uuid.uuid4().hex
            created = True

        session = SESSIONS.get(session_id)
        if session is None:
            session = {"env": VulnArenaEnv(), "last_seen": time.time()}
            SESSIONS[session_id] = session
            created = True
        else:
            session["last_seen"] = time.time()

    return session_id, session["env"], created


def _json_response(
    payload: Any,
    request: Request,
    session_id: str | None = None,
    session_created: bool = False,
    status_code: int = 200,
) -> JSONResponse:
    response = JSONResponse(payload, status_code=status_code)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if session_id and session_created:
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            samesite="lax",
        )
    return response


def _validate_step_payload(req: StepRequest) -> None:
    report = req.report_text or ""
    code = req.code_snippet or ""
    logs = req.logs or []
    joined_logs = "\n".join(logs)

    if len(report) > 16000:
        raise HTTPException(status_code=413, detail="Bug report is too large.")
    if len(code) > 24000:
        raise HTTPException(status_code=413, detail="Code snippet is too large.")
    if len(joined_logs) > 16000:
        raise HTTPException(status_code=413, detail="Log payload is too large.")


def build_user_prompt(report: str) -> str:
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
        "- If the report describes a chained or multi-step attack, mention that multiple "
        "vulnerabilities need combined remediation\n"
        "- Do not include explanations\n"
        "- Do not include markdown\n"
        "- Only return valid JSON"
    )


def safe_json_parse(text: str) -> dict[str, str]:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return validate_action(json.loads(fence.group(1)))
        except (json.JSONDecodeError, ValueError):
            pass

    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return validate_action(json.loads(brace.group(0)))
        except (json.JSONDecodeError, ValueError):
            pass

    try:
        return validate_action(json.loads(text.strip()))
    except (json.JSONDecodeError, ValueError):
        return dict(FALLBACK_ACTION)


def validate_action(parsed: dict[str, Any]) -> dict[str, str]:
    severity = str(parsed.get("severity", "low")).strip().lower()
    if severity not in VALID_SEVERITIES:
        severity = FALLBACK_ACTION["severity"]

    component = str(parsed.get("component", "api")).strip().lower()
    if component not in VALID_COMPONENTS:
        component = FALLBACK_ACTION["component"]

    remediation = str(parsed.get("remediation", "")).strip()
    if not remediation:
        remediation = FALLBACK_ACTION["remediation"]

    return {
        "severity": severity,
        "component": component,
        "remediation": remediation,
    }


def infer_expected(report: str) -> tuple[str, str, str, list[str]]:
    text = report.lower()

    if any(
        kw in text
        for kw in ("sql injection", "sqli", "union select", "' or 1=1", "parameterized", "sql query", "concatenat")
    ):
        difficulty = "hard" if any(kw in text for kw in ("union", "credential", "dump")) else "easy"
        return "critical", "database", difficulty, [
            "parameterized queries",
            "prepared statements",
            "input validation",
            "least-privilege database access",
        ]

    if any(
        kw in text
        for kw in ("rce", "remote code execution", "command injection", "reverse shell", "file upload", "shell.php", "os.system")
    ):
        return "critical", "api", "hard", [
            "strict allowlists",
            "sandbox execution",
            "file type validation",
            "remove shell execution paths",
        ]

    if any(kw in text for kw in ("ssrf", "server-side request", "169.254", "metadata", "fetch-url", "internal service")):
        return "critical", "network", "hard", [
            "URL allowlists",
            "private IP blocking",
            "metadata endpoint protections",
            "network segmentation",
        ]

    if any(kw in text for kw in ("xss", "cross-site scripting", "<script>", "stored xss", "reflected xss", "document.cookie")):
        severity = "critical" if "stored" in text or "session" in text else "high"
        difficulty = "hard" if any(kw in text for kw in ("chain", "cookie", "→")) else "medium"
        return severity, "frontend", difficulty, [
            "output encoding",
            "input sanitization",
            "strict CSP",
            "HttpOnly and SameSite cookies",
        ]

    if any(kw in text for kw in ("csrf", "cross-site request forgery", "anti-csrf", "forged request")):
        return "medium", "frontend", "medium", [
            "anti-CSRF tokens",
            "SameSite cookies",
            "Origin and Referer validation",
        ]

    if any(
        kw in text
        for kw in (
            "authentication bypass",
            "broken auth",
            "jwt",
            "token reuse",
            "password reset",
            "brute-force",
            "credential rotation",
            "privilege escalation",
            "role cookie",
        )
    ):
        severity = "critical" if any(kw in text for kw in ("privilege escalation", "admin")) else "high"
        difficulty = "hard" if any(kw in text for kw in ("chain", "→")) else "medium"
        return severity, "auth", difficulty, [
            "token invalidation",
            "session rotation",
            "server-side authorization checks",
            "rate limiting",
        ]

    if any(kw in text for kw in ("idor", "insecure direct object", "access control", "authorization bypass", "horizontal privilege")):
        return "high", "api", "medium", [
            "ownership checks",
            "server-side authorization",
            "object-level access control",
        ]

    if any(kw in text for kw in ("information disclosure", "verbose error", "stack trace", "debug mode", "error message", "internal path")):
        return "low", "api", "easy", [
            "generic error responses",
            "disable debug mode",
            "server-side structured logging",
        ]

    if any(kw in text for kw in ("deserialization", "pickle", "yaml.load", "unserialize", "marshalling")):
        return "critical", "api", "hard", [
            "safe deserialization",
            "schema validation",
            "allowlists for accepted types",
        ]

    if any(kw in text for kw in ("path traversal", "directory traversal", "../", "local file inclusion", "remote file inclusion", "lfi", "rfi")):
        return "high", "api", "medium", [
            "path normalization",
            "allowlisted directories",
            "filesystem sandboxing",
        ]

    if any(kw in text for kw in ("open redirect", "url redirect", "redirect_url", "phishing")):
        return "medium", "frontend", "easy", [
            "redirect allowlists",
            "destination validation",
        ]

    if any(kw in text for kw in ("denial of service", "dos", "ddos", "resource exhaust", "crash", "regex dos")):
        return "medium", "network", "medium", [
            "request size limits",
            "timeouts",
            "resource quotas",
            "rate limiting",
        ]

    if any(kw in text for kw in ("critical", "severe", "full compromise", "complete access")):
        return "high", "api", "medium", ["input validation", "access control", "least privilege"]

    return "medium", "api", "easy", ["input validation", "access control", "logging"]


def build_fallback_action(report: str) -> dict[str, str]:
    severity, component, _, keywords = infer_expected(report)
    component_specific = {
        "database": "Replace string-built queries with parameterized statements and tighten database privileges.",
        "frontend": "Sanitize untrusted content before rendering and enforce browser-side protections.",
        "auth": "Invalidate stale credentials, rotate sessions, and enforce server-side authorization.",
        "network": "Restrict outbound targets, block private address ranges, and isolate sensitive services.",
        "api": "Validate untrusted input and remove unsafe execution or file access paths.",
    }
    tail = ", ".join(keywords[:4])
    return {
        "severity": severity,
        "component": component,
        "remediation": f"{component_specific.get(component, FALLBACK_ACTION['remediation'])} Prioritize {tail}.",
    }


def call_llm(report: str) -> dict[str, str]:
    if not client:
        return build_fallback_action(report)

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
    except Exception as exc:
        print(f"[LLM ERROR] {exc}")
        return build_fallback_action(report)


def _clean_info(info: dict[str, Any]) -> dict[str, Any]:
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


def run_triage_custom(report: str) -> dict[str, Any]:
    action = call_llm(report)
    inferred_severity, inferred_component, inferred_difficulty, inferred_keywords = infer_expected(report)

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

    try:
        _, reward, _, info = env.step(action)
    except Exception as exc:
        return {
            "report": report,
            "action": action,
            "reward": 0.0,
            "info": {"error": str(exc)},
        }

    return {
        "report": report,
        "action": action,
        "reward": round(reward, 4),
        "difficulty": inferred_difficulty,
        "info": _clean_info(info),
        "mode": "live-llm" if LLM_ENABLED else "heuristic-fallback",
    }


def run_triage_task(task_id: str | None = None) -> dict[str, Any]:
    if task_id:
        task = next((candidate for candidate in ALL_TASKS if candidate["id"] == task_id), None)
        if task is None:
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
        _, reward, _, info = env.step(action)
    except Exception as exc:
        return {
            "report": report,
            "action": action,
            "reward": 0.0,
            "info": {"error": str(exc)},
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
        "mode": "live-llm" if LLM_ENABLED else "heuristic-fallback",
    }


@app.middleware("http")
async def enforce_request_limits(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_BODY_BYTES:
                    return _json_response(
                        {"error": f"Request body exceeds {MAX_BODY_BYTES} bytes."},
                        request,
                        status_code=413,
                    )
            except ValueError:
                return _json_response({"error": "Invalid Content-Length header."}, request, status_code=400)

    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


@app.get("/api/health")
def health(request: Request):
    return _json_response(
        {
            "status": "ok",
            "frontend_built": FRONTEND_INDEX.exists(),
            "llm_mode": "live" if LLM_ENABLED else "heuristic-fallback",
            "public_triage_api": TRIAGE_API_ENABLED,
        },
        request,
    )


@app.get("/api/tasks")
def list_tasks(request: Request):
    tasks = [
        {
            "id": task["id"],
            "difficulty": task["difficulty"],
            "report_preview": f"{task['report'][:120]}...",
        }
        for task in ALL_TASKS
    ]
    return _json_response(tasks, request)


@app.post("/api/triage")
def triage_custom(req: TriageRequest, request: Request):
    if not TRIAGE_API_ENABLED:
        raise HTTPException(status_code=403, detail="Public triage API is disabled for this deployment.")
    _enforce_rate_limit(_client_ip(request), "triage", EXPENSIVE_RATE_LIMIT, EXPENSIVE_RATE_WINDOW_SECONDS)
    return _json_response(run_triage_custom(req.report.strip()), request)


@app.post("/api/triage/random")
def triage_random(req: RandomTriageRequest, request: Request):
    if not TRIAGE_API_ENABLED:
        raise HTTPException(status_code=403, detail="Public triage API is disabled for this deployment.")
    _enforce_rate_limit(_client_ip(request), "triage", EXPENSIVE_RATE_LIMIT, EXPENSIVE_RATE_WINDOW_SECONDS)
    return _json_response(run_triage_task(req.task_id), request)


@app.get("/state")
def state(request: Request):
    _enforce_rate_limit(_client_ip(request), "env", GENERAL_RATE_LIMIT, GENERAL_RATE_WINDOW_SECONDS)
    session_id, env, created = _get_session_env(request)
    return _json_response({"state": env.state()}, request, session_id=session_id, session_created=created)


@app.post("/reset")
def reset(req: ResetRequest, request: Request):
    _enforce_rate_limit(_client_ip(request), "env", GENERAL_RATE_LIMIT, GENERAL_RATE_WINDOW_SECONDS)
    session_id, env, created = _get_session_env(request)
    task_name = req.task_name if req.task_name in {"easy", "medium", "hard"} else "easy"
    return _json_response(env.reset(task_name), request, session_id=session_id, session_created=created)


@app.post("/step")
def step(req: StepRequest, request: Request):
    _validate_step_payload(req)
    _enforce_rate_limit(_client_ip(request), "env", GENERAL_RATE_LIMIT, GENERAL_RATE_WINDOW_SECONDS)
    if req.action == "suggest_fix":
        _enforce_rate_limit(_client_ip(request), "llm-fix", EXPENSIVE_RATE_LIMIT, EXPENSIVE_RATE_WINDOW_SECONDS)

    session_id, env, created = _get_session_env(request)
    custom_req = None
    if any((req.report_text, req.logs, req.code_snippet)):
        custom_req = SimpleNamespace(
            report_text=req.report_text or None,
            logs=req.logs if req.logs is not None else None,
            code_snippet=req.code_snippet or None,
        )

    try:
        observation, reward, done, info = env.step(req.action, custom_req=custom_req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step execution failed: {exc}") from exc

    return _json_response(
        {
            "observation": observation,
            "reward": reward,
            "done": done,
            "info": info,
        },
        request,
        session_id=session_id,
        session_created=created,
    )


def _resolve_frontend_path(full_path: str) -> Path | None:
    if not FRONTEND_DIST.exists():
        return None

    candidate = (FRONTEND_DIST / full_path).resolve()
    try:
        candidate.relative_to(FRONTEND_DIST.resolve())
    except ValueError:
        return None

    if candidate.is_file():
        return candidate
    return None


@app.get("/")
def frontend_root():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return JSONResponse(
        {"error": "Frontend build not found. Run the frontend build before starting the server."},
        status_code=503,
    )


@app.get("/{full_path:path}")
def frontend_assets(full_path: str):
    if full_path.startswith(("api/", "reset", "step", "state")):
        raise HTTPException(status_code=404, detail="Not found")

    asset = _resolve_frontend_path(full_path)
    if asset:
        return FileResponse(asset)
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    raise HTTPException(status_code=404, detail="Frontend build not found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the VulnArena deployment backend.")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "7860")))
    args = parser.parse_args()

    print(f"[BOOT] VulnArena AI listening on http://0.0.0.0:{args.port}")
    print(f"[BOOT] Frontend dist: {'present' if FRONTEND_INDEX.exists() else 'missing'}")
    print(f"[BOOT] LLM mode: {'live' if LLM_ENABLED else 'heuristic fallback'}")
    print(f"[BOOT] Public triage API: {'enabled' if TRIAGE_API_ENABLED else 'disabled'}")

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
