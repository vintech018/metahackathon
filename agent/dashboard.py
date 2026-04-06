"""
Explainability Dashboard — Real-time web UI for the triage agent.

Serves a rich, interactive dashboard showing:
    • Training progress (reward curves, accuracy)
    • Episode-by-episode breakdown
    • Reasoning chain visualization
    • Reward component analysis
    • Reflection memory and learned patterns
    • Live inference mode
"""

from __future__ import annotations

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves the dashboard and API endpoints."""

    agent_data_dir: Path = Path("agent_data")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self._serve_dashboard()
        elif parsed.path == "/api/metrics":
            self._serve_json(self._load_json("training_metrics.json"))
        elif parsed.path == "/api/experiences":
            self._serve_json(self._load_json("experience_buffer.json"))
        elif parsed.path == "/api/memory":
            self._serve_json(self._load_json("reflection_memory.json"))
        elif parsed.path == "/api/summary":
            self._serve_json(self._build_summary())
        else:
            self.send_error(404)

    def _load_json(self, filename: str) -> Any:
        path = self.agent_data_dir / filename
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _build_summary(self) -> dict:
        metrics = self._load_json("training_metrics.json")
        experiences = self._load_json("experience_buffer.json")
        memory = self._load_json("reflection_memory.json")

        if not metrics:
            return {"status": "no_data"}

        rewards = [m["reward"] for m in metrics]
        return {
            "total_episodes": len(metrics),
            "mean_reward": round(sum(rewards) / len(rewards), 4) if rewards else 0,
            "max_reward": round(max(rewards), 4) if rewards else 0,
            "min_reward": round(min(rewards), 4) if rewards else 0,
            "severity_accuracy": round(
                sum(1 for m in metrics if m.get("severity_correct")) / len(metrics), 4
            ) if metrics else 0,
            "component_accuracy": round(
                sum(1 for m in metrics if m.get("component_correct")) / len(metrics), 4
            ) if metrics else 0,
            "total_tokens": sum(m.get("tokens_used", 0) for m in metrics),
            "buffer_size": len(experiences) if isinstance(experiences, list) else 0,
            "reflection_count": len(memory.get("entries", [])) if isinstance(memory, dict) else 0,
            "patterns": memory.get("patterns", []) if isinstance(memory, dict) else [],
        }

    def _serve_json(self, data: Any) -> None:
        body = json.dumps(data, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_dashboard(self) -> None:
        html = DASHBOARD_HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, fmt, *args):
        pass  # Suppress default logging


def run_dashboard(port: int = 8080, data_dir: str = "agent_data") -> None:
    DashboardHandler.agent_data_dir = Path(data_dir)
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"🛡️  Dashboard running at http://localhost:{port}")
    print(f"   Data dir: {data_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        server.server_close()


# ─────────────────────────────────────────────────────────────────────────────
#  Dashboard HTML (self-contained)
# ─────────────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Vulnerability Triage — Explainability Dashboard</title>
<meta name="description" content="Real-time monitoring dashboard for the AI vulnerability triage agent with RL training metrics and explainability.">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg-primary: #0a0e1a;
  --bg-secondary: #111827;
  --bg-tertiary: #1a2235;
  --bg-card: #1e2a3e;
  --bg-card-hover: #243049;
  --text-primary: #e8edf5;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent-cyan: #22d3ee;
  --accent-blue: #3b82f6;
  --accent-purple: #a855f7;
  --accent-green: #10b981;
  --accent-yellow: #f59e0b;
  --accent-red: #ef4444;
  --accent-orange: #f97316;
  --gradient-1: linear-gradient(135deg, #22d3ee 0%, #3b82f6 50%, #a855f7 100%);
  --gradient-2: linear-gradient(135deg, #10b981 0%, #22d3ee 100%);
  --gradient-3: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
  --border: rgba(148, 163, 184, 0.08);
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 20px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 40px rgba(0,0,0,0.5);
  --radius: 16px;
  --radius-sm: 10px;
}

* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: 'Inter', -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── Animated background ─────── */
body::before {
  content: '';
  position: fixed;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(ellipse at 20% 50%, rgba(34,211,238,0.03) 0%, transparent 50%),
              radial-gradient(ellipse at 80% 20%, rgba(168,85,247,0.03) 0%, transparent 50%),
              radial-gradient(ellipse at 50% 80%, rgba(59,130,246,0.02) 0%, transparent 50%);
  animation: float 20s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  33% { transform: translate(30px, -30px) rotate(1deg); }
  66% { transform: translate(-20px, 20px) rotate(-1deg); }
}

/* ── Header ─────── */
.header {
  position: relative;
  z-index: 10;
  padding: 28px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(20px);
  background: rgba(10,14,26,0.8);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.logo {
  width: 48px;
  height: 48px;
  background: var(--gradient-1);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 4px 16px rgba(34,211,238,0.3);
}
.header h1 {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.header h1 span {
  background: var(--gradient-1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.3);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  color: var(--accent-green);
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-green);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
  50% { opacity: 0.8; box-shadow: 0 0 0 6px rgba(16,185,129,0); }
}
.refresh-btn {
  padding: 8px 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  border-radius: 100px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  transition: all 0.2s;
}
.refresh-btn:hover {
  background: var(--bg-card);
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

/* ── Main Layout ─────── */
.main {
  position: relative;
  z-index: 1;
  max-width: 1600px;
  margin: 0 auto;
  padding: 32px 40px;
}

/* ── Stat Cards ─────── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
}
.stat-card:hover {
  transform: translateY(-2px);
  border-color: rgba(34,211,238,0.2);
  box-shadow: var(--shadow-md);
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}
.stat-card:nth-child(1)::before { background: var(--gradient-1); }
.stat-card:nth-child(2)::before { background: var(--gradient-2); }
.stat-card:nth-child(3)::before { background: var(--gradient-3); }
.stat-card:nth-child(4)::before { background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); }
.stat-card:nth-child(5)::before { background: linear-gradient(135deg, var(--accent-green), var(--accent-yellow)); }
.stat-card:nth-child(6)::before { background: linear-gradient(135deg, var(--accent-orange), var(--accent-red)); }
.stat-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  margin-bottom: 8px;
  font-weight: 600;
}
.stat-value {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -1px;
  line-height: 1.1;
}
.stat-sub {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 6px;
}

/* ── Section Grid ─────── */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 32px;
}
.grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 24px;
  margin-bottom: 32px;
}
@media (max-width: 1200px) {
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
}

/* ── Panels ─────── */
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.panel-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
}
.panel-header h2 {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.3px;
}
.panel-body {
  padding: 24px;
}
.panel-body canvas {
  max-height: 300px;
}

/* ── Episode Table ─────── */
.episode-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.episode-table th {
  text-align: left;
  padding: 10px 12px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text-muted);
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--bg-card);
}
.episode-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
}
.episode-table tr:hover td {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}
.scrollable {
  max-height: 400px;
  overflow-y: auto;
}
.scrollable::-webkit-scrollbar { width: 6px; }
.scrollable::-webkit-scrollbar-track { background: transparent; }
.scrollable::-webkit-scrollbar-thumb {
  background: var(--text-muted);
  border-radius: 3px;
}

/* ── Tags & Badges ─────── */
.tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.tag-critical { background: rgba(239,68,68,0.15); color: #f87171; }
.tag-high { background: rgba(249,115,22,0.15); color: #fb923c; }
.tag-medium { background: rgba(245,158,11,0.15); color: #fbbf24; }
.tag-low { background: rgba(16,185,129,0.15); color: #34d399; }
.tag-correct { background: rgba(16,185,129,0.15); color: #34d399; }
.tag-wrong { background: rgba(239,68,68,0.15); color: #f87171; }
.tag-explore { background: rgba(245,158,11,0.15); color: #fbbf24; }
.tag-exploit { background: rgba(59,130,246,0.15); color: #60a5fa; }

/* ── Pattern List ─────── */
.pattern-list {
  list-style: none;
}
.pattern-item {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: flex-start;
  gap: 10px;
  transition: background 0.2s;
}
.pattern-item:hover {
  background: var(--bg-card-hover);
}
.pattern-icon {
  color: var(--accent-purple);
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}
.no-data {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}
.no-data-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}
.no-data p {
  font-size: 14px;
}

/* ── Reward Breakdown ─────── */
.breakdown-bar {
  display: flex;
  height: 24px;
  border-radius: 12px;
  overflow: hidden;
  margin: 8px 0;
  background: var(--bg-primary);
}
.breakdown-segment {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: white;
  transition: width 0.5s ease;
}
.breakdown-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

/* ── Animations ─────── */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-in {
  animation: fadeIn 0.5s ease-out forwards;
}
.stat-card:nth-child(1) { animation-delay: 0ms; }
.stat-card:nth-child(2) { animation-delay: 50ms; }
.stat-card:nth-child(3) { animation-delay: 100ms; }
.stat-card:nth-child(4) { animation-delay: 150ms; }
.stat-card:nth-child(5) { animation-delay: 200ms; }
.stat-card:nth-child(6) { animation-delay: 250ms; }
</style>
</head>
<body>

<header class="header">
  <div class="header-left">
    <div class="logo">🛡️</div>
    <h1>AI Vulnerability <span>Triage</span></h1>
  </div>
  <div class="header-right">
    <div class="status-badge">
      <div class="status-dot"></div>
      <span id="status-text">Loading...</span>
    </div>
    <button class="refresh-btn" onclick="loadAll()">↻ Refresh</button>
  </div>
</header>

<main class="main">
  <!-- Stats Cards -->
  <div id="stats-grid" class="stats-grid"></div>

  <!-- Charts Row -->
  <div class="grid-2">
    <div class="panel animate-in">
      <div class="panel-header">
        <span>📈</span>
        <h2>Reward Curve</h2>
      </div>
      <div class="panel-body">
        <canvas id="rewardChart"></canvas>
      </div>
    </div>
    <div class="panel animate-in">
      <div class="panel-header">
        <span>🎯</span>
        <h2>Accuracy Over Time</h2>
      </div>
      <div class="panel-body">
        <canvas id="accuracyChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Reward Breakdown + Difficulty Analysis -->
  <div class="grid-2">
    <div class="panel animate-in">
      <div class="panel-header">
        <span>🔬</span>
        <h2>Reward Component Breakdown (Latest)</h2>
      </div>
      <div class="panel-body" id="reward-breakdown"></div>
    </div>
    <div class="panel animate-in">
      <div class="panel-header">
        <span>📊</span>
        <h2>Performance by Difficulty</h2>
      </div>
      <div class="panel-body">
        <canvas id="difficultyChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Episode History + Patterns -->
  <div class="grid-2">
    <div class="panel animate-in">
      <div class="panel-header">
        <span>📋</span>
        <h2>Episode History</h2>
      </div>
      <div class="scrollable">
        <table class="episode-table" id="episode-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Task</th>
              <th>Diff</th>
              <th>Reward</th>
              <th>Severity</th>
              <th>Component</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
    <div class="panel animate-in">
      <div class="panel-header">
        <span>🧠</span>
        <h2>Learned Patterns (Reflection Memory)</h2>
      </div>
      <div class="scrollable" id="patterns-list"></div>
    </div>
  </div>
</main>

<script>
let rewardChart, accuracyChart, difficultyChart;

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    return await res.json();
  } catch {
    return null;
  }
}

async function loadAll() {
  const [summary, metrics, experiences, memory] = await Promise.all([
    fetchJSON('/api/summary'),
    fetchJSON('/api/metrics'),
    fetchJSON('/api/experiences'),
    fetchJSON('/api/memory'),
  ]);

  if (!summary || summary.status === 'no_data') {
    document.getElementById('status-text').textContent = 'No Data Yet';
    renderNoData();
    return;
  }

  document.getElementById('status-text').textContent =
    `${summary.total_episodes} Episodes`;

  renderStats(summary);
  renderRewardChart(metrics);
  renderAccuracyChart(metrics);
  renderDifficultyChart(metrics);
  renderEpisodeTable(metrics);
  renderRewardBreakdown(experiences);
  renderPatterns(memory);
}

function renderNoData() {
  document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card animate-in" style="grid-column: 1/-1;">
      <div class="no-data">
        <div class="no-data-icon">🛡️</div>
        <p>No training data yet. Run the agent to see results.</p>
        <p style="margin-top:8px; font-family: 'JetBrains Mono'; font-size:12px; color:var(--accent-cyan)">
          python run_training.py --episodes 20
        </p>
      </div>
    </div>
  `;
}

function renderStats(s) {
  const cards = [
    { label: 'Episodes', value: s.total_episodes, sub: 'training runs' },
    { label: 'Mean Reward', value: s.mean_reward.toFixed(3), sub: `max: ${s.max_reward.toFixed(3)}` },
    { label: 'Severity Acc', value: (s.severity_accuracy * 100).toFixed(1) + '%', sub: 'classification' },
    { label: 'Component Acc', value: (s.component_accuracy * 100).toFixed(1) + '%', sub: 'identification' },
    { label: 'Reflections', value: s.reflection_count, sub: `${s.patterns.length} patterns` },
    { label: 'Tokens Used', value: s.total_tokens.toLocaleString(), sub: 'LLM compute' },
  ];
  document.getElementById('stats-grid').innerHTML = cards.map(c => `
    <div class="stat-card animate-in">
      <div class="stat-label">${c.label}</div>
      <div class="stat-value">${c.value}</div>
      <div class="stat-sub">${c.sub}</div>
    </div>
  `).join('');
}

function renderRewardChart(metrics) {
  if (!metrics?.length) return;
  const ctx = document.getElementById('rewardChart').getContext('2d');
  if (rewardChart) rewardChart.destroy();

  const rewards = metrics.map(m => m.reward);
  const episodes = metrics.map(m => m.episode);

  // Compute running average
  const window = 5;
  const avg = rewards.map((_, i) => {
    const start = Math.max(0, i - window + 1);
    const slice = rewards.slice(start, i + 1);
    return slice.reduce((a, b) => a + b, 0) / slice.length;
  });

  rewardChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: episodes,
      datasets: [
        {
          label: 'Reward',
          data: rewards,
          borderColor: 'rgba(34,211,238,0.4)',
          backgroundColor: 'rgba(34,211,238,0.05)',
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: rewards.map(r =>
            r >= 0.9 ? '#10b981' : r >= 0.6 ? '#f59e0b' : '#ef4444'
          ),
          tension: 0.3,
        },
        {
          label: 'Running Avg',
          data: avg,
          borderColor: '#a855f7',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          tension: 0.4,
        }
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } }
      },
      scales: {
        y: {
          min: 0, max: 1.1,
          grid: { color: 'rgba(148,163,184,0.06)' },
          ticks: { color: '#64748b', font: { family: 'Inter' } }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { family: 'Inter' } }
        }
      }
    }
  });
}

function renderAccuracyChart(metrics) {
  if (!metrics?.length) return;
  const ctx = document.getElementById('accuracyChart').getContext('2d');
  if (accuracyChart) accuracyChart.destroy();

  const window = 5;
  const episodes = metrics.map(m => m.episode);

  const sevAcc = metrics.map((_, i) => {
    const start = Math.max(0, i - window + 1);
    const slice = metrics.slice(start, i + 1);
    return slice.filter(m => m.severity_correct).length / slice.length;
  });
  const compAcc = metrics.map((_, i) => {
    const start = Math.max(0, i - window + 1);
    const slice = metrics.slice(start, i + 1);
    return slice.filter(m => m.component_correct).length / slice.length;
  });

  accuracyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: episodes,
      datasets: [
        {
          label: 'Severity Accuracy',
          data: sevAcc,
          borderColor: '#22d3ee',
          backgroundColor: 'rgba(34,211,238,0.05)',
          fill: true,
          tension: 0.4,
          pointRadius: 0,
        },
        {
          label: 'Component Accuracy',
          data: compAcc,
          borderColor: '#a855f7',
          backgroundColor: 'rgba(168,85,247,0.05)',
          fill: true,
          tension: 0.4,
          pointRadius: 0,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } }
      },
      scales: {
        y: {
          min: 0, max: 1.05,
          grid: { color: 'rgba(148,163,184,0.06)' },
          ticks: {
            color: '#64748b',
            font: { family: 'Inter' },
            callback: v => (v * 100).toFixed(0) + '%'
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { family: 'Inter' } }
        }
      }
    }
  });
}

function renderDifficultyChart(metrics) {
  if (!metrics?.length) return;
  const ctx = document.getElementById('difficultyChart').getContext('2d');
  if (difficultyChart) difficultyChart.destroy();

  const byDiff = {};
  metrics.forEach(m => {
    if (!byDiff[m.difficulty]) byDiff[m.difficulty] = [];
    byDiff[m.difficulty].push(m.reward);
  });

  const labels = Object.keys(byDiff);
  const avgs = labels.map(d => byDiff[d].reduce((a, b) => a + b, 0) / byDiff[d].length);
  const counts = labels.map(d => byDiff[d].length);
  const colors = { easy: '#10b981', medium: '#f59e0b', hard: '#ef4444' };

  difficultyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
      datasets: [{
        label: 'Avg Reward',
        data: avgs,
        backgroundColor: labels.map(l => colors[l] || '#3b82f6'),
        borderRadius: 8,
        barPercentage: 0.6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => `Count: ${counts[ctx.dataIndex]}`
          }
        }
      },
      scales: {
        y: {
          min: 0, max: 1.1,
          grid: { color: 'rgba(148,163,184,0.06)' },
          ticks: { color: '#64748b' }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { weight: 600 } }
        }
      }
    }
  });
}

function renderEpisodeTable(metrics) {
  if (!metrics?.length) return;
  const tbody = document.querySelector('#episode-table tbody');
  tbody.innerHTML = metrics.slice().reverse().slice(0, 50).map(m => `
    <tr>
      <td>${m.episode}</td>
      <td style="font-family:'JetBrains Mono';font-size:11px">${m.task_id}</td>
      <td><span class="tag tag-${m.difficulty === 'hard' ? 'critical' : m.difficulty === 'medium' ? 'medium' : 'low'}">${m.difficulty}</span></td>
      <td style="font-weight:600;color:${m.reward >= 0.9 ? '#10b981' : m.reward >= 0.6 ? '#f59e0b' : '#ef4444'}">${m.reward.toFixed(3)}</td>
      <td><span class="tag tag-${m.severity_correct ? 'correct' : 'wrong'}">${m.severity_correct ? '✓' : '✗'}</span></td>
      <td><span class="tag tag-${m.component_correct ? 'correct' : 'wrong'}">${m.component_correct ? '✓' : '✗'}</span></td>
      <td><span class="tag tag-${m.was_exploration ? 'explore' : 'exploit'}">${m.was_exploration ? 'explore' : 'exploit'}</span></td>
    </tr>
  `).join('');
}

function renderRewardBreakdown(experiences) {
  const container = document.getElementById('reward-breakdown');
  if (!experiences?.length) {
    container.innerHTML = '<div class="no-data"><p>No experience data yet</p></div>';
    return;
  }

  const latest = experiences[experiences.length - 1];
  const info = latest.info || {};
  const explanation = info.explanation || {};

  const segments = [
    { label: 'Severity', value: explanation.severity_score || 0, color: '#22d3ee', max: 0.4 },
    { label: 'Component', value: explanation.component_score || 0, color: '#a855f7', max: 0.3 },
    { label: 'Remediation', value: explanation.remediation_score || 0, color: '#10b981', max: 0.3 },
    { label: 'Bonus', value: explanation.bonus_score || 0, color: '#f59e0b', max: 0.4 },
  ];

  const total = segments.reduce((s, seg) => s + seg.value, 0);

  container.innerHTML = `
    <div style="margin-bottom:16px; font-size:13px; color:var(--text-secondary);">
      Task: <strong style="color:var(--text-primary)">${latest.task_id || '?'}</strong> |
      Total Reward: <strong style="color:${latest.reward >= 0.8 ? '#10b981' : latest.reward >= 0.5 ? '#f59e0b' : '#ef4444'}">${(latest.reward || 0).toFixed(4)}</strong>
    </div>
    <div class="breakdown-bar">
      ${segments.map(s => {
        const pct = total > 0 ? (s.value / Math.max(total, 1)) * 100 : 0;
        return pct > 3
          ? `<div class="breakdown-segment" style="width:${pct}%;background:${s.color}">${s.value.toFixed(2)}</div>`
          : `<div class="breakdown-segment" style="width:${pct}%;background:${s.color}"></div>`;
      }).join('')}
    </div>
    <div class="breakdown-legend">
      ${segments.map(s => `
        <div class="legend-item">
          <div class="legend-dot" style="background:${s.color}"></div>
          ${s.label}: ${s.value.toFixed(3)} / ${s.max}
        </div>
      `).join('')}
    </div>
    <div style="margin-top:20px;">
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">Agent Decision</div>
      <div style="display:flex;gap:8px;">
        <span class="tag tag-${latest.action?.severity || 'medium'}">${latest.action?.severity || '?'}</span>
        <span class="tag" style="background:rgba(59,130,246,0.15);color:#60a5fa">${latest.action?.component || '?'}</span>
      </div>
      <div style="margin-top:12px;font-size:12px;color:var(--text-secondary);max-height:80px;overflow-y:auto;">
        ${(latest.action?.remediation || 'N/A').substring(0, 300)}
      </div>
    </div>
  `;
}

function renderPatterns(memory) {
  const container = document.getElementById('patterns-list');
  const patterns = memory?.patterns || [];

  if (!patterns.length) {
    container.innerHTML = `
      <div class="no-data">
        <div class="no-data-icon">🧠</div>
        <p>No patterns learned yet.<br>Low-scoring episodes trigger reflection.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `<ul class="pattern-list">
    ${patterns.map((p, i) => `
      <li class="pattern-item">
        <span class="pattern-icon">💡</span>
        <span>${p}</span>
      </li>
    `).join('')}
  </ul>`;
}

// Auto-refresh every 10 seconds
loadAll();
setInterval(loadAll, 10000);
</script>

</body>
</html>
"""
