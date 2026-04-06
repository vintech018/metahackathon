import { motion } from 'framer-motion';
import {
  Shield, Server, Wrench, Activity,
  Lock, Database, Monitor, Wifi,
  Copy, Check,
} from 'lucide-react';
import { useState } from 'react';
import SeverityBadge from './SeverityBadge';

const COMPONENT_META = {
  auth: { icon: Lock, color: '#f97316', label: 'Authentication' },
  database: { icon: Database, color: '#3b82f6', label: 'Database' },
  api: { icon: Server, color: '#8b5cf6', label: 'API' },
  frontend: { icon: Monitor, color: '#eab308', label: 'Frontend' },
  network: { icon: Wifi, color: '#22c55e', label: 'Network' },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.4, 0, 0.2, 1] },
  }),
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  return (
    <button
      onClick={handleCopy}
      className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]
                 transition-colors p-1.5 rounded-lg hover:bg-[rgba(255,255,255,0.06)] cursor-pointer"
      title="Copy to clipboard"
    >
      {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
    </button>
  );
}

function formatRemediation(text) {
  if (!text) return null;
  // Split on sentence boundaries or numbered items
  const items = text
    .split(/(?:\d+\.\s+|;\s+|(?<=\.)\s+(?=[A-Z]))/)
    .map((s) => s.trim())
    .filter(Boolean);

  if (items.length <= 1) {
    return <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{text}</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((item, idx) => (
        <li key={idx} className="flex gap-2.5 text-sm leading-relaxed text-[var(--text-secondary)]">
          <span className="text-[var(--accent-violet)] mt-0.5 shrink-0">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ResultDashboard({ result }) {
  if (!result) return null;

  const { action, reward, info } = result;
  const severity = action?.severity || 'low';
  const component = action?.component || 'api';
  const remediation = action?.remediation || '';
  const confidence = info?.confidence ?? Math.round(reward * 100);
  const compMeta = COMPONENT_META[component] || COMPONENT_META.api;
  const CompIcon = compMeta.icon;

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      className="space-y-4"
    >
      {/* ── Severity Hero ──────────────────────────────────────────────── */}
      <motion.div custom={0} variants={cardVariants} className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
            <Shield size={13} />
            Severity Assessment
          </div>
          <CopyButton text={`Severity: ${severity}`} />
        </div>
        <SeverityBadge severity={severity} large />
      </motion.div>

      {/* ── Component + Confidence Row ─────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Component */}
        <motion.div custom={1} variants={cardVariants} className="glass-card p-5">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-4">
            <Server size={13} />
            Affected Component
          </div>
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: `${compMeta.color}12` }}
            >
              <CompIcon size={18} style={{ color: compMeta.color }} />
            </div>
            <div>
              <p className="text-base font-semibold text-[var(--text-primary)]">{compMeta.label}</p>
              <p className="text-xs text-[var(--text-tertiary)] font-mono">{component}</p>
            </div>
          </div>
        </motion.div>

        {/* Confidence */}
        <motion.div custom={2} variants={cardVariants} className="glass-card p-5">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-4">
            <Activity size={13} />
            Confidence Score
          </div>
          <div className="flex items-center gap-4">
            <span className="text-3xl font-bold text-[var(--text-primary)] tabular-nums">
              {confidence}<span className="text-lg text-[var(--text-tertiary)]">%</span>
            </span>
            <div className="flex-1">
              <div className="progress-track h-2.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${confidence}%` }}
                  transition={{ duration: 1, delay: 0.4, ease: [0.4, 0, 0.2, 1] }}
                  className="h-full rounded-full"
                  style={{
                    background: `linear-gradient(90deg, var(--accent-violet), var(--accent-blue))`,
                  }}
                />
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* ── Remediation ────────────────────────────────────────────────── */}
      <motion.div custom={3} variants={cardVariants} className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
            <Wrench size={13} />
            Recommended Remediation
          </div>
          <CopyButton text={remediation} />
        </div>
        {formatRemediation(remediation)}
      </motion.div>
    </motion.div>
  );
}
