/*
  Cascade AI Dashboard — Complete JavaScript
  Data fetching, parsing, state management, and DOM rendering.
  No external dependencies. Vanilla JS only.
  Designed to be dropped into a <script> tag at the bottom of <body>.
*/

// ============================================================
// 1. DATA FETCHERS
// ============================================================

/**
 * Fetch health endpoint. Returns JSON or null on error.
 */
async function fetchHealth() {
  try {
    const res = await fetch('/health');
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

/**
 * Fetch logs endpoint. Returns {lines: [...]} or null on error.
 */
async function fetchLogs() {
  try {
    const res = await fetch('/logs');
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

/**
 * Fetch text content from a relative path.
 * e.g. fetchFile('logs/x402_spend.json')
 */
async function fetchFile(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) return null;
    return await res.text();
  } catch (e) {
    return null;
  }
}

// ============================================================
// 2. JSONL PARSER
// ============================================================

/**
 * Parse JSONL text: split by newline, JSON.parse each line, filter out nulls.
 */
function parseJSONL(text) {
  if (!text) return [];
  const lines = text.split('\n');
  const result = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    try {
      const obj = JSON.parse(line);
      if (obj !== null) result.push(obj);
    } catch (e) {
      // Skip malformed lines
    }
  }
  return result;
}

// ============================================================
// 3. GLOBAL STATE
// ============================================================

const state = {
  health: {},
  decisions: [],
  x402Spend: {},
  x402Calls: [],
  positions: [],
  trades: [],
  logs: [],
  startTime: Date.now(),
  lastCycle: null,
};

// ============================================================
// 4. FORMATTERS
// ============================================================

const fmt = {
  /**
   * HH:MM:SS from ISO string or timestamp.
   */
  time(ts) {
    if (!ts) return '--:--:--';
    let d;
    if (typeof ts === 'number') {
      d = new Date(ts);
    } else {
      d = new Date(ts);
    }
    if (isNaN(d.getTime())) return '--:--:--';
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    const s = String(d.getSeconds()).padStart(2, '0');
    return `${h}:${m}:${s}`;
  },

  /**
   * "Xs ago", "Xm ago", "Xh ago" from ISO string or timestamp.
   */
  ago(ts) {
    if (!ts) return 'Never';
    let d;
    if (typeof ts === 'number') {
      d = new Date(ts);
    } else {
      d = new Date(ts);
    }
    if (isNaN(d.getTime())) return 'Never';
    const now = Date.now();
    const diff = Math.floor((now - d.getTime()) / 1000);
    if (diff < 0) return 'Now';
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  },

  /**
   * "$0.00" with 2 decimals.
   */
  usd(n) {
    if (n === null || n === undefined || isNaN(n)) return '$0.00';
    const num = Number(n);
    return '$' + num.toFixed(2);
  },

  /**
   * "+0.00%" or "-0.00%"
   */
  pct(n) {
    if (n === null || n === undefined || isNaN(n)) return '+0.00%';
    const num = Number(n);
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
  },

  /**
   * Comma-separated integer.
   */
  num(n) {
    if (n === null || n === undefined || isNaN(n)) return '0';
    return Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 });
  },
};

// ============================================================
// 5. RENDER FUNCTIONS
// ============================================================

/**
 * Helper: safely get element by ID, return null if not found.
 */
function el(id) {
  return document.getElementById(id) || null;
}

/**
 * Helper: set text content of an element if it exists.
 */
function setText(id, text) {
  const element = el(id);
  if (element) element.textContent = text;
}

/**
 * Helper: set HTML content of an element if it exists.
 */
function setHTML(id, html) {
  const element = el(id);
  if (element) element.innerHTML = html;
}

/**
 * Helper: remove all classes and add a single class.
 */
function setClass(id, className) {
  const element = el(id);
  if (!element) return;
  element.className = className;
}

// ------------------------------------------------------------
// 5.1 renderStatusBar
// ------------------------------------------------------------

function renderStatusBar() {
  const health = state.health || {};
  const status = health.status || 'offline';
  const mode = health.mode || 'paper';
  const lastCycle = health.last_cycle || state.lastCycle || null;
  const positions = health.positions || 0;
  const drawdown = health.drawdown_pct || 0;

  // Status dot and text
  const dot = el('status-dot');
  if (dot) {
    dot.className = 'glow-dot';
    if (status === 'running' || status === 'online') {
      dot.style.color = 'var(--green)';
      dot.style.background = 'var(--green)';
    } else if (status === 'starting' || status === 'initializing') {
      dot.style.color = 'var(--accent)';
      dot.style.background = 'var(--accent)';
    } else {
      dot.style.color = 'var(--red)';
      dot.style.background = 'var(--red)';
    }
  }

  const statusText = el('status-text');
  if (statusText) {
    statusText.textContent = status === 'running' || status === 'online'
      ? 'Online'
      : status === 'starting' || status === 'initializing'
      ? 'Starting'
      : 'Offline';
  }

  // Mode badge
  const modeBadge = el('mode-badge');
  if (modeBadge) {
    if (mode === 'live' || mode === 'Live') {
      modeBadge.textContent = '🔴 Live';
      modeBadge.style.color = 'var(--red)';
    } else {
      modeBadge.textContent = '🧪 Paper';
      modeBadge.style.color = 'var(--blue)';
    }
  }

  // Last cycle
  setText('last-cycle', lastCycle ? fmt.ago(lastCycle) : 'Never');

  // Positions count
  setText('positions-count', String(positions));

  // Drawdown with color class
  const drawdownEl = el('drawdown');
  if (drawdownEl) {
    drawdownEl.textContent = fmt.pct(drawdown);
    if (drawdown < 5) {
      drawdownEl.className = 'green';
    } else if (drawdown <= 10) {
      drawdownEl.className = 'yellow';
    } else {
      drawdownEl.className = 'red';
    }
  }
}

// ------------------------------------------------------------
// 5.2 renderBudget
// ------------------------------------------------------------

function renderBudget() {
  const spend = state.x402Spend || {};
  const dailyBudget = spend.daily_budget_usdc || 0;
  const dailySpend = spend.daily_spend_usdc || 0;
  const totalSpend = spend.total_spend_usdc || 0;
  const remaining = Math.max(0, dailyBudget - dailySpend);

  // Calculate calls today from x402Calls
  const calls = state.x402Calls || [];
  let callsToday = 0;
  if (calls.length > 0) {
    // Try to count calls with today's date or just total if no date filtering
    callsToday = calls.length;
  }
  // If health has daily_trades, use that as fallback
  if (state.health && state.health.daily_trades) {
    callsToday = state.health.daily_trades;
  }

  // Budget metrics
  setText('budget-daily', fmt.usd(dailyBudget));
  setText('budget-spent', fmt.usd(dailySpend));
  setText('budget-remaining', fmt.usd(remaining));
  setText('total-spend', fmt.usd(totalSpend));
  setText('calls-today', fmt.num(callsToday));

  // Budget fill bar
  const fillPct = dailyBudget > 0 ? Math.min(100, (dailySpend / dailyBudget) * 100) : 0;
  const fillEl = el('budget-fill');
  if (fillEl) {
    fillEl.style.width = `${fillPct}%`;
    fillEl.classList.remove('filled', 'yellow', 'red');
    if (fillPct >= 100) {
      fillEl.classList.add('red');
    } else if (fillPct >= 80) {
      fillEl.classList.add('yellow');
    } else {
      fillEl.classList.add('filled');
    }
  }

  // Budget badge
  const badgeEl = el('budget-badge');
  if (badgeEl) {
    if (fillPct >= 100) {
      badgeEl.textContent = 'Exhausted';
      badgeEl.className = 'red';
    } else if (fillPct >= 80) {
      badgeEl.textContent = 'Throttling';
      badgeEl.className = 'yellow';
    } else {
      badgeEl.textContent = 'Healthy';
      badgeEl.className = 'green';
    }
  }

  // Circuit status (derived from risk_state or health status)
  const circuitEl = el('circuit-status');
  if (circuitEl) {
    const riskState = state.health && state.health.risk_state ? state.health.risk_state : 'normal';
    if (riskState === 'kill_switch' || riskState === 'tripped' || fillPct >= 100) {
      circuitEl.textContent = 'Tripped';
      circuitEl.className = 'red';
    } else {
      circuitEl.textContent = 'Active';
      circuitEl.className = 'green';
    }
  }
}

// ------------------------------------------------------------
// 5.3 renderDataQuality
// ------------------------------------------------------------

function renderDataQuality() {
  const health = state.health || {};
  const decisions = state.decisions || [];
  const lastDecision = decisions.length > 0 ? decisions[decisions.length - 1] : null;
  const lastTs = lastDecision ? lastDecision.timestamp : null;

  // Snapshot age
  setText('snapshot-age', lastTs ? fmt.ago(lastTs) : 'No data');

  // Determine data source from last decision or health
  let source = 'keyless-only';
  let badgeText = 'Keyless';
  let badgeClass = 'muted';

  if (lastDecision) {
    if (lastDecision.x402_enriched === true || lastDecision.mode === 'x402') {
      source = 'x402-enriched';
      badgeText = 'x402';
      badgeClass = 'purple';
    } else if (lastDecision.mode === 'keyless' || lastDecision.mode === 'paper') {
      source = 'keyless-only';
      badgeText = 'Keyless';
      badgeClass = 'muted';
    }
  }
  if (health.mode === 'live' && health.sentiment_fgi) {
    source = 'x402-enriched';
    badgeText = 'x402';
    badgeClass = 'purple';
  }

  setText('data-source', source);
  const dataBadge = el('data-badge');
  if (dataBadge) {
    dataBadge.textContent = badgeText;
    dataBadge.className = badgeClass;
  }

  // Regime
  const regime = lastDecision ? (lastDecision.regime || 'N/A') : (health.regime || 'N/A');
  setText('regime', String(regime));

  // FGI
  const fgi = health.sentiment_fgi || (lastDecision ? lastDecision.sentiment_fgi : null) || 'N/A';
  setText('fgi', String(fgi));

  // Strategy
  const strategy = lastDecision ? (lastDecision.strategy || lastDecision.mode || 'N/A') : (health.strategy || 'N/A');
  setText('strategy', String(strategy));

  // Technicals
  const technicals = lastDecision ? (lastDecision.technicals || lastDecision.reasons || 'N/A') : 'N/A';
  setText('technicals', String(technicals));

  // Risk state
  const riskState = lastDecision ? (lastDecision.risk_state || 'normal') : (health.risk_state || 'normal');
  const riskEl = el('risk-state');
  if (riskEl) {
    riskEl.textContent = String(riskState);
    if (riskState === 'kill_switch' || riskState === 'critical') {
      riskEl.className = 'red';
    } else if (riskState === 'throttle' || riskState === 'warning') {
      riskEl.className = 'yellow';
    } else {
      riskEl.className = 'green';
    }
  }
}

// ------------------------------------------------------------
// 5.4 renderPositions
// ------------------------------------------------------------

function renderPositions() {
  const positions = state.positions || [];
  const body = el('positions-body');
  if (!body) return;

  // Update badge
  const badge = el('pos-badge');
  if (badge) {
    badge.textContent = String(positions.length);
  }

  if (positions.length === 0) {
    // Empty state
    body.innerHTML = `
      <div class="empty-state">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
        <p>No open positions</p>
        <span class="muted">Waiting for next cycle...</span>
      </div>
    `;
    return;
  }

  // Calculate portfolio value
  let portfolioValue = 0;
  let totalPnl = 0;

  // Build table rows
  let rows = '';
  for (let i = 0; i < positions.length; i++) {
    const p = positions[i];
    const symbol = p.symbol || 'N/A';
    const entry = p.entry_price || p.entry || 0;
    const size = p.size || p.quantity || 0;
    const pnlPct = p.pnl_pct || p.unrealized_pnl_pct || 0;
    const pnlClass = pnlPct >= 0 ? 'pos' : 'neg';

    portfolioValue += (p.portfolio_value_usdc || p.value || 0);
    totalPnl += pnlPct;

    rows += `
      <tr>
        <td>${symbol}</td>
        <td>${fmt.usd(entry)}</td>
        <td>${fmt.num(size)}</td>
        <td class="${pnlClass}">${fmt.pct(pnlPct)}</td>
      </tr>
    `;
  }

  body.innerHTML = `
    <table class="positions-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Entry</th>
          <th>Size</th>
          <th>P&L%</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
      <tfoot>
        <tr class="summary">
          <td colspan="2"><strong>Portfolio</strong></td>
          <td colspan="2" class="${totalPnl >= 0 ? 'pos' : 'neg'}">${fmt.pct(totalPnl)}</td>
        </tr>
      </tfoot>
    </table>
  `;
}

// ------------------------------------------------------------
// 5.5 renderROI
// ------------------------------------------------------------

function renderROI() {
  const trades = state.trades || [];
  const spend = state.x402Spend || {};
  const totalSpend = spend.total_spend_usdc || 0;

  // Calculate metrics from trades
  let totalPnl = 0;
  let x402Wins = 0;
  let x402Total = 0;
  let keylessWins = 0;
  let keylessTotal = 0;
  let closedCount = 0;
  const pnlValues = [];

  for (let i = 0; i < trades.length; i++) {
    const t = trades[i];
    if (t.event === 'CLOSE' || t.exit_price) {
      closedCount++;
      const pnl = t.realized_pnl_usdc || t.pnl_usdc || 0;
      totalPnl += pnl;
      pnlValues.push(pnl);

      if (t.x402_enriched === true) {
        x402Total++;
        if (pnl > 0) x402Wins++;
      } else {
        keylessTotal++;
        if (pnl > 0) keylessWins++;
      }
    }
  }

  const net = totalPnl - totalSpend;

  // Set metrics
  setText('roi-spend', fmt.usd(totalSpend));
  setText('roi-pnl', fmt.usd(totalPnl));

  const netEl = el('roi-net');
  if (netEl) {
    netEl.textContent = fmt.usd(net);
    netEl.className = net >= 0 ? 'pos' : 'neg';
  }

  const x402Rate = x402Total > 0 ? ((x402Wins / x402Total) * 100) : 0;
  const keylessRate = keylessTotal > 0 ? ((keylessWins / keylessTotal) * 100) : 0;

  setText('win-x402', fmt.pct(x402Rate));
  setText('win-keyless', fmt.pct(keylessRate));
  setText('trades-closed', fmt.num(closedCount));

  // ROI badge
  const badgeEl = el('roi-badge');
  if (badgeEl) {
    if (closedCount >= 3) {
      badgeEl.textContent = 'Analyzed';
      badgeEl.className = 'green';
    } else {
      badgeEl.textContent = 'Pending';
      badgeEl.className = 'yellow';
    }
  }

  // ROI chart: 10 bar divs, height proportional to average P&L in chunks
  const chartEl = el('roi-chart');
  if (chartEl) {
    if (pnlValues.length === 0) {
      chartEl.innerHTML = '<div class="empty-chart">No trade data yet</div>';
    } else {
      const chunkSize = Math.max(1, Math.ceil(pnlValues.length / 10));
      let bars = '';
      for (let i = 0; i < 10; i++) {
        const start = i * chunkSize;
        const end = Math.min(start + chunkSize, pnlValues.length);
        if (start >= pnlValues.length) break;

        let chunkSum = 0;
        for (let j = start; j < end; j++) {
          chunkSum += pnlValues[j];
        }
        const avg = chunkSum / (end - start);
        const maxVal = Math.max(...pnlValues.map(Math.abs));
        const heightPct = maxVal > 0 ? Math.min(100, (Math.abs(avg) / maxVal) * 100) : 0;
        const barClass = avg >= 0 ? 'pos' : 'neg';

        bars += `<div class="bar ${barClass}" style="height:${heightPct}%;" title="Avg: ${fmt.usd(avg)}"></div>`;
      }
      chartEl.innerHTML = bars;
    }
  }
}

// ------------------------------------------------------------
// 5.6 renderDecisions
// ------------------------------------------------------------

function renderDecisions() {
  const tbody = el('decision-tbody');
  if (!tbody) return;

  const decisions = state.decisions || [];
  const count = decisions.length;

  // Update badge
  setText('decision-count', fmt.num(count));

  if (count === 0) {
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="7" style="text-align:center; padding:2rem 0;">
          <div class="empty-state">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 8v4M12 16h.01"/>
            </svg>
            <p>No decisions yet</p>
            <span class="muted">Cycle is running...</span>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  // Last 15 decisions, reversed (newest first)
  const recent = decisions.slice(-15).reverse();

  let rows = '';
  for (let i = 0; i < recent.length; i++) {
    const d = recent[i];
    const ts = d.timestamp || d.ts || '';
    const action = (d.action || 'WAIT').toUpperCase();
    const symbol = d.symbol || 'N/A';
    const regime = d.regime || 'N/A';
    const score = d.entry_score || d.score || '-';
    const reasons = d.reasons || d.reason || '';
    const mode = d.mode || 'paper';
    const riskState = d.risk_state || 'normal';

    let actionClass = 'muted';
    if (action === 'ENTER') actionClass = 'green';
    else if (action === 'EXIT') actionClass = 'red';
    else if (action === 'HALT') actionClass = 'red';
    else if (action === 'WAIT') actionClass = 'muted';

    const reasonText = String(reasons);
    const truncated = reasonText.length > 40 ? reasonText.substring(0, 40) + '…' : reasonText;

    rows += `
      <tr>
        <td class="muted">${fmt.time(ts)}</td>
        <td class="${actionClass}">${action}</td>
        <td>${symbol}</td>
        <td>${regime}</td>
        <td>${score}</td>
        <td title="${reasonText}">${truncated}</td>
        <td class="muted">${mode}</td>
      </tr>
    `;
  }

  tbody.innerHTML = rows;
}

// ------------------------------------------------------------
// 5.7 renderTerminal
// ------------------------------------------------------------

function renderTerminal() {
  const terminal = el('terminal');
  if (!terminal) return;

  const logs = state.logs || [];
  setText('log-badge', fmt.num(logs.length));

  if (logs.length === 0) {
    terminal.innerHTML = '<div class="log-line muted"><span class="log-time">--:--:--</span> <span class="log-msg">Waiting for logs...</span></div>';
    return;
  }

  // Last 12 log lines
  const recent = logs.slice(-12);

  let html = '';
  for (let i = 0; i < recent.length; i++) {
    const line = recent[i];
    let ts = '';
    let msg = line;

    // Try to extract timestamp from beginning of log line (ISO or HH:MM:SS)
    const timeMatch = line.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\d\.Z+-]*)/);
    if (timeMatch) {
      ts = fmt.time(timeMatch[1]);
      msg = line.substring(timeMatch[0].length).trim();
    } else {
      const shortMatch = line.match(/^(\d{2}:\d{2}:\d{2})/);
      if (shortMatch) {
        ts = shortMatch[1];
        msg = line.substring(8).trim();
      }
    }

    // If no timestamp found, use current time approximation
    if (!ts) {
      ts = fmt.time(Date.now() - (recent.length - i) * 1000);
      msg = line;
    }

    // Color-code the message
    let msgClass = '';
    const upperMsg = msg.toUpperCase();
    if (upperMsg.includes('ERROR') || upperMsg.includes('FAIL') || upperMsg.includes('KILL')) {
      msgClass = 'red';
    } else if (upperMsg.includes('WARN') || upperMsg.includes('THROTTLE')) {
      msgClass = 'yellow';
    } else if (upperMsg.includes('ENTER') || upperMsg.includes('PROFIT') || upperMsg.includes('WIN')) {
      msgClass = 'green';
    } else if (upperMsg.includes('EXIT') || upperMsg.includes('LOSS')) {
      msgClass = 'red';
    }

    // Try to parse JSON in the message for better coloring
    let coloredMsg = msg;
    try {
      const jsonStart = msg.indexOf('{');
      if (jsonStart !== -1) {
        const jsonStr = msg.substring(jsonStart);
        const jsonObj = JSON.parse(jsonStr);
        coloredMsg = msg.substring(0, jsonStart) + colorizeJSON(jsonObj);
      }
    } catch (e) {
      // Not JSON, color inline key=value pairs
      coloredMsg = colorizeInline(msg);
    }

    html += `<div class="log-line ${msgClass}"><span class="log-time">${ts}</span> <span class="log-msg">${coloredMsg}</span></div>`;
  }

  terminal.innerHTML = html;

  // Auto-scroll to bottom
  terminal.scrollTop = terminal.scrollHeight;
}

/**
 * Colorize a JSON object as HTML spans.
 */
function colorizeJSON(obj) {
  const pairs = [];
  const keys = Object.keys(obj);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const v = obj[k];
    let valStr = '';
    if (typeof v === 'number') {
      valStr = `<span class="${v >= 0 ? 'green' : 'red'}">${v}</span>`;
    } else if (typeof v === 'string') {
      if (v.toUpperCase() === 'ENTER' || v.toUpperCase() === 'BUY') {
        valStr = `<span class="green">"${v}"</span>`;
      } else if (v.toUpperCase() === 'EXIT' || v.toUpperCase() === 'SELL') {
        valStr = `<span class="red">"${v}"</span>`;
      } else {
        valStr = `<span class="">"${v}"</span>`;
      }
    } else {
      valStr = String(v);
    }
    pairs.push(`<span class="purple">${k}</span>: ${valStr}`);
  }
  return `{ ${pairs.join(', ')} }`;
}

/**
 * Colorize inline key=value pairs in a log line.
 */
function colorizeInline(msg) {
  // Color P&L values like +1.23% or -0.45%
  let result = msg;
  result = result.replace(/(\+[\d.]+)%/g, '<span class="green">+$1%</span>');
  result = result.replace(/(-[\d.]+)%/g, '<span class="red">-$1%</span>');
  result = result.replace(/(\$[\d.]+)/g, '<span class="">$1</span>');
  result = result.replace(/(action=)(\w+)/gi, '$1<span class="green">$2</span>');
  result = result.replace(/(symbol=)(\w+)/gi, '$1<span class="purple">$2</span>');
  result = result.replace(/(pnl=)([\d.-]+)/gi, (m, p1, p2) => {
    const n = parseFloat(p2);
    return `${p1}<span class="${n >= 0 ? 'green' : 'red'}">${p2}</span>`;
  });
  return result;
}

// ============================================================
// 6. MASTER LOADER
// ============================================================

async function loadAll() {
  // Fetch all data sources in parallel
  const [
    healthData,
    logsData,
    spendText,
    callsText,
    decisionsText,
    positionsText,
    tradesText,
  ] = await Promise.all([
    fetchHealth(),
    fetchLogs(),
    fetchFile('logs/x402_spend.json'),
    fetchFile('logs/x402_calls.jsonl'),
    fetchFile('logs/decision_live.jsonl'),
    fetchFile('logs/portfolio_snapshots.jsonl'),
    fetchFile('logs/trade_outcomes.jsonl'),
  ]);

  // Update state: health
  if (healthData) {
    state.health = healthData;
    if (healthData.last_cycle) {
      state.lastCycle = healthData.last_cycle;
    }
  }

  // Update state: logs
  if (logsData && Array.isArray(logsData.lines)) {
    state.logs = logsData.lines;
  } else {
    state.logs = [];
  }

  // Update state: x402 spend
  if (spendText) {
    try {
      state.x402Spend = JSON.parse(spendText);
    } catch (e) {
      state.x402Spend = {};
    }
  } else {
    state.x402Spend = {};
  }

  // Update state: x402 calls (JSONL)
  state.x402Calls = callsText ? parseJSONL(callsText) : [];

  // Update state: decisions (JSONL)
  state.decisions = decisionsText ? parseJSONL(decisionsText) : [];

  // Update state: positions from portfolio snapshots
  if (positionsText) {
    const snaps = parseJSONL(positionsText);
    if (snaps.length > 0) {
      const latest = snaps[snaps.length - 1];
      state.positions = latest.open_positions || [];
      if (!state.health.positions && latest.open_positions) {
        state.health.positions = latest.open_positions.length;
      }
    } else {
      state.positions = [];
    }
  } else {
    state.positions = [];
  }

  // Update state: trades (JSONL)
  state.trades = tradesText ? parseJSONL(tradesText) : [];

  // Render all panels in order
  renderStatusBar();
  renderBudget();
  renderDataQuality();
  renderPositions();
  renderROI();
  renderDecisions();
  renderTerminal();

  // Update last refresh timestamp
  setText('last-refresh', fmt.time(Date.now()));
}

// ============================================================
// 7. INITIALIZATION
// ============================================================

function init() {
  // Initial load
  loadAll();

  // Auto-refresh every 5 seconds
  setInterval(loadAll, 5000);

  // Nav click handlers: toggle .active class
  const nav = el('top-nav');
  if (nav) {
    nav.addEventListener('click', function(e) {
      const link = e.target.closest('.nav-link');
      if (!link) return;
      const links = nav.querySelectorAll('.nav-link');
      for (let i = 0; i < links.length; i++) {
        links[i].classList.remove('active');
      }
      link.classList.add('active');
    });
  }
}

// Start on DOM ready
document.addEventListener('DOMContentLoaded', init);
