import { motion } from 'framer-motion';
import { AlertTriangle, AlertOctagon, AlertCircle, Info } from 'lucide-react';

const CONFIG = {
  critical: {
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.08)',
    border: 'rgba(239, 68, 68, 0.2)',
    icon: AlertOctagon,
    label: 'CRITICAL',
  },
  high: {
    color: '#f97316',
    bg: 'rgba(249, 115, 22, 0.08)',
    border: 'rgba(249, 115, 22, 0.2)',
    icon: AlertTriangle,
    label: 'HIGH',
  },
  medium: {
    color: '#eab308',
    bg: 'rgba(234, 179, 8, 0.08)',
    border: 'rgba(234, 179, 8, 0.2)',
    icon: AlertCircle,
    label: 'MEDIUM',
  },
  low: {
    color: '#22c55e',
    bg: 'rgba(34, 197, 94, 0.08)',
    border: 'rgba(34, 197, 94, 0.2)',
    icon: Info,
    label: 'LOW',
  },
};

export default function SeverityBadge({ severity, large = false }) {
  const key = (severity || 'low').toLowerCase();
  const cfg = CONFIG[key] || CONFIG.low;
  const Icon = cfg.icon;

  if (large) {
    return (
      <motion.div
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-xl font-bold text-lg tracking-wide"
        style={{
          color: cfg.color,
          background: cfg.bg,
          border: `1px solid ${cfg.border}`,
          boxShadow: `0 0 20px ${cfg.bg}`,
        }}
      >
        <Icon size={20} />
        {cfg.label}
      </motion.div>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold tracking-wider"
      style={{
        color: cfg.color,
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
      }}
    >
      <Icon size={12} />
      {cfg.label}
    </span>
  );
}
