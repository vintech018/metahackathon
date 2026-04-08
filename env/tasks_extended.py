"""
Extended task registry — noisy, incomplete, and multi-vulnerability reports.

These tasks simulate real-world bug bounty submissions that are often:
    • Poorly written or ambiguous
    • Missing key details
    • Contain multiple vulnerabilities in one report
    • Use non-standard terminology
    • Include red herrings and irrelevant details
"""

from env.tasks import Task, ExpectedOutput, ALL_TASKS

# ─────────────────────────────────────────────────────────────────────────────
#  NOISY / INCOMPLETE REPORTS
# ─────────────────────────────────────────────────────────────────────────────

TASK_NOISY_SQLI: Task = {
    "id": "task_ext_1",
    "difficulty": "hard",
    "report": (
        "yo so i found this weird thing on ur site... basically when i put "
        "some special chars in the login box it logs me in as admin?? i think "
        "its the username field. i tried putting a single quote and some SQL "
        "stuff and the whole thing just broke and showed me the database. "
        "idk if this is serious but it seemed pretty bad. also the error "
        "messages showed the full query which is: SELECT * FROM users WHERE "
        "username = '[INPUT]' AND password = '[HASH]'. the app uses MySQL i think. "
        "oh and btw your forgot password page is also kinda broken but thats "
        "a diff issue. plz fix thx"
    ),
    "expected": {
        "severity": "critical",
        "component": "database",
        "remediation_keywords": [
            "parameterized",
            "prepared statements",
            "input validation",
            "sanitize",
            "error handling",
        ],
    },
}

TASK_NOISY_XSS_VAGUE: Task = {
    "id": "task_ext_2",
    "difficulty": "hard",
    "report": (
        "Subject: security bug found!!!\n\n"
        "Hi team, I noticed something concerning. When I enter HTML tags into "
        "the comment section, they actually render on the page. I tried typing "
        "<b>bold</b> and it showed up bold. Then I tried something more "
        "dangerous with script tags and... yeah. The alert box popped up. "
        "I'm not a security expert but this seems like it could be used to "
        "steal cookies or something? The page is the blog post comments. "
        "Affects all users who view comments. Didn't test on mobile."
    ),
    "expected": {
        "severity": "high",
        "component": "frontend",
        "remediation_keywords": [
            "sanitize",
            "escape",
            "content security policy",
            "output encoding",
        ],
    },
}

TASK_NOISY_INCOMPLETE_SSRF: Task = {
    "id": "task_ext_3",
    "difficulty": "hard",
    "report": (
        "vulnerability in URL fetcher\n"
        "endpoint: /api/fetch\n"
        "can access internal services\n"
        "tested with 127.0.0.1 and metadata endpoint\n"
        "got back IAM creds\n"
        "severity: think its bad\n"
        "no auth needed to hit this endpoint"
    ),
    "expected": {
        "severity": "critical",
        "component": "network",
        "remediation_keywords": [
            "url allowlist",
            "ssrf protection",
            "input validation",
            "network segmentation",
        ],
    },
}

TASK_NOISY_MISLEADING_SEVERITY: Task = {
    "id": "task_ext_4",
    "difficulty": "hard",
    "report": (
        "URGENT CRITICAL P0 EMERGENCY\n\n"
        "Found a bug where the application returns slightly different HTTP "
        "response times when checking if a username exists versus when it "
        "doesn't. GET /api/v1/check-user?username=admin returns in ~50ms but "
        "GET /api/v1/check-user?username=nonexistent123456 returns in ~45ms. "
        "This is a CRITICAL timing side-channel that allows username enumeration! "
        "AN ATTACKER CAN DETERMINE ALL VALID USERNAMES! PLEASE FIX IMMEDIATELY!\n\n"
        "Note: rate limiting is already in place (10 req/sec). The endpoint "
        "does not reveal any other information. 2FA is enabled for all accounts."
    ),
    "expected": {
        "severity": "low",
        "component": "auth",
        "remediation_keywords": [
            "constant time",
            "response normalization",
            "timing",
        ],
    },
}

TASK_NOISY_TYPOS_AND_SLANG: Task = {
    "id": "task_ext_5",
    "difficulty": "medium",
    "report": (
        "heyyy found a rly bad bug in ur API. basicaly the /api/v2/admin/users "
        "endpoint duznt check if ur actually an admin lol. i just sent a GET "
        "reqest with my normal user tokken and it gave me back ALL the user data "
        "incuding emails, hashed paswords, and phone numers. pretty sure this "
        "is an authorizaton bypass. u shud prolly add some middleware to check "
        "the users role b4 returning sensitive data. also the passwords r using "
        "MD5 wich is kinda weak ngl"
    ),
    "expected": {
        "severity": "high",
        "component": "api",
        "remediation_keywords": [
            "authorization check",
            "access control",
            "rbac",
            "middleware",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  MULTI-VULNERABILITY REPORTS
# ─────────────────────────────────────────────────────────────────────────────

TASK_MULTI_XSS_CSRF: Task = {
    "id": "task_ext_6",
    "difficulty": "hard",
    "report": (
        "Title: Reflected XSS + CSRF Combo in Settings Page\n\n"
        "Description: Found two related vulnerabilities:\n\n"
        "Vuln 1: The /settings page has a reflected XSS via the 'tab' parameter. "
        "Visiting /settings?tab=<script>alert(1)</script> executes JavaScript. "
        "The parameter is reflected in the page title without encoding.\n\n"
        "Vuln 2: The /api/v1/update-email endpoint accepts POST requests "
        "without a CSRF token. Combined with the XSS above, an attacker can "
        "craft a payload that automatically changes the victim's email to "
        "attacker@evil.com when they click a malicious link.\n\n"
        "Chain: XSS → inject form → auto-submit to change email → account takeover\n\n"
        "Impact: Full account takeover through chained XSS and CSRF."
    ),
    "expected": {
        "severity": "critical",
        "component": "frontend",
        "remediation_keywords": [
            "output encoding",
            "csrf token",
            "content security policy",
            "sanitize",
            "samesite cookie",
        ],
    },
}

TASK_MULTI_SQLI_PRIV_ESC: Task = {
    "id": "task_ext_7",
    "difficulty": "hard",
    "report": (
        "Title: SQL Injection to Privilege Escalation\n\n"
        "A second-order SQL injection exists in the admin reporting module.\n\n"
        "Step 1: Register with username: admin'-- \n"
        "Step 2: Login normally (the registration stores the malicious username)\n"
        "Step 3: Visit /admin/reports which builds a query using the stored "
        "username: SELECT * FROM reports WHERE author = '{stored_username}'\n"
        "Step 4: The injected SQL comment truncates the WHERE clause, returning "
        "all reports from all users\n\n"
        "Additionally, the /admin/reports endpoint doesn't verify the user's "
        "role, allowing any authenticated user to access admin reports through "
        "the SQL injection.\n\n"
        "Impact: Unauthorized access to all internal reports, possible data "
        "exfiltration of customer financial records."
    ),
    "expected": {
        "severity": "critical",
        "component": "database",
        "remediation_keywords": [
            "parameterized",
            "input validation",
            "authorization check",
            "rbac",
            "sanitize",
        ],
    },
}

TASK_MULTI_AUTH_BYPASS_DATA_LEAK: Task = {
    "id": "task_ext_8",
    "difficulty": "hard",
    "report": (
        "Title: JWT None Algorithm + Unprotected GraphQL Introspection\n\n"
        "Vulnerability 1 — JWT None Algorithm Attack:\n"
        "The API accepts JWTs with alg: 'none'. By modifying the JWT header to "
        "use the 'none' algorithm and removing the signature, any user can forge "
        "tokens with arbitrary claims including admin roles. The library used "
        "is an outdated version of pyjwt that doesn't reject 'none' by default.\n\n"
        "Vulnerability 2 — GraphQL Introspection Enabled:\n"
        "The GraphQL endpoint at /graphql has introspection enabled in "
        "production. This exposes the entire schema including internal mutation "
        "types like deleteAllUsers, resetDatabase, and exportAllData.\n\n"
        "Combined Impact: An attacker can forge an admin JWT and then use the "
        "exposed GraphQL mutations to delete users, export all data, or reset "
        "the database.\n\n"
        "Severity: CRITICAL — full system compromise possible."
    ),
    "expected": {
        "severity": "critical",
        "component": "auth",
        "remediation_keywords": [
            "jwt validation",
            "algorithm whitelist",
            "disable introspection",
            "token validation",
            "access control",
        ],
    },
}

TASK_MULTI_RATE_LIMIT_BRUTE: Task = {
    "id": "task_ext_9",
    "difficulty": "medium",
    "report": (
        "Title: Missing Rate Limiting on Login + Weak Password Policy\n\n"
        "The /api/auth/login endpoint has no rate limiting. I was able to send "
        "over 10,000 login attempts per minute without being blocked. Combined "
        "with the fact that the application allows passwords as short as 4 "
        "characters with no complexity requirements, brute-force attacks are "
        "trivially easy.\n\n"
        "I wrote a script that successfully cracked several test accounts "
        "(with permission) in under 30 minutes using a common password list.\n\n"
        "Additionally, failed login attempts are not logged or monitored, so "
        "there would be no alert even during an active attack.\n\n"
        "Impact: Account compromise through brute force, undetected credential "
        "stuffing attacks."
    ),
    "expected": {
        "severity": "high",
        "component": "auth",
        "remediation_keywords": [
            "rate limiting",
            "account lockout",
            "password policy",
            "monitoring",
            "logging",
        ],
    },
}

TASK_NOISY_REDIRECT: Task = {
    "id": "task_ext_10",
    "difficulty": "medium",
    "report": (
        "found open redirect on /login?next=http://evil.com\n"
        "after login it redirects to attacker site\n"
        "can be used for phishing\n"
        "no validation on the next parameter\n"
        "users trust the domain and enter creds on fake page\n"
        "works on all browsers tested chrome firefox safari\n"
        "the redirect happens server-side with a 302"
    ),
    "expected": {
        "severity": "medium",
        "component": "auth",
        "remediation_keywords": [
            "url validation",
            "redirect whitelist",
            "relative url",
            "domain check",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  EXTENDED REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

EXTENDED_TASKS: list[Task] = [
    TASK_NOISY_SQLI,
    TASK_NOISY_XSS_VAGUE,
    TASK_NOISY_INCOMPLETE_SSRF,
    TASK_NOISY_MISLEADING_SEVERITY,
    TASK_NOISY_TYPOS_AND_SLANG,
    TASK_MULTI_XSS_CSRF,
    TASK_MULTI_SQLI_PRIV_ESC,
    TASK_MULTI_AUTH_BYPASS_DATA_LEAK,
    TASK_MULTI_RATE_LIMIT_BRUTE,
    TASK_NOISY_REDIRECT,
]

# Combined: original + extended
ALL_TASKS_EXTENDED: list[Task] = ALL_TASKS + EXTENDED_TASKS

EXTENDED_TASKS_BY_ID: dict[str, Task] = {t["id"]: t for t in ALL_TASKS_EXTENDED}
EXTENDED_TASKS_BY_DIFFICULTY: dict[str, list[Task]] = {
    "easy": [t for t in ALL_TASKS_EXTENDED if t["difficulty"] == "easy"],
    "medium": [t for t in ALL_TASKS_EXTENDED if t["difficulty"] == "medium"],
    "hard": [t for t in ALL_TASKS_EXTENDED if t["difficulty"] == "hard"],
}
