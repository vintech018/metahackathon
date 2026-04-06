import { motion } from 'framer-motion';

export default function RewardMeter({ reward, isVisible }) {
  if (!isVisible) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--green)' }}>
            📈
          </div>
          <h2 className="text-sm font-semibold">Confidence Score</h2>
        </div>
        <div className="flex flex-col items-center py-4" style={{ color: 'var(--text-muted)' }}>
          <p className="text-xs">Awaiting triage result</p>
        </div>
      </div>
    );
  }

  const pct = Math.min(reward * 100, 100);
  const color = reward >= 0.8 ? '#10b981' : reward >= 0.6 ? '#f59e0b' : '#ef4444';
  const label = reward >= 0.8 ? 'HIGH CONFIDENCE' : reward >= 0.6 ? 'MODERATE' : 'LOW CONFIDENCE';
  const success = reward >= 0.6;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--green)' }}>
            📈
          </div>
          <h2 className="text-sm font-semibold">Confidence Score</h2>
        </div>
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.6, type: 'spring', stiffness: 400 }}
          className="px-3 py-1 rounded-full text-[10px] font-bold"
          style={{
            background: success ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
            color: success ? '#10b981' : '#ef4444',
            border: `1px solid ${success ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
          }}
        >
          {success ? '✓ PASS' : '✗ FAIL'} (≥0.60)
        </motion.div>
      </div>

      {/* Large Score Display */}
      <div className="text-center mb-5">
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4, type: 'spring', stiffness: 200 }}
          className="text-5xl font-black font-mono"
          style={{ color, textShadow: `0 0 40px ${color}40` }}
        >
          {reward.toFixed(2)}
        </motion.div>
        <div className="text-[10px] font-bold mt-1 tracking-widest" style={{ color: `${color}99` }}>
          {label}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-3 rounded-full overflow-hidden" style={{ background: 'rgba(148,163,184,0.08)' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ delay: 0.5, duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
          className="h-full rounded-full relative"
          style={{
            background: `linear-gradient(90deg, ${color}60, ${color})`,
            boxShadow: `0 0 16px ${color}50`,
          }}
        >
          <div className="progress-shimmer absolute inset-0 rounded-full" />
        </motion.div>
      </div>

      {/* Scale Labels */}
      <div className="flex justify-between mt-2">
        <span className="text-[9px] font-mono" style={{ color: 'var(--text-muted)' }}>0.00</span>
        <span className="text-[9px] font-mono" style={{ color: 'var(--text-muted)' }}>0.60</span>
        <span className="text-[9px] font-mono" style={{ color: 'var(--text-muted)' }}>1.00</span>
      </div>
    </motion.div>
  );
}
