import { motion } from 'framer-motion';
import { BarChart3, ChevronRight, CheckCircle2, XCircle } from 'lucide-react';

const SCORE_COLORS = {
  severity: { bar: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.12)' },
  component: { bar: '#3b82f6', bg: 'rgba(59, 130, 246, 0.12)' },
  remediation: { bar: '#22c55e', bg: 'rgba(34, 197, 94, 0.12)' },
  bonus: { bar: '#f97316', bg: 'rgba(249, 115, 22, 0.12)' },
};

function ScoreBar({ label, value, maxValue = 1, color, delay = 0 }) {
  const pct = Math.round((value / maxValue) * 100);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[var(--text-secondary)] capitalize">{label}</span>
        <span className="text-xs font-mono text-[var(--text-tertiary)]">{pct}%</span>
      </div>
      <div className="progress-track h-2">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, delay, ease: [0.4, 0, 0.2, 1] }}
          className="h-full rounded-full"
          style={{ background: color }}
        />
      </div>
    </div>
  );
}

function MatchIndicator({ label, expected, actual }) {
  const match = expected && actual && expected.toLowerCase() === actual.toLowerCase();
  return (
    <div className="flex items-center gap-2 text-xs">
      {match ? (
        <CheckCircle2 size={13} className="text-green-400 shrink-0" />
      ) : (
        <XCircle size={13} className="text-red-400 shrink-0" />
      )}
      <span className="text-[var(--text-tertiary)]">{label}:</span>
      <span className="font-mono text-[var(--text-secondary)]">{actual || '—'}</span>
      {expected && !match && (
        <>
          <ChevronRight size={10} className="text-[var(--text-tertiary)]" />
          <span className="font-mono text-[var(--text-tertiary)]">expected {expected}</span>
        </>
      )}
    </div>
  );
}

export default function ExplanationPanel({ result }) {
  if (!result) return null;

  const { info, reward, action } = result;
  const explanation = info?.explanation || {};

  // Extract individual scores from explanation
  const severityScore = explanation.severity_score ?? (info?.expected_severity === action?.severity ? 0.35 : 0);
  const componentScore = explanation.component_score ?? (info?.expected_component === action?.component ? 0.25 : 0);
  const remediationScore = explanation.remediation_score ?? Math.max(0, (reward || 0) - severityScore - componentScore);
  const bonusScore = explanation.bonus_score ?? 0;

  const maxPossible = 0.35 + 0.25 + 0.3 + 0.1;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.5 }}
      className="glass-card p-5"
    >
      <div className="flex items-center gap-2 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-5">
        <BarChart3 size={13} />
        Scoring Breakdown
      </div>

      {/* Score bars */}
      <div className="space-y-4 mb-6">
        <ScoreBar
          label="Severity Match"
          value={severityScore}
          maxValue={0.35}
          color={SCORE_COLORS.severity.bar}
          delay={0.6}
        />
        <ScoreBar
          label="Component Match"
          value={componentScore}
          maxValue={0.25}
          color={SCORE_COLORS.component.bar}
          delay={0.72}
        />
        <ScoreBar
          label="Remediation Quality"
          value={remediationScore}
          maxValue={0.3}
          color={SCORE_COLORS.remediation.bar}
          delay={0.84}
        />
        <ScoreBar
          label="Bonus (Chain Detection)"
          value={bonusScore}
          maxValue={0.1}
          color={SCORE_COLORS.bonus.bar}
          delay={0.96}
        />
      </div>

      {/* Total score */}
      <div className="flex items-center justify-between py-3 border-t border-[var(--border-subtle)]">
        <span className="text-xs font-medium text-[var(--text-secondary)]">Total Score</span>
        <div className="flex items-center gap-2">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.1 }}
            className="text-lg font-bold tabular-nums"
            style={{
              color: reward >= 0.7 ? '#22c55e' : reward >= 0.4 ? '#eab308' : '#ef4444',
            }}
          >
            {((reward || 0) * 100).toFixed(0)}%
          </motion.span>
          <span className="text-xs text-[var(--text-tertiary)] font-mono">/ {(maxPossible * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Match details */}
      <div className="space-y-2 pt-3 border-t border-[var(--border-subtle)]">
        <MatchIndicator
          label="Severity"
          expected={info?.expected_severity}
          actual={action?.severity}
        />
        <MatchIndicator
          label="Component"
          expected={info?.expected_component}
          actual={action?.component}
        />
      </div>
    </motion.div>
  );
}
