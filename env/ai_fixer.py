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

# ── Provider candidates ────────────────────────────────────────────────────────
_CANDIDATES = [
    ("https://api.groq.com/openai/v1",        "llama-3.1-8b-instant"),
    ("https://api.groq.com/openai/v1",        "llama-3.3-70b-versatile"),
    ("https://api.together.xyz/v1",            "meta-llama/Llama-3-8b-chat-hf"),
    ("https://openrouter.ai/api/v1",           "meta-llama/llama-3-8b-instruct:free"),
    ("https://api.openai.com/v1",              "gpt-3.5-turbo"),
    ("https://api.mistral.ai/v1",              "mistral-tiny"),
    ("http://localhost:11434/v1",              "llama3"),
]


def _get_config():
    load_dotenv(_ENV_PATH, override=True)
    return (
        os.getenv("OLLAMA_API_KEY",  "").strip(),
        os.getenv("OLLAMA_BASE_URL", "").strip(),
        os.getenv("OLLAMA_MODEL",    "").strip(),
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
    Generate a structured security fix.
    Always returns a dict: { vulnerability, severity, fixed_code, raw }
    """
    api_key, base_url, model = _get_config()

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

    # 1. Try explicitly configured provider
    if base_url and model:
        raw = _try_chat(base_url, model, api_key, messages)
        if raw:
            print(f"[AI FIXER] ✅ {base_url} / {model}")
            return _parse_response(raw)
        print(f"[AI FIXER] ❌ Configured provider failed, auto-discovering...")

    # 2. Auto-discover
    for c_url, c_model in _CANDIDATES:
        if c_url == base_url and c_model == model:
            continue
        raw = _try_chat(c_url, c_model, api_key, messages, timeout=15)
        if raw:
            print(f"[AI FIXER] ✅ Auto-discovered: {c_url} / {c_model}")
            os.environ["OLLAMA_BASE_URL"] = c_url
            os.environ["OLLAMA_MODEL"]    = c_model
            return _parse_response(raw)

    # 3. Deterministic fallback
    print("[AI FIXER] ⚠️  All providers failed — deterministic fallback.")
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
