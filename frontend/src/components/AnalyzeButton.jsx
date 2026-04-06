import { useRef } from 'react';
import { motion } from 'framer-motion';
import { Scan } from 'lucide-react';

export default function AnalyzeButton({ onClick, loading, disabled }) {
  const btnRef = useRef(null);

  const handleClick = (e) => {
    // Ripple effect
    const btn = btnRef.current;
    if (btn) {
      const rect = btn.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = e.clientX - rect.left - size / 2 + 'px';
      ripple.style.top = e.clientY - rect.top - size / 2 + 'px';
      btn.appendChild(ripple);
      setTimeout(() => ripple.remove(), 600);
    }
    onClick?.();
  };

  return (
    <motion.button
      ref={btnRef}
      onClick={handleClick}
      disabled={disabled || loading}
      whileHover={!disabled && !loading ? { scale: 1.015, y: -1 } : {}}
      whileTap={!disabled && !loading ? { scale: 0.985 } : {}}
      className="btn-gradient w-full py-3.5 rounded-2xl text-white font-semibold text-sm
                 flex items-center justify-center gap-2.5 tracking-wide shadow-lg
                 shadow-[var(--accent-violet)]/10 transition-shadow hover:shadow-xl
                 hover:shadow-[var(--accent-violet)]/20"
    >
      {loading ? (
        <div className="dot-loader flex gap-1.5">
          <span /><span /><span />
        </div>
      ) : (
        <>
          <Scan size={16} strokeWidth={2.5} />
          Analyze Vulnerability
        </>
      )}
    </motion.button>
  );
}
