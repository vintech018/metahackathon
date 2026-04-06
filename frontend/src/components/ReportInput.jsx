import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const PLACEHOLDER = `Paste vulnerability report here...

Example:
Title: SQL Injection in Login Form
Description: The /api/v1/login endpoint is vulnerable to SQL injection. Submitting ' OR 1=1 -- in the username field bypasses authentication and returns the first user record from the database.
Steps to Reproduce:
1. Navigate to /login
2. Enter ' OR 1=1 -- as the username
3. Observe successful authentication as admin
Impact: Full authentication bypass and data exfiltration.`;

const SAMPLE_REPORTS = [
  {
    label: 'SQL Injection',
    icon: '🗄️',
    text: "Title: SQL Injection in User Search\nDescription: The /api/v2/search endpoint concatenates user input directly into SQL queries. Sending ' UNION SELECT * FROM credentials -- in the search field returns all stored credentials including hashed passwords and API keys. No authentication is required to access the search endpoint.\nImpact: Full credential dump, mass data exfiltration without authentication.",
  },
  {
    label: 'XSS + Cookie Theft',
    icon: '🖥️',
    text: "Title: Stored XSS with Session Hijack\nDescription: The comment system on /api/v1/comments does not sanitize HTML input. An attacker can inject a persistent XSS payload that steals session cookies via document.cookie. The HttpOnly flag is not set on session cookies, allowing full session hijack.\nThe attack chain is:\n1. Inject stored XSS via comment → 2. Steal session cookie → 3. Replay cookie to impersonate victim.\nImpact: Mass session hijacking and account takeover at scale.",
  },
  {
    label: 'SSRF Attack',
    icon: '🌐',
    text: "Title: SSRF to Cloud Metadata\nDescription: The /api/v1/fetch-url endpoint accepts user-supplied URLs and makes server-side requests with no restrictions. An attacker can supply http://169.254.169.254/latest/meta-data/ to access AWS instance metadata including IAM credentials, then use those credentials to access S3 buckets and RDS databases.\nImpact: Cloud infrastructure compromise, internal data exfiltration.",
  },
  {
    label: 'Auth Bypass',
    icon: '🔐',
    text: "Title: JWT Token Reuse After Password Change\nDescription: After changing password via /api/v1/change-password, old JWT tokens remain valid indefinitely. The application does not invalidate tokens upon credential rotation. A stolen token continues to grant access even after the user rotates credentials.\nImpact: Persistent unauthorized access after credential compromise.",
  },
];

export default function ReportInput({ onSubmit, isLoading }) {
  const [report, setReport] = useState('');
  const [error, setError] = useState('');
  const [charCount, setCharCount] = useState(0);
  const textareaRef = useRef(null);

  useEffect(() => {
    setCharCount(report.length);
  }, [report]);

  const handleSubmit = () => {
    const trimmed = report.trim();
    if (!trimmed) {
      setError('Please enter a vulnerability report before submitting.');
      return;
    }
    if (trimmed.length < 20) {
      setError('Report is too short. Please provide a detailed vulnerability description.');
      return;
    }
    setError('');
    onSubmit(trimmed);
  };

  const handleSampleClick = (text) => {
    setReport(text);
    setError('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleClear = () => {
    setReport('');
    setError('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="glass-card overflow-hidden"
    >
      {/* Header */}
      <div
        className="px-6 py-4 flex items-center justify-between border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(168,85,247,0.1)', color: 'var(--purple)' }}
          >
            ✏️
          </div>
          <div>
            <h2 className="text-sm font-semibold">Custom Report</h2>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              Paste or type a vulnerability report for AI analysis
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-[10px] font-mono px-2 py-0.5 rounded-full"
            style={{
              background: charCount > 0 ? 'rgba(34,211,238,0.1)' : 'rgba(148,163,184,0.08)',
              color: charCount > 0 ? 'var(--cyan)' : 'var(--text-muted)',
            }}
          >
            {charCount} chars
          </span>
          {report.length > 0 && (
            <motion.button
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              onClick={handleClear}
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full cursor-pointer border-none"
              style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}
            >
              ✕ Clear
            </motion.button>
          )}
        </div>
      </div>

      {/* Textarea */}
      <div className="p-5">
        <textarea
          ref={textareaRef}
          id="report-input"
          value={report}
          onChange={(e) => {
            setReport(e.target.value);
            if (error) setError('');
          }}
          placeholder={PLACEHOLDER}
          disabled={isLoading}
          rows={8}
          className="w-full rounded-xl p-4 text-sm leading-relaxed resize-none outline-none transition-all duration-300"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '12.5px',
            background: 'rgba(6,10,19,0.6)',
            border: error
              ? '1px solid rgba(239,68,68,0.5)'
              : '1px solid var(--border)',
            color: 'var(--text-primary)',
            opacity: isLoading ? 0.5 : 1,
          }}
          onFocus={(e) => {
            e.target.style.borderColor = 'rgba(34,211,238,0.4)';
            e.target.style.boxShadow = '0 0 20px rgba(34,211,238,0.08)';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = error ? 'rgba(239,68,68,0.5)' : 'var(--border)';
            e.target.style.boxShadow = 'none';
          }}
        />

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -5, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -5, height: 0 }}
              className="mt-2 flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
              style={{ background: 'rgba(239,68,68,0.08)', color: '#ef4444' }}
            >
              <span>⚠️</span> {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Sample Reports */}
        <div className="mt-4">
          <div
            className="text-[10px] font-bold uppercase tracking-wider mb-2.5"
            style={{ color: 'var(--text-muted)' }}
          >
            Quick Templates
          </div>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_REPORTS.map((sample, i) => (
              <motion.button
                key={i}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => handleSampleClick(sample.text)}
                disabled={isLoading}
                className="flex items-center gap-1.5 text-[11px] font-medium px-3 py-1.5 rounded-lg cursor-pointer border-none transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: 'rgba(148,163,184,0.06)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border)',
                }}
              >
                <span>{sample.icon}</span> {sample.label}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <motion.button
          id="submit-custom-triage"
          onClick={handleSubmit}
          disabled={isLoading || !report.trim()}
          whileHover={{ scale: isLoading ? 1 : 1.01 }}
          whileTap={{ scale: isLoading ? 1 : 0.99 }}
          className="w-full mt-4 py-3 rounded-xl font-semibold text-sm text-white cursor-pointer overflow-hidden disabled:opacity-40 disabled:cursor-not-allowed border-none"
          style={{
            background:
              isLoading || !report.trim()
                ? 'rgba(168,85,247,0.15)'
                : 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)',
            boxShadow:
              isLoading || !report.trim()
                ? 'none'
                : '0 4px 20px rgba(168,85,247,0.3)',
          }}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              AI analyzing vulnerability...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              🛡️ Analyze Custom Report
            </span>
          )}
        </motion.button>
      </div>
    </motion.div>
  );
}
