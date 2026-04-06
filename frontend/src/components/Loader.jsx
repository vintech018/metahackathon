import { motion } from 'framer-motion';
import { ShieldAlert } from 'lucide-react';

export default function Loader() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center py-16 gap-5"
    >
      {/* Animated shield icon */}
      <div className="relative">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          className="w-16 h-16 rounded-full border-2 border-transparent
                     border-t-[var(--accent-violet)] border-r-[var(--accent-violet)]/30"
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <ShieldAlert size={22} className="text-[var(--accent-violet)]" />
          </motion.div>
        </div>
      </div>

      {/* Text */}
      <div className="text-center">
        <p className="text-sm font-medium text-[var(--text-primary)] mb-1">
          Analyzing vulnerability
        </p>
        <p className="text-xs text-[var(--text-tertiary)]">
          Running LLM triage pipeline…
        </p>
      </div>

      {/* Animated bars */}
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.div
            key={i}
            className="w-1 rounded-full bg-[var(--accent-violet)]"
            animate={{ height: [12, 28, 12] }}
            transition={{
              duration: 0.8,
              repeat: Infinity,
              delay: i * 0.12,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}
