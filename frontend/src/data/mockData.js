/**
 * Mock vulnerability reports and simulation data.
 * In production, these come from the TriageEnv backend.
 */

export const MOCK_REPORTS = [
  {
    id: 'task_1',
    difficulty: 'easy',
    report:
      "Title: SQL Injection in Login Form\nDescription: The /api/v1/login endpoint is vulnerable to SQL injection. Submitting the payload ' OR 1=1 -- in the 'username' field bypasses authentication entirely and returns the first user record from the database. The application concatenates user input directly into the SQL query string without any parameterization or input sanitization.\nSteps to Reproduce:\n1. Navigate to /login\n2. Enter ' OR 1=1 -- as the username\n3. Enter any value as the password\n4. Observe successful authentication as admin\nImpact: Full authentication bypass and potential data exfiltration.",
    action: {
      severity: 'critical',
      component: 'database',
      remediation:
        'Implement parameterized queries (prepared statements) for all database interactions. Validate and sanitize all user input on the server side. Apply the principle of least privilege to database accounts. Deploy a Web Application Firewall (WAF) with SQL injection detection rules. Enable session management with secure token rotation after authentication.',
    },
    reward: 0.94,
    info: {
      task_id: 'task_1',
      difficulty: 'easy',
      expected_severity: 'critical',
      expected_component: 'database',
      expected_remediation_keywords: ['parameterized', 'prepared statements', 'input validation', 'sanitize'],
      agent_severity: 'critical',
      agent_component: 'database',
      explanation: {
        severity_score: 0.4,
        component_score: 0.3,
        remediation_score: 0.24,
        bonus_score: 0.2,
      },
      confidence: 0.94,
    },
  },
  {
    id: 'task_7',
    difficulty: 'hard',
    report:
      "Title: Stored XSS Leading to Session Hijack Chain\nDescription: The application's comment system on /api/v1/comments does not sanitize HTML input. An attacker can inject a persistent XSS payload that steals session cookies of every user who views the comment. Because the HttpOnly flag is not set on session cookies, the JavaScript payload can read document.cookie and exfiltrate it to an attacker-controlled server. This gives the attacker valid session tokens for any affected user, enabling full session hijack.\nThe attack chain is:\n1. Inject stored XSS via comment → 2. Steal session cookie via document.cookie → 3. Replay cookie to impersonate victim.\nImpact: Mass session hijacking, account takeover at scale.",
    action: {
      severity: 'critical',
      component: 'frontend',
      remediation:
        'Implement comprehensive input sanitization for all user-submitted content using a whitelist approach. Set the HttpOnly, Secure, and SameSite flags on all session cookies to prevent client-side access. Deploy a strict Content Security Policy (CSP) header to block inline script execution. Apply output encoding when rendering user content in HTML contexts. Implement session rotation on privilege changes. Address the multiple chained vulnerabilities in a combined remediation strategy: sanitize input, secure cookies, enforce CSP, and implement proper session management.',
    },
    reward: 0.88,
    info: {
      task_id: 'task_7',
      difficulty: 'hard',
      expected_severity: 'critical',
      expected_component: 'frontend',
      expected_remediation_keywords: ['input sanitization', 'httponly', 'output encoding', 'content security policy', 'session rotation'],
      agent_severity: 'critical',
      agent_component: 'frontend',
      explanation: {
        severity_score: 0.4,
        component_score: 0.3,
        remediation_score: 0.18,
        bonus_score: 0.3,
      },
      confidence: 0.88,
    },
  },
  {
    id: 'task_8',
    difficulty: 'hard',
    report:
      "Title: SSRF Leading to Internal Data Exposure\nDescription: The /api/v1/fetch-url endpoint accepts a user-supplied URL and makes a server-side HTTP request to retrieve its contents. There are no restrictions on the target URL scheme or host. An attacker can supply http://169.254.169.254/latest/meta-data/ to access the AWS instance metadata service, including IAM credentials. The retrieved credentials can then be used to access S3 buckets, RDS databases, and other internal resources.\nThe attack chain is:\n1. Submit SSRF payload targeting metadata endpoint → 2. Retrieve IAM role credentials → 3. Use credentials to access internal AWS resources.\nImpact: Cloud infrastructure compromise, data exfiltration from internal services.",
    action: {
      severity: 'critical',
      component: 'network',
      remediation:
        'Implement a strict URL allowlist to restrict outbound requests to approved domains only. Enforce SSRF protection by blocking requests to private IP ranges (10.x, 172.16-31.x, 192.168.x, 169.254.x) and cloud metadata endpoints. Migrate to IMDSv2 which requires session tokens. Apply network segmentation to isolate the application from internal services. Validate and sanitize all URL inputs. Address the combined chain of vulnerabilities with multiple layers of defense.',
    },
    reward: 0.92,
    info: {
      task_id: 'task_8',
      difficulty: 'hard',
      expected_severity: 'critical',
      expected_component: 'network',
      expected_remediation_keywords: ['url allowlist', 'ssrf protection', 'network segmentation', 'metadata endpoint', 'imds v2', 'input validation'],
      agent_severity: 'critical',
      agent_component: 'network',
      explanation: {
        severity_score: 0.4,
        component_score: 0.3,
        remediation_score: 0.22,
        bonus_score: 0.3,
      },
      confidence: 0.92,
    },
  },
  {
    id: 'task_4',
    difficulty: 'medium',
    report:
      "Title: Auth Token Reuse After Password Change\nDescription: After a user changes their password, previously issued JWT tokens remain valid. The application does not invalidate old tokens upon credential rotation. This means a stolen token continues to grant access even after the legitimate user has rotated their credentials.\nSteps to Reproduce:\n1. Authenticate and copy the JWT from the Authorization header\n2. Change the account password via /api/v1/change-password\n3. Use the old JWT to access /api/v1/profile\n4. Observe that the old token still works\nImpact: Persistent unauthorized access after credential rotation.",
    action: {
      severity: 'high',
      component: 'auth',
      remediation:
        'Implement token invalidation upon password change by maintaining a server-side revocation list or blacklist. Use short-lived access tokens with refresh token rotation. Implement proper session management with token binding to the current credential hash. Deploy rate limiting on authentication endpoints.',
    },
    reward: 0.78,
    info: {
      task_id: 'task_4',
      difficulty: 'medium',
      expected_severity: 'high',
      expected_component: 'auth',
      expected_remediation_keywords: ['token invalidation', 'revocation', 'blacklist', 'refresh token', 'session management'],
      agent_severity: 'high',
      agent_component: 'auth',
      explanation: {
        severity_score: 0.4,
        component_score: 0.3,
        remediation_score: 0.18,
        bonus_score: 0.0,
      },
      confidence: 0.78,
    },
  },
  {
    id: 'task_10',
    difficulty: 'easy',
    report:
      "Title: Information Disclosure via Verbose Error Messages\nDescription: The /api/v1/users endpoint returns detailed stack traces and internal debugging information when an unhandled exception occurs. By sending a malformed JSON payload, the server responds with a 500 error that includes the full Python traceback, framework version, database connection string, and internal file paths. Debug mode appears to be enabled in the production environment.\nSteps to Reproduce:\n1. Send a POST request to /api/v1/users with an invalid JSON body\n2. Observe the 500 response containing a full stack trace\n3. Note the exposed database connection string and internal paths\nImpact: Leaks internal architecture details, software versions, and database credentials that aid further attacks.",
    action: {
      severity: 'low',
      component: 'api',
      remediation:
        'Disable debug mode in the production environment. Implement custom error handlers that return generic error messages to clients while logging detailed errors server-side. Sanitize and validate all incoming request payloads. Remove database connection strings and internal paths from error responses.',
    },
    reward: 0.62,
    info: {
      task_id: 'task_10',
      difficulty: 'easy',
      expected_severity: 'low',
      expected_component: 'api',
      expected_remediation_keywords: ['error handling', 'disable debug', 'hide stack trace'],
      agent_severity: 'low',
      agent_component: 'api',
      explanation: {
        severity_score: 0.4,
        component_score: 0.3,
        remediation_score: 0.12,
        bonus_score: 0.0,
      },
      confidence: 0.62,
    },
  },
  {
    id: 'task_6',
    difficulty: 'medium',
    report:
      "Title: CSRF on Account Settings Update\nDescription: The /api/v1/settings endpoint accepts state-changing POST requests without validating a CSRF token. An attacker can host a malicious page that automatically submits a form to this endpoint when visited by an authenticated user, changing their email address or password without consent.\nSteps to Reproduce:\n1. Create an HTML page with an auto-submitting form targeting /api/v1/settings\n2. Host the page and send the link to a victim\n3. When the victim visits the page, their settings are changed\nImpact: Account takeover via email/password change.",
    action: {
      severity: 'medium',
      component: 'frontend',
      remediation:
        'Implement anti-CSRF tokens on all state-changing endpoints. Set SameSite=Strict or SameSite=Lax attribute on session cookies. Validate the Origin and Referer headers for sensitive operations. Consider implementing double-submit cookie pattern as a secondary defense.',
    },
    reward: 0.71,
    info: {
      task_id: 'task_6',
      difficulty: 'medium',
      expected_severity: 'medium',
      expected_component: 'frontend',
      expected_remediation_keywords: ['csrf token', 'samesite cookie', 'anti-csrf', 'origin validation', 'referer check'],
      agent_severity: 'medium',
      agent_component: 'frontend',
      explanation: {
        severity_score: 0.4,
        component_score: 0.3,
        remediation_score: 0.11,
        bonus_score: 0.0,
      },
      confidence: 0.71,
    },
  },
];

/**
 * Call the real backend API to triage a report via Groq LLM.
 * Falls back to mock data if the backend is unavailable.
 */
export async function simulateTriage(index = null) {
  // Try real backend first
  try {
    const res = await fetch('/api/triage/random', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      const data = await res.json();
      return data;
    }
  } catch (e) {
    console.warn('Backend unavailable, using mock data:', e.message);
  }

  // Fallback to mock
  return new Promise((resolve) => {
    const delay = 800 + Math.random() * 1200;
    setTimeout(() => {
      const i = index !== null ? index : Math.floor(Math.random() * MOCK_REPORTS.length);
      resolve(MOCK_REPORTS[i % MOCK_REPORTS.length]);
    }, delay);
  });
}

/**
 * Triage a custom user-provided report via the backend.
 */
export async function triageCustomReport(report) {
  const res = await fetch('/api/triage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report }),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export const SEVERITY_CONFIG = {
  critical: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)', label: 'CRITICAL', icon: '🔴' },
  high:     { color: '#f97316', bg: 'rgba(249,115,22,0.12)', border: 'rgba(249,115,22,0.3)', label: 'HIGH', icon: '🟠' },
  medium:   { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)', label: 'MEDIUM', icon: '🟡' },
  low:      { color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.3)', label: 'LOW', icon: '🟢' },
};

export const COMPONENT_CONFIG = {
  auth:     { color: '#a855f7', bg: 'rgba(168,85,247,0.12)', icon: '🔐' },
  database: { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', icon: '🗄️' },
  api:      { color: '#22d3ee', bg: 'rgba(34,211,238,0.12)', icon: '⚡' },
  frontend: { color: '#ec4899', bg: 'rgba(236,72,153,0.12)', icon: '🖥️' },
  network:  { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', icon: '🌐' },
};

export const DIFFICULTY_CONFIG = {
  easy:   { color: '#10b981', label: 'Easy' },
  medium: { color: '#f59e0b', label: 'Medium' },
  hard:   { color: '#ef4444', label: 'Hard' },
};
