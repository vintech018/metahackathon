import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SEVERITY_CONFIG, COMPONENT_CONFIG } from '../data/mockData';

function CompareRow({ label, expected, predicted, isMatch }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b" style={{ borderColor: 'var(--border)' }}>
      <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <div className="text-[9px] uppercase tracking-wider mb-0.5" style={{ color: 'var(--text-muted)' }}>Expected</div>
          <span
            className="text-xs font-bold px-2.5 py-0.5 rounded-md"
            style={{
              background: 'rgba(34,211,238,0.1)',
              color: 'var(--cyan)',
            }}
          >
            {expected}
          </span>
        </div>
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.4, type: 'spring' }}
          className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
          style={{
            background: isMatch ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
            color: isMatch ? '#10b981' : '#ef4444',
          }}
        >
          {isMatch ? '✓' : '✗'}
        </motion.div>
        <div className="text-left">
          <div className="text-[9px] uppercase tracking-wider mb-0.5" style={{ color: 'var(--text-muted)' }}>Predicted</div>
          <span
            className="text-xs font-bold px-2.5 py-0.5 rounded-md"
            style={{
              background: isMatch ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
              color: isMatch ? '#10b981' : '#ef4444',
            }}
          >
            {predicted}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ExplainabilityPanel({ info, action, isVisible }) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!info || !action || !isVisible) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--yellow)' }}>
            🔍
          </div>
          <h2 className="text-sm font-semibold">Explainability</h2>
        </div>
        <div className="flex flex-col items-center py-6" style={{ color: 'var(--text-muted)' }}>
          <p className="text-xs">Decision analysis will appear here</p>
        </div>
      </div>
    );
  }

  const sevMatch = info.expected_severity === action.severity;
  const compMatch = info.expected_component === action.component;
  const explanation = info.explanation || {};

  const analysisItems = [];
  if (explanation.severity_score >= 0.35) analysisItems.push({ text: 'Severity classification is accurate', type: 'success' });
  else analysisItems.push({ text: `Severity mismatch: expected ${info.expected_severity}, got ${action.severity}`, type: 'error' });

  if (explanation.component_score >= 0.25) analysisItems.push({ text: 'Component identification is correct', type: 'success' });
  else analysisItems.push({ text: `Component mismatch: expected ${info.expected_component}, got ${action.component}`, type: 'error' });

  if (explanation.remediation_score >= 0.2) analysisItems.push({ text: 'Remediation covers key security controls', type: 'success' });
  else analysisItems.push({ text: 'Remediation missing critical keywords', type: 'warning' });

  if (explanation.bonus_score > 0) analysisItems.push({ text: `Bonus signals detected (+${explanation.bonus_score.toFixed(2)})`, type: 'info' });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="glass-card overflow-hidden"
    >
      {/* Header — Collapsible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between cursor-pointer border-none bg-transparent text-left"
        style={{ color: 'var(--text-primary)' }}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--yellow)' }}>
            🔍
          </div>
          <div>
            <h2 className="text-sm font-semibold">Explainability</h2>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              Why this decision was made
            </p>
          </div>
        </div>
        <motion.span
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.3 }}
          className="text-sm"
          style={{ color: 'var(--text-muted)' }}
        >
          ▾
        </motion.span>
      </button>

      {/* Body */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-6">
              {/* Expected vs Predicted */}
              <div className="mb-5">
                <div className="text-[10px] font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  Expected vs Predicted
                </div>
                <CompareRow
                  label="Severity"
                  expected={info.expected_severity?.toUpperCase()}
                  predicted={action.severity?.toUpperCase()}
                  isMatch={sevMatch}
                />
                <CompareRow
                  label="Component"
                  expected={info.expected_component?.toUpperCase()}
                  predicted={action.component?.toUpperCase()}
                  isMatch={compMatch}
                />
              </div>

              {/* Analysis */}
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  Decision Analysis
                </div>
                <div className="space-y-2">
                  {analysisItems.map((item, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + i * 0.1 }}
                      className="flex items-start gap-2.5 text-xs p-2.5 rounded-lg"
                      style={{
                        background:
                          item.type === 'success' ? 'rgba(16,185,129,0.06)' :
                          item.type === 'error' ? 'rgba(239,68,68,0.06)' :
                          item.type === 'warning' ? 'rgba(245,158,11,0.06)' :
                          'rgba(34,211,238,0.06)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      <span className="flex-shrink-0 mt-0.5">
                        {item.type === 'success' ? '✅' :
                         item.type === 'error' ? '❌' :
                         item.type === 'warning' ? '⚠️' : 'ℹ️'}
                      </span>
                      <span>{item.text}</span>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Remediation Keywords */}
              {info.expected_remediation_keywords && (
                <div className="mt-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
                    Expected Keywords
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {info.expected_remediation_keywords.map((kw, i) => {
                      const found = action.remediation?.toLowerCase().includes(kw.toLowerCase());
                      return (
                        <span
                          key={i}
                          className="text-[10px] font-medium px-2 py-1 rounded-md"
                          style={{
                            background: found ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                            color: found ? '#10b981' : '#ef4444',
                            border: `1px solid ${found ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                          }}
                        >
                          {found ? '✓' : '✗'} {kw}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
