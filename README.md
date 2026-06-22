# 🚀 Startup Cash Flow Projector

**Interactive single-page HTML tool** for projecting startup cash flow with multiple income streams, cost structures, and scenario analysis.

## ✨ Features

- **Dynamic income & costs** — Add/remove up to 10 income streams, 10 fixed costs, 10 variable costs
- **4 Growth Models** per item:
  - `constant` — Fixed monthly growth rate
  - `random_range` — Random growth within a min/max range
  - `seasonal` — Base rate + 12 monthly multipliers (Jan–Dec)
  - `custom` — Exact percentage per month
- **3-Scenario Projections** — Normal, Best Case (optimistic), Worst Case (pessimistic)
- **6 Live Charts** (powered by Chart.js):
  1. Cash Balance — 3 scenarios (line)
  2. Income Streams Detail (multi-line)
  3. Fixed Costs Detail (multi-line)
  4. Variable Costs Detail (multi-line)
  5. Income vs Costs (bar chart)
  6. Net Cash Flow & Cash Balance (combo)
- **Auto-save** — State persists in localStorage across sessions
- **Zero server dependencies** — Open the HTML file directly in any browser

## 📋 Usage

1. Download `cashflow.html`
2. Open in any modern browser
3. Edit any parameter — charts & data update instantly
4. Use the Reset Example button to restore defaults

## 🧮 Growth Models

| Type | Description | Parameters |
|------|-------------|------------|
| `constant` | Fixed % growth each month | Rate (%) |
| `random_range` | Random growth between min & max | Min Rate (%), Max Rate (%) |
| `seasonal` | Base growth + 12 monthly multipliers | Base Rate (%), 12 multipliers |
| `custom` | Exact growth rate per month | One rate per month of projection |

## 🛠 Tech

- Pure HTML/CSS/JavaScript
- [Chart.js](https://www.chart.js/) (loaded from CDN)
- localStorage for state persistence
- No build tools, no frameworks, no server required

## 📄 License

MIT — free to use, modify, and share.
