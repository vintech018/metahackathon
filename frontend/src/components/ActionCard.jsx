import { motion } from 'framer-motion';
import { SEVERITY_CONFIG, COMPONENT_CONFIG } from '../data/mockData';

export default function ActionCard({ action, isVisible }) {
  if (!action || !isVisible) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(168,85,247,0.1)', color: 'var(--purple)' }}
          >
            🤖
          </div>
          <h2 className="text-sm font-semibold">AI Triage Decision</h2>
        </div>
        <div className="flex flex-col items-center py-8" style={{ color: 'var(--text-muted)' }}>
          <div className="text-4xl mb-3 opacity-40">🧠</div>
          <p className="text-xs">Waiting for analysis...</p>
        </div>
      </div>
    );
  }

  const sevConfig = SEVERITY_CONFIG[action.severity] || SEVERITY_CONFIG.medium;
  const compConfig = COMPONENT_CONFIG[action.component] || COMPONENT_CONFIG.api;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
      className="glass-card overflow-hidden"
    >
      {/* Header Strip */}
      <div className="h-1" style={{ background: `linear-gradient(90deg, ${sevConfig.color}, ${compConfig.color})` }} />

      <div className="p-6">
        {/* Title */}
        <div className="flex items-center gap-3 mb-5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(168,85,247,0.1)', color: 'var(--purple)' }}
          >
            🤖
          </div>
          <div>
            <h2 className="text-sm font-semibold">AI Triage Decision</h2>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Multi-step reasoning engine</p>
          </div>
        </div>

        {/* Severity + Component Row */}
        <div className="flex items-center gap-3 mb-5">
          {/* Severity Badge */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.3, type: 'spring', stiffness: 300 }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm"
            style={{
              background: sevConfig.bg,
              color: sevConfig.color,
              border: `1px solid ${sevConfig.border}`,
            }}
          >
            <span className="severity-pulse">{sevConfig.icon}</span>
            {sevConfig.label}
          </motion.div>

          {/* Component Badge */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.4, type: 'spring', stiffness: 300 }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-xs"
            style={{
              background: compConfig.bg,
              color: compConfig.color,
              border: `1px solid ${compConfig.color}30`,
            }}
          >
            {compConfig.icon} {action.component.toUpperCase()}
          </motion.div>
        </div>

        {/* Remediation */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.4 }}
        >
          <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
            Remediation
          </div>
          <div
            className="text-xs leading-relaxed p-4 rounded-xl"
            style={{
              background: 'rgba(16,185,129,0.05)',
              border: '1px solid rgba(16,185,129,0.1)',
              color: 'var(--text-secondary)',
            }}
          >
            {action.remediation}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
