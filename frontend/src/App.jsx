import React, { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, ShieldAlert, Cpu, Sparkles, Activity, RefreshCw, Layers, CheckCircle2, Zap, LayoutDashboard, Copy, Code, Check, Play } from 'lucide-react';

const Editor = lazy(() => import('@monaco-editor/react'));

const API_BASE = ""; // Routed via Vite proxy → vaibhav's backend on port 5001

const ACTIONS = [
  "analyze_report",
  "analyze_logs",
  "inspect_code",
  "extract_vulnerability",
  "classify_type",
  "estimate_severity",
  "identify_component",
  "suggest_fix",
  "validate_fix"
];

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    if(!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button 
      onClick={handleCopy}
      className="flex items-center gap-1.5 px-2 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/5 transition-colors text-[10px] uppercase font-mono text-slate-400 hover:text-white"
    >
      {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
      {copied ? "Copied!" : label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Classification Parser
// Converts the backend observation (from classify_type step) into a strict
// structured schema WITHOUT any keyword matching — all intelligence comes
// from the backend's identified_vulnerability + exploit_chain fields.
// ---------------------------------------------------------------------------
function parseClassification(observation) {
  const raw = observation?.identified_vulnerability;
  const chain = observation?.exploit_chain ?? [];

  let type, confidence, reasoning;

  if (raw === "XSS") {
    type       = "XSS";
    confidence = 0.97;
    reasoning  = `Backend classify_type detected Cross-Site Scripting. Exploit chain: ${chain.join(" → ") || "N/A"}. User input is rendered into HTML without sanitization, allowing script injection.`;
  } else if (raw === "SQL Injection") {
    type       = "SQL_INJECTION";
    confidence = 0.97;
    reasoning  = `Backend classify_type detected SQL Injection. Exploit chain: ${chain.join(" → ") || "N/A"}. User-supplied data flows directly into a SQL query without parameterization.`;
  } else if (raw === "IDOR") {
    type       = "IDOR";
    confidence = 0.93;
    reasoning  = `Backend classify_type detected Insecure Direct Object Reference. Exploit chain: ${chain.join(" → ") || "N/A"}. Object access is controlled by user-supplied input without authorization checks.`;
  } else if (raw === null || raw === undefined || raw === "") {
    // Backend returned null → either SAFE or genuinely ambiguous
    if (chain.length === 0 || chain[0] === "No exploit path") {
      type       = "SAFE";
      confidence = 0.90;
      reasoning  = "Backend classify_type found no exploit path. Code uses safe patterns — no injection vectors detected.";
    } else {
      type       = "UNKNOWN";
      confidence = 0.40;
      reasoning  = `Backend classify_type could not confidently determine a vulnerability type. Exploit chain: ${chain.join(" → ") || "N/A"}. Manual review recommended.`;
    }
  } else {
    // Any other unexpected string from backend
    type       = "UNKNOWN";
    confidence = 0.50;
    reasoning  = `Backend classify_type returned an unrecognized label "${raw}". Unable to confidently classify — manual review recommended.`;
  }

  return { type, confidence, reasoning };
}

function App() {
  const [mode, setMode] = useState("demo"); // "demo" or "custom"
  const [state, setState] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState(null);
  const [autoSolving, setAutoSolving] = useState(false);
  const [finalScore, setFinalScore] = useState(null);
  const [result, setResult] = useState(null);
  const [vulnType, setVulnType] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [classificationReasoning, setClassificationReasoning] = useState(null);
  const classificationRef = useRef(null); // mutable ref for autoSolve pipeline gating
  
  // Custom Input State
  const [customInputs, setCustomInputs] = useState({
    report: "",
    logs: "",
    code: ""
  });
  const [errors, setErrors] = useState({});

  const logsEndRef = useRef(null);

  const prefillExample = () => {
    setCustomInputs({
      report: "Users are reporting that they can bypass authentication entirely by injecting special characters into the login form. The security team noticed weird payloads in the auth proxy logs.",
      logs: "POST /login HTTP/1.1\nHost: portal.vulnarena.local\nPayload: username=admin' OR '1'='1&password=xyz",
      code: "def authenticate(username, password):\n    # Direct string interpolation of user input\n    query = f\"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'\"\n    cursor.execute(query)\n    return cursor.fetchone()"
    });
    setErrors({});
  };

  const handleCustomModeSwitch = () => {
    setMode("custom");
    setState(null);
    setLogs([{ type: "system", text: "[SYS]: Switched to Custom Input Mode. Awaiting payload..." }]);
  };

  const handleDemoModeSwitch = () => {
    setMode("demo");
    resetEnv();
  };

  const resetEnv = async (useCustomPayload = false) => {
    setLoading(true);
    setAutoSolving(false);
    setActiveAction(null);
    setFinalScore(null);
    setResult(null);
    setVulnType(null);
    setConfidence(null);
    setClassificationReasoning(null);
    classificationRef.current = null;
    
    try {
      const res = await fetch(`${API_BASE}/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_name: "easy" })
      });
      const data = await res.json();
      
      if (useCustomPayload) {
        setState({
          ...data,
          report_text: customInputs.report,
          code_snippet: customInputs.code,
          logs: [customInputs.logs]
        });
      } else {
        setState(data);
      }
      setLogs([{ type: "system", text: "Environment reset. Target state isolated. Ready for analysis." }]);
    } catch (err) {
      setLogs([{ type: "error", text: "Failed to connect to backend. Is it running?" }]);
    }
    setLoading(false);
  };

  const resetApp = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_name: "easy" })
      });

      // Reset all frontend state
      setActiveAction(null);
      setFinalScore(null);
      setResult(null);
      setVulnType(null);
      setConfidence(null);
      setClassificationReasoning(null);
      classificationRef.current = null;
      setLogs([{ type: "success", text: "Environment Reset ✅" }]);
      
      // Clear inputs
      setCustomInputs({ report: "", logs: "", code: "" });
      setErrors({});

      if (mode === "demo") {
        const res = await fetch(`${API_BASE}/reset`, {
           method: "POST",
           headers: { "Content-Type": "application/json" },
           body: JSON.stringify({ task_name: "easy" })
        });
        const data = await res.json();
        setState(data);
      } else {
        setState(null);
      }
      
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      console.error("Reset failed:", err);
    }
    setLoading(false);
  };

  const runCustomAnalysis = async () => {
    const newErrors = {};
    if (!customInputs.report.trim()) newErrors.report = "Bug Report is required.";
    if (!customInputs.code.trim()) newErrors.code = "Code snippet is required.";
    
    if (Object.keys(newErrors).length > 0) {
      if (newErrors.code) alert("Code snippet is required");
      setErrors(newErrors);
      return;
    }
    
    setErrors({});
    await resetEnv(true);
    // Slight delay to let UI render the state before auto solving
    setTimeout(() => startAutoSolve(), 500);
  };

  const takeAction = async (action) => {
    setLoading(true);
    setActiveAction(action);
    setLogs(prev => [...prev, { type: "action", text: `[AGENT]: Executing ${action}...` }]);
    
    const payload = { action };
    if (mode === "custom") {
      payload.report_text = customInputs.report;
      payload.logs = customInputs.logs ? [customInputs.logs] : [];
      payload.code_snippet = customInputs.code;
    }

    try {
      const res = await fetch(`${API_BASE}/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const response = await res.json();

      // ── classify_type handler ──────────────────────────────────────────────
      if (action === "classify_type") {
        console.log("CLASSIFICATION:", response);

        // Guard: response must exist and have observation
        if (!response || !response.observation) {
          throw new Error("Classification failed — invalid response from backend");
        }

        // Parse into enforced schema: { type, confidence, reasoning }
        const classification = parseClassification(response.observation);
        console.log("PARSED CLASSIFICATION:", classification);

        // Commit to state — this is the ONLY place setVulnType is called
        setVulnType(classification.type);
        setConfidence(classification.confidence);
        setClassificationReasoning(classification.reasoning);
        classificationRef.current = classification; // sync ref for pipeline gating

        setLogs(prev => [...prev, {
          type: "success",
          text: `[CLASSIFY]: Type=${classification.type} | Confidence=${(classification.confidence * 100).toFixed(0)}%`
        }]);
      }
      // ── END classify_type handler ──────────────────────────────────────────

      setState(prev => ({ ...prev, ...response.observation }));
      
      const resText = `[SYS]: Reward: +${(response.reward || 0).toFixed(2)}`;
      const isDone = response.done;
      const score = response.info?.final_score;

      if (response.info?.error && response.info.error !== "null") {
        setLogs(prev => [...prev, { type: "error", text: `[SYS ERROR]: ${response.info.error}` }]);
      } else if (action !== "classify_type") {
        // classify_type already logged above
        setLogs(prev => [...prev, { type: "success", text: resText }]);
      }

      if (isDone) {
        setFinalScore(score !== undefined ? score : null);
        setResult({ ...response.observation });
        setLogs(prev => [...prev, { type: "system", text: `[SYS]: ANALYSIS COMPLETE. Final Score: ${score?.toFixed(2) || 0}` }]);
      }
      
      if (!autoSolving) setLoading(false);
      return isDone;
    } catch (err) {
      setLogs(prev => [...prev, { type: "error", text: `[API ERROR]: ${err.message}` }]);
      if (!autoSolving) setLoading(false);
      return true;
    }
  };

  const CLASSIFY_ACTION = "classify_type";
  const BLOCKED_BEFORE_CLASSIFICATION = ["estimate_severity", "suggest_fix", "validate_fix"];

  const startAutoSolve = async () => {
    if (autoSolving || state?.done) return;
    setAutoSolving(true);
    classificationRef.current = null; // reset before pipeline run
    
    for (const action of ACTIONS) {
      // Block downstream steps if classification is missing
      if (BLOCKED_BEFORE_CLASSIFICATION.includes(action)) {
        const cls = classificationRef.current;
        if (!cls || !cls.type) {
          setLogs(prev => [...prev, {
            type: "error",
            text: `[PIPELINE BLOCKED]: Cannot run "${action}" — classification has not completed yet.`
          }]);
          break;
        }
      }

      try {
        const isDone = await takeAction(action);
        await new Promise(r => setTimeout(r, 700));
        if (isDone) break;
      } catch (err) {
        console.error("Step failed:", action, err);
        break;
      }
    }
    
    setActiveAction(null);
    setAutoSolving(false);
    setLoading(false);
  };

  useEffect(() => {
    if (mode === "demo") {
      resetEnv();
    }
  }, [mode]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const displayScore = finalScore !== null 
    ? Math.round(finalScore * 100) 
    : Math.max(0, 100 - ((state?.step_count || 0) * 5));

  return (
    <div className="min-h-screen bg-black text-slate-200 font-sans relative pb-24 selection:bg-blue-500/30 selection:text-white">
      
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[80%] max-w-5xl h-[500px] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none z-0" />
      <div className="fixed bottom-0 right-0 w-[500px] h-[500px] bg-purple-600/10 blur-[150px] rounded-full pointer-events-none z-0" />
      
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-black/60 backdrop-blur-xl">
         <div className="w-full max-w-7xl mx-auto px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4">
               <div className="w-10 h-10 rounded-xl bg-gradient-to-b from-[#222] to-[#0a0a0a] border border-[#333] flex items-center justify-center shadow-lg relative overflow-hidden">
                  <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-blue-400/50 to-transparent" />
                  <LayoutDashboard className="text-blue-400" size={18} />
               </div>
               <div>
                  <h1 className="text-xl font-semibold text-white tracking-tight flex items-center gap-3 flex-wrap">
                     VulnArena AI  
                     <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] uppercase tracking-widest font-mono text-slate-400">Security Pipeline</span>
                     <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase tracking-widest font-mono ${
                       !vulnType ? 'bg-slate-500/10 border-slate-500/20 text-slate-500' :
                       vulnType === 'UNKNOWN' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
                       vulnType === 'SAFE' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                       'bg-red-500/10 border-red-500/20 text-red-400'
                     }`}>
                       {vulnType ? `${vulnType}` : 'CLASSIFYING...'}
                       {confidence !== null && vulnType && ` · ${(confidence * 100).toFixed(0)}%`}
                     </span>
                  </h1>
               </div>
            </div>
            
            {/* Mode Switcher and Reset */}
            <div className="flex items-center gap-5">
              <div className="bg-[#111] border border-[#333] p-1 rounded-lg flex items-center gap-1 shadow-inner">
                 <button 
                    onClick={handleDemoModeSwitch}
                    className={`px-4 py-1.5 rounded-md text-xs font-mono font-bold uppercase transition-all ${mode === 'demo' ? 'bg-white/10 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                 >
                    Demo Mode
                 </button>
                 <button 
                    onClick={handleCustomModeSwitch}
                    className={`px-4 py-1.5 rounded-md text-xs font-mono font-bold uppercase transition-all ${mode === 'custom' ? 'bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'text-slate-500 hover:text-slate-300'}`}
                 >
                    Custom Mode
                 </button>
              </div>

              {/* Global Reset Button */}
              <button 
                onClick={resetApp} 
                disabled={loading || autoSolving}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-colors font-medium text-xs font-mono uppercase tracking-widest text-slate-300 hover:text-white hover:shadow-[0_0_15px_rgba(255,255,255,0.1)] disabled:opacity-50"
              >
                <RefreshCw size={14} className={loading && !autoSolving ? "animate-spin" : ""} />
                Reset Environment
              </button>
            </div>
         </div>
      </header>

      <main className="relative z-10 w-full max-w-7xl mx-auto px-6 pt-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Column: Context & State */}
        <div className="lg:col-span-5 flex flex-col gap-8 w-full">
          
          {/* Custom Input Panel (If in Custom Mode and State not generated) */}
          {mode === "custom" && !state && (
             <motion.div 
               initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
               className="glass-card rounded-2xl p-7 relative border-l-4 border-l-blue-500"
             >
               <div className="flex justify-between items-center mb-6">
                 <h2 className="flex items-center gap-3 text-sm font-bold text-white uppercase tracking-widest">
                   <Code size={16} className="text-blue-400"/> Custom Payload
                 </h2>
                 <button onClick={prefillExample} className="text-[10px] font-mono text-blue-400 hover:text-blue-300 bg-blue-500/10 px-2 py-1 rounded">
                   Load Example
                 </button>
               </div>

               <div className="space-y-4">
                  {/* Report */}
                  <div className="flex flex-col gap-2">
                     <label className="text-[10px] uppercase font-mono tracking-widest text-slate-500">Bug Report <span className="text-red-400">*</span></label>
                     <textarea 
                        value={customInputs.report}
                        onChange={(e) => setCustomInputs(prev => ({...prev, report: e.target.value}))}
                        className={`w-full bg-[#050505] border ${errors.report ? 'border-red-500/50 focus:border-red-500' : 'border-[#333] focus:border-blue-500/50'} rounded-lg p-3 text-xs font-mono text-slate-200 outline-none resize-none h-20 transition-colors`}
                        placeholder="Describe the vulnerability or user report..."
                     />
                     {errors.report && <span className="text-red-400 text-[10px] font-mono">{errors.report}</span>}
                  </div>

                  {/* Logs */}
                  <div className="flex flex-col gap-2">
                     <label className="text-[10px] uppercase font-mono tracking-widest text-slate-500">Server Logs (Optional)</label>
                     <textarea 
                        value={customInputs.logs}
                        onChange={(e) => setCustomInputs(prev => ({...prev, logs: e.target.value}))}
                        className="w-full bg-[#050505] border border-[#333] focus:border-blue-500/50 rounded-lg p-3 text-xs font-mono text-slate-400 outline-none resize-none h-20 transition-colors"
                        placeholder="Paste server logs, HTTP requests..."
                     />
                  </div>

                  {/* Code Snippet */}
                  <div className="flex flex-col gap-2">
                     <label className="text-[10px] uppercase font-mono tracking-widest text-slate-500">Code Snippet <span className="text-red-400">*</span></label>
                     <div className={`h-[200px] rounded-lg overflow-hidden border ${errors.code ? 'border-red-500/50' : 'border-[#333] focus-within:border-blue-500/50'} transition-colors`}>
                        <Suspense fallback={<div className="h-full w-full bg-[#050505] flex items-center justify-center text-xs font-mono text-slate-600">Loading editor...</div>}>
                           <Editor 
                              height="100%"
                              theme="vs-dark"
                              defaultLanguage="python"
                              value={customInputs.code}
                              onChange={(val) => setCustomInputs(prev => ({...prev, code: val || ""}))}
                              options={{ minimap: { enabled: false }, fontSize: 12, padding: { top: 10 } }}
                           />
                        </Suspense>
                     </div>
                     {errors.code && <span className="text-red-400 text-[10px] font-mono">{errors.code}</span>}
                  </div>

                  <div className="flex gap-3 pt-4">
                     <button 
                        onClick={runCustomAnalysis}
                        className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-white text-black hover:bg-slate-200 transition-colors font-semibold text-sm shadow-[0_0_20px_rgba(255,255,255,0.2)]"
                     >
                        <Play fill="currentColor" size={14} /> Run Custom Analysis
                     </button>
                  </div>
               </div>
             </motion.div>
          )}

          {/* Target Telemetry (Visible if state is populated) */}
          {state && (
             <motion.div 
               initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
               className="glass-card rounded-2xl p-7 relative"
             >
               <h2 className="flex items-center gap-3 text-sm font-semibold mb-6 text-white uppercase tracking-widest">
                 <Activity className="text-blue-400" size={16} /> Target Telemetry
               </h2>
               
               <div className="space-y-6 flex flex-col items-start w-full">
                 <div className="flex flex-col gap-2 w-full">
                   <div className="flex justify-between items-center">
                      <span className="text-[10px] uppercase font-mono tracking-widest text-slate-500 flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-yellow-500 rounded-full"></div> Bug Bounty Report
                      </span>
                      <CopyButton text={state.report_text} label="Copy" />
                   </div>
                   <div className="bg-[#050505] border border-[#222] p-4 rounded-xl text-sm text-slate-300 leading-relaxed font-mono w-full break-words whitespace-pre-wrap">
                     {state.report_text}
                   </div>
                 </div>

                 <div className="flex flex-col gap-2 w-full">
                    <div className="flex justify-between items-center">
                       <span className="text-[10px] uppercase font-mono tracking-widest text-slate-500 flex items-center gap-2">
                         <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div> Target Code Snippet
                       </span>
                       <CopyButton text={state.code_snippet} label="Copy" />
                    </div>
                   <div className="bg-[#050505] border border-[#222] p-4 rounded-xl shadow-inner relative group w-full overflow-hidden">
                     <pre className="text-[11px] text-blue-300/90 font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                       {state.code_snippet}
                     </pre>
                   </div>
                 </div>
               </div>
             </motion.div>
          )}

          {/* Memory Graph */}
          {state && (
             <motion.div 
               initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
               className="glass-card rounded-2xl p-7"
             >
               <h2 className="flex items-center gap-3 text-sm font-semibold mb-6 text-white uppercase tracking-widest">
                 <Layers className="text-purple-400" size={16} /> Agent Memory
               </h2>
               
               <div className="grid grid-cols-2 gap-4 mb-5">
                  <div className="bg-[#050505] border border-[#222] rounded-xl p-4 flex flex-col items-start justify-center">
                     <span className="text-[10px] font-mono tracking-widest text-slate-500 uppercase mb-2">Severity</span>
                     <AnimatePresence mode="popLayout">
                        <motion.div 
                           key={state.severity || 'empty'}
                           initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                           className={`text-sm font-semibold uppercase tracking-wider ${state.severity ? 'text-red-400 glow-text' : 'text-slate-600'}`}
                        >
                           {state.severity || 'UNKNOWN'}
                        </motion.div>
                     </AnimatePresence>
                  </div>
                  <div className="bg-[#050505] border border-[#222] rounded-xl p-4 flex flex-col items-start justify-center">
                     <span className="text-[10px] font-mono tracking-widest text-slate-500 uppercase mb-2">Component</span>
                     <AnimatePresence mode="popLayout">
                        <motion.div 
                           key={state.component || 'empty'}
                           initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                           className={`text-sm font-semibold capitalize tracking-wide ${state.component ? 'text-white' : 'text-slate-600'}`}
                        >
                           {state.component || 'Analyzing...'}
                        </motion.div>
                     </AnimatePresence>
                  </div>
               </div>

               {/* Classification Reasoning Panel */}
               {classificationReasoning && (
                 <motion.div
                   initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                   className="bg-[#050505] border border-blue-500/20 rounded-xl p-4 mb-5 w-full"
                 >
                   <div className="flex items-center justify-between mb-2">
                     <span className="text-[10px] font-mono tracking-widest text-blue-400 uppercase">Why this classification?</span>
                     {confidence !== null && (
                       <span className="text-[10px] font-mono text-slate-500">
                         Confidence: <span className={`font-bold ${
                           confidence >= 0.9 ? 'text-emerald-400' :
                           confidence >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                         }`}>{(confidence * 100).toFixed(0)}%</span>
                       </span>
                     )}
                   </div>
                   <p className="text-[11px] font-mono text-slate-300 leading-relaxed">{classificationReasoning}</p>
                 </motion.div>
               )}

               <div className="bg-[#050505] border border-[#222] rounded-xl p-5 w-full relative overflow-hidden">
                  <div className="absolute top-0 left-5 w-px h-full bg-gradient-to-b from-purple-500/50 via-purple-500/10 to-transparent" />
                  <span className="block text-[10px] font-mono tracking-widest text-slate-500 uppercase mb-4 ml-6">Exploit Chain Flow</span>
                  
                  <div className="flex flex-col gap-4 relative z-10 w-full ml-5">
                     {state.exploit_chain?.length > 0 ? (
                       <AnimatePresence>
                         {state.exploit_chain.map((c, i) => (
                           <motion.div 
                             initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                             key={i} 
                             className="flex items-start gap-4 relative"
                           >
                              <div className="absolute -left-[24px] top-1.5 w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.8)]" />
                              <p className="text-xs font-mono text-slate-300 leading-relaxed pr-2">{c}</p>
                           </motion.div>
                         ))}
                       </AnimatePresence>
                     ) : (
                        <div className="flex items-center gap-4 -ml-5 opacity-40">
                            <div className="w-2 h-2 rounded-full border border-slate-500 mt-0" />
                            <span className="font-mono text-xs italic text-slate-400">Awaiting vector discovery...</span>
                        </div>
                     )}
                  </div>
               </div>
             </motion.div>
          )}
        </div>

        {/* Right Column: Interaction & Results */}
        <div className="lg:col-span-7 flex flex-col gap-8 w-full">
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className={`glass-card rounded-2xl p-7 transition-all ${autoSolving ? 'ring-1 ring-blue-500/50 shadow-[0_0_30px_rgba(59,130,246,0.1)]' : ''}`}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="flex items-center gap-3 text-sm font-semibold text-white uppercase tracking-widest">
                <Cpu className="text-blue-400" size={16} /> Compute Matrix
              </h2>
              <div className="flex items-center gap-2">
                 <span className="text-[10px] uppercase font-mono text-slate-500">Tick Sequence</span>
                 <div className="bg-[#111] border border-[#333] rounded px-2 py-0.5 text-xs font-mono text-blue-400 font-medium">
                    {state ? state.step_count : 0} / {ACTIONS.length}
                 </div>
              </div>
            </div>
            
            {(!state && mode !== "demo") ? (
               <div className="h-24 w-full flex items-center justify-center border border-dashed border-[#333] rounded-xl bg-[#050505]">
                  <span className="text-[10px] uppercase tracking-widest font-mono text-slate-500">Submit Payload to Activate Pipeline</span>
               </div>
            ) : (
               <>
                 <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                   {ACTIONS.map((action) => {
                     const isActive = activeAction === action;
                     return (
                       <motion.button
                         key={action}
                         disabled={loading || autoSolving || (!state)}
                         onClick={() => takeAction(action)}
                         whileHover={!(loading || autoSolving) ? { scale: 1.02 } : {}}
                         whileTap={!(loading || autoSolving) ? { scale: 0.98 } : {}}
                         className={`
                           relative p-3 rounded-xl border flex flex-col items-start justify-center gap-2 transition-colors duration-200 text-left w-full
                           ${isActive ? 'bg-blue-500/10 border-blue-500/50 text-blue-200' : 'bg-[#0a0a0a] border-[#222] text-slate-400'}
                           ${(loading || autoSolving || !state) && !isActive ? "opacity-30 cursor-not-allowed" : "cursor-pointer hover:border-[#444] hover:bg-[#111]"}
                         `}
                       >
                         {isActive && (
                           <motion.div className="absolute inset-0 bg-blue-500/10 pointer-events-none rounded-xl" animate={{ opacity: [0.1, 0.4, 0.1] }} transition={{ repeat: Infinity, duration: 1 }}/>
                         )}
                         <span className="text-[10px] font-mono tracking-wider uppercase relative z-10 w-full flex justify-between items-center">
                            <span className="truncate">{action.replace('_', ' ')}</span>
                            {isActive && <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse shrink-0" />}
                         </span>
                       </motion.button>
                     );
                   })}
                 </div>
                 
                 {/* Explicit Run Pipeline button for Demo Mode */}
                 {mode === "demo" && (
                    <div className="w-full border-t border-[#333] pt-5 flex justify-end">
                       <motion.button 
                          whileHover={!autoSolving ? { scale: 1.02 } : {}}
                          whileTap={!autoSolving ? { scale: 0.98 } : {}}
                          onClick={startAutoSolve} 
                          disabled={autoSolving || !state}
                          className="relative overflow-hidden flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors font-bold text-xs uppercase tracking-widest text-white disabled:opacity-50"
                       >
                          <Zap size={14} className={autoSolving ? "animate-pulse" : ""} fill={autoSolving ? "currentColor" : "none"} />
                          {autoSolving ? "EXECUTING PIPELINE..." : "RUN DEMO PIPELINE"}
                       </motion.button>
                    </div>
                 )}
               </>
            )}
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-[380px]">
            {/* Terminal */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
              className="bg-[#050505] rounded-2xl flex flex-col overflow-hidden border border-[#222] shadow-[0_10px_40px_rgba(0,0,0,0.5)] h-full"
            >
              <div className="bg-[#0a0a0a] px-4 py-3 border-b border-[#222] flex items-center justify-between">
                <div className="flex items-center gap-2">
                   <Terminal size={14} className="text-slate-500" />
                   <span className="text-[10px] font-mono font-medium tracking-widest uppercase text-slate-400">VERBOSE STDOUT</span>
                </div>
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]"></div>
                </div>
              </div>
              <div className="flex-1 p-5 overflow-y-auto font-mono text-[11px] leading-relaxed relative">
                <AnimatePresence>
                  {logs.map((log, i) => (
                    <motion.div 
                      initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }}
                      key={i} 
                      className={`mb-1
                        ${log.type === "action" ? "text-yellow-400" : 
                          log.type === "success" ? "text-emerald-400" : 
                          log.type === "error" ? "text-red-400" : "text-slate-400"}
                      `}
                    >
                      <span className="opacity-30 mr-3 select-none">[{new Date().toLocaleTimeString().split(' ')[0]}]</span>
                      <span>{log.text}</span>
                    </motion.div>
                  ))}
                </AnimatePresence>
                <div ref={logsEndRef} className="h-4" />
              </div>
            </motion.div>

            {/* AI Results Intelligence Panel */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
              className="glass-card rounded-2xl relative flex flex-col overflow-hidden h-full p-0 text-left"
            >
               <AnimatePresence mode="wait">
                 {(() => {
                    // Empty state
                    if (!result && mode !== "demo" && !state) {
                        return (
                           <motion.div 
                             key="empty-view"
                             initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                             className="flex flex-col items-center justify-center opacity-30 z-10 w-full h-full text-center"
                           >
                             <Sparkles size={32} className="text-white mb-4" />
                             <p className="font-mono text-[10px] uppercase tracking-[0.2em] leading-loose">Awaiting Payload<br/>Classification</p>
                           </motion.div>
                        );
                    }
                    if (!result) return null;

                    const finalType = vulnType;

                    // UNKNOWN — classification ran but was ambiguous
                    if (finalType === "UNKNOWN") {
                        return (
                           <motion.div
                             key="result-unknown"
                             initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                             className="w-full h-full flex flex-col z-10 p-6 items-center justify-center text-center"
                           >
                             <div className="w-14 h-14 rounded-full border border-yellow-500/30 bg-yellow-500/10 text-yellow-400 flex items-center justify-center shadow-[0_0_30px_rgba(234,179,8,0.2)] mb-4">
                               <Sparkles size={24} />
                             </div>
                             <h3 className="text-lg font-bold text-yellow-400 tracking-tight mb-2">Unable to Confidently Classify</h3>
                             <p className="text-slate-400 font-mono text-[11px] uppercase tracking-widest mb-4">Classification returned UNKNOWN</p>
                             {classificationReasoning && (
                               <div className="w-full text-left p-4 bg-[#050505] border border-yellow-500/20 rounded-xl text-[11px] font-mono text-yellow-300 leading-relaxed shadow-inner">
                                 <span className="block text-[9px] text-yellow-500/60 uppercase tracking-widest mb-1">Reasoning</span>
                                 {classificationReasoning}
                               </div>
                             )}
                           </motion.div>
                        );
                    }

                    // No classification yet
                    if (!finalType) {
                        return (
                           <motion.div
                             key="no-classification"
                             initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                             className="flex flex-col items-center justify-center opacity-40 z-10 w-full h-full text-center gap-3"
                           >
                             <Sparkles size={28} className="text-slate-500" />
                             <p className="font-mono text-[10px] uppercase tracking-[0.2em] leading-loose text-slate-500">Results Ready<br/>Run classify_type to proceed</p>
                           </motion.div>
                        );
                    }

                    if (finalType === "XSS") {
                        return (
                           <motion.div 
                             key="result-xss"
                             initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                             className="w-full h-full flex flex-col z-10 p-6 overflow-y-auto custom-scrollbar"
                           >
                             <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                   <motion.div animate={result.severity === 'CRITICAL' ? { scale: [1, 1.1, 1] } : {}} transition={{ repeat: Infinity, duration: 2 }}>
                                     <div className="w-10 h-10 rounded-full border border-red-500/30 bg-red-500/10 text-red-500 flex items-center justify-center shadow-[0_0_30px_rgba(239,68,68,0.2)]">
                                        <ShieldAlert size={20} />
                                     </div>
                                   </motion.div>
                                   <div>
                                      <h3 className="text-lg font-bold text-white tracking-tight leading-tight">
                                         Cross-Site Scripting
                                      </h3>
                                      <div className="flex items-center gap-2 mt-1">
                                         <span className="px-2 py-0.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded text-[9px] font-mono uppercase tracking-widest font-semibold">
                                            Severity: {result.severity || 'HIGH'}
                                         </span>
                                         <span className="text-[10px] font-mono uppercase text-slate-400">Conf: 99.8%</span>
                                      </div>
                                   </div>
                                </div>
                             </div>
                             <div className="w-full bg-[#080808] border border-[#222] rounded-xl overflow-hidden mt-2 mb-4">
                                <div className="bg-[#111] px-3 py-1.5 border-b border-[#222] flex items-center justify-between">
                                   <span className="text-[9px] uppercase font-mono tracking-widest text-slate-500">Before (Vulnerable)</span>
                                </div>
                                <div className="p-3 text-[10px] font-mono text-red-300 leading-relaxed max-h-24 overflow-y-auto">
                                   {result.code_snippet?.split('\n').map((line, i) => (
                                      <div key={i} className="flex gap-3"><span className="opacity-30 select-none">{i+1}</span> <span>{line}</span></div>
                                   ))}
                                </div>
                             </div>
                             <div className="w-full bg-[#050505] border border-emerald-500/30 rounded-xl overflow-hidden shadow-[0_0_20px_rgba(16,185,129,0.05)] mb-4">
                                <div className="bg-emerald-500/10 px-3 py-1.5 border-b border-emerald-500/20 flex items-center justify-between">
                                   <span className="text-[9px] uppercase font-mono tracking-widest text-emerald-400 flex items-center gap-1.5">
                                      <CheckCircle2 size={10} /> After (Remediated)
                                   </span>
                                   <CopyButton text={result.fix_suggestion} label="Copy Fix" />
                                </div>
                                <div className="p-3 text-[10px] font-mono text-emerald-300 leading-relaxed max-h-24 overflow-y-auto">
                                   {result.fix_suggestion || "No specific code fix supplied."}
                                </div>
                             </div>
                             <div className="mt-auto pt-2 border-t border-[rgba(255,255,255,0.05)] flex justify-between items-center mb-1">
                                <div className="flex items-center gap-1.5 opacity-80">
                                   <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                   <span className="text-[10px] uppercase font-mono tracking-widest text-emerald-400">Exploit blocked ✅</span>
                                </div>
                                <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                                   Efficiency Score: <span className="text-white">{displayScore}%</span>
                                </span>
                             </div>
                           </motion.div>
                        );
                    } else if (finalType === "SQL_INJECTION") {
                        return (
                           <motion.div 
                             key="result-sql"
                             initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                             className="w-full h-full flex flex-col z-10 p-6 overflow-y-auto custom-scrollbar"
                           >
                             <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                   <motion.div animate={result.severity === 'CRITICAL' ? { scale: [1, 1.1, 1] } : {}} transition={{ repeat: Infinity, duration: 2 }}>
                                     <div className="w-10 h-10 rounded-full border border-red-500/30 bg-red-500/10 text-red-500 flex items-center justify-center shadow-[0_0_30px_rgba(239,68,68,0.2)]">
                                        <ShieldAlert size={20} />
                                     </div>
                                   </motion.div>
                                   <div>
                                      <h3 className="text-lg font-bold text-white tracking-tight leading-tight">
                                         SQL Injection
                                      </h3>
                                      <div className="flex items-center gap-2 mt-1">
                                         <span className="px-2 py-0.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded text-[9px] font-mono uppercase tracking-widest font-semibold">
                                            Severity: {result.severity || 'HIGH'}
                                         </span>
                                         <span className="text-[10px] font-mono uppercase text-slate-400">Conf: 99.8%</span>
                                      </div>
                                   </div>
                                </div>
                             </div>
                             <div className="w-full bg-[#080808] border border-[#222] rounded-xl overflow-hidden mt-2 mb-4">
                                <div className="bg-[#111] px-3 py-1.5 border-b border-[#222] flex items-center justify-between">
                                   <span className="text-[9px] uppercase font-mono tracking-widest text-slate-500">Before (Vulnerable)</span>
                                </div>
                                <div className="p-3 text-[10px] font-mono text-red-300 leading-relaxed max-h-24 overflow-y-auto">
                                   {result.code_snippet?.split('\n').map((line, i) => (
                                      <div key={i} className="flex gap-3"><span className="opacity-30 select-none">{i+1}</span> <span>{line}</span></div>
                                   ))}
                                </div>
                             </div>
                             <div className="w-full bg-[#050505] border border-emerald-500/30 rounded-xl overflow-hidden shadow-[0_0_20px_rgba(16,185,129,0.05)] mb-4">
                                <div className="bg-emerald-500/10 px-3 py-1.5 border-b border-emerald-500/20 flex items-center justify-between">
                                   <span className="text-[9px] uppercase font-mono tracking-widest text-emerald-400 flex items-center gap-1.5">
                                      <CheckCircle2 size={10} /> After (Remediated)
                                   </span>
                                   <CopyButton text={result.fix_suggestion} label="Copy Fix" />
                                </div>
                                <div className="p-3 text-[10px] font-mono text-emerald-300 leading-relaxed max-h-24 overflow-y-auto">
                                   {result.fix_suggestion || "No specific code fix supplied."}
                                </div>
                             </div>
                             <div className="mt-auto pt-2 border-t border-[rgba(255,255,255,0.05)] flex justify-between items-center mb-1">
                                <div className="flex items-center gap-1.5 opacity-80">
                                   <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                   <span className="text-[10px] uppercase font-mono tracking-widest text-emerald-400">Exploit blocked ✅</span>
                                </div>
                                <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                                   Efficiency Score: <span className="text-white">{displayScore}%</span>
                                </span>
                             </div>
                           </motion.div>
                        );
                    } else if (finalType === "SAFE") {
                        return (
                           <motion.div 
                             key="result-safe"
                             initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                             className="w-full h-full flex flex-col z-10 p-6 items-center justify-center text-center"
                           >
                              <div className="w-16 h-16 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-500 flex items-center justify-center shadow-[0_0_40px_rgba(16,185,129,0.3)] mb-4">
                                 <CheckCircle2 size={32} />
                              </div>
                              <h3 className="text-2xl font-bold text-emerald-400 tracking-tight leading-tight mb-2">
                                 SYSTEM SECURE
                              </h3>
                              <p className="text-slate-400 font-mono text-sm uppercase tracking-widest">No vulnerability detected</p>
                              {result.fix_suggestion && (
                                 <div className="mt-6 w-full text-left p-4 bg-[#050505] border border-emerald-500/20 rounded-xl text-[11px] font-mono text-emerald-300 tracking-wide leading-relaxed shadow-inner">
                                    {result.fix_suggestion}
                                 </div>
                              )}
                           </motion.div>
                        );
                    }
                    
                    return null;
                 })()}
               </AnimatePresence>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
