# VoChill Cash Flow — Hex Project Strategy

**Document Version:** 1.0  
**Created:** 2026-02-25  
**Status:** Planning complete; implementation per [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)  
**Owner:** Dalton Allen  

---

## Executive Summary

This document outlines the strategy for deploying the VoChill cash flow system in Hex. The app will provide an interactive dashboard for cash position, runway, 13-week cash flow, and scenario comparison, using data already in BigQuery (`cash_transactions`, analytical views, and supporting tables). The pattern mirrors the VoChill Demand Forecasting Hex app (vochill-forecasting repo).

### Key Objectives

1. **Self-service cash view**: View current cash position and runway without running Python scripts.
2. **13-week rolling view**: See weekly cash flow (actuals + forecast) in one place.
3. **Scenario comparison**: Compare base / best / worst scenarios side by side.
4. **BigQuery as source of truth**: All data from `vochill.revrec`; no local file parsing.
5. **Single Hex project**: One place for cash flow reporting (no Excel output).

---

## Architecture Overview

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     HEX CASH FLOW PROJECT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [1] Input Controls                                              │
│      ├── Scenario selector (base / best / worst)                │
│      ├── Date range or "last 13 weeks"                           │
│      └── Optional starting balance override                      │
│                           ↓                                      │
│  [2] Data Extraction (SQL Cells)                                  │
│      ├── Get cash_transactions (actuals + forecast by scenario)  │
│      ├── Get v_weekly_cash_flow (or derive from cash_transactions)│
│      ├── Get v_cash_position (current liquidity)                  │
│      └── Optionally: bank_accounts, debt_schedule, scenarios     │
│                           ↓                                      │
│  [3] Metrics (Python Cells)                                      │
│      ├── Runway (weeks until cash < 0)                          │
│      ├── Burn rate (avg weekly net outflow)                      │
│      ├── Ending cash by week                                     │
│      └── Net cash flow by week                                    │
│                           ↓                                      │
│  [4] Output & Visualization                                  │
│      ├── KPI metrics (cash position, runway, burn rate)          │
│      ├── 13-week cash flow table                                 │
│      ├── 13-week cash flow chart                                 │
│      ├── Scenario comparison (if multiple scenarios)             │
│      └── Risk flags (e.g. runway &lt; 4 weeks)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   BIGQUERY (vochill.revrec)                      │
├─────────────────────────────────────────────────────────────────┤
│  • cash_transactions   (actuals + forecast rows by scenario_id)  │
│  • v_weekly_cash_flow  (weekly rollup, actuals only)             │
│  • v_cash_position     (current cash + LOC liquidity)            │
│  • cash_balances       (optional; v_cash_position uses it)         │
│  • bank_accounts      (optional reference)                      │
│  • debt_schedule       (optional reference)                      │
│  • scenarios          (scenario definitions)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Read-mostly**: The app reads from BigQuery. Forecast data is written by `scripts/build_forecast.py` (run separately or on schedule).
2. **Simplicity**: Default to "last 13 weeks" and "base" scenario; minimal inputs required.
3. **Transparency**: Show which scenario is selected; show data as of date if relevant.
4. **Performance**: Use existing views where possible; avoid heavy ad-hoc aggregation in SQL.

---

## Cell-by-Cell Architecture

### Section 1: Configuration & Inputs

| Cell # | Type     | Name                    | Purpose                                      | Output Variable   |
|--------|----------|-------------------------|----------------------------------------------|-------------------|
| 1.1    | Markdown | Project Header          | Title, short instructions, last updated      | —                 |
| 1.2    | Input    | Scenario                | Dropdown: base / best / worst                | `scenario_id`     |
| 1.3    | Input    | Lookback Weeks          | Number (default 13) or "use 13-week forecast" | `lookback_weeks`  |
| 1.4    | Input    | Starting Balance Override | Optional; leave blank to use v_cash_position | `starting_balance_override` |

### Section 2: Data Extraction (SQL)

| Cell # | Type | Name                 | Purpose                                           | Output Variable   |
|--------|------|----------------------|---------------------------------------------------|-------------------|
| 2.1    | SQL  | Get Cash Transactions| Actuals + forecast for selected scenario and range| `cash_transactions_df` |
| 2.2    | SQL  | Get Cash Position    | Current liquidity from v_cash_position            | `cash_position_df` |
| 2.3    | SQL  | Get Weekly Summary   | Weekly net cash flow (actuals + forecast)          | `weekly_cash_flow_df` |

**Notes:**

- `cash_transactions` has `is_forecast` (TRUE/FALSE) and `scenario_id` (e.g. 'base', 'best', 'worst'). Filter by `scenario_id` for forecast rows; actuals have `is_forecast = FALSE`.
- `v_weekly_cash_flow` is actuals-only and last 13 weeks. For a full 13-week view including forecast, query `cash_transactions` and aggregate by week in SQL or Python.
- `v_cash_position` returns one row: total_cash, total_loc_balance, total_loc_available, total_liquidity.

### Section 3: Metrics (Python)

| Cell # | Type   | Name              | Purpose                                      | Input                    | Output           |
|--------|--------|-------------------|----------------------------------------------|---------------------------|------------------|
| 3.1    | Python | Compute Runway    | Weeks until cash < 0 (from weekly balance)   | weekly_cash_flow_df, starting_balance | `runway_weeks`, `weekly_summary_df` |
| 3.2    | Python | Burn Rate         | Avg weekly net cash flow (outflows)           | weekly_summary_df         | `burn_rate`      |
| 3.3    | Python | Risk Flags        | e.g. runway < 4 weeks, negative week        | runway_weeks, weekly_summary_df | `risk_flags` |

**Implementation:** Reuse logic from [scripts/build_forecast.py](../../scripts/build_forecast.py) (e.g. `calculate_cash_position`) where applicable; adapt to DataFrame inputs from SQL cells.

### Section 4: Output & Visualization

| Cell # | Type   | Name                    | Purpose                                              |
|--------|--------|-------------------------|------------------------------------------------------|
| 4.1    | Metric | Current Cash Position   | Total liquidity (or starting balance override)       |
| 4.2    | Metric | Runway (weeks)          | Weeks until cash < 0                               |
| 4.3    | Metric | Burn Rate               | Avg weekly net burn ($/week)                         |
| 4.4    | Chart  | Weekly Cash Flow        | Bar or line: net cash flow by week                   |
| 4.5    | Chart  | Cumulative Cash Balance | Line: running cash balance by week                   |
| 4.6    | Table  | 13-Week Cash Flow       | Sortable table: week, inflows, outflows, net, balance|
| 4.7    | Markdown/Table | Risk Flags        | List of risk items (e.g. "Runway < 4 weeks")        |
| 4.8    | Section (optional) | Scenario Comparison | Side-by-side comparison of base/best/worst (multi-scenario query) |

---

## User Workflows

### Workflow 1: View Current Cash Position and Runway

1. Open Hex project.
2. Leave defaults (scenario = base, lookback = 13 weeks).
3. Run all cells.
4. Review: current cash position, runway, burn rate, 13-week table and charts.

### Workflow 2: Compare Scenarios

1. Run with scenario = base; note runway and ending balance.
2. Change scenario to best; re-run from Section 2 (or Run All).
3. Change scenario to worst; re-run.
4. Optionally use Section 4.8 (Scenario Comparison) to load two or three scenarios in one view.

### Workflow 3: Override Starting Balance

1. Set "Starting Balance Override" to a known value (e.g. from bank).
2. Run metrics and viz; runway and cumulative balance use this instead of v_cash_position.

---

## Technical Details

### BigQuery Connection

- **Project:** `vochill`
- **Dataset:** `revrec`
- **Connection in Hex:** Same as VoChill Demand Forecasting (e.g. "VoChill BigQuery") if in same workspace.

### Key Tables and Views

| Object                | Purpose |
|------------------------|--------|
| `cash_transactions`    | All cash in/out; `is_forecast`, `scenario_id` for forecast rows. |
| `v_weekly_cash_flow`   | Weekly rollup, actuals only, last 13 weeks. |
| `v_cash_position`       | One row: total_cash, total_loc_available, total_liquidity. |
| `scenarios`            | Scenario definitions (base/best/worst). |

### Python Environment

- pandas, numpy (Hex default).
- google-cloud-bigquery (for Hex SQL cells; Python cells typically consume DataFrames produced by SQL).
- Plotly or Hex chart components for visualizations.

### Data Refresh

- Each run pulls fresh data from BigQuery (no local cache). Forecast data is updated when `scripts/build_forecast.py` is run (separate process).

---

## Implementation Phases

| Phase | Goal                                   | Deliverable |
|-------|----------------------------------------|-------------|
| 4A    | Project skeleton, BigQuery connection  | Hex project with Section 1 and one SQL cell (e.g. cash_transactions) running. |
| 4B    | All data cells                         | SQL cells 2.1–2.3 return expected DataFrames. |
| 4C    | Metrics (runway, burn, risk flags)    | Python cells 3.1–3.3 produce runway_weeks, weekly_summary_df, risk_flags. |
| 4D    | Dashboard and charts                  | Metrics 4.1–4.3, charts 4.4–4.5, table 4.6, risk 4.7. |
| 4E    | Scenario comparison (optional)        | Section 4.8 or multi-scenario query + comparison table/chart. |
| 4F    | UAT and docs                           | User sign-off; document Hex project URL in README or docs. |

---

## Success Criteria

- User can open the Hex project and see current cash position and runway without running Python locally.
- 13-week cash flow (actuals + selected scenario forecast) is visible in table and chart.
- Scenario selector changes the forecast portion of the view; actuals remain the same.
- Risk flags surface when runway is short or a week is negative.
- Documentation (this file, [HEX_CELL_BY_CELL_GUIDE.md](HEX_CELL_BY_CELL_GUIDE.md), [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)) is sufficient to build and maintain the app.

---

## Out of Scope (for this app)

- **Excel output**: Not needed; reporting is Hex-only.
- **Forecast engine in Hex**: 13-week forecast is generated by [scripts/build_forecast.py](../../scripts/build_forecast.py); Hex app only reads results from BigQuery.
- **Revenue/demand forecasting**: Lives in the vochill-forecasting Hex project; "connect it all up" (e.g. feeding revenue into cash flow) is a later integration step.

---

## Next Steps

1. Create Hex project "VoChill Cash Flow" in Hex workspace.
2. Follow [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) (Phases 4A → 4F).
3. Copy-paste code from [HEX_CELL_BY_CELL_GUIDE.md](HEX_CELL_BY_CELL_GUIDE.md) for each cell.
