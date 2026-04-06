import { motion } from 'framer-motion';
import { DIFFICULTY_CONFIG } from '../data/mockData';

/**
 * Highlights payloads, endpoints, and security keywords in report text.
 */
function highlightReport(text) {
  if (!text) return null;

  const lines = text.split('\n');

  return lines.map((line, i) => {
    let highlighted = line;

    // Highlight endpoints: /api/... or /path/...
    highlighted = highlighted.replace(
      /(\/(?:api|login|search|admin|settings|upload|graphql|users|comments|reset-password|change-password|profile|fetch-url|k8s-dashboard)[\w/{}.-]*)/gi,
      '<span class="hl-endpoint">$1</span>'
    );

    // Highlight payloads: SQL, XSS, URL-based
    highlighted = highlighted.replace(
      /('?\s*OR\s+1=1\s*--)/gi,
      '<span class="hl-payload">$1</span>'
    );
    highlighted = highlighted.replace(
      /(&lt;script&gt;.*?&lt;\/script&gt;|<script>.*?<\/script>)/gi,
      '<span class="hl-payload">$1</span>'
    );
    highlighted = highlighted.replace(
      /(http:\/\/169\.254\.169\.254[\w/.?=&-]*)/gi,
      '<span class="hl-payload">$1</span>'
    );
    highlighted = highlighted.replace(
      /(\<\?php.*?\?\>)/gi,
      '<span class="hl-payload">$1</span>'
    );
    highlighted = highlighted.replace(
      /(SELECT\s+\*\s+FROM\s+\w+[\s\w='[\]]*)/gi,
      '<span class="hl-payload">$1</span>'
    );
    highlighted = highlighted.replace(
      /(UNION\s+SELECT)/gi,
      '<span class="hl-payload">$1</span>'
    );
    highlighted = highlighted.replace(
      /(document\.cookie)/gi,
      '<span class="hl-payload">$1</span>'
    );

    // Highlight impact keywords
    highlighted = highlighted.replace(
      /\b(Impact|Critical|RCE|XSS|SQL Injection|SSRF|CSRF|IDOR|account takeover|data exfiltration|session hijack|compromise)\b/gi,
      '<span class="hl-impact">$1</span>'
    );

    // Section headers (Title:, Description:, Steps, Impact:)
    if (/^(Title|Description|Steps to Reproduce|Impact|Chain|Vulnerability):?/i.test(line)) {
      return (
        <div key={i} className="mt-3 first:mt-0">
          <span
            className="code-highlight"
            dangerouslySetInnerHTML={{ __html: highlighted }}
          />
        </div>
      );
    }

    // Numbered steps
    if (/^\d+\./.test(line.trim())) {
      return (
        <div key={i} className="pl-4" style={{ color: 'var(--text-secondary)' }}>
          <span className="code-highlight" dangerouslySetInnerHTML={{ __html: highlighted }} />
        </div>
      );
    }

    return (
      <div key={i}>
        <span className="code-highlight" dangerouslySetInnerHTML={{ __html: highlighted }} />
      </div>
    );
  });
}

export default function ReportCard({ report, taskId, difficulty }) {
  const diffConfig = DIFFICULTY_CONFIG[difficulty] || DIFFICULTY_CONFIG.easy;

  return (
    <motion.div
      initial={{ opacity: 0, x: -30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="glass-card h-full flex flex-col"
    >
      {/* Card Header */}
      <div
        className="px-6 py-4 flex items-center justify-between border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(34,211,238,0.1)', color: 'var(--cyan)' }}
          >
            📄
          </div>
          <div>
            <h2 className="text-sm font-semibold">Vulnerability Report</h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(34,211,238,0.1)', color: 'var(--cyan)' }}
              >
                {taskId}
              </span>
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                style={{ background: `${diffConfig.color}18`, color: diffConfig.color }}
              >
                {diffConfig.label}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full" style={{ background: '#ef4444' }} />
          <div className="w-3 h-3 rounded-full" style={{ background: '#f59e0b' }} />
          <div className="w-3 h-3 rounded-full" style={{ background: '#10b981' }} />
        </div>
      </div>

      {/* Report Content */}
      <div
        className="flex-1 overflow-y-auto p-6"
        style={{ maxHeight: '600px', lineHeight: 1.8 }}
      >
        {report ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.4 }}
          >
            {highlightReport(report)}
          </motion.div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full py-20" style={{ color: 'var(--text-muted)' }}>
            <div className="text-5xl mb-4 opacity-40">📋</div>
            <p className="text-sm font-medium">No report loaded</p>
            <p className="text-xs mt-1">Click "Run Triage" to analyze a vulnerability</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
