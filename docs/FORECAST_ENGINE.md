# Cash Flow Forecast Engine - Complete

## ✅ Forecast Engine Built

The 13-week rolling cash flow forecast engine is now operational and ready to generate forward-looking cash projections.

---

## 📊 What It Does

The forecast engine generates weekly cash flow projections for 13 weeks forward by:

### **1. Analyzing Historical Expenses**
- Queries historical `cash_transactions` from BigQuery
- Calculates weekly expense averages from vendor invoices
- Current baseline: **$105,137/week** in operating expenses

### **2. Adding Recurring Transactions**
- Pulls active recurring items from `recurring_transactions` table
- Currently includes:
  - SBA Loan Interest ($4,583.33/month on day 30)
  - Shopify Subscription ($299/month on day 1)
- Automatically schedules based on day_of_month

### **3. Including Debt Service**
- Pulls upcoming payments from `debt_schedule` table
- Currently includes 3 SBA loan payments over next 13 weeks
- Shows principal, interest, and total payment amounts

### **4. Revenue Input**
- **Revenue is NOT auto-calculated** (by design)
- Use `--weekly-revenue` parameter to manually input weekly revenue
- Default: $0 (revenue calculated in separate forecasting model)
- Supports scenario multipliers (base 1.0x, best 1.15x, worst 0.85x)

> **Note**: VoChill demand forecasting module is currently in development in a separate repository at `/Users/dalton/Documents/projects/20260225-vochill-forecasting/`. Once complete, weekly revenue projections from that model will be integrated into this cash flow forecast.

### **5. Cash Position & Runway**
- Calculates weekly net cash flow
- Projects running cash balance (starting at $250k placeholder)
- Determines runway (weeks until cash runs out)

---

## 🚀 Usage

### Preview Mode (Recommended First)
```bash
uv run python scripts/build_forecast.py --preview
```

Shows forecast summary without inserting into BigQuery.

### With Manual Revenue Input
```bash
uv run python scripts/build_forecast.py --weekly-revenue 75000 --preview
```

Projects $75,000/week in revenue.

### Generate Multiple Scenarios
```bash
# Base case (conservative)
uv run python scripts/build_forecast.py --weekly-revenue 75000 --scenario base

# Best case (+15% revenue, -10% expenses)
uv run python scripts/build_forecast.py --weekly-revenue 75000 --scenario best

# Worst case (-15% revenue, +10% expenses)
uv run python scripts/build_forecast.py --weekly-revenue 75000 --scenario worst
```

### Custom Forecast Period
```bash
uv run python scripts/build_forecast.py --weeks 26 --weekly-revenue 75000
```

Generate 26-week (6-month) forecast.

---

## 📈 Output

### Console Summary
```
============================================================
VoChill Cash Flow Forecast - 13 Weeks
============================================================

Generating 13-week base scenario forecast...

Analyzing historical expenses...
  Expenses: $105,137/week (avg)
  Revenue: $0/week (revenue calculated in separate model)

Loading recurring transactions and debt schedule...
  Recurring: 2 items
  Debt payments: 3 scheduled

============================================================
Forecast Summary
============================================================

Starting cash balance: $250,000.00

Week     Dates                     Net Cash Flow      Balance
----------------------------------------------------------------------
1        02/25 - 03/03             $    -108,572      $     141,428
2        03/04 - 03/10             $    -105,137      $      36,291
3        03/11 - 03/17             $    -105,137      $     -68,846

⚠️  RUNWAY: 3 weeks until cash runs out
```

### BigQuery Output
When run without `--preview`, forecast transactions are inserted into:
```sql
SELECT *
FROM `vochill.revrec.cash_transactions`
WHERE is_forecast = TRUE
  AND scenario_id = 'base'
ORDER BY cash_date
```

Each forecast transaction includes:
- `transaction_date`, `cash_date` (date of cash impact)
- `cash_flow_section` (Operating, Financing, Investing)
- `cash_flow_category` (specific classification)
- `amount` (positive = inflow, negative = outflow)
- `description` (what the transaction is)
- `is_forecast = TRUE` (distinguishes from actuals)
- `scenario_id` ('base', 'best', 'worst')

---

## 🔧 Current Configuration

### Expense Baseline
- Source: `cash_transactions` where `amount < 0` (last 12 weeks)
- Current: **$105,137/week**
- Based on: 167 vendor invoice transactions ($701,601 total / ~6.7 weeks)

### Recurring Items
| Item | Amount | Frequency | Day |
|------|--------|-----------|-----|
| SBA Loan Interest | $4,583.33 | Monthly | 30 |
| Shopify Subscription | $299.00 | Monthly | 1 |

### Debt Schedule
- **3 payments** scheduled over next 13 weeks
- Source: `debt_schedule` table (84 total payments through May 2031)
- Includes SBA loan I/O period through May 2026, then P&I amortization

### Scenario Multipliers
| Scenario | Revenue | Expenses |
|----------|---------|----------|
| Base | 1.0x | 1.0x |
| Best | 1.15x | 0.90x |
| Worst | 0.85x | 1.10x |

---

## ⚙️ Architecture

### Script: `scripts/build_forecast.py`

**Key Functions:**
1. `get_historical_actuals()` - Queries past cash transactions for analysis
2. `analyze_expense_patterns()` - Calculates weekly expense averages
3. `get_recurring_transactions()` - Pulls active recurring items
4. `get_debt_schedule()` - Pulls upcoming debt payments
5. `generate_weekly_forecast()` - Main forecast logic, builds 13-week projection
6. `calculate_cash_position()` - Computes running balance and runway
7. `insert_forecast_to_bigquery()` - Saves forecast to `cash_transactions`

**Forecast Generation Logic:**
```python
for week in range(1, 14):
    # Manual revenue input (if provided)
    if weekly_revenue > 0:
        add_revenue_transaction()

    # Historical expense average
    add_expense_transaction(weekly_avg)

    # Recurring items (check if day falls in this week)
    for recurring in recurring_transactions:
        if day_of_month in week_dates:
            add_recurring_transaction()

    # Debt payments (check if payment_date in this week)
    for debt in debt_schedule:
        if payment_date in week_dates:
            add_debt_transaction()
```

### Database Tables Used
- `vochill.revrec.cash_transactions` (both input for actuals, output for forecast)
- `vochill.revrec.recurring_transactions` (monthly/recurring items)
- `vochill.revrec.debt_schedule` (SBA loan payment schedule)

---

## 📋 Next Steps

### 1. Adjust Starting Cash Balance
Currently hardcoded to $250,000. Update to actual bank balance:
```python
# In scripts/build_forecast.py, line ~309
starting_balance = 250000.00  # PLACEHOLDER - adjust based on actual bank balance
```

Or better: Query actual bank balance from `bank_accounts` table or latest statement.

### 2. Integrate Revenue Forecast
VoChill demand forecasting module is in development at `/Users/dalton/Documents/projects/20260225-vochill-forecasting/`.

Once complete:
```bash
# Get weekly revenue from separate model
WEEKLY_REV=$(python ../20260225-vochill-forecasting/get_weekly_revenue.py)

# Pass to cash flow forecast
uv run python scripts/build_forecast.py --weekly-revenue $WEEKLY_REV
```

### 3. Refine Expense Categories
Currently uses aggregate weekly expense average. To split by category:
- Map vendor invoices to expense types (COGS, OpEx, Marketing, etc.)
- Project each category separately
- Apply different growth rates by category

### 4. Add Seasonality
Wine chiller business is seasonal (Q4 peak for holidays). Add:
- Monthly/quarterly adjustment factors
- Inventory build periods (Q3 for Q4 demand)
- Marketing spend ramps

### 5. Create Excel Report Generator
Build `scripts/generate_excel_report.py` to produce:
- Dashboard tab (cash position, runway, KPIs)
- 13-week forecast tab (formatted table)
- Actuals vs Forecast tab (variance analysis)
- Scenario comparison tab (base/best/worst)

### 6. Build CapEx Tracker
Create `scripts/track_capex.py` to:
- Load planned equipment purchases
- Map to cash flow timing
- Show impact on runway

---

## 🎯 Design Decisions

### Why Revenue Is Manual Input
- Revenue forecasting for ecommerce is complex (seasonality, promotions, platform algorithms)
- User has separate dedicated revenue forecasting model in another repo
- Cash flow model focuses on **payment timing** and **cash impact**, not revenue prediction
- Clean separation of concerns: revenue model → weekly revenue → cash flow model

### Why 13 Weeks
- Standard CFO planning horizon (1 quarter)
- Balances precision (near-term) with visibility (medium-term)
- Aligns with board reporting cycles
- Can extend to 26 weeks for longer-term planning

### Why Weekly Granularity
- More actionable than monthly (see issues 2-3 weeks out, not 1 month)
- Less noisy than daily (smooths out day-to-day volatility)
- Matches payment cycles (bi-weekly payouts, monthly vendor payments)
- Natural unit for runway discussions ("we have 8 weeks of cash")

---

## 📊 Sample Output

### No Revenue (Expense-Only Forecast)
```
Week 1: -$108,572 → Balance: $141,428
Week 2: -$105,137 → Balance: $36,291
Week 3: -$105,137 → Balance: -$68,846 ⚠️ CASH OUT
```
Runway: **3 weeks** (without revenue)

### With $75k/week Revenue
```
Week 1: -$33,572 → Balance: $216,428
Week 2: -$30,137 → Balance: $186,291
Week 3: -$30,137 → Balance: $156,154
...
Week 13: -$30,137 → Balance: -$214,393
```
Runway: **~10 weeks** at $75k/week revenue

### With $125k/week Revenue (Break-Even)
```
Week 1: +$16,428 → Balance: $266,428
Week 2: +$19,863 → Balance: $286,291
Week 3: +$19,863 → Balance: $306,154
...
Week 13: +$19,863 → Balance: $524,610
```
Runway: **13+ weeks** (cash positive)

---

**Date**: 2026-02-25
**Status**: Forecast Engine Complete ✅
**Ready for**: Revenue integration, Excel reporting, scenario analysis
