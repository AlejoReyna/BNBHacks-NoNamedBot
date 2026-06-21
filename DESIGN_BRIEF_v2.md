# Design Brief: Cascade AI Dashboard v2
## NOT AIXBT — Bento Grid + Glassmorphism + BNB Chain Brand

### Design Direction
We are building a **judge-auditable dashboard** for the BNB Hackathon. The aesthetic must be **completely different from AIXBT** (no purple terminal, no 48px icon rail, no 2px border-radius, no flat dense table aesthetic). Instead, we use:

- **Bento Grid layout**: Modular CSS grid with cards of varying spans, clean gaps
- **Glassmorphism**: Frosted glass panels with `backdrop-filter: blur()`, semi-transparent tinted backgrounds, subtle glow borders
- **BNB Chain brand palette**: Gold/yellow accent (`#F0B90B`), dark base (`#0B0E11`), card surface (`#1E2026`), warm grays
- **Premium rounded cards**: 12px border-radius (bento style), not 2px
- **Top navigation bar**: Clean horizontal nav with text labels + logo, NOT a sidebar icon rail
- **Status pills with glow**: Soft colored glow behind indicators (glassmorphism style)
- **Typography**: Inter, 16px base, clear hierarchy with weight contrast (not AIXBT's all-400-weight)

---

### Color Tokens

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg` | `#0B0E11` | Page background (warm dark, not pure black) |
| `--bg-glass` | `rgba(30, 32, 38, 0.6)` | Glass card background |
| `--bg-glass-hover` | `rgba(30, 32, 38, 0.8)` | Glass hover state |
| `--surface` | `#1E2026` | Solid card fallback / mobile nav |
| `--elevated` | `#2B2F36` | Borders, dividers |
| `--hover` | `#3A3F4B` | Hover states |
| `--text` | `#FFFFFF` | Primary text |
| `--secondary` | `#B0B3B8` | Secondary text, labels |
| `--muted` | `#848E9C` | Muted text, timestamps |
| `--accent` | `#F0B90B` | BNB gold — primary accent, active states, highlights |
| `--accent-dim` | `rgba(240, 185, 11, 0.15)` | Gold glow backgrounds |
| `--green` | `#0ECB81` | Success, positive P&L |
| `--red` | `#F6465D` | Danger, negative P&L, errors |
| `--blue` | `#4A9EFF` | Info, links, mode indicators |
| `--purple` | `#9B59B6` | x402 micropayment accent (keep for brand identity) |
| `--glass-border` | `rgba(255, 255, 255, 0.08)` | Subtle white border on glass |
| `--glass-border-hover` | `rgba(240, 185, 11, 0.3)` | Gold glow border on hover/active |

---

### Layout Architecture

#### Desktop (≥1024px)
```
┌─────────────────────────────────────────────────────────────┐
│  [TOP NAV: Logo | Dashboard | Positions | x402 | Logs | Chat]  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Status   │  │  x402    │  │ Data     │  │ Positions│   │
│  │ Bar      │  │ Budget   │  │ Quality  │  │ P&L      │   │
│  │ (full)   │  │ (large)  │  │ (medium) │  │ (medium) │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Decision Stream (full width, scrollable table)       │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌────────────────────┐  ┌──────────────────────────┐   │
│  │ x402 ROI           │  │ Live Logs (terminal)     │   │
│  │ (medium)           │  │ (medium)                 │   │
│  └────────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

- CSS Grid: `grid-template-columns: repeat(4, 1fr); gap: 1rem;`
- Status bar: `grid-column: 1 / -1;` — 4 status pills in a row
- x402 Budget: `grid-column: span 2; grid-row: span 2;` — the HERO card (most important for judges)
- Data Quality: `grid-column: span 1;`
- Positions: `grid-column: span 1;`
- Decision Stream: `grid-column: 1 / -1;`
- x402 ROI: `grid-column: span 2;`
- Live Logs: `grid-column: span 2;`

#### Tablet (768px–1023px)
- 2-column grid: `grid-template-columns: repeat(2, 1fr);`
- x402 Budget: `span 2` (full width)
- All others: `span 1` or `span 2` as needed
- Decision Stream: full width

#### Mobile (<768px)
- Single column: `grid-template-columns: 1fr;`
- All cards stack vertically
- Top nav collapses to hamburger or icon-only bottom bar
- Tables horizontal scroll
- Status bar becomes 2-column grid then 1-column

---

### Glassmorphism Card Pattern
```css
.card {
  background: rgba(30, 32, 38, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 1.25rem;
  transition: all 0.2s ease;
}

.card:hover {
  border-color: rgba(240, 185, 11, 0.3);
  background: rgba(30, 32, 38, 0.8);
  box-shadow: 0 0 20px rgba(240, 185, 11, 0.05);
}

/* Fallback for browsers without backdrop-filter */
@supports not (backdrop-filter: blur(12px)) {
  .card { background: #1E2026; }
}
```

---

### Top Navigation Bar
```
┌─────────────────────────────────────────────────────┐
│  [CA]  Cascade AI  ·  Dashboard  Positions  x402   │
│   logo   brand         nav-links            right   │
└─────────────────────────────────────────────────────┘
```
- Height: 64px
- Background: `rgba(11, 14, 17, 0.8)` with `backdrop-filter: blur(16px)`
- Border-bottom: `1px solid rgba(255,255,255,0.06)`
- Logo: "CA" in a rounded square with gold gradient
- Nav links: text labels, 14px, `#B0B3B8`, hover → `#FFFFFF`, active → `#F0B90B` with underline
- Right side: status indicator dot + "Live / Paper" badge
- Mobile: logo + hamburger menu, nav links in a dropdown overlay

---

### Status Pills (Glassmorphism Style)
```css
.status-pill {
  background: rgba(30, 32, 38, 0.5);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.status-pill .glow-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor, 0 0 16px currentColor;
}
```
- 4 pills in a row on desktop: Status, Cycle, Positions, Drawdown
- Each pill has a colored glow dot + label + value
- On mobile: 2×2 grid, then 1-column stack

---

### x402 Budget Hero Card (Most Important)
This is the **hero card** — it should be the largest and most visually prominent.
- Title: "x402 Micropayments" with a purple badge icon
- Large budget progress bar: glassmorphism track, gold gradient fill
- Metrics: Daily Budget, Spent, Remaining, Cost/Call, Calls Today, Circuit Breaker, Total Spend
- All values in `font-variant-numeric: tabular-nums`
- The progress bar should animate on load

---

### Data Quality Card
- Title: "Data Quality" with chart icon
- Metrics: Snapshot Age, Source, Regime, Sentiment FGI, Risk State, Strategy, Technicals
- Source badge shows "x402" or "Keyless" with appropriate color

---

### Positions Card
- Title: "Positions — Live P&L" with position icon
- If no positions: show empty state with icon + message
- If positions: show a compact table (Symbol, Entry, Size, P&L%)
- P&L% colored green/red
- Portfolio value at bottom

---

### Decision Stream (Full Width)
- Title: "Autonomous Decision Stream" with bot icon
- Table with columns: Time, Action, Symbol, Regime, Score, Reason, Mode
- Action colored: ENTER=green, EXIT=red, WAIT=muted, HALT=red
- On mobile: horizontal scroll or card-based list

---

### x402 ROI Card
- Title: "x402 ROI Attribution" with bar chart icon
- Metrics: Total Spend, Realized P&L, Net After Cost, Win Rate x402, Win Rate Keyless, Trades Closed
- Mini bar chart at bottom (CSS div bars, no JS library)
- Net value colored green/red based on value

---

### Live Logs Card (Terminal Style)
- Title: "Live Logs" with terminal icon
- Monospace font, glassmorphism card containing a slightly darker inner panel
- Colored syntax highlighting: keys in purple, values in white, green/red for P&L
- Auto-scroll to bottom, max height ~200px, custom scrollbar

---

### Typography Scale
- Page title: 20px, weight 600, white
- Section title: 11px, weight 500, muted gray, uppercase, letter-spacing 0.5px
- Card label: 12px, weight 500, secondary gray
- Card value: 16px, weight 600, white, tabular-nums
- Table header: 10px, weight 500, muted, uppercase
- Table cell: 13px, weight 400, white
- Terminal: 12px, monospace, secondary gray
- Mobile: reduce by ~10%

---

### Empty States
Every panel must have a contextual empty state — never a blank space.
- Centered icon + message in muted gray
- Icon: simple SVG, 32px, stroke-only, muted color

---

### Responsive Breakpoints
- `≥1024px`: 4-column bento grid, top nav, full sidebar-like spacing
- `768px–1023px`: 2-column grid, top nav, tighter padding
- `<768px`: 1-column stack, mobile nav (hamburger or bottom bar), horizontal scroll tables

---

### JavaScript API Contract
The HTML must expose these exact IDs for the JS to attach to:

#### Elements (by ID):
- `top-nav` — the top navigation container
- `mode-badge` — the Live/Paper indicator in the nav
- `status-dot` — the main status glow dot
- `status-text` — status text
- `last-cycle` — last cycle timestamp
- `positions-count` — open positions count
- `drawdown` — drawdown percentage
- `budget-daily` — daily budget value
- `budget-spent` — spent today
- `budget-remaining` — remaining today
- `budget-fill` — the progress bar fill element
- `budget-badge` — Healthy/Throttling/Exhausted badge
- `calls-today` — x402 call count
- `circuit-status` — Circuit Breaker status
- `total-spend` — total x402 spend
- `snapshot-age` — data snapshot age
- `data-source` — data source text
- `data-badge` — x402/Keyless badge
- `regime` — current regime
- `fgi` — fear & greed index
- `risk-state` — risk state text
- `strategy` — strategy mode
- `technicals` — technicals list
- `positions-body` — positions card body
- `pos-badge` — positions count badge
- `roi-spend` — total spend in ROI card
- `roi-pnl` — realized P&L
- `roi-net` — net after cost
- `win-x402` — win rate with x402
- `win-keyless` — win rate keyless
- `trades-closed` — closed trades count
- `roi-chart` — mini bar chart container
- `roi-badge` — ROI badge
- `decision-tbody` — decision stream table body
- `decision-count` — decision count badge
- `terminal` — live log terminal container
- `log-badge` — log line count badge
- `last-refresh` — last refresh timestamp

#### Data Sources:
- `/health` — JSON, returns: `{status, last_cycle, positions, daily_trades, drawdown_pct, mode, sentiment_fgi, ...}`
- `/logs` — JSON, returns: `{lines: [string]}` (last 50 lines of decision log)
- `logs/x402_spend.json` — JSON, returns: `{day, daily_spend_usdc, total_spend_usdc, daily_budget_usdc}`
- `logs/x402_calls.jsonl` — JSONL, lines of `{amount_usdc, daily_spend_usdc, total_spend_usdc, outcome, tool, ts}`
- `logs/decision_live.jsonl` — JSONL, lines of `{action, symbol, timestamp, regime, entry_score, reasons, mode, risk_state, ...}`
- `logs/portfolio_snapshots.jsonl` — JSONL, lines of `{timestamp, portfolio_value_usdc, open_positions, drawdown_pct, ...}`
- `logs/trade_outcomes.jsonl` — JSONL, lines of `{event, symbol, entry_price, exit_price, realized_pnl_usdc, realized_pnl_pct, x402_enriched, ...}`

#### JS Requirements:
- Auto-refresh every 5 seconds
- Fetch all endpoints in parallel
- Parse JSONL files correctly
- Render all 7 panels with empty states
- Color-code values (green for positive, red for negative, gold for accent)
- Format numbers with `$` and `%`, tabular-nums
- Animate progress bar on budget update
- Scroll terminal to bottom on new logs
- Handle all errors gracefully (show offline state, don't crash)
- All functions must be self-contained, no external dependencies

---

### File Output
Both agents produce code that will be merged into a SINGLE file: `dashboard.html` at the project root.
- The HTML/CSS agent produces the complete HTML structure with all CSS in a `<style>` block.
- The JS agent produces the complete JavaScript in a `<script>` block that goes at the bottom of the body.
- The final file must be valid, self-contained HTML with no external CSS/JS files.

### Critical Constraint
This is **NOT AIXBT**. Do NOT use:
- `#0C0C0F` background (use `#0B0E11`)
- Purple as primary accent (use `#F0B90B` gold)
- 2px border-radius (use 12px)
- 48px sidebar icon rail (use top nav bar)
- Flat dense table rows with no card wrapper (use glassmorphism cards)
- No gradients or shadows (use subtle glow + glass borders)
- All-400-weight typography (use weight hierarchy: 600 for values, 500 for labels, 400 for body)
