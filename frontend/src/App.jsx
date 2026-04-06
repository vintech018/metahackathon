import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, Zap,
  AlertTriangle, RefreshCw,
} from 'lucide-react';

import InputPanel from './components/InputPanel';
import FileUpload from './components/FileUpload';
import AnalyzeButton from './components/AnalyzeButton';
import Loader from './components/Loader';
import ResultDashboard from './components/ResultDashboard';
import ExplanationPanel from './components/ExplanationPanel';

// ── API ───────────────────────────────────────────────────────────────────
async function analyzeReport(text) {
  const res = await fetch('/api/triage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report: text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Server error (${res.status})`);
  }
  return res.json();
}

// ── App ───────────────────────────────────────────────────────────────────
export default function App() {
  const [reportText, setReportText] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const canAnalyze = (reportText.trim().length > 10 || file) && !loading;

  const handleAnalyze = async () => {
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      let text = reportText.trim();

      // If a file is chosen and no text typed, read the file content
      if (file && !text) {
        text = await file.text();
      }

      if (!text || text.length < 10) {
        throw new Error('Please provide a vulnerability report (at least 10 characters) or upload a file.');
      }

      const data = await analyzeReport(text);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setReportText('');
    setFile(null);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-[var(--border-subtle)] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--accent-violet)] to-[var(--accent-blue)] flex items-center justify-center shadow-lg shadow-[var(--accent-violet)]/20">
              <Shield size={16} className="text-white" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
                BugBounty
              </span>
              <span className="text-sm font-medium text-[var(--text-tertiary)]">
                Triage
              </span>
            </div>
            <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-[var(--accent-violet-glow)] text-[var(--accent-violet)] border border-[var(--accent-violet)]/20">
              <Zap size={9} />
              AI-Powered
            </span>
          </div>

          <div className="flex items-center gap-2">
            {result && (
              <motion.button
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                onClick={handleReset}
                className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg
                           text-[var(--text-secondary)] hover:text-[var(--text-primary)]
                           bg-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.08)]
                           border border-[var(--border-subtle)] transition-all cursor-pointer"
              >
                <RefreshCw size={12} />
                New Analysis
              </motion.button>
            )}
          </div>
        </div>
      </header>

      {/* ── Main Content ───────────────────────────────────────────────── */}
      <main className="flex-1 py-8 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <AnimatePresence mode="wait">
            {!result ? (
              /* ── Input View ──────────────────────────────────────────── */
              <motion.div
                key="input-view"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.3 }}
              >
                {/* Hero */}
                <div className="text-center mb-8">
                  <motion.h1
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.05 }}
                    className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)] mb-2"
                  >
                    Vulnerability Triage Agent
                  </motion.h1>
                  <motion.p
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.12 }}
                    className="text-sm text-[var(--text-tertiary)] max-w-lg mx-auto"
                  >
                    Paste a vulnerability report or upload source code. Our AI agent will assess severity,
                    identify the affected component, and recommend remediation.
                  </motion.p>
                </div>

                {/* Input area */}
                <div className="max-w-2xl mx-auto space-y-4">
                  <InputPanel
                    value={reportText}
                    onChange={setReportText}
                    disabled={loading}
                  />

                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-px bg-[var(--border-subtle)]" />
                    <span className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase tracking-widest">or upload</span>
                    <div className="flex-1 h-px bg-[var(--border-subtle)]" />
                  </div>

                  <FileUpload
                    file={file}
                    onFileChange={setFile}
                    disabled={loading}
                  />

                  <div className="pt-2">
                    <AnalyzeButton
                      onClick={handleAnalyze}
                      loading={loading}
                      disabled={!canAnalyze}
                    />
                  </div>

                  {/* Error */}
                  <AnimatePresence>
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        className="glass-card flex items-start gap-3 p-4 !border-red-500/20 !bg-red-500/5"
                      >
                        <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-red-400 mb-0.5">Analysis failed</p>
                          <p className="text-xs text-[var(--text-tertiary)]">{error}</p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Loading */}
                  <AnimatePresence>
                    {loading && <Loader />}
                  </AnimatePresence>
                </div>
              </motion.div>
            ) : (
              /* ── Results View ─────────────────────────────────────────── */
              <motion.div
                key="results-view"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45 }}
              >
                {/* Results header */}
                <div className="mb-6">
                  <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">
                    Analysis Complete
                  </h2>
                  <p className="text-sm text-[var(--text-tertiary)]">
                    Task: <span className="font-mono text-[var(--text-secondary)]">{result.info?.task_id || 'custom'}</span>
                    {result.difficulty && (
                      <>
                        {' · '}Difficulty: <span className="font-mono text-[var(--text-secondary)]">{result.difficulty}</span>
                      </>
                    )}
                  </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
                  {/* Results — 3 cols */}
                  <div className="lg:col-span-3">
                    <ResultDashboard result={result} />
                  </div>

                  {/* Explanation — 2 cols */}
                  <div className="lg:col-span-2">
                    <ExplanationPanel result={result} />
                  </div>
                </div>

                {/* Report preview */}
                {result.report && (
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 }}
                    className="glass-card p-5 mt-5"
                  >
                    <p className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-3">
                      Original Report
                    </p>
                    <pre className="text-xs leading-relaxed text-[var(--text-secondary)] whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                      {result.report}
                    </pre>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-[var(--border-subtle)] py-4 px-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between text-xs text-[var(--text-tertiary)]">
          <span>Bug Bounty Triage Agent · OpenEnv</span>
          <span className="font-mono">v2.0</span>
        </div>
      </footer>
    </div>
  );
}
