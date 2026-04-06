import { motion } from 'framer-motion';
import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';

const SCORE_LABELS = {
  severity_score: { label: 'Severity', max: 0.40, color: '#ef4444', icon: '🎯' },
  component_score: { label: 'Component', max: 0.30, color: '#3b82f6', icon: '🧩' },
  remediation_score: { label: 'Remediation', max: 0.30, color: '#10b981', icon: '🔧' },
  bonus_score: { label: 'Bonus', max: 0.40, color: '#f59e0b', icon: '⭐' },
};

function ScoreBar({ label, value, max, color, icon, delay }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="mb-4 last:mb-0"
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs">{icon}</span>
          <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
            {label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold font-mono" style={{ color }}>
            {value.toFixed(3)}
          </span>
          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            / {max.toFixed(2)}
          </span>
        </div>
      </div>
      <div className="h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(148,163,184,0.08)' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ delay: delay + 0.2, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="h-full rounded-full relative"
          style={{
            background: `linear-gradient(90deg, ${color}80, ${color})`,
            boxShadow: `0 0 12px ${color}40`,
          }}
        >
          <div className="progress-shimmer absolute inset-0 rounded-full" />
        </motion.div>
      </div>
    </motion.div>
  );
}

export default function ScoreBreakdown({ explanation, totalScore, isVisible }) {
  if (!explanation || !isVisible) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--blue)' }}>
            📊
          </div>
          <h2 className="text-sm font-semibold">Score Breakdown</h2>
        </div>
        <div className="flex flex-col items-center py-6" style={{ color: 'var(--text-muted)' }}>
          <p className="text-xs">Run triage to see scores</p>
        </div>
      </div>
    );
  }

  const totalPct = Math.min(totalScore * 100, 100);
  const ringData = [{ value: totalPct, fill: totalScore >= 0.8 ? '#10b981' : totalScore >= 0.6 ? '#f59e0b' : '#ef4444' }];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-6"
    >
      <div className="flex items-center gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
          style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--blue)' }}>
          📊
        </div>
        <h2 className="text-sm font-semibold">Score Breakdown</h2>
      </div>

      {/* Radial Score Ring */}
      <div className="flex items-center justify-center mb-5">
        <div className="relative">
          <RadialBarChart
            width={130}
            height={130}
            cx={65}
            cy={65}
            innerRadius={45}
            outerRadius={60}
            data={ringData}
            startAngle={90}
            endAngle={-270}
            barSize={10}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar
              background={{ fill: 'rgba(148,163,184,0.08)' }}
              dataKey="value"
              angleAxisId={0}
              cornerRadius={10}
              isAnimationActive={true}
              animationDuration={1500}
            />
          </RadialBarChart>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-black font-mono" style={{
              color: totalScore >= 0.8 ? '#10b981' : totalScore >= 0.6 ? '#f59e0b' : '#ef4444'
            }}>
              {totalScore.toFixed(2)}
            </span>
            <span className="text-[9px] font-semibold" style={{ color: 'var(--text-muted)' }}>
              TOTAL
            </span>
          </div>
        </div>
      </div>

      {/* Score Bars */}
      {Object.entries(SCORE_LABELS).map(([key, config], i) => (
        <ScoreBar
          key={key}
          label={config.label}
          value={explanation[key] || 0}
          max={config.max}
          color={config.color}
          icon={config.icon}
          delay={0.3 + i * 0.1}
        />
      ))}
    </motion.div>
  );
}
