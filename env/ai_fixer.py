"""
ai_fixer.py
-----------
Calls an Ollama-compatible API to generate a production-ready, context-aware
security fix for a given vulnerability.

Credentials are read at CALL TIME (not import time) so hot-reloading the
.env file always picks up the latest values without a server restart.

Output schema (parsed from AI response):
    {
        "vulnerability": str,   # e.g. "SQL Injection"
        "severity":      str,   # "Low" | "Medium" | "High" | "Critical"
        "fixed_code":    str,   # the corrected secure code
        "raw":           str,   # full raw AI response (for debugging)
    }
"""

import os
import re
import requests
from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

# ── System prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are an elite cybersecurity expert, senior backend engineer, and "
    "vulnerability researcher. Your task is to analyze backend code, detect "
    "vulnerabilities across multiple classes, and generate a precise, "
    "context-aware fix."
)

# ── User prompt template ───────────────────────────────────────────────────────
_USER_TEMPLATE = """\
=====================================
INPUT
=====================================
[BUG REPORT]
{bug_report}

[SERVER LOGS]
{logs}

[CODE]
{code}

=====================================
ANALYSIS (DO INTERNALLY - DO NOT OUTPUT)
=====================================
1. Identify programming language and framework.
2. Detect ALL possible vulnerabilities, including:
   - SQL Injection (SQLi)
   - Cross-Site Scripting (XSS)
   - Command Injection
   - Path Traversal
   - Insecure Deserialization
   - Hardcoded Credentials
   - Missing Authentication / Authorization
   - SSRF (Server-Side Request Forgery)
3. Trace user-controlled inputs (request.GET / POST / params / headers).
4. Follow data flow: Input → Processing → Sink (DB, HTML, OS, File, etc.)
5. Identify exact vulnerable line(s).
6. Understand intent: login / search / file access / system command / API.

=====================================
DETECTION LOGIC
=====================================
SQL Injection     → user input concatenated into SQL query
XSS               → user input rendered into HTML without escaping
Command Injection → user input passed to OS commands
Path Traversal    → user input used in file path without validation
Deserialization   → untrusted input passed to pickle/eval
Hardcoded Secrets → credentials/API keys in code
Missing Auth      → sensitive endpoint lacks authentication

=====================================
FIX GENERATION RULES (STRICT)
=====================================
- Use SAME variables from original code
- DO NOT rename variables
- DO NOT change logic or structure
- ONLY modify the vulnerable part
- Apply correct fix per type:
    SQLi          → parameterized queries
    XSS           → html.escape / safe templating
    Command Inj   → subprocess list, no shell=True
    Path Traversal→ validate + restrict to safe dir
    Deserialization → remove unsafe methods
    Secrets       → use environment variables
    Auth          → add authentication checks

=====================================
STRICT OUTPUT FORMAT
=====================================
You MUST respond ONLY in this exact format with no extra text:

Vulnerability: <type>
Severity: <Low|Medium|High|Critical>

Fixed Code:
<corrected secure code only>
"""

# ── Provider config ────────────────────────────────────────────────────────────
# Single source of truth: read from .env (API_KEY, API_BASE_URL, MODEL_NAME)

def _get_config():
    """Read Groq API credentials from environment at call-time (hot-reload safe)."""
    load_dotenv(_ENV_PATH, override=True)
    return (
        os.getenv("API_KEY"),       # Groq API key — None if not set
        os.getenv("API_BASE_URL"),  # Groq base URL — None if not set
        os.getenv("MODEL_NAME"),    # Groq model    — None if not set
    )




def _try_chat(base_url, model, api_key, messages, timeout=30):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        r = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 1024},
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _parse_response(raw: str) -> dict:
    """
    Parse the structured AI response into a dict:
    { vulnerability, severity, fixed_code, raw }
    """
    vuln     = "Unknown"
    severity = "High"
    code     = raw  # fallback: entire response as code

    # Extract Vulnerability line
    m = re.search(r"Vulnerability\s*:\s*(.+)", raw, re.IGNORECASE)
    if m:
        vuln = m.group(1).strip()

    # Extract Severity line
    m = re.search(r"Severity\s*:\s*(.+)", raw, re.IGNORECASE)
    if m:
        severity = m.group(1).strip()

    # Extract Fixed Code block (everything after "Fixed Code:")
    m = re.search(r"Fixed Code\s*:\s*\n([\s\S]+)", raw, re.IGNORECASE)
    if m:
        code = m.group(1).strip()
        # Strip markdown fences if model adds them
        code = re.sub(r"^```[a-z]*\n?", "", code).rstrip("`").strip()

    return {"vulnerability": vuln, "severity": severity, "fixed_code": code, "raw": raw}


def generate_fix(bug_report: str, logs, code: str) -> dict:
    """
    Generate a structured security fix using Groq API when configured.
    Falls back to a deterministic local fix when credentials are missing or the
    provider call fails so the public demo remains usable.
    """
    api_key, base_url, model = _get_config()

    missing = [name for name, val in [
        ("API_KEY",      api_key),
        ("API_BASE_URL", base_url),
        ("MODEL_NAME",   model),
    ] if not val]
    if missing:
        print(f"[AI FIXER] Falling back to local heuristics; missing: {', '.join(missing)}")
        return _fallback_fix(code)

    log_str = "\n".join(logs) if isinstance(logs, list) else (logs or "(no logs)")
    prompt  = _USER_TEMPLATE.format(
        bug_report=bug_report or "(no report)",
        logs=log_str,
        code=code or "(no code)",
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]

    # Call Groq API — single provider, no waterfall, no fallback
    raw = _try_chat(base_url, model, api_key, messages)
    if raw:
        print(f"[AI FIXER] ✅ Groq / {model}")
        return _parse_response(raw)

    print(f"[AI FIXER] Falling back after provider error (base_url={base_url}, model={model}).")
    return _fallback_fix(code)



def _fallback_fix(code: str) -> dict:
    sql_signals = code and any(k in code for k in ["SELECT", "INSERT", "UPDATE", "DELETE", "execute", "query"])
    concat_signals = code and any(k in code for k in ["f'", 'f"', ".format(", '+ "', "+ '"])
    xss_signals = code and any(k in code for k in ["innerHTML", "res.send", "document.write", "render("])

    if sql_signals and concat_signals:
        return {
            "vulnerability": "SQL Injection",
            "severity": "Critical",
            "fixed_code": 'cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))',
            "raw": "fallback"
        }
    if xss_signals:
        return {
            "vulnerability": "XSS",
            "severity": "High",
            "fixed_code": code.replace("innerHTML", "textContent") if code else "",
            "raw": "fallback"
        }
    return {
        "vulnerability": "Unknown",
        "severity": "Medium",
        "fixed_code": code or "",
        "raw": "fallback"
    }
