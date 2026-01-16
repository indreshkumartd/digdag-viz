"""Template management for HTML output."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from .exceptions import ConfigurationError
from .logger import get_logger

logger = get_logger(__name__)


# Default embedded template for schedule page (modern professional theme)
DEFAULT_SCHEDULE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Scheduled Workflows - Digdag Graph</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --primary: #1a365d;
    --primary-light: #2c5282;
    --accent: #3182ce;
    --font-sans: "Inter", "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
    --gray-50: #f7fafc;
    --gray-100: #edf2f7;
    --gray-200: #e2e8f0;
    --gray-300: #cbd5e0;
    --gray-600: #4a5568;
    --gray-800: #1a202c;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);

    /* Light Mode Colors */
    --bg-body: #ffffff;
    --bg-main: #f7fafc;
    --bg-card: #ffffff;
    --bg-sidebar: #ffffff;
    --bg-header: #1a365d;
    --text-main: #1a202c;
    --text-muted: #4a5568;
    --border-color: #e2e8f0;
    --shadow-color: rgba(0, 0, 0, 0.1);
  }

  /* Dark Mode Colors */
  [data-theme="dark"] {
    --bg-body: #171923;
    --bg-main: #1a202c;
    --bg-card: #2d3748;
    --bg-sidebar: #2d3748;
    --bg-header: #2d3748;
    --text-main: #f7fafc;
    --text-muted: #a0aec0;
    --border-color: #4a5568;
    --shadow-color: rgba(0, 0, 0, 0.4);
    --gray-50: #2d3748;
    --gray-100: #4a5568;
    --gray-200: #4a5568;
    --gray-600: #a0aec0;
    --gray-800: #f7fafc;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { 
    font-family: var(--font-sans);
    background: var(--bg-body); color: var(--text-main); font-size: 14px; line-height: 1.5;
    min-height: 100vh; display: flex; flex-direction: column;
    transition: background 0.3s ease, color 0.3s ease;
  }
  header { 
    padding: 0 32px; height: 64px; background: var(--bg-header);
    border-bottom: 1px solid rgba(0,0,0,0.1); display: flex;
    align-items: center; justify-content: space-between;
    box-shadow: 0 2px 4px var(--shadow-color); position: sticky; top: 0; z-index: 1000;
    transition: background 0.3s ease;
  }
  .brand { 
    font-weight: 600; font-size: 18px; color: white;
    text-decoration: none; display: flex; align-items: center; gap: 12px;
  }
  .brand-icon {
    width: 32px; height: 32px; background: var(--accent);
    border-radius: 6px; display: flex; align-items: center;
    justify-content: center; font-weight: 700; font-size: 16px; color: white;
  }
  .nav-links { display: flex; gap: 4px; }
  .nav-links a { 
    color: rgba(255, 255, 255, 0.9); text-decoration: none; 
    font-size: 14px; font-weight: 500; padding: 8px 16px;
    border-radius: 6px; transition: all 0.2s ease;
  }
  .nav-links a:hover { background: rgba(255,255,255,0.1); color: white; }
  .nav-links a.active { background: var(--accent); color: white; }
  
  .header-controls { display: flex; align-items: center; gap: 16px; }
  .theme-toggle {
    background: rgba(255,255,255,0.1); border: none; cursor: pointer;
    color: white; padding: 8px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
  }
  .theme-toggle:hover { background: rgba(255,255,255,0.2); }
  
  main { flex: 1; padding: 32px; max-width: 1200px; width: 100%; margin: 0 auto; background: var(--bg-body); transition: background 0.3s ease; }
  h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--text-main); }
  .subtitle { color: var(--text-muted); margin-bottom: 24px; }
  
  .controls { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
  input[type="search"], select {
    background: var(--bg-card); color: var(--text-main); border: 1px solid var(--border-color);
    border-radius: 6px; padding: 10px 14px; outline: none; font-family: var(--font-sans);
    font-size: 14px; transition: all 0.2s;
  }
  input[type="search"] { flex: 1; min-width: 250px; }
  input[type="search"]:focus, select:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1); }
  input[type="search"]::placeholder { color: var(--text-muted); }
  select { padding-right: 32px; }
  
  table { width: 100%; border-collapse: separate; border-spacing: 0; 
    border: 1px solid var(--border-color); border-radius: 8px;
    background: var(--bg-card); box-shadow: 0 2px 4px var(--shadow-color);
  }
  thead th { 
    background: var(--gray-50); border-bottom: 1px solid var(--border-color);
    text-align: left; padding: 14px 16px; font-weight: 600; font-size: 13px;
    color: var(--text-main); position: sticky; top: 64px; z-index: 1;
  }
  tbody tr { background: var(--bg-card); transition: background 0.15s; }
  tbody tr:nth-child(even) { background: var(--gray-50); }
  tbody tr:hover { background: var(--gray-100); }
  tbody td { padding: 14px 16px; border-bottom: 1px solid var(--border-color); vertical-align: top; }
  tbody tr:last-child td { border-bottom: none; }
  
  code { 
    background: var(--gray-100); padding: 3px 8px; border-radius: 4px;
    font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
    color: var(--text-main); display: inline-block;
  }
  
  .c-project { width: 18%; font-weight: 500; color: var(--text-main); }
  .c-workflow { width: 25%; }
  .c-schedule { width: 57%; }
  .badge { 
    background: var(--accent); color: white; border-radius: 999px;
    padding: 4px 12px; font-size: 12px; font-weight: 500;
  }
  a { color: var(--accent); text-decoration: none; font-weight: 500; }
  a:hover { text-decoration: underline; }
  
  footer { 
    color: var(--text-muted); font-size: 12px; padding: 24px 32px;
    text-align: center; border-top: 1px solid var(--border-color);
    background: var(--bg-body);
  }
</style>
</head>
<body>

<header>
  <a href="index.html" class="brand">
    <div class="brand-icon">D</div>
    <span>Digdag Workflow Graph</span>
  </a>
  
  <div class="header-controls">
    <nav class="nav-links">
      <a href="index.html">Home</a>
      <a href="index.html">Workflows</a>
      <a href="scheduled_workflows.html" class="active">Scheduled</a>
      <a href="unscheduled_workflows.html">Unscheduled</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" title="Toggle Dark Mode">
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    </button>
  </div>
</header>

<main>
  <h1>Scheduled Workflows</h1>
  <div class="subtitle">Search and filter schedules from your Digdag projects</div>
  
  <div class="controls">
    <input id="q" type="search" placeholder="Search workflows, projects, schedule text...">
    <select id="proj">
      <option value="">All projects</option>
      {% for p in projects %}
      <option value="{{ p }}">{{ p }}</option>
      {% endfor %}
    </select>
    <span class="badge" id="count"></span>
  </div>
  
  <table id="tbl">
    <thead>
      <tr>
        <th>Project</th>
        <th>Workflow</th>
        <th>Schedule</th>
      </tr>
    </thead>
    <tbody>
      {% for it in items %}
      <tr data-project="{{ it.project }}">
        <td class="c-project">{{ it.project }}</td>
        <td class="c-workflow"><a href="{{ it.svg }}">{{ it.workflow }}</a></td>
        <td class="c-schedule"><code>{{ it.schedule }}{% if it.timezone %} ({{ it.timezone }}){% endif %}</code></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</main>

<footer>Generated by digdag-graph</footer>

<script>
(function() {
  const q = document.getElementById('q');
  const proj = document.getElementById('proj');
  const tbody = document.querySelector('#tbl tbody');
  const count = document.getElementById('count');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  function norm(s) { return (s||'').toLowerCase(); }

  function apply() {
    const term = norm(q.value);
    const pf = proj.value;
    let visible = 0;

    rows.forEach(tr => {
      const projName = tr.getAttribute('data-project');
      const text = norm(tr.innerText);
      const matchesProj = !pf || projName === pf;
      const matchesText = !term || text.includes(term);

      if (matchesProj && matchesText) {
        tr.style.display = 'table-row';
        visible++;
      } else {
        tr.style.display = 'none';
      }
    });

    count.textContent = visible + ' shown';
  }

  if (q && proj) {
    q.addEventListener('input', apply);
    proj.addEventListener('change', apply);
    // Initial apply
    setTimeout(apply, 10);
  }
  
  // Dark Mode Logic
  const themeToggle = document.getElementById('themeToggle');
  const storedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
    });
  }
})();
</script>

</body>
</html>
"""


# Default embedded template for index page (modern professional theme)
DEFAULT_INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Digdag Workflows - Digdag Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --success: #38a169;
      --font-sans: "Inter", "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
      --gray-50: #f7fafc;
      --gray-100: #edf2f7;
      --gray-200: #e2e8f0;
      --gray-600: #4a5568;
      --gray-800: #1a202c;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
      
      /* Light Mode Colors */
      --bg-body: #ffffff;
      --bg-main: #f7fafc;
      --bg-card: #ffffff;
      --bg-sidebar: #ffffff;
      --bg-header: #1a365d;
      --text-main: #1a202c;
      --text-muted: #4a5568;
      --border-color: #e2e8f0;
      --shadow-color: rgba(0, 0, 0, 0.1);
    }

    /* Dark Mode Colors */
    [data-theme="dark"] {
      --bg-body: #171923;
      --bg-main: #1a202c;
      --bg-card: #2d3748;
      --bg-sidebar: #2d3748;
      --bg-header: #2d3748;
      --text-main: #f7fafc;
      --text-muted: #a0aec0;
      --border-color: #4a5568;
      --shadow-color: rgba(0, 0, 0, 0.4);
      --gray-50: #2d3748;
      --gray-100: #4a5568;
      --gray-200: #4a5568;
      --gray-600: #a0aec0;
      --gray-800: #f7fafc;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-sans);
      background: var(--bg-body); color: var(--text-main); font-size: 14px; line-height: 1.5;
      min-height: 100vh; display: flex; flex-direction: column;
      transition: background 0.3s ease, color 0.3s ease;
    }
    header {
      padding: 0 32px; height: 64px; background: var(--bg-header);
      border-bottom: 1px solid rgba(0,0,0,0.1); display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: 0 2px 4px var(--shadow-color); position: sticky; top: 0; z-index: 1000;
      transition: background 0.3s ease;
    }
    .brand {
      font-weight: 600; font-size: 18px; color: white;
      text-decoration: none; display: flex; align-items: center; gap: 12px;
    }
    .brand-icon {
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 6px; display: flex; align-items: center;
      justify-content: center; font-weight: 700; font-size: 16px; color: white;
    }
    .nav-links { display: flex; gap: 4px; }
    .nav-links a {
      color: rgba(255, 255, 255, 0.9); text-decoration: none;
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }
    .nav-links a:hover { background: rgba(255,255,255,0.1); color: white; }
    .nav-links a.active { background: var(--accent); color: white; }
    
    .header-controls { display: flex; align-items: center; gap: 16px; }
    .theme-toggle {
      background: rgba(255,255,255,0.1); border: none; cursor: pointer;
      color: white; padding: 8px; border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s;
    }
    .theme-toggle:hover { background: rgba(255,255,255,0.2); }
    .header-btn {
      background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
      color: white; padding: 8px 12px; border-radius: 6px;
      font-size: 13px; font-weight: 600; cursor: pointer;
      transition: all 0.2s ease;
    }
    .header-btn:hover { background: rgba(255,255,255,0.2); }

    main { flex: 1; padding: 32px; max-width: 1200px; width: 100%; margin: 0 auto; background: var(--bg-body); transition: background 0.3s ease; }
    h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--text-main); }
    .subtitle { color: var(--text-muted); margin-bottom: 32px; }
    
    .controls { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
    input[type="search"], select {
      background: var(--bg-card); color: var(--text-main); border: 1px solid var(--border-color);
      border-radius: 6px; padding: 10px 14px; outline: none; font-family: var(--font-sans);
      font-size: 14px; transition: all 0.2s;
    }
    input[type="search"] { flex: 1; min-width: 250px; }
    input[type="search"]:focus, select:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1); }
    input[type="search"]::placeholder { color: var(--text-muted); }
    select { padding-right: 32px; }
    
    .workflow-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px; margin-top: 24px;
    }
    .workflow-card {
      border: 1px solid var(--border-color); border-radius: 8px;
      padding: 20px; background: var(--bg-card); box-shadow: 0 2px 4px var(--shadow-color);
      transition: all 0.2s ease;
    }
    .workflow-card:hover {
      box-shadow: 0 10px 15px -3px var(--shadow-color);
      transform: translateY(-2px);
    }
    .workflow-card h3 {
      margin: 0 0 12px; font-size: 18px; font-weight: 600; color: var(--text-main);
    }
    .workflow-card p {
      margin: 8px 0; font-size: 14px; color: var(--text-muted);
    }
    .workflow-card a {
      color: var(--accent); text-decoration: none; font-weight: 500;
    }
    .workflow-card a:hover { text-decoration: underline; }
    code {
      background: var(--gray-100); padding: 3px 8px; border-radius: 4px;
      font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
      color: var(--text-main); display: inline-block;
    }
    .schedule-badge {
      display: inline-block; background: var(--success); color: white;
      padding: 4px 10px; border-radius: 4px; font-size: 12px;
      font-weight: 500; margin-top: 8px;
    }
    .badge-row {
      display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px;
    }
    .summary-badge {
      background: var(--bg-main); color: var(--text-main);
      border: 1px solid var(--border-color); border-radius: 999px;
      padding: 3px 10px; font-size: 12px; font-weight: 600;
    }
    .summary-badge.warn {
      background: #fff4d6; color: #7b4a00; border-color: #f6d28b;
    }
    [data-theme="dark"] .summary-badge {
      background: #3b4758; border-color: #556; color: #f7fafc;
    }
    [data-theme="dark"] .summary-badge.warn {
      background: #5a3d00; border-color: #8a5a00; color: #ffe4a6;
    }
    .quick-links {
      display: flex; gap: 12px; margin-top: 32px; padding-top: 32px;
      border-top: 1px solid var(--border-color);
    }
    .quick-link {
      flex: 1; padding: 16px; background: var(--gray-50);
      border: 1px solid var(--border-color); border-radius: 8px;
      text-decoration: none; color: var(--text-main);
      transition: all 0.2s ease;
    }
    .quick-link:hover {
      background: var(--primary); box-shadow: 0 4px 6px var(--shadow-color);
    }
    .quick-link:hover h4, .quick-link:hover p { color: white; }
    
    .quick-link h4 {
      font-size: 14px; font-weight: 600; margin-bottom: 4px; color: var(--text-main);
    }
    .quick-link p {
      font-size: 13px; color: var(--text-muted); margin: 0;
    }
    
    footer {
      color: var(--text-muted); font-size: 12px; padding: 24px 32px;
      text-align: center; border-top: 1px solid var(--border-color);
      background: var(--bg-body);
    }
  </style>
</head>
<body>
  <header>
    <a href="index.html" class="brand">
      <div class="brand-icon">D</div>
      <span>Digdag Workflow Graph</span>
    </a>
    
    <div class="header-controls">
      <nav class="nav-links">
        <a href="index.html" class="active">Home</a>
        <a href="index.html">Workflows</a>
        <a href="scheduled_workflows.html">Scheduled</a>
        <a href="unscheduled_workflows.html">Unscheduled</a>
      </nav>
      <button class="theme-toggle" id="themeToggle" title="Toggle Dark Mode">
        <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      </button>
    </div>
  </header>
  
  <main>
    <h1>Digdag Workflows</h1>
    <div class="subtitle">Total workflows: {{ workflows|length }}</div>
    
    <div class="controls">
      <input id="q" type="search" placeholder="Search workflows, projects, files...">
      <select id="proj">
        <option value="">All projects</option>
        {% for p in projects %}
        <option value="{{ p }}">{{ p }}</option>
        {% endfor %}
      </select>
      <span class="badge" id="count"></span>
    </div>
    
    <div class="workflow-grid">
    {% for wf in workflows %}
      <div class="workflow-card" data-project="{{ wf.project }}">
        <h3>{{ wf.name }}</h3>
        <p><code>{{ wf.file }}</code></p>
        {% if wf.schedule %}
        <p>Schedule: <code>{{ wf.schedule }}</code></p>
        <span class="schedule-badge">Scheduled</span>
        {% endif %}
        {% if wf.summary %}
        <div class="badge-row">
          <span class="summary-badge">Tasks {{ wf.summary.task_count }}</span>
          {% if wf.summary.td_queries %}
          <span class="summary-badge">TD {{ wf.summary.td_queries }}</span>
          {% endif %}
          {% if wf.summary.input_tables %}
          <span class="summary-badge">Inputs {{ wf.summary.input_tables }}</span>
          {% endif %}
          {% if wf.summary.output_tables %}
          <span class="summary-badge">Outputs {{ wf.summary.output_tables }}</span>
          {% endif %}
          {% if wf.summary.has_error_handlers %}
          <span class="summary-badge warn">_error</span>
          {% endif %}
          {% if wf.summary.has_parallel %}
          <span class="summary-badge warn">_parallel</span>
          {% endif %}
        </div>
        {% endif %}
        {% if wf.graph %}
        <p><a href="{{ wf.graph }}">View Graph →</a></p>
        {% endif %}
      </div>
    {% endfor %}
    </div>
    
    {% if scheduled_workflows %}
    <div class="quick-links">
      <a href="scheduled_workflows.html" class="quick-link">
        <h4>📅 Scheduled Workflows</h4>
        <p>View all workflows with schedules</p>
      </a>
      <a href="unscheduled_workflows.html" class="quick-link">
        <h4>📋 Unscheduled Workflows</h4>
        <p>View workflows without schedules</p>
      </a>
      <a href="lineage.html" class="quick-link">
        <h4>🔗 Data Lineage</h4>
        <p>Explore table dependencies and data flow</p>
      </a>
    </div>
    {% endif %}
  </main>
  
  <footer>Generated by digdag-graph</footer>
  
  <script>
  (function() {
    const q = document.getElementById('q');
    const proj = document.getElementById('proj');
    const grid = document.querySelector('.workflow-grid');
    const count = document.getElementById('count');
    const cards = Array.from(grid.querySelectorAll('.workflow-card'));

    function norm(s) { return (s||'').toLowerCase(); }

    function apply() {
      const term = norm(q.value);
      const pf = proj.value;
      let visible = 0;

      cards.forEach(card => {
        const projName = card.getAttribute('data-project');
        const name = norm(card.querySelector('h3').innerText);
        const file = norm(card.querySelector('code').innerText); // File path is in the first code block
        const text = name + ' ' + file;
        
        const matchesProj = !pf || projName === pf;
        const matchesText = !term || text.includes(term);

        if (matchesProj && matchesText) {
          card.style.display = 'block';
          visible++;
        } else {
          card.style.display = 'none';
        }
      });

      count.textContent = visible + ' shown';
    }

    if (q && proj) {
      q.addEventListener('input', apply);
      proj.addEventListener('change', apply);
      // Initial apply
      setTimeout(apply, 10);
    }
    
    // Dark Mode Logic
    const themeToggle = document.getElementById('themeToggle');
    const storedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
    
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
      });
    }
  })();
  </script>
</body>
</html>
"""


# Default embedded template for unscheduled workflows page (modern professional theme)
DEFAULT_UNSCHEDULED_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Unscheduled Workflows - Digdag Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --font-sans: "Inter", "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
      --gray-50: #f7fafc;
      --gray-100: #edf2f7;
      --gray-200: #e2e8f0;
      --gray-600: #4a5568;
      --gray-800: #1a202c;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);

      /* Light Mode Colors */
      --bg-body: #ffffff;
      --bg-main: #f7fafc;
      --bg-card: #ffffff;
      --bg-sidebar: #ffffff;
      --bg-header: #1a365d;
      --text-main: #1a202c;
      --text-muted: #4a5568;
      --border-color: #e2e8f0;
      --shadow-color: rgba(0, 0, 0, 0.1);
    }

    /* Dark Mode Colors */
    [data-theme="dark"] {
      --bg-body: #171923;
      --bg-main: #1a202c;
      --bg-card: #2d3748;
      --bg-sidebar: #2d3748;
      --bg-header: #2d3748;
      --text-main: #f7fafc;
      --text-muted: #a0aec0;
      --border-color: #4a5568;
      --shadow-color: rgba(0, 0, 0, 0.4);
      --gray-50: #2d3748;
      --gray-100: #4a5568;
      --gray-200: #4a5568;
      --gray-600: #a0aec0;
      --gray-800: #f7fafc;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-sans);
      background: var(--bg-body); color: var(--text-main); font-size: 14px; line-height: 1.5;
      min-height: 100vh; display: flex; flex-direction: column;
      transition: background 0.3s ease, color 0.3s ease;
    }
    header {
      padding: 0 32px; height: 64px; background: var(--bg-header);
      border-bottom: 1px solid rgba(0,0,0,0.1); display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: 0 2px 4px var(--shadow-color); position: sticky; top: 0; z-index: 1000;
      transition: background 0.3s ease;
    }
    .brand {
      font-weight: 600; font-size: 18px; color: white;
      text-decoration: none; display: flex; align-items: center; gap: 12px;
    }
    .brand-icon {
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 6px; display: flex; align-items: center;
      justify-content: center; font-weight: 700; font-size: 16px; color: white;
    }
    .nav-links { display: flex; gap: 4px; }
    .nav-links a {
      color: rgba(255, 255, 255, 0.9); text-decoration: none;
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }
    .nav-links a:hover { background: rgba(255,255,255,0.1); color: white; }
    .nav-links a.active { background: var(--accent); color: white; }
    
    .header-controls { display: flex; align-items: center; gap: 16px; }
    .theme-toggle {
      background: rgba(255,255,255,0.1); border: none; cursor: pointer;
      color: white; padding: 8px; border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s;
    }
    .theme-toggle:hover { background: rgba(255,255,255,0.2); }
    
    main { flex: 1; padding: 32px; max-width: 1200px; width: 100%; margin: 0 auto; background: var(--bg-body); transition: background 0.3s ease; }
    h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--text-main); }
    .subtitle { color: var(--text-muted); margin-bottom: 24px; }
    
    .controls { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
    input[type="search"], select {
      background: var(--bg-card); color: var(--text-main); border: 1px solid var(--border-color);
      border-radius: 6px; padding: 10px 14px; outline: none; font-family: var(--font-sans);
      font-size: 14px; transition: all 0.2s;
    }
    input[type="search"] { flex: 1; min-width: 250px; }
    input[type="search"]:focus, select:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1); }
    input[type="search"]::placeholder { color: var(--text-muted); }
    select { padding-right: 32px; }
    
    table { width: 100%; border-collapse: separate; border-spacing: 0; 
      border: 1px solid var(--border-color); border-radius: 8px;
      background: var(--bg-card); box-shadow: 0 2px 4px var(--shadow-color);
    }
    thead th { 
      background: var(--gray-50); border-bottom: 1px solid var(--border-color);
      text-align: left; padding: 14px 16px; font-weight: 600; font-size: 13px;
      color: var(--text-main); position: sticky; top: 64px; z-index: 1;
    }
    tbody tr { background: var(--bg-card); transition: background 0.15s; }
    tbody tr:nth-child(even) { background: var(--gray-50); }
    tbody tr:hover { background: var(--gray-100); }
    tbody td { padding: 14px 16px; border-bottom: 1px solid var(--border-color); vertical-align: top; }
    tbody tr:last-child td { border-bottom: none; }
    
    code { 
      background: var(--gray-100); padding: 3px 8px; border-radius: 4px;
      font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
      color: var(--text-main); display: inline-block;
    }
    
    .c-project { width: 20%; font-weight: 500; color: var(--text-main); }
    .c-workflow { width: 30%; }
    .c-file { width: 50%; }
    .badge { 
      background: var(--accent); color: white; border-radius: 999px;
      padding: 4px 12px; font-size: 12px; font-weight: 500;
    }
    .badge-row {
      display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;
    }
    .summary-badge {
      background: var(--gray-100); color: var(--text-main);
      border: 1px solid var(--border-color); border-radius: 999px;
      padding: 3px 10px; font-size: 11px; font-weight: 600;
    }
    .summary-badge.warn {
      background: #fff4d6; color: #7b4a00; border-color: #f6d28b;
    }
    [data-theme="dark"] .summary-badge {
      background: #3b4758; border-color: #556; color: #f7fafc;
    }
    [data-theme="dark"] .summary-badge.warn {
      background: #5a3d00; border-color: #8a5a00; color: #ffe4a6;
    }
    a { color: var(--accent); text-decoration: none; font-weight: 500; }
    a:hover { text-decoration: underline; }
    
    footer { 
      color: var(--text-muted); font-size: 12px; padding: 24px 32px;
      text-align: center; border-top: 1px solid var(--border-color);
      background: var(--bg-body);
    }
  </style>
</head>
<body>

<header>
  <a href="index.html" class="brand">
    <div class="brand-icon">D</div>
    <span>Digdag Workflow Graph</span>
  </a>
  
  <div class="header-controls">
    <nav class="nav-links">
      <a href="index.html">Home</a>
      <a href="index.html">Workflows</a>
      <a href="scheduled_workflows.html">Scheduled</a>
      <a href="unscheduled_workflows.html" class="active">Unscheduled</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" title="Toggle Dark Mode">
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    </button>
  </div>
</header>

<main>
  <h1>Unscheduled Workflows</h1>
  <div class="subtitle">Total workflows: {{ workflows|length }}</div>
  
  <div class="controls">
    <input id="q" type="search" placeholder="Search workflows, projects, files...">
    <select id="proj">
      <option value="">All projects</option>
      {% for p in projects %}
      <option value="{{ p }}">{{ p }}</option>
      {% endfor %}
    </select>
    <span class="badge" id="count"></span>
  </div>
  
  <table id="tbl">
    <thead>
      <tr>
        <th>Project</th>
        <th>Workflow</th>
        <th>File Path</th>
      </tr>
    </thead>
    <tbody>
      {% for wf in workflows %}
      <tr data-project="{{ wf.project }}">
        <td class="c-project">{{ wf.project }}</td>
        <td class="c-workflow">
          <a href="{{ wf.graph }}">{{ wf.name }}</a>
          {% if wf.summary %}
          <div class="badge-row">
            <span class="summary-badge">Tasks {{ wf.summary.task_count }}</span>
            {% if wf.summary.td_queries %}
            <span class="summary-badge">TD {{ wf.summary.td_queries }}</span>
            {% endif %}
            {% if wf.summary.input_tables %}
            <span class="summary-badge">In {{ wf.summary.input_tables }}</span>
            {% endif %}
            {% if wf.summary.output_tables %}
            <span class="summary-badge">Out {{ wf.summary.output_tables }}</span>
            {% endif %}
            {% if wf.summary.has_error_handlers %}
            <span class="summary-badge warn">_error</span>
            {% endif %}
            {% if wf.summary.has_parallel %}
            <span class="summary-badge warn">_parallel</span>
            {% endif %}
          </div>
          {% endif %}
        </td>
        <td class="c-file"><code>{{ wf.file }}</code></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</main>

<footer>Generated by digdag-graph</footer>

<script>
(function() {
  const q = document.getElementById('q');
  const proj = document.getElementById('proj');
  const tbody = document.querySelector('#tbl tbody');
  const count = document.getElementById('count');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  function norm(s) { return (s||'').toLowerCase(); }

  function apply() {
    const term = norm(q.value);
    const pf = proj.value;
    let visible = 0;

    rows.forEach(tr => {
      const projName = tr.getAttribute('data-project');
      const text = norm(tr.innerText);
      const matchesProj = !pf || projName === pf;
      const matchesText = !term || text.includes(term);

      if (matchesProj && matchesText) {
        tr.style.display = 'table-row';
        visible++;
      } else {
        tr.style.display = 'none';
      }
    });

    count.textContent = visible + ' shown';
  }

  if (q && proj) {
    q.addEventListener('input', apply);
    proj.addEventListener('change', apply);
    // Initial apply
    setTimeout(apply, 10);
  }
  
  // Dark Mode Logic
  const themeToggle = document.getElementById('themeToggle');
  const storedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
    });
  }
})();
</script>
</body>
</html>
"""


# Default embedded template for interactive workflow graph
DEFAULT_INTERACTIVE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ wf_name }} - Digdag Workflow Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --success: #38a169;
      --warning: #d69e2e;
      --error: #e53e3e;
      --font-sans: "Inter", "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
      
      /* Light Mode Colors */
      --bg-body: #ffffff;
      --bg-main: #f7fafc;
      --bg-card: #ffffff;
      --bg-sidebar: #ffffff;
      --bg-header: #1a365d;
      --text-main: #1a202c;
      --text-muted: #4a5568;
      --border-color: #e2e8f0;
      --shadow-color: rgba(0, 0, 0, 0.1);
      --node-fill: #ffffff;
      --node-stroke: #4a5568;
    }
    
    /* Dark Mode Colors */
    [data-theme="dark"] {
      --bg-body: #171923;
      --bg-main: #1a202c;
      --bg-card: #2d3748;
      --bg-sidebar: #2d3748;
      --bg-header: #2d3748;
      --text-main: #f7fafc;
      --text-muted: #a0aec0;
      --border-color: #4a5568;
      --shadow-color: rgba(0, 0, 0, 0.4);
      --node-fill: #2d3748;
      --node-stroke: #cbd5e0;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      margin: 0; height: 100vh; display: flex; flex-direction: column;
      font-family: var(--font-sans);
      background: var(--bg-body); color: var(--text-main); overflow: hidden;
      font-size: 14px; line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      transition: background 0.3s ease, color 0.3s ease;
    }
    header { 
      padding: 0 32px; height: 64px; background: var(--bg-header);
      border-bottom: 1px solid rgba(0,0,0,0.1); display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: 0 2px 4px var(--shadow-color); z-index: 1000;
      transition: background 0.3s ease;
    }
    .brand { 
      font-weight: 600; font-size: 18px; color: white;
      text-decoration: none; display: flex; align-items: center;
      gap: 12px; letter-spacing: -0.01em;
    }
    .brand-icon {
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 6px; display: flex; align-items: center;
      justify-content: center; font-weight: 700; font-size: 16px; color: white;
    }
    .workflow-title {
      color: rgba(255,255,255,0.7); font-weight: 400; font-size: 14px;
      margin-left: 8px; padding-left: 12px;
      border-left: 1px solid rgba(255,255,255,0.2);
    }
    .nav-links { display: flex; align-items: center; gap: 4px; }
    .nav-links a { 
      color: rgba(255, 255, 255, 0.8); text-decoration: none; 
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }
    .nav-links a:hover { background: rgba(255,255,255,0.1); color: white; }
    
    .header-controls { display: flex; align-items: center; gap: 16px; }
    
    .search-box { position: relative; }
    .search-box input {
      background: rgba(255,255,255,0.1); border: 1px solid transparent;
      color: white; padding: 8px 16px 8px 36px; border-radius: 6px;
      font-size: 14px; width: 240px; outline: none;
      font-family: var(--font-sans); transition: all 0.2s ease;
    }
    .search-box input::placeholder { color: rgba(255, 255, 255, 0.5); }
    .search-box input:focus { 
      background: white; color: var(--gray-800);
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.3);
    }
    .search-box input:focus::placeholder { color: var(--gray-400); }
    .search-icon {
      position: absolute; left: 10px; top: 50%;
      transform: translateY(-50%); color: rgba(255, 255, 255, 0.5);
      pointer-events: none; font-size: 14px;
    }
    .search-box input:focus ~ .search-icon { color: var(--gray-400); }
    
    .theme-toggle {
      background: rgba(255,255,255,0.1); border: none; cursor: pointer;
      color: white; padding: 8px; border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s;
    }
    .theme-toggle:hover { background: rgba(255,255,255,0.2); }
    
    main { 
      flex: 1; position: relative; background: var(--bg-main);
      overflow: hidden; cursor: grab; transition: background 0.3s ease;
    }
    main:active { cursor: grabbing; }
    #scene { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
    
    /* SVG Styling */
    svg { 
      max-width: none; height: auto; 
      background: var(--bg-card); border-radius: 8px; 
      box-shadow: 0 10px 15px -3px var(--shadow-color);
      transition: background 0.3s ease;
    }
    
    /* Interactive Elements */
    .node polygon, .node ellipse, .node path { 
      fill: var(--node-fill); stroke: var(--node-stroke);
      transition: all 0.3s ease;
    }
    .node text { fill: var(--text-main); }
    .edge path { stroke: var(--text-muted); }
    .edge polygon { fill: var(--text-muted); stroke: var(--text-muted); }
    
    .node.highlighted polygon, .node.highlighted ellipse, .node.highlighted path {
      stroke: var(--accent) !important; stroke-width: 3px !important;
      filter: drop-shadow(0 0 8px rgba(49, 130, 206, 0.4));
    }
    .node.focused polygon, .node.focused ellipse, .node.focused path {
      stroke: var(--accent) !important; stroke-width: 3px !important;
      filter: drop-shadow(0 0 8px rgba(49, 130, 206, 0.4));
    }
    .node.dimmed { opacity: 0.15; }
    .edge.dimmed { opacity: 0.1; }
    
    /* Sidebar */
    #sidebar {
      position: fixed; top: 64px; right: -450px; width: 450px;
      height: calc(100vh - 64px); background: var(--bg-sidebar);
      box-shadow: -4px 0 16px var(--shadow-color);
      transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s ease;
      z-index: 999; overflow-y: auto; border-left: 1px solid var(--border-color);
    }
    #sidebar.open { right: 0; }
    .sidebar-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 24px; border-bottom: 1px solid var(--border-color);
      background: var(--bg-sidebar); position: sticky; top: 0; z-index: 10;
    }
    .sidebar-title { font-size: 18px; font-weight: 600; color: var(--text-main); }
    .close-btn { 
      cursor: pointer; font-size: 24px; color: var(--text-muted);
      width: 32px; height: 32px; display: flex; align-items: center;
      justify-content: center; border-radius: 6px; transition: all 0.2s;
    }
    .close-btn:hover { background: rgba(0,0,0,0.05); color: var(--text-main); }
    
    .sidebar-content { padding: 24px; }
    .task-prop { margin-bottom: 20px; }
    .prop-label { 
      font-size: 11px; font-weight: 600; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
    }
    .prop-value { 
      font-size: 14px; color: var(--text-main); word-break: break-word;
      white-space: pre-wrap; background: rgba(0,0,0,0.03); padding: 12px;
      border-radius: 6px; border: 1px solid var(--border-color); line-height: 1.6;
    }
    .prop-value.code { 
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      font-size: 13px;
    }
    
    .controls {
      position: absolute; bottom: 24px; right: 24px;
      display: flex; flex-direction: column; gap: 8px; z-index: 100;
    }
    .btn {
      width: 44px; height: 44px; border-radius: 8px;
      border: 1px solid var(--border-color); background: var(--bg-card);
      color: var(--text-main); font-size: 18px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 2px 4px var(--shadow-color); transition: all 0.2s ease; font-weight: 500;
    }
    .btn:hover {
      background: var(--primary); color: white; border-color: var(--primary);
      transform: translateY(-1px); box-shadow: 0 4px 6px var(--shadow-color);
    }
    .btn:active { transform: translateY(0); }
    
    .summary-bar {
      position: absolute; top: 16px; left: 16px; right: 16px;
      display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 8px; padding: 8px 12px; z-index: 50;
      box-shadow: 0 2px 4px var(--shadow-color);
    }
    .summary-title {
      font-size: 11px; font-weight: 600; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .summary-badge {
      background: var(--gray-100); color: var(--text-main);
      border: 1px solid var(--border-color); border-radius: 999px;
      padding: 3px 10px; font-size: 12px; font-weight: 600;
    }
    .summary-badge.warn {
      background: #fff4d6; color: #7b4a00; border-color: #f6d28b;
    }
    [data-theme="dark"] .summary-badge {
      background: #3b4758; border-color: #556; color: #f7fafc;
    }
    [data-theme="dark"] .summary-badge.warn {
      background: #5a3d00; border-color: #8a5a00; color: #ffe4a6;
    }
    
    .tour-panel {
      position: fixed; left: 24px; bottom: 24px; width: 320px;
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 10px; box-shadow: 0 8px 16px var(--shadow-color);
      z-index: 1200; display: none;
    }
    .tour-panel.open { display: block; }
    .tour-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 14px; border-bottom: 1px solid var(--border-color);
      font-weight: 600; color: var(--text-main);
    }
    .tour-close {
      background: transparent; border: none; cursor: pointer;
      font-size: 18px; color: var(--text-muted);
    }
    .tour-body { padding: 14px; }
    .tour-step { font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
    .tour-text { font-size: 14px; color: var(--text-main); }
    .tour-controls {
      display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border-color);
    }
    .tour-controls button {
      flex: 1; border: 1px solid var(--border-color); background: var(--bg-main);
      color: var(--text-main); border-radius: 6px; padding: 8px 10px;
      font-size: 13px; cursor: pointer;
    }
    .tour-controls button.primary {
      background: var(--accent); border-color: var(--accent); color: white;
    }
  </style>
</head>
<body>
  <header>
    <div style="display: flex; align-items: center;">
      <a href="index.html" class="brand">
        <div class="brand-icon">D</div>
        <span>Digdag Workflow Graph</span>
      </a>
      <span class="workflow-title">{{ wf_name }}</span>
    </div>
    <div class="header-controls">
      <nav class="nav-links">
        <a href="index.html">Home</a>
        <a href="index.html">Workflows</a>
        <a href="scheduled_workflows.html">Scheduled</a>
        <a href="unscheduled_workflows.html">Unscheduled</a>
      </nav>
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" placeholder="Search tasks..." />
      </div>
      <button class="header-btn" id="tourBtn">Tour</button>
      <button class="header-btn" id="copyLinkBtn" title="Copy deep link">Copy Link</button>
      <button class="theme-toggle" id="themeToggle" title="Toggle Dark Mode">
        <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      </button>
    </div>
  </header>
  
  <main id="scene">
    {% if summary %}
    <div class="summary-bar">
      <span class="summary-title">Summary</span>
      <span class="summary-badge">Tasks {{ summary.task_count }}</span>
      {% if summary.td_queries %}
      <span class="summary-badge">TD {{ summary.td_queries }}</span>
      {% endif %}
      {% if summary.input_tables %}
      <span class="summary-badge">Inputs {{ summary.input_tables }}</span>
      {% endif %}
      {% if summary.output_tables %}
      <span class="summary-badge">Outputs {{ summary.output_tables }}</span>
      {% endif %}
      {% if summary.has_error_handlers %}
      <span class="summary-badge warn">_error</span>
      {% endif %}
      {% if summary.has_parallel %}
      <span class="summary-badge warn">_parallel</span>
      {% endif %}
      {% if summary.has_retry %}
      <span class="summary-badge warn">retry</span>
      {% endif %}
    </div>
    {% endif %}
    {{ svg_content | safe }}
  </main>
  
  <div id="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title">Task Details</div>
      <div class="close-btn" onclick="closeSidebar()">×</div>
    </div>
    <div class="sidebar-content" id="sidebarContent">
      <p style="color: var(--text-muted); text-align: center; padding: 40px 20px;">
        Click on a task to view details
      </p>
    </div>
  </div>
  
  <div class="controls">
    <button class="btn" onclick="zoomIn()" title="Zoom In">+</button>
    <button class="btn" onclick="zoomOut()" title="Zoom Out">−</button>
    <button class="btn" onclick="resetZoom()" title="Reset">⟲</button>
  </div>
  
  <div class="tour-panel" id="tourPanel">
    <div class="tour-header">
      Guided Tour
      <button class="tour-close" id="tourCloseBtn">×</button>
    </div>
    <div class="tour-body">
      <div class="tour-step" id="tourStep"></div>
      <div class="tour-text" id="tourText"></div>
    </div>
    <div class="tour-controls">
      <button id="tourPrevBtn">Prev</button>
      <button class="primary" id="tourNextBtn">Next</button>
    </div>
  </div>
  
  <script>
    // Task Definitions
    const taskDefs = {{ task_defs | safe }};
    
    // Pan/Zoom (offline, no external deps)
    const scene = document.getElementById('scene');
    const svgElement = scene.querySelector('svg');
    svgElement.style.transformOrigin = '0 0';
    let panX = 0;
    let panY = 0;
    let scale = 1;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;
    
    function applyTransform() {
      svgElement.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    }
    
    function zoomAt(multiplier, clientX, clientY) {
      const rect = scene.getBoundingClientRect();
      const offsetX = clientX - rect.left;
      const offsetY = clientY - rect.top;
      const prevScale = scale;
      scale = Math.min(5, Math.max(0.1, scale * multiplier));
      const ratio = scale / prevScale;
      panX = offsetX - ratio * (offsetX - panX);
      panY = offsetY - ratio * (offsetY - panY);
      applyTransform();
    }
    
    scene.addEventListener('wheel', (e) => {
      e.preventDefault();
      const multiplier = e.deltaY > 0 ? 0.9 : 1.1;
      zoomAt(multiplier, e.clientX, e.clientY);
    }, { passive: false });
    
    scene.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      if (e.target.closest('.node') || e.target.closest('a')) return;
      isPanning = true;
      panStartX = e.clientX - panX;
      panStartY = e.clientY - panY;
    });
    
    window.addEventListener('mousemove', (e) => {
      if (!isPanning) return;
      panX = e.clientX - panStartX;
      panY = e.clientY - panStartY;
      applyTransform();
    });
    
    window.addEventListener('mouseup', () => { isPanning = false; });
    
    function zoomIn() {
      const rect = scene.getBoundingClientRect();
      zoomAt(1.1, rect.left + rect.width / 2, rect.top + rect.height / 2);
    }
    function zoomOut() {
      const rect = scene.getBoundingClientRect();
      zoomAt(0.9, rect.left + rect.width / 2, rect.top + rect.height / 2);
    }
    function resetZoom() {
      panX = 0; panY = 0; scale = 1;
      applyTransform();
    }
    applyTransform();
    
    // Sidebar Logic
    function openSidebar(taskId) {
      const sidebar = document.getElementById('sidebar');
      const content = document.getElementById('sidebarContent');
      const taskDef = taskDefs[taskId];
      
      if (!taskDef) {
        content.innerHTML = '<p style="color: var(--text-muted);">No details available for this task.</p>';
        sidebar.classList.add('open');
        return;
      }
      
      let html = '';
      html += '<div class="task-prop"><div class="prop-label">Task Name</div><div class="prop-value">' + taskId.split('__').pop() + '</div></div>';
      
      const operators = ['td>', 'sh>', 'py>', 'echo>', 'call>', 'require>', 'loop>', 'for_each>'];
      let operator = 'unknown';
      for (const op of operators) {
        if (taskDef[op]) { operator = op; break; }
      }
      
      html += '<div class="task-prop"><div class="prop-label">Operator</div><div class="prop-value">' + operator + '</div></div>';
      
      if (taskDef[operator]) {
        let commandHtml = escapeHtml(String(taskDef[operator]));
        if (taskDef._url && taskDef._url !== '#') {
          commandHtml = '<a href="' + taskDef._url + '" target="_blank" style="color: var(--accent); text-decoration: underline;">' + commandHtml + '</a>';
        }
        html += '<div class="task-prop"><div class="prop-label">Command</div><div class="prop-value code">' + commandHtml + '</div></div>';
      }
      
      for (const [key, value] of Object.entries(taskDef)) {
        if (!operators.includes(key) && !key.startsWith('_') && !key.startsWith('+')) {
          html += '<div class="task-prop"><div class="prop-label">' + escapeHtml(key) + '</div><div class="prop-value">' + escapeHtml(JSON.stringify(value, null, 2)) + '</div></div>';
        }
      }
      
      content.innerHTML = html;
      sidebar.classList.add('open');
    }
    
    function closeSidebar() { document.getElementById('sidebar').classList.remove('open'); }
    
    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
    
    // Search Logic
    const searchInput = document.getElementById('searchInput');
    const nodes = Array.from(document.querySelectorAll('.node'));
    const edges = Array.from(document.querySelectorAll('.edge'));
    const nodeMap = new Map();
    let focusActive = false;
    let tourActive = false;
    
    nodes.forEach(node => {
      const title = node.querySelector('title');
      if (!title) return;
      const nodeId = title.textContent.trim();
      nodeMap.set(nodeId, node);
    });
    
    function clearFocus() {
      focusActive = false;
      nodes.forEach(n => n.classList.remove('dimmed', 'focused', 'highlighted', 'current', 'upstream', 'downstream'));
      edges.forEach(e => e.classList.remove('dimmed', 'upstream', 'downstream'));
    }
    
    function centerOnNode(nodeId) {
      const node = nodeMap.get(nodeId);
      if (!node) return;
      const rect = scene.getBoundingClientRect();
      const box = node.getBBox();
      const nodeCenterX = (box.x + box.width / 2) * scale;
      const nodeCenterY = (box.y + box.height / 2) * scale;
      panX = rect.width / 2 - nodeCenterX;
      panY = rect.height / 2 - nodeCenterY;
      applyTransform();
    }
    
    function updateHash(nodeId, isTour) {
      const params = new URLSearchParams();
      if (nodeId) params.set('node', nodeId);
      if (isTour) params.set('tour', '1');
      const hash = params.toString();
      if (hash) {
        history.replaceState(null, '', `#${hash}`);
      } else {
        history.replaceState(null, '', window.location.pathname + window.location.search);
      }
    }
    
    function focusNode(nodeId, options = {}) {
      const node = nodeMap.get(nodeId);
      if (!node) return false;
      focusActive = true;
      nodes.forEach(n => n.classList.add('dimmed'));
      edges.forEach(e => e.classList.add('dimmed'));
      node.classList.remove('dimmed');
      node.classList.add('focused');
      if (options.center) centerOnNode(nodeId);
      if (options.openSidebar) openSidebar(nodeId);
      if (options.setHash) updateHash(nodeId, options.tour);
      return true;
    }
    
    searchInput.addEventListener('input', (e) => {
      if (tourActive) return;
      const query = e.target.value.toLowerCase().trim();
      if (!query) {
        clearFocus();
        return;
      }
      
      nodes.forEach(node => {
        const title = node.querySelector('title');
        const text = title ? title.textContent.toLowerCase() : '';
        
        if (text.includes(query)) {
          node.classList.remove('dimmed');
          node.classList.add('highlighted');
        } else {
          node.classList.add('dimmed');
          node.classList.remove('highlighted');
        }
      });
      edges.forEach(edge => edge.classList.add('dimmed'));
    });
    
    // Dark Mode Logic
    const themeToggle = document.getElementById('themeToggle');
    const storedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
    
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
    });
    
    // Interaction Logic (Highlighting)
    const dependencyGraph = {};
    const reverseDependencyGraph = {};
    
    edges.forEach(edge => {
      const title = edge.querySelector('title');
      if (!title) return;
      const match = title.textContent.match(/(.+)->(.+)/);
      if (!match) return;
      
      const [, from, to] = match.map(s => s.trim());
      if (!dependencyGraph[from]) dependencyGraph[from] = [];
      if (!reverseDependencyGraph[to]) reverseDependencyGraph[to] = [];
      
      dependencyGraph[from].push(to);
      reverseDependencyGraph[to].push(from);
    });
    
    nodes.forEach(node => {
      const title = node.querySelector('title');
      if (!title) return;
      const nodeId = title.textContent.trim();
      
      node.addEventListener('mouseenter', () => {
        if (tourActive || focusActive) return;
        nodes.forEach(n => n.classList.add('dimmed'));
        edges.forEach(e => e.classList.add('dimmed'));
        
        node.classList.remove('dimmed');
        node.classList.add('current');
        
        const upstream = new Set();
        const queue = [nodeId];
        
        while (queue.length) {
          const current = queue.shift();
          const deps = reverseDependencyGraph[current] || [];
          deps.forEach(dep => {
            if (!upstream.has(dep)) { upstream.add(dep); queue.push(dep); }
          });
        }
        
        upstream.forEach(upId => {
          const upNode = nodes.find(n => n.querySelector('title')?.textContent.trim() === upId);
          if (upNode) { upNode.classList.remove('dimmed'); upNode.classList.add('upstream'); }
        });
        
        const downstream = new Set();
        const queue2 = [nodeId];
        
        while (queue2.length) {
          const current = queue2.shift();
          const deps = dependencyGraph[current] || [];
          deps.forEach(dep => {
            if (!downstream.has(dep)) { downstream.add(dep); queue2.push(dep); }
          });
        }
        
        downstream.forEach(downId => {
          const downNode = nodes.find(n => n.querySelector('title')?.textContent.trim() === downId);
          if (downNode) { downNode.classList.remove('dimmed'); downNode.classList.add('downstream'); }
        });
        
        edges.forEach(edge => {
          const edgeTitle = edge.querySelector('title');
          if (!edgeTitle) return;
          const match = edgeTitle.textContent.match(/(.+)->(.+)/);
          if (!match) return;
          
          const [, from, to] = match.map(s => s.trim());
          if (upstream.has(from) || from === nodeId) {
            edge.classList.remove('dimmed');
            edge.classList.add('upstream');
          }
          if (downstream.has(to) || to === nodeId) {
            edge.classList.remove('dimmed');
            edge.classList.add('downstream');
          }
        });
      });
      
      node.addEventListener('mouseleave', () => {
        if (tourActive || focusActive) return;
        nodes.forEach(n => n.classList.remove('dimmed', 'current', 'upstream', 'downstream'));
        edges.forEach(e => e.classList.remove('dimmed', 'upstream', 'downstream'));
      });
      
      node.addEventListener('click', () => {
        focusNode(nodeId, { openSidebar: true, setHash: true, center: false });
      });
    });
    
    function buildTourSteps() {
      const steps = [];
      const used = new Set();
      
      function addStep(id, title, text) {
        if (!id || used.has(id)) return;
        if (!nodeMap.has(id)) return;
        steps.push({ id, title, text });
        used.add(id);
      }
      
      const rootId = Array.from(nodeMap.keys()).find(id => id.endsWith('__root'));
      addStep(rootId, 'Workflow entry', 'This is the start of the workflow.');
      
      const tdId = Array.from(nodeMap.entries()).find(([, node]) => {
        const label = Array.from(node.querySelectorAll('text')).map(t => t.textContent).join(' ');
        const normalized = label.toLowerCase();
        return normalized.includes('[td>]') || normalized.includes('📊') || normalized.includes(' td>');
      });
      addStep(tdId ? tdId[0] : null, 'Treasure Data query', 'A td> task that reads or writes tables.');
      
      const errorId = Array.from(nodeMap.keys()).find(id => id.includes('__error'));
      addStep(errorId, 'Error handler', 'Fallback logic triggered when a task fails.');
      
      let maxNode = null;
      let maxDegree = -1;
      Object.entries(dependencyGraph).forEach(([id, outs]) => {
        if (id.endsWith('__root')) return;
        if (outs.length > maxDegree) {
          maxDegree = outs.length;
          maxNode = id;
        }
      });
      addStep(maxNode, 'Branching point', 'A task with multiple downstream dependencies.');
      
      const sinkId = Array.from(nodeMap.keys()).find(id => {
        if (id.endsWith('__root')) return false;
        return !dependencyGraph[id] || dependencyGraph[id].length === 0;
      });
      addStep(sinkId, 'Workflow end', 'A terminal task that closes the workflow.');
      
      return steps;
    }
    
    const tourPanel = document.getElementById('tourPanel');
    const tourBtn = document.getElementById('tourBtn');
    const tourCloseBtn = document.getElementById('tourCloseBtn');
    const tourPrevBtn = document.getElementById('tourPrevBtn');
    const tourNextBtn = document.getElementById('tourNextBtn');
    const tourStepEl = document.getElementById('tourStep');
    const tourTextEl = document.getElementById('tourText');
    const tourSteps = buildTourSteps();
    let tourIndex = 0;
    
    function showTourStep(index) {
      if (!tourSteps.length) return;
      tourIndex = Math.max(0, Math.min(index, tourSteps.length - 1));
      const step = tourSteps[tourIndex];
      tourStepEl.textContent = `Step ${tourIndex + 1} of ${tourSteps.length} - ${step.title}`;
      tourTextEl.textContent = step.text;
      focusNode(step.id, { openSidebar: true, setHash: true, center: true, tour: true });
      tourPrevBtn.disabled = tourIndex === 0;
      tourNextBtn.textContent = tourIndex === tourSteps.length - 1 ? 'Finish' : 'Next';
    }
    
    function openTour(startIndex = 0) {
      if (!tourSteps.length) return;
      tourActive = true;
      tourPanel.classList.add('open');
      showTourStep(startIndex);
    }
    
    function closeTour() {
      tourActive = false;
      tourPanel.classList.remove('open');
      clearFocus();
      updateHash(null, false);
    }
    
    if (tourBtn) {
      tourBtn.addEventListener('click', () => openTour(0));
    }
    if (tourCloseBtn) {
      tourCloseBtn.addEventListener('click', closeTour);
    }
    if (tourPrevBtn) {
      tourPrevBtn.addEventListener('click', () => showTourStep(tourIndex - 1));
    }
    if (tourNextBtn) {
      tourNextBtn.addEventListener('click', () => {
        if (tourIndex >= tourSteps.length - 1) {
          closeTour();
        } else {
          showTourStep(tourIndex + 1);
        }
      });
    }
    
    const copyLinkBtn = document.getElementById('copyLinkBtn');
    if (copyLinkBtn) {
      copyLinkBtn.addEventListener('click', async () => {
        const link = window.location.href;
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(link);
          } else {
            const tempInput = document.createElement('input');
            tempInput.value = link;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
          }
          copyLinkBtn.textContent = 'Copied';
          setTimeout(() => { copyLinkBtn.textContent = 'Copy Link'; }, 1000);
        } catch (e) {
          window.prompt('Copy this link:', link);
          copyLinkBtn.textContent = 'Copy failed';
          setTimeout(() => { copyLinkBtn.textContent = 'Copy Link'; }, 1000);
        }
      });
    }
    
    function handleHash() {
      const hash = window.location.hash.replace(/^#/, '');
      if (!hash) return;
      const params = new URLSearchParams(hash);
      const nodeId = params.get('node');
      const startTour = params.get('tour') === '1';
      if (nodeId) {
        focusNode(nodeId, { openSidebar: true, setHash: false, center: true, tour: startTour });
      }
      if (startTour) {
        openTour(0);
      }
    }
    
    window.addEventListener('hashchange', handleHash);
    handleHash();
  </script>
</body>
</html>
"""


class TemplateManager:
    """Manage Jinja2 templates for HTML output."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template manager.
        
        Args:
            template_dir: Optional custom template directory
        """
        self.template_dir = template_dir
        self.env = self._create_environment()
    
    def _create_environment(self) -> Environment:
        """Create Jinja2 environment.
        
        Returns:
            Configured Jinja2 Environment
        """
        if self.template_dir and self.template_dir.exists():
            logger.info(f"Using custom templates from {self.template_dir}")
            return Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            # Check for bundled templates
            bundled_templates = Path(__file__).parent.parent.parent / "templates"
            if bundled_templates.exists():
                logger.debug(f"Using bundled templates from {bundled_templates}")
                return Environment(
                    loader=FileSystemLoader(str(bundled_templates)),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            else:
                # Use embedded templates
                logger.debug("Using embedded templates")
                return Environment(autoescape=select_autoescape(['html', 'xml']))
    
    def get_template(self, name: str) -> Template:
        """Get a template by name.
        
        Args:
            name: Template name (e.g., 'schedule.html.j2')
        
        Returns:
            Jinja2 Template instance
        """
        try:
            return self.env.get_template(name)
        except Exception:
            # Fall back to embedded templates
            logger.debug(f"Template {name} not found, using embedded default")
            if name == 'schedule.html.j2':
                return self.env.from_string(DEFAULT_SCHEDULE_TEMPLATE)
            elif name == 'index.html.j2':
                return self.env.from_string(DEFAULT_INDEX_TEMPLATE)
            elif name == 'unscheduled.html.j2':
                return self.env.from_string(DEFAULT_UNSCHEDULED_TEMPLATE)
            elif name == 'lineage.html.j2':
                return self.env.from_string(DEFAULT_LINEAGE_TEMPLATE)
            elif name == 'interactive.html.j2':
                return self.env.from_string(DEFAULT_INTERACTIVE_TEMPLATE)
            else:
                raise ConfigurationError(f"Template not found: {name}")
    
    def render_schedule_page(self, items: List[Dict[str, str]], output_path: Path):
        """Render schedule page.
        
        Args:
            items: List of schedule items
            output_path: Output file path
        """
        template = self.get_template('schedule.html.j2')
        
        # Extract unique projects for filter dropdown
        projects = sorted(set(item.get('project', 'unknown') for item in items))
        
        html = template.render(items=items, projects=projects)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated schedule page: {output_path}")
    
    def render_index_page(self, workflows: List[Dict[str, Any]], output_path: Path):
        """Render index page.
        
        Args:
            workflows: List of workflow information
            output_path: Output file path
        """
        template = self.get_template('index.html.j2')
        scheduled = [wf for wf in workflows if wf.get('schedule')]
        
        # Extract unique projects for filter dropdown
        projects = sorted(set(wf.get('project', 'unknown') for wf in workflows))
        
        html = template.render(workflows=workflows, scheduled_workflows=scheduled, projects=projects)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated index page: {output_path}")
    
    def render_unscheduled_page(self, workflows: List[Dict[str, Any]], output_path: Path):
        """Render unscheduled workflows page.
        
        Args:
            workflows: List of workflow information
            output_path: Output file path
        """
        template = self.get_template('unscheduled.html.j2')
        unscheduled = [wf for wf in workflows if not wf.get('schedule')]
        
        # Extract unique projects for filter dropdown
        projects = sorted(set(wf.get('project', 'unknown') for wf in unscheduled))
        
        html = template.render(workflows=unscheduled, projects=projects)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated unscheduled workflows page: {output_path}")
    
    def render_lineage_page(self, lineage_data: List[Dict[str, Any]], output_path: Path):
        """Render data lineage page.
        
        Args:
            lineage_data: List of table lineage information
            output_path: Output file path
        """
        template = self.get_template('lineage.html.j2')
        
        # Extract unique databases for filter dropdown
        databases = sorted(set(
            table['database'] for table in lineage_data 
            if table.get('database')
        ))
        
        html = template.render(tables=lineage_data, databases=databases)
        output_path.write_text(html, encoding='utf-8')
        html = template.render(tables=lineage_data, databases=databases)
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated lineage page: {output_path}")

    def render_interactive_graph(
        self,
        wf_name: str,
        svg_content: str,
        task_defs: str,
        output_path: Path,
        summary: Optional[Dict[str, Any]] = None
    ):
        """Render interactive workflow graph.
        
        Args:
            wf_name: Workflow name
            svg_content: SVG content string
            task_defs: JSON string of task definitions
            output_path: Output file path
            summary: Optional summary data for badges
        """
        template = self.get_template('interactive.html.j2')
        task_defs_json = task_defs
        if not isinstance(task_defs, str):
            task_defs_json = json.dumps(task_defs, ensure_ascii=True, default=str)
        html = template.render(
            wf_name=wf_name,
            svg_content=svg_content,
            task_defs=task_defs_json,
            summary=summary
        )
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"Generated interactive graph: {output_path}")


# Default embedded template for lineage page
DEFAULT_LINEAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Data Lineage - Digdag Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --font-sans: "Inter", "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
      --gray-50: #f7fafc;
      --gray-100: #edf2f7;
      --gray-200: #e2e8f0;
      --gray-300: #cbd5e0;
      --gray-600: #4a5568;
      --gray-800: #1a202c;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);

      /* Light Mode Colors */
      --bg-body: #ffffff;
      --bg-main: #f7fafc;
      --bg-card: #ffffff;
      --bg-sidebar: #ffffff;
      --bg-header: #1a365d;
      --text-main: #1a202c;
      --text-muted: #4a5568;
      --border-color: #e2e8f0;
      --shadow-color: rgba(0, 0, 0, 0.1);
    }

    /* Dark Mode Colors */
    [data-theme="dark"] {
      --bg-body: #171923;
      --bg-main: #1a202c;
      --bg-card: #2d3748;
      --bg-sidebar: #2d3748;
      --bg-header: #2d3748;
      --text-main: #f7fafc;
      --text-muted: #a0aec0;
      --border-color: #4a5568;
      --shadow-color: rgba(0, 0, 0, 0.4);
      --gray-50: #2d3748;
      --gray-100: #4a5568;
      --gray-200: #4a5568;
      --gray-600: #a0aec0;
      --gray-800: #f7fafc;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-sans);
      background: var(--bg-body); color: var(--text-main); font-size: 14px; line-height: 1.5;
      min-height: 100vh; display: flex; flex-direction: column;
      transition: background 0.3s ease, color 0.3s ease;
    }
    header { 
      padding: 0 32px; height: 64px; background: var(--bg-header);
      border-bottom: 1px solid rgba(0,0,0,0.1); display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: 0 2px 4px var(--shadow-color); position: sticky; top: 0; z-index: 1000;
      transition: background 0.3s ease;
    }
    .brand { 
      font-weight: 600; font-size: 18px; color: white;
      text-decoration: none; display: flex; align-items: center; gap: 12px;
    }
    .brand-icon {
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 6px; display: flex; align-items: center;
      justify-content: center; font-weight: 700; font-size: 16px; color: white;
    }
    .nav-links { display: flex; gap: 4px; }
    .nav-links a { 
      color: rgba(255, 255, 255, 0.9); text-decoration: none; 
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }
    .nav-links a:hover { background: rgba(255,255,255,0.1); color: white; }
    .nav-links a.active { background: var(--accent); color: white; }
    
    .header-controls { display: flex; align-items: center; gap: 16px; }
    .theme-toggle {
      background: rgba(255,255,255,0.1); border: none; cursor: pointer;
      color: white; padding: 8px; border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s;
    }
    .theme-toggle:hover { background: rgba(255,255,255,0.2); }
    
    main { flex: 1; padding: 32px; max-width: 1400px; width: 100%; margin: 0 auto; background: var(--bg-body); transition: background 0.3s ease; }
    h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--text-main); }
    .subtitle { color: var(--text-muted); margin-bottom: 24px; }
    
    .controls { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
    input[type="search"], select {
      background: var(--bg-card); color: var(--text-main); border: 1px solid var(--border-color);
      border-radius: 6px; padding: 10px 14px; outline: none; font-family: var(--font-sans);
      font-size: 14px; transition: all 0.2s;
    }
    input[type="search"] { flex: 1; min-width: 250px; }
    input[type="search"]:focus, select:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1); }
    input[type="search"]::placeholder { color: var(--text-muted); }
    select { padding-right: 32px; }
    
    table { width: 100%; border-collapse: separate; border-spacing: 0; 
      border: 1px solid var(--border-color); border-radius: 8px;
      background: var(--bg-card); box-shadow: 0 2px 4px var(--shadow-color);
    }
    thead th { 
      background: var(--gray-50); border-bottom: 1px solid var(--border-color);
      text-align: left; padding: 14px 16px; font-weight: 600; font-size: 13px;
      color: var(--text-main); position: sticky; top: 64px; z-index: 1;
    }
    tbody tr { background: var(--bg-card); transition: background 0.15s; }
    tbody tr:nth-child(even) { background: var(--gray-50); }
    tbody tr:hover { background: var(--gray-100); }
    tbody td { padding: 14px 16px; border-bottom: 1px solid var(--border-color); vertical-align: top; }
    tbody tr:last-child td { border-bottom: none; }
    
    code { 
      background: var(--gray-100); padding: 3px 8px; border-radius: 4px;
      font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
      color: var(--text-main); display: inline-block;
    }
    
    .badge {
      display: inline-block; padding: 4px 10px; border-radius: 12px;
      font-size: 12px; font-weight: 500;
    }
    .badge-source { background: #FED7AA; color: #7C2D12; }
    .badge-staging { background: #BFDBFE; color: #1E3A8A; }
    .badge-golden { background: #BBF7D0; color: #14532D; }
    .badge-other { background: var(--gray-200); color: var(--gray-800); }
    
    a.view-btn {
      display: inline-block; padding: 6px 14px; background: var(--accent);
      color: white; text-decoration: none; border-radius: 6px;
      font-size: 13px; font-weight: 500; transition: all 0.2s;
    }
    a.view-btn:hover { background: var(--primary-light); }
    
    .empty-state {
      text-align: center; padding: 64px 32px; color: var(--text-muted);
    }
    .empty-state svg {
      width: 64px; height: 64px; margin-bottom: 16px; opacity: 0.5;
    }
  </style>
</head>
<body>

<header>
  <a href="index.html" class="brand">
    <div class="brand-icon">DG</div>
    <span>Digdag Graph</span>
  </a>
  
  <div class="header-controls">
    <nav class="nav-links">
      <a href="index.html">Home</a>
      <a href="index.html">Workflows</a>
      <a href="scheduled_workflows.html">Scheduled</a>
      <a href="unscheduled_workflows.html">Unscheduled</a>
      <a href="lineage.html" class="active">Lineage</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" title="Toggle Dark Mode">
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    </button>
  </div>
</header>

<main>
  <h1>📊 Data Lineage</h1>
  <p class="subtitle">Trace table dependencies across workflows</p>

  <div class="controls">
    <input type="search" id="search" placeholder="Search tables...">
    <select id="database-filter">
      <option value="">All Databases</option>
      {% for db in databases %}
      <option value="{{ db }}">{{ db }}</option>
      {% endfor %}
    </select>
    <a href="lineage/full_lineage.html" class="view-btn" style="margin-left: auto;">🌐 View Full Lineage Graph</a>
  </div>

  {% if tables %}
  <table id="lineage-table">
    <thead>
      <tr>
        <th>Table</th>
        <th>Database</th>
        <th>Upstream</th>
        <th>Downstream</th>
        <th>Workflows</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for table in tables %}
      <tr data-database="{{ table.database or '' }}">
        <td><code>{{ table.name }}</code></td>
        <td>
          {% if table.database %}
            {% if table.layer %}
              <span class="badge" style="background-color: {{ table.layer.color }}; color: #333; border: 1px solid #ccc;">{{ table.database }}</span>
            {% else %}
              <span class="badge badge-other">{{ table.database }}</span>
            {% endif %}
          {% else %}
            <span class="badge badge-other">-</span>
          {% endif %}
        </td>
        <td>{{ table.upstream_count or 0 }}</td>
        <td>{{ table.downstream_count or 0 }}</td>
        <td>{{ table.workflow_count or 0 }}</td>
        <td>
          {% if table.graph_path %}
          <a href="{{ table.graph_path }}" class="view-btn" target="_blank">View Graph</a>
          {% else %}
          <span style="color: var(--text-muted); font-size: 13px;">No graph</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty-state">
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
    </svg>
    <p>No lineage data available</p>
    <p style="font-size: 13px; margin-top: 8px;">Run with --lineage-all to generate lineage data</p>
  </div>
  {% endif %}
</main>

<script>
(function() {
  const q = document.getElementById('search');
  const dbFilter = document.getElementById('database-filter');
  const table = document.getElementById('lineage-table');
  
  function apply() {
    if (!table) return;
    
    const query = q.value.toLowerCase();
    const db = dbFilter.value.toLowerCase();
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      const rowDb = row.dataset.database.toLowerCase();
      const matchesQuery = !query || text.includes(query);
      const matchesDb = !db || rowDb.includes(db);
      row.style.display = (matchesQuery && matchesDb) ? '' : 'none';
    });
  }

  if (q && dbFilter) {
    q.addEventListener('input', apply);
    dbFilter.addEventListener('change', apply);
  }
  
  // Dark Mode Logic
  const themeToggle = document.getElementById('themeToggle');
  const storedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
    });
  }
})();
</script>

</body>
</html>
"""
