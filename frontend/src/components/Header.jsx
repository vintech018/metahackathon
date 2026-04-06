import { motion } from 'framer-motion';

export default function Header({ onRunTriage, isLoading, triageCount }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="relative z-10 px-6 lg:px-10 py-5 flex items-center justify-between border-b"
      style={{ borderColor: 'var(--border)', background: 'rgba(6,10,19,0.85)', backdropFilter: 'blur(20px)' }}
    >
      {/* Left: Logo + Title */}
      <div className="flex items-center gap-4">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center text-xl"
          style={{
            background: 'linear-gradient(135deg, #22d3ee 0%, #3b82f6 50%, #a855f7 100%)',
            boxShadow: '0 4px 20px rgba(34,211,238,0.3)',
          }}
        >
          🛡️
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight">
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: 'linear-gradient(135deg, #22d3ee 0%, #3b82f6 50%, #a855f7 100%)' }}
            >
              Bug Bounty Triage
            </span>
          </h1>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            AI Security Operations Dashboard
          </p>
        </div>
      </div>

      {/* Center: Stats */}
      <div className="hidden md:flex items-center gap-6">
        <div className="text-center">
          <div className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Reports Analyzed</div>
          <div className="text-sm font-bold" style={{ color: 'var(--cyan)' }}>{triageCount}</div>
        </div>
        <div className="w-px h-8" style={{ background: 'var(--border)' }} />
        <div className="text-center">
          <div className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Engine</div>
          <div className="text-sm font-bold" style={{ color: 'var(--purple)' }}>GPT-4o + RL</div>
        </div>
        <div className="w-px h-8" style={{ background: 'var(--border)' }} />
        <div className="text-center">
          <div className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Status</div>
          <div className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{
                background: '#10b981',
                boxShadow: '0 0 8px rgba(16,185,129,0.5)',
                animation: 'severity-pulse 2s ease-in-out infinite',
              }}
            />
            <span className="text-sm font-bold" style={{ color: '#10b981' }}>Online</span>
          </div>
        </div>
      </div>

      {/* Right: Run Button */}
      <motion.button
        id="run-triage-btn"
        onClick={onRunTriage}
        disabled={isLoading}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        className="relative px-6 py-2.5 rounded-xl font-semibold text-sm text-white cursor-pointer overflow-hidden disabled:opacity-60 disabled:cursor-not-allowed"
        style={{
          background: isLoading
            ? 'rgba(34,211,238,0.15)'
            : 'linear-gradient(135deg, #22d3ee 0%, #3b82f6 100%)',
          boxShadow: isLoading ? 'none' : '0 4px 20px rgba(34,211,238,0.3)',
          border: 'none',
        }}
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4" fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            AI Analyzing...
          </span>
        ) : (
          <span className="flex items-center gap-2">
            ▶ Run Triage
          </span>
        )}
      </motion.button>
    </motion.header>
  );
}
