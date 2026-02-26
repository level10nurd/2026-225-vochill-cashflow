# VoChill Cash Flow Hex App — Cell-by-Cell Guide

Copy-paste the code below into the corresponding Hex cells. Variable names match [HEX_PROJECT_STRATEGY.md](HEX_PROJECT_STRATEGY.md) and [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md).

**Conventions:**

- SQL output variable names are set in Hex (e.g. Cell 2.1 → `cash_transactions_df`).
- Python cells assume DataFrames from previous cells are in scope (e.g. `cash_transactions_df`, `cash_position_df`).
- Use Hex connection name **VoChill BigQuery** (project: vochill, dataset: revrec).

---

## Section 1: Configuration & Inputs

### Cell 1.1 — Markdown: Project Header

```markdown
# VoChill Cash Flow Dashboard

View current cash position, runway, and 13-week cash flow. Data is read from BigQuery (`vochill.revrec`).

- **Scenario:** Select base, best, or worst to show that forecast in the 13-week view.
- **Lookback weeks:** Number of weeks of history + forecast to include (default 13).
- **Starting balance override:** Leave blank to use liquidity from `v_cash_position`; or enter a value to override.

Last updated: 2026-02-25
```

### Cell 1.2 — Input: Scenario

- **Type:** Dropdown or text input.
- **Variable name:** `scenario_id`
- **Options / default:** `base` (options: `base`, `best`, `worst`)

(In Hex: create an Input cell, set variable to `scenario_id`, default value `base`. If dropdown: choices base, best, worst.)

### Cell 1.3 — Input: Lookback Weeks

- **Type:** Number input.
- **Variable name:** `lookback_weeks`
- **Default:** 13
- **Min:** 1, **Max:** 26 (or as needed)

### Cell 1.4 — Input: Starting Balance Override

- **Type:** Number input (optional).
- **Variable name:** `starting_balance_override`
- **Default:** empty / null (use BigQuery cash position when empty).

---

## Section 2: Data Extraction (SQL)

### Cell 2.1 — SQL: Get Cash Transactions

**Output variable:** `cash_transactions_df`

Returns actuals plus forecast rows for the selected scenario and date range. Use in Hex SQL cell with connection VoChill BigQuery.

```sql
SELECT
  cash_date,
  cash_flow_section,
  cash_flow_category,
  amount,
  is_forecast,
  scenario_id,
  description
FROM `vochill.revrec.cash_transactions`
WHERE cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @lookback_weeks WEEK)
  AND (
    is_forecast = FALSE
    OR (is_forecast = TRUE AND scenario_id = @scenario_id)
  )
ORDER BY cash_date
```

**Hex parameters:** Bind `@lookback_weeks` to `lookback_weeks` (integer) and `@scenario_id` to `scenario_id` (string). If Hex does not support parameters, use a Python cell to build the query string and run via `bq.query()` or replace inline:

```sql
-- Example without parameters (replace 13 and 'base' before run)
SELECT
  cash_date,
  cash_flow_section,
  cash_flow_category,
  amount,
  is_forecast,
  scenario_id,
  description
FROM `vochill.revrec.cash_transactions`
WHERE cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 WEEK)
  AND (is_forecast = FALSE OR (is_forecast = TRUE AND scenario_id = 'base'))
ORDER BY cash_date
```

### Cell 2.2 — SQL: Get Cash Position

**Output variable:** `cash_position_df`

Single row: total_cash, total_loc_balance, total_loc_available, total_liquidity.

```sql
SELECT
  total_cash,
  total_loc_balance,
  total_loc_available,
  total_liquidity
FROM `vochill.revrec.v_cash_position`
```

### Cell 2.3 — SQL: Get Weekly Cash Flow (Actuals + Forecast)

**Output variable:** `weekly_cash_flow_df`

Weekly net cash flow for the same range and scenario as 2.1. Aggregate in SQL for consistency.

```sql
SELECT
  DATE_TRUNC(cash_date, WEEK(MONDAY)) AS week_start,
  DATE_ADD(DATE_TRUNC(cash_date, WEEK(MONDAY)), INTERVAL 6 DAY) AS week_end,
  SUM(amount) AS net_cash_flow,
  SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS inflows,
  SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) AS outflows
FROM `vochill.revrec.cash_transactions`
WHERE cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @lookback_weeks WEEK)
  AND (is_forecast = FALSE OR (is_forecast = TRUE AND scenario_id = @scenario_id))
GROUP BY week_start, week_end
ORDER BY week_start
```

Again, bind `@lookback_weeks` and `@scenario_id` if Hex supports SQL parameters; otherwise replace in the query.

---

## Section 3: Metrics (Python)

### Cell 3.1 — Python: Compute Runway and Weekly Summary

**Inputs:** `weekly_cash_flow_df`, `cash_position_df`, `starting_balance_override` (from inputs), optional `lookback_weeks`.

**Outputs:** `weekly_summary_df` (with cash_balance column), `runway_weeks` (int or None), `starting_balance` (float).

```python
import pandas as pd

# Starting balance: override if provided, else from v_cash_position
if starting_balance_override is not None and starting_balance_override != "":
    try:
        starting_balance = float(starting_balance_override)
    except (TypeError, ValueError):
        starting_balance = float(cash_position_df["total_liquidity"].iloc[0])
else:
    starting_balance = float(cash_position_df["total_liquidity"].iloc[0])

# Ensure week_start is datetime
weekly = weekly_cash_flow_df.copy()
weekly["week_start"] = pd.to_datetime(weekly["week_start"])

# Sort by week for cumulative balance
weekly = weekly.sort_values("week_start").reset_index(drop=True)
weekly["cash_balance"] = starting_balance + weekly["net_cash_flow"].cumsum()

# Runway: first week where balance < 0
runway_weeks = None
for i, row in weekly.iterrows():
    if row["cash_balance"] < 0:
        runway_weeks = int((weekly.index.get_loc(i) + 1))  # 1-based week number
        break

weekly_summary_df = weekly
```

### Cell 3.2 — Python: Burn Rate

**Input:** `weekly_summary_df`  
**Output:** `burn_rate` (avg weekly net outflow; positive number when net is negative).

```python
# Burn rate: average weekly net cash flow (negative = outflow)
net_flows = weekly_summary_df["net_cash_flow"]
if net_flows.sum() >= 0:
    burn_rate = 0.0
else:
    burn_rate = abs(net_flows.mean())
```

### Cell 3.3 — Python: Risk Flags

**Inputs:** `runway_weeks`, `weekly_summary_df`  
**Output:** `risk_flags` (list of strings).

```python
risk_flags = []
if runway_weeks is not None and runway_weeks < 4:
    risk_flags.append(f"Runway under 4 weeks ({runway_weeks} weeks)")
if runway_weeks is None and len(weekly_summary_df) > 0:
    # Check if any week is negative
    if (weekly_summary_df["cash_balance"] < 0).any():
        risk_flags.append("One or more weeks show negative cash balance")
if len(weekly_summary_df) > 0 and weekly_summary_df["cash_balance"].iloc[-1] < 0:
    risk_flags.append("Ending cash balance is negative")
if not risk_flags:
    risk_flags.append("No high-priority risk flags")
```

---

## Section 4: Output & Visualization

### Cell 4.1 — Metric: Current Cash Position

In Hex: create a **Metric** or **Text** cell that displays `starting_balance` (or the value used in 3.1). Example Python that outputs a display value:

```python
display_cash_position = starting_balance
# In Hex you can show this as a metric: f"${display_cash_position:,.0f}"
```

### Cell 4.2 — Metric: Runway (weeks)

Display `runway_weeks` if set, else "N/A" or "> lookback_weeks".

```python
display_runway = runway_weeks if runway_weeks is not None else "N/A"
```

### Cell 4.3 — Metric: Burn Rate

Display `burn_rate` as dollars per week.

```python
display_burn_rate = f"${burn_rate:,.0f}/week"
```

### Cell 4.4 — Chart: Weekly Net Cash Flow

Use Hex chart component. Data: `weekly_summary_df` with columns `week_start` (or `week_end`) and `net_cash_flow`.

- **X:** week_start (or week_end)
- **Y:** net_cash_flow
- **Type:** Bar or line; color by sign (e.g. green positive, red negative) if supported.

Example (Plotly):

```python
import plotly.express as px
fig = px.bar(
    weekly_summary_df,
    x="week_start",
    y="net_cash_flow",
    title="Weekly Net Cash Flow",
    labels={"net_cash_flow": "Net Cash Flow ($)", "week_start": "Week"}
)
fig.update_layout(xaxis_tickformat="%Y-%m-%d")
fig.show()
```

### Cell 4.5 — Chart: Cumulative Cash Balance

**X:** week_start  
**Y:** cash_balance  
**Type:** Line.

```python
fig2 = px.line(
    weekly_summary_df,
    x="week_start",
    y="cash_balance",
    title="Cumulative Cash Balance",
    labels={"cash_balance": "Cash Balance ($)", "week_start": "Week"}
)
fig2.update_layout(xaxis_tickformat="%Y-%m-%d")
fig2.add_hline(y=0, line_dash="dash", line_color="gray")
fig2.show()
```

### Cell 4.6 — Table: 13-Week Cash Flow

Display `weekly_summary_df` (or a subset of columns: week_start, week_end, inflows, outflows, net_cash_flow, cash_balance) as a sortable table. In Hex use a Table cell bound to that DataFrame.

### Cell 4.7 — Risk Flags

Display `risk_flags` as a list or table.

```python
for flag in risk_flags:
    print(f"• {flag}")
```

Or render as a small Markdown list from Python.

### Cell 4.8 — Scenario Comparison (Optional)

To compare multiple scenarios, add a SQL cell that returns weekly summary by scenario (e.g. pivot or one row per week per scenario), then a chart with one line per scenario. Example query idea:

```sql
SELECT
  DATE_TRUNC(cash_date, WEEK(MONDAY)) AS week_start,
  scenario_id,
  SUM(amount) AS net_cash_flow
FROM `vochill.revrec.cash_transactions`
WHERE cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 WEEK)
  AND (is_forecast = FALSE OR is_forecast = TRUE)
GROUP BY week_start, scenario_id
ORDER BY week_start, scenario_id
```

Then in Python, compute running balance per scenario and plot with Plotly (one line per scenario).

---

## Quick Reference

| Cell   | Type   | Output Variable(s)     |
|--------|--------|------------------------|
| 2.1    | SQL    | cash_transactions_df   |
| 2.2    | SQL    | cash_position_df       |
| 2.3    | SQL    | weekly_cash_flow_df    |
| 3.1    | Python | weekly_summary_df, runway_weeks, starting_balance |
| 3.2    | Python | burn_rate             |
| 3.3    | Python | risk_flags            |

If Hex SQL cells do not support parameters, use a Python cell that builds the query string and runs it via the BigQuery client, then assign the result to the expected variable name so downstream cells work unchanged.
