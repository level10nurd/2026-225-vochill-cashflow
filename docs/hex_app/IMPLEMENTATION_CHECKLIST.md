# VoChill Cash Flow Hex App — Implementation Checklist

Step-by-step checklist to build the Hex project. Copy-paste code from [HEX_CELL_BY_CELL_GUIDE.md](HEX_CELL_BY_CELL_GUIDE.md); architecture from [HEX_PROJECT_STRATEGY.md](HEX_PROJECT_STRATEGY.md).

**Conventions:**

- Variable names match the strategy and cell guide (e.g. `scenario_id`, `cash_transactions_df`).
- BigQuery connection in Hex: **VoChill BigQuery** (project: vochill, dataset: revrec).

---

## Phase 4A: Project Skeleton (≈1 hour)

**Goal:** Hex project exists, BigQuery connection works, Section 1 and one SQL cell run successfully.

| # | Task | Done |
|---|------|------|
| 1 | Open Hex workspace; create new project **"VoChill Cash Flow"** | ☐ |
| 2 | Confirm BigQuery connection **VoChill BigQuery** (project: vochill, dataset: revrec) | ☐ |
| 3 | Add **Cell 1.1** — Markdown: Project Header (see Guide Section 1, Cell 1.1) | ☐ |
| 4 | Add **Cell 1.2** — Input: Scenario, variable `scenario_id`, default `base` (options: base, best, worst) | ☐ |
| 5 | Add **Cell 1.3** — Input: Lookback Weeks, variable `lookback_weeks`, default 13 | ☐ |
| 6 | Add **Cell 1.4** — Input: Starting Balance Override, variable `starting_balance_override`, optional | ☐ |
| 7 | Add **Cell 2.1** — SQL: Get Cash Transactions → output `cash_transactions_df` (see Guide 2.1) | ☐ |
| 8 | If Hex SQL does not support parameters: use Python + BigQuery client to run parameterized query and assign to `cash_transactions_df` | ☐ |
| 9 | Run project through Cell 2.1; verify rows returned and columns include cash_date, amount, is_forecast, scenario_id | ☐ |

**Done when:** Project runs without errors and `cash_transactions_df` has data (or empty if no data in range).

---

## Phase 4B: Data Cells (≈1 hour)

**Goal:** All data extraction cells return expected DataFrames.

| # | Task | Done |
|---|------|------|
| 1 | Add **Cell 2.2** — SQL: Get Cash Position → `cash_position_df` (Guide 2.2) | ☐ |
| 2 | Run 2.2; verify one row with total_cash, total_loc_available, total_liquidity | ☐ |
| 3 | Add **Cell 2.3** — SQL: Get Weekly Cash Flow → `weekly_cash_flow_df` (Guide 2.3) | ☐ |
| 4 | Run 2.3; verify columns week_start, week_end, net_cash_flow, inflows, outflows; handle parameters if needed | ☐ |

**Done when:** `cash_transactions_df`, `cash_position_df`, and `weekly_cash_flow_df` load correctly.

---

## Phase 4C: Metrics (≈1 hour)

**Goal:** Runway, burn rate, and risk flags compute correctly.

| # | Task | Done |
|---|------|------|
| 1 | Add **Cell 3.1** — Python: Compute Runway and Weekly Summary (Guide 3.1) | ☐ |
| 2 | Run 3.1; verify `weekly_summary_df` has cash_balance column, `runway_weeks` is int or None | ☐ |
| 3 | Add **Cell 3.2** — Python: Burn Rate (Guide 3.2) | ☐ |
| 4 | Add **Cell 3.3** — Python: Risk Flags (Guide 3.3) | ☐ |
| 5 | Run Section 3; confirm no errors and risk_flags is a list | ☐ |

**Done when:** `weekly_summary_df`, `runway_weeks`, `burn_rate`, and `risk_flags` are available for Section 4.

---

## Phase 4D: Dashboard and Charts (≈1–2 hours)

**Goal:** KPIs, charts, and table display correctly.

| # | Task | Done |
|---|------|------|
| 1 | Add **Cell 4.1** — Metric: Current Cash Position (use starting_balance or display value from 3.1) | ☐ |
| 2 | Add **Cell 4.2** — Metric: Runway (weeks) | ☐ |
| 3 | Add **Cell 4.3** — Metric: Burn Rate | ☐ |
| 4 | Add **Cell 4.4** — Chart: Weekly Net Cash Flow (Guide 4.4) | ☐ |
| 5 | Add **Cell 4.5** — Chart: Cumulative Cash Balance (Guide 4.5) | ☐ |
| 6 | Add **Cell 4.6** — Table: 13-Week Cash Flow (bind to weekly_summary_df) | ☐ |
| 7 | Add **Cell 4.7** — Risk Flags (list or table) | ☐ |
| 8 | Run all; verify layout and that changing scenario_id (and re-running) updates forecast portion of the view | ☐ |

**Done when:** Dashboard shows cash position, runway, burn rate, two charts, one table, and risk flags.

---

## Phase 4E: Scenario Comparison (optional, ≈30 min)

**Goal:** Optional section to compare base/best/worst side by side.

| # | Task | Done |
|---|------|------|
| 1 | Add **Cell 4.8** (or new section): SQL to get weekly net by scenario_id | ☐ |
| 2 | Add Python to compute running balance per scenario and Plotly chart (one line per scenario) | ☐ |
| 3 | Test with at least two scenarios populated in BigQuery | ☐ |

**Done when:** User can view multiple scenarios on one chart (or table).

---

## Phase 4F: UAT and Documentation (≈30 min)

**Goal:** User sign-off and docs updated.

| # | Task | Done |
|---|------|------|
| 1 | Walk through Workflow 1: open project, run all, review cash position and runway | ☐ |
| 2 | Walk through Workflow 2: change scenario, re-run, confirm forecast portion changes | ☐ |
| 3 | If using override: set starting balance override, re-run, confirm runway/balance use it | ☐ |
| 4 | Document Hex project URL in README or docs/hex_app/ (e.g. README section or LINK.md) | ☐ |

**Done when:** User sign-off and Hex project URL recorded.

---

## Quick Reference

- **Code for each cell:** [HEX_CELL_BY_CELL_GUIDE.md](HEX_CELL_BY_CELL_GUIDE.md)
- **Architecture and workflows:** [HEX_PROJECT_STRATEGY.md](HEX_PROJECT_STRATEGY.md)
- **Repo forecast script (writes forecast to BQ):** [scripts/build_forecast.py](../../scripts/build_forecast.py)
- **BQ schema (views):** [database/create_financial_tables.sql](../../database/create_financial_tables.sql) (v_daily_cash_flow, v_weekly_cash_flow, v_cash_position)

---

## Success Criteria (from Strategy)

Phase 4 is complete when:

1. User can open the Hex project and see current cash position and runway without running Python locally.
2. 13-week cash flow (actuals + selected scenario forecast) is visible in table and chart.
3. Scenario selector changes the forecast portion of the view.
4. Risk flags surface when runway is short or a week is negative.
5. Documentation (strategy, cell guide, this checklist) is sufficient to build and maintain the app.
