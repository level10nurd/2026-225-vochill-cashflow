# BigQuery Financial Schema - Implementation Summary

## 🎯 Overview

We've designed a comprehensive financial data model for BigQuery to support VoChill's cash flow forecasting and reporting needs. This schema creates purpose-built financial tables that complement the existing sales/operations tables.

---

## 📊 New Tables Added to BigQuery

### Core Cash Flow Tables (7)
| Table | Purpose | Key Features |
|-------|---------|--------------|
| **cash_transactions** | Single source of truth for all cash in/out | Partitioned by cash_date, supports actuals + forecasts |
| **cash_balances** | Daily cash position by account | Tracks beginning/ending balances, LOC availability |
| **bank_accounts** | Master list of accounts & credit lines | Includes Frost checking, SBA LOC, credit cards |
| **debt_schedule** | Loan payment schedule | Principal/interest split, SBA loan terms |
| **cash_forecast** | 13-week rolling forecast output | Supports multiple scenarios, runway calculation |
| **gl_transactions** | QuickBooks GL export | Full accounting detail from QB |
| **chart_of_accounts** | CoA with CF category mapping | Maps every QB account to cash flow categories |

### Supporting Tables (6)
| Table | Purpose |
|-------|---------|
| **payment_terms** | Payment timing rules (Amazon bi-weekly, Shopify daily, Net 30, etc.) |
| **recurring_transactions** | Known recurring items (rent, subscriptions, loan payments) |
| **capex_plan** | Planned capital expenditures |
| **budget** | Annual/monthly budgets by category |
| **scenarios** | Forecast scenario definitions (base/best/worst) |
| **forecast_assumptions** | Detailed forecast assumptions & rationale |

### Analytical Views (3)
- `v_daily_cash_flow` - Daily cash flow statement
- `v_weekly_cash_flow` - 13-week rolling view
- `v_cash_position` - Current cash + liquidity

---

## 🏗️ Architecture Benefits

### Before (Current State)
```
Sales/Ops Tables (deposits, orders, fees)
    ↓
  Complex SQL queries every time
    ↓
  Cash flow analysis
```
**Problems:**
- ❌ Repeated complex transformations
- ❌ Inconsistent cash timing logic
- ❌ No historical forecast tracking
- ❌ Difficult to separate actuals from forecasts

### After (New Architecture)
```
Sales/Ops Tables (deposits, orders, fees)
    ↓
  ETL Pipeline (1x transformation)
    ↓
Financial Tables (cash_transactions, cash_balances, etc.)
    ↓
  Simple queries + views
    ↓
  Cash flow reports & dashboards
```
**Benefits:**
- ✅ Transform once, query many times
- ✅ Consistent cash timing rules
- ✅ Full history of forecasts & assumptions
- ✅ Clean separation: actuals vs forecasts
- ✅ Scenario planning built-in
- ✅ Purpose-built for cash flow analysis

---

## 📋 Data Flow

### 1. Historical Data Load (One-Time)
```sql
-- Step 1: Populate master data
INSERT INTO bank_accounts --> Frost Checking, SBA LOC, credit cards
INSERT INTO chart_of_accounts --> QB CoA with CF mappings
INSERT INTO payment_terms --> Amazon bi-weekly, Shopify daily, etc.

-- Step 2: Transform existing sales data → cash transactions
INSERT INTO cash_transactions
SELECT ... FROM deposits  -- Revenue from Amazon/Shopify
UNION ALL
SELECT ... FROM fees      -- Platform fees (informational)
UNION ALL
SELECT ... FROM refunds   -- Customer refunds

-- Step 3: Load GL from QuickBooks
INSERT INTO gl_transactions --> QuickBooks export
--> Transform to cash_transactions (OpEx, CapEx, Financing)

-- Step 4: Calculate daily balances
INSERT INTO cash_balances --> Daily cash position
```

### 2. Ongoing Updates (Daily/Weekly)
```sql
-- Daily: Sync new deposits/orders → cash_transactions
-- Weekly: Update cash_balances from bank feeds
-- Monthly: Generate new cash_forecast runs
```

### 3. Forecasting (As Needed)
```python
# Python forecast engine:
# 1. Query historical cash_transactions (actuals)
# 2. Apply revenue forecast from existing forecast table
# 3. Project expenses using trends + recurring_transactions
# 4. Schedule debt service from debt_schedule
# 5. Add planned CapEx from capex_plan
# 6. Calculate 13-week forecast → INSERT INTO cash_forecast
```

---

## 🚀 Implementation Roadmap

### Phase 1: Create Tables ✅ READY
```bash
# Execute DDL in BigQuery
bq query --use_legacy_sql=false < database/create_financial_tables.sql
```

### Phase 2: Populate Master Data
**Tasks:**
1. ✍️ **bank_accounts** - Manually insert VoChill accounts
   - Frost Checking
   - Money Market
   - SBA LOC ($500k limit)
   - AMEX Gold Card
   - Chase Inc Card
   - Shopify Card
   - Southwest Card

2. 🗺️ **chart_of_accounts** - Load from `data/coa.csv` + apply mappings from `cash_flow_categories.yaml`

3. ⏰ **payment_terms** - Already seeded with defaults (Amazon, Shopify, Net 30, etc.)

4. 🔁 **recurring_transactions** - Manually insert known recurring items:
   - SBA Loan interest ($4,583/mo on day 30)
   - Rent
   - Software subscriptions
   - Insurance

5. 📅 **debt_schedule** - Generate SBA loan payment schedule
   - I/O period: May 2024 - May 2026 (interest only)
   - Amortization: Jun 2026 - May 2031 (60 months P&I)
   - Rate: Prime + 2.25% (variable, adjusts monthly)

### Phase 3: Historical Data ETL
**Transform existing data:**
1. **deposits** → **cash_transactions** (revenue)
   - Use settlement_id to group transactions
   - Apply Amazon bi-weekly + 2 day timing
   - Apply Shopify daily + 2 day timing
   - Net proceeds only (fees already deducted)

2. **refunds** → **cash_transactions** (contra-revenue)
   - Same timing logic as deposits

3. **invoices** + **vendors** → **cash_transactions** (COGS/OpEx)
   - Join to vendors table for payment terms
   - Calculate cash_date using vendor payment days

4. **QuickBooks GL** → **gl_transactions** → **cash_transactions**
   - Export QB GL for OpEx, CapEx, Financing
   - Map to chart_of_accounts for categorization
   - Transform to cash basis

5. **Bank statements** → **cash_balances**
   - Daily ending balances by account
   - LOC balance and available credit

### Phase 4: Forecast Engine
**Build Python forecasting module:**
1. Query historical actuals from `cash_transactions`
2. Apply revenue forecast from existing `forecast` table
3. Project expenses using:
   - Trailing 3-month average
   - Known `recurring_transactions`
   - Planned `capex_plan`
4. Schedule debt service from `debt_schedule`
5. Calculate weekly net cash flow
6. Generate 13-week forecast → `INSERT INTO cash_forecast`
7. Run scenarios (base/best/worst)

### Phase 5: Reporting & Dashboards
**Build outputs:**
1. Excel workbook generator (Python)
2. Hex notebook dashboards
3. Weekly cash position email report
4. Alerts for cash below thresholds

---

## 🔧 Tools & Technologies

| Component | Technology |
|-----------|-----------|
| **Data Warehouse** | Google Cloud BigQuery |
| **ETL/Transformation** | Python + BigQuery SQL |
| **Forecast Engine** | Python (pandas, numpy) |
| **Reporting** | Excel (openpyxl/xlsxwriter), Hex |
| **Orchestration** | TBD (Cloud Scheduler, Airflow, or manual) |

---

## 📁 File Locations

### Design Documents
- `database/financial_schema_design.md` - Full schema design with rationale
- `database/create_financial_tables.sql` - DDL to create all tables
- `database/bigquery_entity_map.csv` - Existing table schema reference
- `docs/ARCHITECTURE.md` - Overall system architecture

### Configuration
- `data/config/cash_flow_categories.yaml` - CoA → CF category mapping
- `data/config/payment_timing.yaml` - Payment timing rules

### Code
- `src/data/bigquery_connector.py` - BigQuery client
- `src/queries/*.sql` - SQL query templates
- `src/config.py` - Configuration management

---

## 💡 Key Design Decisions

### 1. **Separate Financial Tables**
**Why:** Sales/ops data is optimized for operational analysis. Financial tables are optimized for cash flow forecasting.

### 2. **cash_date vs transaction_date**
**Why:** Cash flow forecasting requires knowing *when cash moves*, not when transactions occur. We track both.

### 3. **Single cash_transactions Table**
**Why:** One source of truth for all cash movements. Easier to query, easier to maintain.

### 4. **Forecast Data in Same Tables**
**Why:** `is_forecast` flag allows mixing actuals and forecasts. Simplifies queries and rolling forecasts.

### 5. **Scenario Support Built-In**
**Why:** Scenario planning is critical for cash flow. Better to design for it upfront.

### 6. **Denormalization Where Helpful**
**Why:** BigQuery favors denormalization for query performance. We denormalize `bank_account_name` in `cash_transactions` for convenience.

---

## 📊 Sample Queries

### Get last 30 days of cash flow by category
```sql
SELECT
  cash_date,
  cash_flow_category,
  SUM(amount) as net_cash_flow
FROM vochill.revrec.cash_transactions
WHERE cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND is_forecast = FALSE
GROUP BY cash_date, cash_flow_category
ORDER BY cash_date DESC;
```

### Get current cash position
```sql
SELECT * FROM vochill.revrec.v_cash_position;
```

### Get 13-week forecast (latest run, base case)
```sql
SELECT
  period_date as week_ending,
  week_number,
  operating_cash_flow,
  ending_cash,
  total_liquidity,
  weeks_of_runway
FROM vochill.revrec.cash_forecast
WHERE forecast_id = (SELECT MAX(forecast_id) FROM vochill.revrec.cash_forecast)
  AND scenario_id = 'base'
ORDER BY week_number;
```

---

## ✅ Next Steps

1. **Review schema design** - Confirm structure meets all requirements
2. **Execute DDL** - Run `create_financial_tables.sql` in BigQuery
3. **Populate master data** - Insert bank accounts, recurring transactions, debt schedule
4. **Build ETL pipeline** - Transform existing data → financial tables
5. **Test data quality** - Verify transformations are accurate
6. **Build forecast engine** - Python module to generate `cash_forecast`
7. **Create reports** - Excel workbooks, Hex dashboards

---

## 📞 Questions to Resolve

1. **QuickBooks GL Export:**
   - Do you have a GL export available?
   - What date range should we backfill?
   - Format: CSV, Excel, QBO file?

2. **Bank Statement Data:**
   - Can we get daily balance history from Frost Bank?
   - What about credit card statements?

3. **Payroll Schedule:**
   - Bi-weekly or semi-monthly?
   - What days are payroll processed?

4. **Forecast Scope:**
   - Start with 13-week forecast or longer?
   - Which scenarios to build first? (Base only, or Base + Best + Worst?)

5. **Automation:**
   - Manual refresh or automated daily/weekly?
   - Where should alerts/reports be sent?
