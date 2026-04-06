"""
Task registry for the Bug Bounty Triage environment.

Each task is a fully self-contained vulnerability report with ground-truth
labels used by the grader.  Tasks are grouped by difficulty tier.
"""

from typing import TypedDict


class ExpectedOutput(TypedDict):
    severity: str
    component: str
    remediation_keywords: list[str]


class Task(TypedDict):
    id: str
    difficulty: str  # "easy" | "medium" | "hard"
    report: str
    expected: ExpectedOutput


# ─────────────────────────────────────────────────────────────────────────────
#  EASY TASKS  (3)
# ─────────────────────────────────────────────────────────────────────────────

TASK_EASY_SQL_INJECTION: Task = {
    "id": "task_1",
    "difficulty": "easy",
    "report": (
        "Title: SQL Injection in Login Form\n"
        "Description: The /api/v1/login endpoint is vulnerable to SQL injection. "
        "Submitting the payload ' OR 1=1 -- in the 'username' field bypasses "
        "authentication entirely and returns the first user record from the "
        "database.  The application concatenates user input directly into the "
        "SQL query string without any parameterization or input sanitization.\n"
        "Steps to Reproduce:\n"
        "1. Navigate to /login\n"
        "2. Enter ' OR 1=1 -- as the username\n"
        "3. Enter any value as the password\n"
        "4. Observe successful authentication as admin\n"
        "Impact: Full authentication bypass and potential data exfiltration."
    ),
    "expected": {
        "severity": "critical",
        "component": "database",
        "remediation_keywords": [
            "parameterized",
            "prepared statements",
            "input validation",
            "sanitize",
        ],
    },
}

TASK_EASY_XSS: Task = {
    "id": "task_2",
    "difficulty": "easy",
    "report": (
        "Title: Reflected XSS in Search Page\n"
        "Description: The /search endpoint reflects the 'q' query parameter "
        "directly into the HTML response without encoding.  An attacker can "
        "craft a URL such as /search?q=<script>alert(document.cookie)</script> "
        "and share it with a victim.  When the victim clicks the link, the "
        "injected script executes in their browser context.\n"
        "Steps to Reproduce:\n"
        "1. Open /search?q=<script>alert('XSS')</script>\n"
        "2. Observe the JavaScript alert dialog\n"
        "Impact: Cookie theft, session hijacking, phishing."
    ),
    "expected": {
        "severity": "high",
        "component": "frontend",
        "remediation_keywords": [
            "output encoding",
            "escape",
            "content security policy",
            "csp",
            "sanitize",
        ],
    },
}

TASK_EASY_RCE: Task = {
    "id": "task_3",
    "difficulty": "easy",
    "report": (
        "Title: Remote Code Execution via File Upload\n"
        "Description: The /api/v1/upload endpoint allows uploading arbitrary "
        "files including .php and .py scripts.  Uploaded files are stored in a "
        "web-accessible directory and can be executed by navigating to their "
        "URL.  An attacker can upload a reverse shell and gain full control of "
        "the server.\n"
        "Steps to Reproduce:\n"
        "1. Upload a file named shell.php with contents <?php system($_GET['cmd']); ?>\n"
        "2. Navigate to /uploads/shell.php?cmd=id\n"
        "3. Observe server-side command execution\n"
        "Impact: Full server compromise, data breach, lateral movement."
    ),
    "expected": {
        "severity": "critical",
        "component": "api",
        "remediation_keywords": [
            "file type validation",
            "whitelist",
            "sandbox",
            "upload directory",
            "non-executable",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  MEDIUM TASKS  (3)
# ─────────────────────────────────────────────────────────────────────────────

TASK_MEDIUM_TOKEN_REUSE: Task = {
    "id": "task_4",
    "difficulty": "medium",
    "report": (
        "Title: Auth Token Reuse After Password Change\n"
        "Description: After a user changes their password, previously issued "
        "JWT tokens remain valid.  The application does not invalidate old "
        "tokens upon credential rotation.  This means a stolen token continues "
        "to grant access even after the legitimate user has rotated their "
        "credentials.\n"
        "Steps to Reproduce:\n"
        "1. Authenticate and copy the JWT from the Authorization header\n"
        "2. Change the account password via /api/v1/change-password\n"
        "3. Use the old JWT to access /api/v1/profile\n"
        "4. Observe that the old token still works\n"
        "Impact: Persistent unauthorized access after credential rotation."
    ),
    "expected": {
        "severity": "high",
        "component": "auth",
        "remediation_keywords": [
            "token invalidation",
            "revocation",
            "blacklist",
            "refresh token",
            "session management",
        ],
    },
}

TASK_MEDIUM_IDOR: Task = {
    "id": "task_5",
    "difficulty": "medium",
    "report": (
        "Title: IDOR on User Profile Endpoint\n"
        "Description: The /api/v1/users/{id}/profile endpoint does not verify "
        "that the authenticated user matches the requested {id}.  Any "
        "authenticated user can read or modify another user's profile by "
        "changing the {id} parameter.  No authorization check is performed "
        "server-side.\n"
        "Steps to Reproduce:\n"
        "1. Authenticate as user A (id=42)\n"
        "2. Send GET /api/v1/users/1/profile with user A's token\n"
        "3. Observe that user 1's (admin) profile data is returned\n"
        "Impact: Unauthorized access to sensitive user data, potential "
        "account takeover."
    ),
    "expected": {
        "severity": "high",
        "component": "api",
        "remediation_keywords": [
            "authorization check",
            "access control",
            "ownership verification",
            "rbac",
            "middleware",
        ],
    },
}

TASK_MEDIUM_CSRF: Task = {
    "id": "task_6",
    "difficulty": "medium",
    "report": (
        "Title: CSRF on Account Settings Update\n"
        "Description: The /api/v1/settings endpoint accepts state-changing "
        "POST requests without validating a CSRF token.  An attacker can host "
        "a malicious page that automatically submits a form to this endpoint "
        "when visited by an authenticated user, changing their email address "
        "or password without consent.\n"
        "Steps to Reproduce:\n"
        "1. Create an HTML page with an auto-submitting form targeting "
        "/api/v1/settings\n"
        "2. Host the page and send the link to a victim\n"
        "3. When the victim visits the page, their settings are changed\n"
        "Impact: Account takeover via email/password change."
    ),
    "expected": {
        "severity": "medium",
        "component": "frontend",
        "remediation_keywords": [
            "csrf token",
            "samesite cookie",
            "anti-csrf",
            "origin validation",
            "referer check",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  HARD TASKS  (3)
# ─────────────────────────────────────────────────────────────────────────────

TASK_HARD_STORED_XSS_CHAIN: Task = {
    "id": "task_7",
    "difficulty": "hard",
    "report": (
        "Title: Stored XSS Leading to Session Hijack Chain\n"
        "Description: The application's comment system on /api/v1/comments "
        "does not sanitize HTML input.  An attacker can inject a persistent "
        "XSS payload that steals session cookies of every user who views the "
        "comment.  Because the HttpOnly flag is not set on session cookies, "
        "the JavaScript payload can read document.cookie and exfiltrate it "
        "to an attacker-controlled server.  This gives the attacker valid "
        "session tokens for any affected user, enabling full session hijack.\n"
        "The attack chain is:\n"
        "1. Inject stored XSS via comment → 2. Steal session cookie via "
        "document.cookie → 3. Replay cookie to impersonate victim.\n"
        "Impact: Mass session hijacking, account takeover at scale."
    ),
    "expected": {
        "severity": "critical",
        "component": "frontend",
        "remediation_keywords": [
            "input sanitization",
            "httponly",
            "output encoding",
            "content security policy",
            "session rotation",
        ],
    },
}

TASK_HARD_SSRF_CHAIN: Task = {
    "id": "task_8",
    "difficulty": "hard",
    "report": (
        "Title: SSRF Leading to Internal Data Exposure\n"
        "Description: The /api/v1/fetch-url endpoint accepts a user-supplied "
        "URL and makes a server-side HTTP request to retrieve its contents.  "
        "There are no restrictions on the target URL scheme or host.  An "
        "attacker can supply http://169.254.169.254/latest/meta-data/ to "
        "access the AWS instance metadata service, including IAM credentials.  "
        "The retrieved credentials can then be used to access S3 buckets, "
        "RDS databases, and other internal resources.\n"
        "The attack chain is:\n"
        "1. Submit SSRF payload targeting metadata endpoint → 2. Retrieve IAM "
        "role credentials → 3. Use credentials to access internal AWS "
        "resources.\n"
        "Impact: Cloud infrastructure compromise, data exfiltration from "
        "internal services."
    ),
    "expected": {
        "severity": "critical",
        "component": "network",
        "remediation_keywords": [
            "url allowlist",
            "ssrf protection",
            "network segmentation",
            "metadata endpoint",
            "imds v2",
            "input validation",
        ],
    },
}

TASK_HARD_BROKEN_AUTH_CHAIN: Task = {
    "id": "task_9",
    "difficulty": "hard",
    "report": (
        "Title: Broken Authentication Combined with Privilege Escalation\n"
        "Description: The application's password reset flow at "
        "/api/v1/reset-password uses a predictable 4-digit numeric token that "
        "does not expire.  An attacker can brute-force the reset token within "
        "minutes.  Once authenticated via the reset password, the application "
        "stores the user's role in a client-side cookie called 'role'.  By "
        "modifying this cookie from 'user' to 'admin', the attacker gains "
        "administrative access to all management endpoints including user "
        "deletion, financial record access, and system configuration.\n"
        "The attack chain is:\n"
        "1. Brute-force predictable reset token → 2. Gain authenticated "
        "session → 3. Modify role cookie to escalate privileges.\n"
        "Impact: Full administrative access, data manipulation, service "
        "disruption."
    ),
    "expected": {
        "severity": "critical",
        "component": "auth",
        "remediation_keywords": [
            "strong token",
            "token expiry",
            "rate limiting",
            "server-side role",
            "rbac",
            "session management",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  EDGE CASE — LOW SEVERITY  (1)
# ─────────────────────────────────────────────────────────────────────────────

TASK_EASY_INFO_DISCLOSURE: Task = {
    "id": "task_10",
    "difficulty": "easy",
    "report": (
        "Title: Information Disclosure via Verbose Error Messages\n"
        "Description: The /api/v1/users endpoint returns detailed stack traces "
        "and internal debugging information when an unhandled exception occurs.  "
        "By sending a malformed JSON payload, the server responds with a 500 "
        "error that includes the full Python traceback, framework version, "
        "database connection string, and internal file paths.  Debug mode "
        "appears to be enabled in the production environment.\n"
        "Steps to Reproduce:\n"
        "1. Send a POST request to /api/v1/users with an invalid JSON body\n"
        "2. Observe the 500 response containing a full stack trace\n"
        "3. Note the exposed database connection string and internal paths\n"
        "Impact: Leaks internal architecture details, software versions, and "
        "database credentials that aid further attacks."
    ),
    "expected": {
        "severity": "low",
        "component": "api",
        "remediation_keywords": [
            "error handling",
            "disable debug",
            "hide stack trace",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  TASK REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

ALL_TASKS: list[Task] = [
    # Easy
    TASK_EASY_SQL_INJECTION,
    TASK_EASY_XSS,
    TASK_EASY_RCE,
    # Easy — low severity edge case
    TASK_EASY_INFO_DISCLOSURE,
    # Medium
    TASK_MEDIUM_TOKEN_REUSE,
    TASK_MEDIUM_IDOR,
    TASK_MEDIUM_CSRF,
    # Hard
    TASK_HARD_STORED_XSS_CHAIN,
    TASK_HARD_SSRF_CHAIN,
    TASK_HARD_BROKEN_AUTH_CHAIN,
]

TASKS_BY_ID: dict[str, Task] = {task["id"]: task for task in ALL_TASKS}
TASKS_BY_DIFFICULTY: dict[str, list[Task]] = {
    "easy": [t for t in ALL_TASKS if t["difficulty"] == "easy"],
    "medium": [t for t in ALL_TASKS if t["difficulty"] == "medium"],
    "hard": [t for t in ALL_TASKS if t["difficulty"] == "hard"],
}
