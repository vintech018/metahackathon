import { motion } from 'framer-motion';
import { SEVERITY_CONFIG, COMPONENT_CONFIG, DIFFICULTY_CONFIG } from '../data/mockData';

export default function HistoryPanel({ history, onSelect, activeIndex }) {
  if (!history.length) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(168,85,247,0.1)', color: 'var(--purple)' }}>
            📋
          </div>
          <h2 className="text-sm font-semibold">Triage History</h2>
        </div>
        <div className="flex flex-col items-center py-6" style={{ color: 'var(--text-muted)' }}>
          <div className="text-3xl mb-2 opacity-30">📜</div>
          <p className="text-xs">No history yet</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
      className="glass-card overflow-hidden"
    >
      <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(168,85,247,0.1)', color: 'var(--purple)' }}>
            📋
          </div>
          <div>
            <h2 className="text-sm font-semibold">Triage History</h2>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{history.length} reports analyzed</p>
          </div>
        </div>
      </div>

      <div className="overflow-y-auto" style={{ maxHeight: '350px' }}>
        {history.map((item, i) => {
          const sevConfig = SEVERITY_CONFIG[item.action.severity] || SEVERITY_CONFIG.medium;
          const diffConfig = DIFFICULTY_CONFIG[item.difficulty] || DIFFICULTY_CONFIG.easy;
          const isActive = i === activeIndex;
          const reward = item.reward;

          return (
            <motion.button
              key={i}
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => onSelect(i)}
              className="w-full text-left px-5 py-3.5 border-b cursor-pointer bg-transparent transition-colors duration-200"
              style={{
                borderColor: 'var(--border)',
                background: isActive ? 'rgba(34,211,238,0.05)' : 'transparent',
                borderLeft: isActive ? '3px solid var(--cyan)' : '3px solid transparent',
                color: 'inherit',
              }}
              whileHover={{ backgroundColor: 'rgba(148,163,184,0.04)' }}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono font-bold" style={{ color: 'var(--cyan)' }}>
                    {item.id}
                  </span>
                  <span
                    className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                    style={{ background: `${diffConfig.color}18`, color: diffConfig.color }}
                  >
                    {diffConfig.label}
                  </span>
                </div>
                <span
                  className="text-xs font-black font-mono"
                  style={{ color: reward >= 0.8 ? '#10b981' : reward >= 0.6 ? '#f59e0b' : '#ef4444' }}
                >
                  {reward.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className="text-[9px] font-bold px-1.5 py-0.5 rounded severity-pulse"
                  style={{ background: sevConfig.bg, color: sevConfig.color }}
                >
                  {sevConfig.label}
                </span>
                <span
                  className="text-[9px] font-semibold px-1.5 py-0.5 rounded"
                  style={{
                    background: (COMPONENT_CONFIG[item.action.component] || COMPONENT_CONFIG.api).bg,
                    color: (COMPONENT_CONFIG[item.action.component] || COMPONENT_CONFIG.api).color,
                  }}
                >
                  {item.action.component}
                </span>
              </div>
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
}
