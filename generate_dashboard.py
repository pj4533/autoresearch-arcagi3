#!/usr/bin/env python3
"""
Generate a static HTML dashboard from experiments/log.md.

Usage:
    uv run python generate_dashboard.py
    uv run python generate_dashboard.py --log experiments/log.md --output experiments/dashboard.html
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def parse_log(log_path: str) -> list[dict]:
    """Parse experiments/log.md markdown table into list of dicts."""
    path = Path(log_path)
    if not path.exists():
        return []

    text = path.read_text()
    experiments = []

    # Find table rows (skip header and separator)
    lines = text.strip().split("\n")
    in_table = False
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            in_table = False
            continue

        # Skip header row
        if "Exp" in line and "Description" in line:
            in_table = True
            continue
        # Skip separator
        if re.match(r"^\|[\s\-|]+\|$", line):
            continue
        if not in_table:
            continue

        cells = [c.strip() for c in line.split("|")]
        # Remove empty first/last from leading/trailing |
        cells = [c for c in cells if c != ""]

        if len(cells) < 10:
            continue

        try:
            exp = {
                "id": cells[0].strip(),
                "idea": cells[1].strip(),
                "description": cells[2].strip(),
                "avg_score": float(cells[3]) if cells[3].strip() else 0.0,
                "actions": int(cells[4]) if cells[4].strip() else 0,
                "ls20": float(cells[5]) if cells[5].strip() else 0.0,
                "ft09": float(cells[6]) if cells[6].strip() else 0.0,
                "vc33": float(cells[7]) if cells[7].strip() else 0.0,
                "duration": cells[8].strip(),
                "status": cells[9].strip().lower(),
                "notes": cells[10].strip() if len(cells) > 10 else "",
            }
            experiments.append(exp)
        except (ValueError, IndexError):
            continue

    return experiments


def build_data(experiments: list[dict]) -> dict:
    """Build dashboard data from parsed experiments."""
    completed = [e for e in experiments if e["status"] in ("baseline", "improved", "reverted")]
    improved = [e for e in experiments if e["status"] == "improved"]
    reverted = [e for e in experiments if e["status"] == "reverted"]
    baselines = [e for e in experiments if e["status"] == "baseline"]

    best_score = 0.0
    best_exp = "none"
    running_best = []
    current_best = 0.0

    for e in experiments:
        if e["status"] in ("baseline", "improved"):
            if e["avg_score"] > current_best:
                current_best = e["avg_score"]
                best_score = e["avg_score"]
                best_exp = e["id"]
        running_best.append(current_best)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(experiments),
            "completed": len(completed),
            "improved": len(improved),
            "reverted": len(reverted),
            "baselines": len(baselines),
            "best_score": best_score,
            "best_experiment": best_exp,
        },
        "experiments": experiments,
        "running_best": running_best,
    }


def generate_html(data: dict) -> str:
    """Generate self-contained HTML dashboard."""
    summary = data["summary"]
    experiments = data["experiments"]
    running_best = data["running_best"]
    generated_at = data["generated_at"]

    # Build chart data
    exp_ids = [e["id"] for e in experiments]
    scores = [e["avg_score"] for e in experiments]
    statuses = [e["status"] for e in experiments]
    actions = [e["actions"] for e in experiments]
    descriptions = [e["description"][:60] for e in experiments]
    hypotheses = [f"{e['id']}: {e['description'][:80]}" for e in experiments]

    # Color map
    color_map = {
        "improved": "#22c55e",
        "reverted": "#ef4444",
        "baseline": "#3b82f6",
        "neutral": "#64748b",
        "failed": "#374151",
    }
    colors = [color_map.get(s, "#64748b") for s in statuses]

    # Status strip colors
    strip_colors = colors[:]

    # JSON-encode for embedding
    data_json = json.dumps({
        "exp_ids": exp_ids,
        "scores": scores,
        "statuses": statuses,
        "actions": actions,
        "descriptions": descriptions,
        "hypotheses": hypotheses,
        "colors": colors,
        "strip_colors": strip_colors,
        "running_best": running_best,
        "experiments": experiments,
        "summary": summary,
        "generated_at": generated_at,
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARC-AGI-3 Autoresearch</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-deep: #0f172a;
    --bg-card: #1e293b;
    --bg-card-hover: #253349;
    --border: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-green: #22c55e;
    --accent-red: #ef4444;
    --accent-blue: #3b82f6;
    --accent-amber: #fbbf24;
    --accent-violet: #a78bfa;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: var(--bg-deep);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    min-height: 100vh;
  }}

  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-card);
  }}

  .header h1 {{
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }}

  .header-right {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .tabs {{
    display: flex;
    gap: 4px;
    background: var(--bg-deep);
    border-radius: 8px;
    padding: 3px;
  }}

  .tab {{
    padding: 6px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    transition: all 0.15s;
    border: none;
    background: none;
    font-family: inherit;
  }}

  .tab:hover {{ color: var(--text-primary); }}
  .tab.active {{
    background: var(--bg-card);
    color: var(--text-primary);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }}

  .timer {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-muted);
  }}

  .live-dot {{
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-green);
    margin-right: 4px;
    animation: pulse 2s infinite;
  }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
  }}

  .content {{ padding: 20px 24px; }}

  .stats {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }}

  .stat-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }}

  .stat-value {{
    font-size: 28px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.02em;
  }}

  .stat-label {{
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .stat-value.green {{ color: var(--accent-green); }}
  .stat-value.red {{ color: var(--accent-red); }}
  .stat-value.blue {{ color: var(--accent-blue); }}
  .stat-value.amber {{ color: var(--accent-amber); }}

  .chart-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
  }}

  .chart-title {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
  }}

  .bottom-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}

  .activity-list {{
    list-style: none;
  }}

  .activity-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }}

  .activity-item:last-child {{ border-bottom: none; }}

  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
  }}

  .badge-improved {{ background: rgba(34,197,94,0.15); color: var(--accent-green); }}
  .badge-reverted {{ background: rgba(239,68,68,0.15); color: var(--accent-red); }}
  .badge-baseline {{ background: rgba(59,130,246,0.15); color: var(--accent-blue); }}
  .badge-neutral {{ background: rgba(100,116,139,0.15); color: var(--text-muted); }}

  /* Detail view */
  .detail-layout {{
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 16px;
    height: calc(100vh - 180px);
  }}

  .exp-list {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow-y: auto;
  }}

  .exp-list-item {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.1s;
    font-size: 13px;
  }}

  .exp-list-item:hover {{ background: var(--bg-card-hover); }}
  .exp-list-item.selected {{ background: var(--bg-card-hover); border-left: 3px solid var(--accent-blue); }}

  .exp-list-item .exp-id {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 12px;
  }}

  .exp-list-item .exp-desc {{
    color: var(--text-secondary);
    font-size: 12px;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .exp-list-header {{
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .detail-panel {{
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
  }}

  .detail-section {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }}

  .detail-section h3 {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
  }}

  .detail-row {{
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(51,65,85,0.5);
    font-size: 13px;
  }}

  .detail-row:last-child {{ border-bottom: none; }}
  .detail-label {{ color: var(--text-secondary); }}
  .detail-value {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}

  .game-charts {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }}

  .view {{ display: none; }}
  .view.active {{ display: block; }}

  .empty-state {{
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
  }}

  .empty-state h2 {{
    font-size: 16px;
    margin-bottom: 8px;
    color: var(--text-secondary);
  }}
</style>
</head>
<body>

<div class="header">
  <h1>ARC-AGI-3 Autoresearch</h1>
  <div class="header-right">
    <div class="tabs">
      <button class="tab active" onclick="switchView('progress')">Progress</button>
      <button class="tab" onclick="switchView('details')">Details</button>
    </div>
    <div class="timer"><span class="live-dot"></span><span id="countdown">30</span>s</div>
  </div>
</div>

<div class="content">
  <!-- Progress View -->
  <div id="progress-view" class="view active">
    <div class="stats">
      <div class="stat-card">
        <div class="stat-value" id="stat-total">0</div>
        <div class="stat-label">Total Experiments</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-completed">0</div>
        <div class="stat-label">Completed</div>
      </div>
      <div class="stat-card">
        <div class="stat-value green" id="stat-improved">0</div>
        <div class="stat-label">Improved</div>
      </div>
      <div class="stat-card">
        <div class="stat-value red" id="stat-reverted">0</div>
        <div class="stat-label">Reverted</div>
      </div>
      <div class="stat-card">
        <div class="stat-value amber" id="stat-best">0.000</div>
        <div class="stat-label">Best Score</div>
      </div>
    </div>

    <div class="chart-card">
      <div class="chart-title">Score Timeline</div>
      <div id="score-chart"></div>
    </div>

    <div class="chart-card">
      <div class="chart-title">Experiment Status</div>
      <div id="status-strip"></div>
    </div>

    <div class="bottom-grid">
      <div class="chart-card">
        <div class="chart-title">Recent Experiments</div>
        <ul class="activity-list" id="recent-list"></ul>
      </div>
      <div class="chart-card">
        <div class="chart-title">Actions Per Experiment</div>
        <div id="actions-chart"></div>
      </div>
    </div>
  </div>

  <!-- Details View -->
  <div id="details-view" class="view">
    <div class="detail-layout">
      <div class="exp-list" id="exp-list">
        <div class="exp-list-header">Experiments</div>
      </div>
      <div class="detail-panel" id="detail-panel">
        <div class="empty-state">
          <h2>Select an experiment</h2>
          <p>Click an experiment on the left to view details</p>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const DATA = {data_json};

let countdown = 30;
let selectedExp = null;

// --- Render functions ---

function renderStats(d) {{
  document.getElementById('stat-total').textContent = d.summary.total;
  document.getElementById('stat-completed').textContent = d.summary.completed;
  document.getElementById('stat-improved').textContent = d.summary.improved;
  document.getElementById('stat-reverted').textContent = d.summary.reverted;
  document.getElementById('stat-best').textContent = d.summary.best_score.toFixed(4);
}}

function renderScoreChart(d) {{
  if (d.exp_ids.length === 0) {{
    document.getElementById('score-chart').innerHTML = '<div class="empty-state"><p>No experiments yet</p></div>';
    return;
  }}

  const traces = [];

  // Main score line (completed experiments only)
  const completedIdx = d.statuses.map((s, i) => ['baseline', 'improved', 'reverted', 'neutral'].includes(s) ? i : -1).filter(i => i >= 0);
  const completedIds = completedIdx.map(i => d.exp_ids[i]);
  const completedScores = completedIdx.map(i => d.scores[i]);
  const completedColors = completedIdx.map(i => d.colors[i]);
  const completedHover = completedIdx.map(i => d.hypotheses[i]);

  traces.push({{
    x: completedIds,
    y: completedScores,
    mode: 'lines+markers',
    type: 'scatter',
    name: 'Score',
    line: {{ color: '#38bdf8', width: 2 }},
    marker: {{
      color: completedColors,
      size: 10,
      line: {{ color: '#0f172a', width: 2 }}
    }},
    text: completedHover,
    hovertemplate: '%{{text}}<br>Score: %{{y:.4f}}<extra></extra>',
  }});

  // Running best line
  if (d.running_best.length > 0) {{
    const bestIds = completedIdx.map(i => d.exp_ids[i]);
    const bestVals = completedIdx.map(i => d.running_best[i]);
    traces.push({{
      x: bestIds,
      y: bestVals,
      mode: 'lines',
      type: 'scatter',
      name: 'Best',
      line: {{ color: '#fbbf24', width: 2, dash: 'dot' }},
      hoverinfo: 'skip',
    }});
  }}

  Plotly.react('score-chart', traces, {{
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: '#1e293b',
    height: 350,
    margin: {{ l: 50, r: 20, t: 10, b: 50 }},
    xaxis: {{
      gridcolor: '#334155',
      tickfont: {{ family: 'JetBrains Mono', size: 10, color: '#94a3b8' }},
      tickangle: -45,
    }},
    yaxis: {{
      title: {{ text: 'Avg Score', font: {{ size: 12, color: '#94a3b8' }} }},
      gridcolor: '#334155',
      tickfont: {{ family: 'JetBrains Mono', size: 10, color: '#94a3b8' }},
      range: [0, Math.max(0.1, Math.max(...d.scores) * 1.2 || 0.1)],
    }},
    legend: {{
      x: 1, y: 1, xanchor: 'right',
      bgcolor: 'rgba(30,41,59,0.8)',
      font: {{ size: 11, color: '#94a3b8' }},
    }},
    showlegend: true,
  }}, {{ responsive: true, displayModeBar: false }});
}}

function renderStatusStrip(d) {{
  if (d.exp_ids.length === 0) return;

  const trace = {{
    x: d.exp_ids,
    y: d.exp_ids.map(() => 1),
    type: 'bar',
    marker: {{ color: d.strip_colors }},
    text: d.statuses,
    hovertemplate: '%{{x}}: %{{text}}<extra></extra>',
  }};

  Plotly.react('status-strip', [trace], {{
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: '#1e293b',
    height: 60,
    margin: {{ l: 50, r: 20, t: 0, b: 20 }},
    xaxis: {{
      showticklabels: false,
      gridcolor: 'transparent',
    }},
    yaxis: {{
      showticklabels: false,
      gridcolor: 'transparent',
      range: [0, 1.2],
    }},
    bargap: 0.1,
    showlegend: false,
  }}, {{ responsive: true, displayModeBar: false }});
}}

function renderRecentList(d) {{
  const recent = d.experiments.slice(-8).reverse();
  const list = document.getElementById('recent-list');
  list.innerHTML = '';

  if (recent.length === 0) {{
    list.innerHTML = '<li class="activity-item" style="color:var(--text-muted)">No experiments yet</li>';
    return;
  }}

  recent.forEach(e => {{
    const badgeClass = 'badge-' + e.status;
    const li = document.createElement('li');
    li.className = 'activity-item';
    li.innerHTML = `
      <span><span style="font-family:JetBrains Mono;font-weight:600;font-size:12px">${{e.id}}</span> ${{e.description.substring(0, 40)}}</span>
      <span><span class="badge ${{badgeClass}}">${{e.status}}</span> <span style="font-family:JetBrains Mono;color:var(--text-muted);font-size:12px">${{e.avg_score.toFixed(4)}}</span></span>
    `;
    list.appendChild(li);
  }});
}}

function renderActionsChart(d) {{
  const completed = d.experiments.filter(e => ['baseline', 'improved', 'reverted', 'neutral'].includes(e.status));
  if (completed.length === 0) return;

  const trace = {{
    x: completed.map(e => e.id),
    y: completed.map(e => e.actions),
    type: 'bar',
    marker: {{ color: completed.map(e => ({{
      improved: '#22c55e', reverted: '#ef4444', baseline: '#3b82f6', neutral: '#64748b'
    }})[e.status] || '#64748b') }},
    hovertemplate: '%{{x}}: %{{y}} actions<extra></extra>',
  }};

  Plotly.react('actions-chart', [trace], {{
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: '#1e293b',
    height: 200,
    margin: {{ l: 40, r: 10, t: 0, b: 40 }},
    xaxis: {{
      tickfont: {{ family: 'JetBrains Mono', size: 9, color: '#94a3b8' }},
      tickangle: -45,
      gridcolor: 'transparent',
    }},
    yaxis: {{
      title: {{ text: 'Actions', font: {{ size: 11, color: '#94a3b8' }} }},
      gridcolor: '#334155',
      tickfont: {{ family: 'JetBrains Mono', size: 10, color: '#94a3b8' }},
    }},
    showlegend: false,
  }}, {{ responsive: true, displayModeBar: false }});
}}

function renderExpList(d) {{
  const list = document.getElementById('exp-list');
  list.innerHTML = '<div class="exp-list-header">Experiments (' + d.experiments.length + ')</div>';

  const reversed = [...d.experiments].reverse();
  reversed.forEach(e => {{
    const div = document.createElement('div');
    div.className = 'exp-list-item' + (selectedExp === e.id ? ' selected' : '');
    const badgeClass = 'badge-' + e.status;
    div.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span class="exp-id">${{e.id}}</span>
        <span class="badge ${{badgeClass}}">${{e.status}}</span>
      </div>
      <div class="exp-desc">${{e.description}}</div>
    `;
    div.onclick = () => selectExperiment(e.id, d);
    list.appendChild(div);
  }});
}}

function selectExperiment(expId, d) {{
  selectedExp = expId;
  const e = d.experiments.find(x => x.id === expId);
  if (!e) return;

  renderExpList(d);

  const panel = document.getElementById('detail-panel');
  panel.innerHTML = `
    <div class="detail-section">
      <h3>${{e.id}} <span class="badge badge-${{e.status}}" style="margin-left:8px">${{e.status}}</span></h3>
      <div class="detail-row"><span class="detail-label">Description</span></div>
      <div style="font-size:13px;color:var(--text-secondary);padding:4px 0 12px">${{e.description}}</div>
      <div class="detail-row"><span class="detail-label">Idea</span><span class="detail-value">${{e.idea || '—'}}</span></div>
      <div class="detail-row"><span class="detail-label">Avg Score</span><span class="detail-value">${{e.avg_score.toFixed(4)}}</span></div>
      <div class="detail-row"><span class="detail-label">Total Actions</span><span class="detail-value">${{e.actions}}</span></div>
      <div class="detail-row"><span class="detail-label">Duration</span><span class="detail-value">${{e.duration}}</span></div>
      ${{e.notes ? `<div class="detail-row"><span class="detail-label">Notes</span><span style="font-size:12px;color:var(--text-secondary)">${{e.notes}}</span></div>` : ''}}
    </div>
    <div class="detail-section">
      <h3>Per-Game Results</h3>
      <div class="detail-row"><span class="detail-label">ls20</span><span class="detail-value">${{e.ls20.toFixed(4)}}</span></div>
      <div class="detail-row"><span class="detail-label">ft09</span><span class="detail-value">${{e.ft09.toFixed(4)}}</span></div>
      <div class="detail-row"><span class="detail-label">vc33</span><span class="detail-value">${{e.vc33.toFixed(4)}}</span></div>
    </div>
  `;

  // Per-game comparison charts
  const gameDiv = document.createElement('div');
  gameDiv.className = 'detail-section';
  gameDiv.innerHTML = '<h3>Per-Game Comparison (All Experiments)</h3><div class="game-charts"><div id="game-ls20"></div><div id="game-ft09"></div><div id="game-vc33"></div></div>';
  panel.appendChild(gameDiv);

  ['ls20', 'ft09', 'vc33'].forEach(game => {{
    const completed = d.experiments.filter(x => ['baseline', 'improved', 'reverted', 'neutral'].includes(x.status));
    const trace = {{
      x: completed.map(x => x.actions),
      y: completed.map(x => x[game]),
      mode: 'markers',
      type: 'scatter',
      marker: {{
        color: completed.map(x => x.id === expId ? '#fbbf24' : ({{
          improved: '#22c55e', reverted: '#ef4444', baseline: '#3b82f6'
        }})[x.status] || '#64748b'),
        size: completed.map(x => x.id === expId ? 14 : 8),
        line: {{ color: '#0f172a', width: 1 }},
      }},
      text: completed.map(x => x.id),
      hovertemplate: '%{{text}}<br>Actions: %{{x}}<br>Score: %{{y:.4f}}<extra></extra>',
    }};

    Plotly.newPlot('game-' + game, [trace], {{
      template: 'plotly_dark',
      paper_bgcolor: 'transparent',
      plot_bgcolor: '#1e293b',
      height: 200,
      margin: {{ l: 40, r: 10, t: 24, b: 30 }},
      title: {{ text: game, font: {{ size: 13, color: '#94a3b8' }}, x: 0.5 }},
      xaxis: {{
        title: {{ text: 'Actions', font: {{ size: 10, color: '#64748b' }} }},
        gridcolor: '#334155',
        tickfont: {{ size: 9, color: '#94a3b8' }},
      }},
      yaxis: {{
        title: {{ text: 'Score', font: {{ size: 10, color: '#64748b' }} }},
        gridcolor: '#334155',
        tickfont: {{ size: 9, color: '#94a3b8' }},
      }},
      showlegend: false,
    }}, {{ responsive: true, displayModeBar: false }});
  }});
}}

// --- View switching ---

function switchView(view) {{
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(view + '-view').classList.add('active');
  document.querySelector(`[onclick="switchView('${{view}}')"]`).classList.add('active');

  if (view === 'details') {{
    renderExpList(DATA);
  }}
}}

// --- Countdown timer ---
setInterval(() => {{
  countdown--;
  if (countdown <= 0) {{
    countdown = 30;
    location.reload();
  }}
  document.getElementById('countdown').textContent = countdown;
}}, 1000);

// --- Initial render ---
renderStats(DATA);
renderScoreChart(DATA);
renderStatusStrip(DATA);
renderRecentList(DATA);
renderActionsChart(DATA);
</script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate ARC-AGI-3 autoresearch dashboard")
    parser.add_argument("--log", default="experiments/log.md", help="Path to log.md")
    parser.add_argument("--output", default="experiments/dashboard.html", help="Output HTML path")
    parser.add_argument("--data-output", default="experiments/dashboard_data.json", help="Output JSON path")
    args = parser.parse_args()

    experiments = parse_log(args.log)
    data = build_data(experiments)

    # Write JSON data
    Path(args.data_output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.data_output, "w") as f:
        json.dump(data, f, indent=2)

    # Write HTML
    html = generate_html(data)
    with open(args.output, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {args.output}")
    print(f"Data written: {args.data_output}")
    print(f"Experiments: {len(experiments)}")


if __name__ == "__main__":
    main()
