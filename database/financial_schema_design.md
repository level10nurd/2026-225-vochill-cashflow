# VoChill BigQuery Financial Schema Design

## Overview

This document defines new financial tables to add to the `vochill.revrec` BigQuery dataset. These tables are purpose-built for cash flow forecasting, reporting, and financial analysis.

## Design Principles

1. **Separate concerns**: Sales/operations data stays in existing tables; financial data in new tables
2. **Single source of truth**: Each fact stored once, derived metrics calculated in views
3. **Cash-focused**: Emphasize actual cash dates, not accrual accounting dates
4. **Forecast-ready**: Support both historical actuals and future projections
5. **Scenario planning**: Enable base/best/worst case modeling

---

## Table Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXISTING TABLES                              │
│  (Sales & Operations - Already in BigQuery)                    │
│                                                                 │
│  • deposits, orders, fees, refunds                             │
│  • items, vendors, po, po_line_item, invoices                  │
│  • forecast (existing SKU-level forecast)                      │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ ETL/Transform
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NEW FINANCIAL TABLES                         │
│  (Purpose-built for cash flow & financial analysis)            │
│                                                                 │
│  CORE TABLES:                                                   │
│  • cash_transactions ──► All cash in/out with categories       │
│  • cash_balances ──────► Daily cash position by account        │
│  • bank_accounts ──────► Master list of accounts & LOCs        │
│  • debt_schedule ──────► Loan payment schedule                 │
│  • cash_forecast ──────► 13-week rolling forecast              │
│                                                                 │
│  SUPPORTING TABLES:                                             │
│  • gl_transactions ────► QuickBooks GL export                  │
│  • chart_of_accounts ──► CoA with CF mapping                   │
│  • payment_terms ──────► Payment timing rules                  │
│  • recurring_transactions ─► Known recurring items             │
│  • capex_plan ──────────► Planned capital expenditures         │
│  • budget ──────────────► Annual/monthly budgets               │
│  • scenarios ────────────► Scenario definitions                │
│  • forecast_assumptions ─► Forecast inputs & drivers           │
└─────────────────────────────────────────────────────────────────┘
             │
             │ Query/Report
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICAL VIEWS                             │
│                                                                 │
│  • v_daily_cash_flow ──────► Daily cash flow statement         │
│  • v_weekly_cash_flow ─────► Weekly cash flow (13-week view)   │
│  • v_cash_position ────────► Current cash position & runway    │
│  • v_budget_variance ──────► Budget vs actual analysis         │
│  • v_scenario_comparison ──► Compare scenarios side-by-side    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Tables

### 1. `cash_transactions`
**Purpose**: Single source of truth for all cash inflows and outflows

**Schema**:
```sql
CREATE TABLE vochill.revrec.cash_transactions (
  -- Primary key
  transaction_id STRING NOT NULL,

  -- Dates
  transaction_date DATE NOT NULL,      -- When transaction occurred
  cash_date DATE NOT NULL,             -- When cash actually moved
  value_date DATE,                     -- Bank value date (if different)

  -- Source tracking
  source_system STRING NOT NULL,       -- 'QuickBooks', 'Amazon', 'Shopify', 'Manual', etc.
  source_id STRING,                    -- ID from source system
  source_table STRING,                 -- Which table this came from

  -- Account information
  bank_account_id STRING,              -- FK to bank_accounts table
  bank_account_name STRING,            -- Denormalized for convenience

  -- Cash flow classification
  cash_flow_section STRING NOT NULL,   -- 'Operating', 'Investing', 'Financing'
  cash_flow_category STRING NOT NULL,  -- 'Revenue - Amazon', 'COGS - Materials', etc.
  cash_flow_subcategory STRING,        -- Additional detail

  -- Amounts
  amount FLOAT64 NOT NULL,             -- Positive = inflow, Negative = outflow
  currency STRING DEFAULT 'USD',

  -- Counterparty
  counterparty STRING,                 -- Customer, vendor, lender, etc.
  counterparty_type STRING,            -- 'Customer', 'Vendor', 'Bank', 'Owner', etc.

  -- Description
  description STRING,
  notes STRING,

  -- Metadata
  is_forecast BOOLEAN DEFAULT FALSE,   -- TRUE for forecasted transactions
  is_recurring BOOLEAN DEFAULT FALSE,  -- TRUE for recurring transactions
  recurring_id STRING,                 -- FK to recurring_transactions
  scenario_id STRING,                  -- FK to scenarios (for forecasts)

  -- Tags for analysis
  tags ARRAY<STRING>,                  -- ['marketing', 'amazon_ppc', etc.]

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING DEFAULT 'system'
)
PARTITION BY DATE(cash_date)
CLUSTER BY bank_account_id, cash_flow_category;

-- Indexes for common queries
CREATE INDEX idx_cash_transactions_dates
  ON cash_transactions(cash_date, transaction_date);

CREATE INDEX idx_cash_transactions_category
  ON cash_transactions(cash_flow_section, cash_flow_category);
```

**Sample Data**:
| transaction_id | transaction_date | cash_date | source_system | bank_account_id | cash_flow_category | amount | counterparty | description |
|---|---|---|---|---|---|---|---|---|
| txn_001 | 2026-02-21 | 2026-02-23 | Amazon | frost_checking | Revenue - Amazon | 3202.73 | Amazon | Settlement 25725857361 |
| txn_002 | 2026-02-01 | 2026-03-01 | QuickBooks | amex_gold | OpEx - Marketing - Google Ads | -2500.00 | Google LLC | Google Ads - Feb |
| txn_003 | 2026-02-28 | 2026-02-28 | QuickBooks | frost_checking | Financing - Debt Service | -4583.33 | Frost Bank | SBA Loan Interest - Feb |

---

### 2. `cash_balances`
**Purpose**: Track daily cash position across all accounts

**Schema**:
```sql
CREATE TABLE vochill.revrec.cash_balances (
  -- Composite primary key
  balance_date DATE NOT NULL,
  bank_account_id STRING NOT NULL,

  -- Account details (denormalized)
  bank_account_name STRING,
  account_type STRING,               -- 'Checking', 'Money Market', 'LOC', etc.

  -- Balance amounts
  beginning_balance FLOAT64 NOT NULL,
  ending_balance FLOAT64 NOT NULL,

  -- Daily activity
  total_inflows FLOAT64 DEFAULT 0,
  total_outflows FLOAT64 DEFAULT 0,
  net_change FLOAT64,                -- ending - beginning

  -- For credit lines
  credit_limit FLOAT64,              -- NULL for non-LOC accounts
  available_credit FLOAT64,          -- credit_limit - ending_balance

  -- Metadata
  is_forecast BOOLEAN DEFAULT FALSE,
  scenario_id STRING,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY balance_date
CLUSTER BY bank_account_id;

-- Unique constraint
ALTER TABLE cash_balances
  ADD CONSTRAINT pk_cash_balances
  PRIMARY KEY (balance_date, bank_account_id) NOT ENFORCED;
```

---

### 3. `bank_accounts`
**Purpose**: Master list of all bank accounts and credit lines

**Schema**:
```sql
CREATE TABLE vochill.revrec.bank_accounts (
  -- Primary key
  account_id STRING NOT NULL,

  -- Account details
  account_name STRING NOT NULL,
  account_number STRING,             -- Masked: XXXX1234
  account_type STRING NOT NULL,      -- 'Checking', 'Savings', 'Money Market', 'LOC', 'Credit Card'

  -- Institution
  institution_name STRING NOT NULL,
  institution_routing STRING,

  -- For credit lines
  is_credit_line BOOLEAN DEFAULT FALSE,
  credit_limit FLOAT64,
  interest_rate FLOAT64,             -- Annual rate as decimal (0.1075 = 10.75%)

  -- QuickBooks mapping
  qb_account_name STRING,
  qb_account_number STRING,

  -- Status
  is_active BOOLEAN DEFAULT TRUE,
  opened_date DATE,
  closed_date DATE,

  -- Metadata
  notes STRING,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Unique constraint
ALTER TABLE bank_accounts
  ADD CONSTRAINT pk_bank_accounts
  PRIMARY KEY (account_id) NOT ENFORCED;
```

**Sample Data**:
| account_id | account_name | account_type | institution_name | is_credit_line | credit_limit |
|---|---|---|---|---|---|
| frost_checking | VoChill Checking | Checking | Frost Bank | FALSE | NULL |
| frost_mm | Money Market | Money Market | Frost Bank | FALSE | NULL |
| sba_loc | SBA Loan | LOC | Frost Bank | TRUE | 500000.00 |
| amex_gold | AMEX Gold Card | Credit Card | American Express | TRUE | 50000.00 |
| chase_inc | Chase Inc | Credit Card | Chase | TRUE | 25000.00 |

---

### 4. `debt_schedule`
**Purpose**: Detailed loan payment schedule with principal/interest split

**Schema**:
```sql
CREATE TABLE vochill.revrec.debt_schedule (
  -- Primary key
  schedule_id STRING NOT NULL,

  -- Loan identification
  loan_id STRING NOT NULL,
  loan_name STRING NOT NULL,         -- 'SBA Loan', 'Equipment Loan', etc.
  lender STRING NOT NULL,

  -- Payment details
  payment_date DATE NOT NULL,
  payment_number INT64,

  -- Payment breakdown
  payment_amount FLOAT64 NOT NULL,
  principal_amount FLOAT64 NOT NULL,
  interest_amount FLOAT64 NOT NULL,
  fees_amount FLOAT64 DEFAULT 0,

  -- Running balances
  beginning_principal FLOAT64 NOT NULL,
  ending_principal FLOAT64 NOT NULL,

  -- Interest calculation
  interest_rate FLOAT64 NOT NULL,    -- Rate at time of payment
  days_in_period INT64,

  -- Status
  is_paid BOOLEAN DEFAULT FALSE,
  actual_payment_date DATE,
  actual_payment_amount FLOAT64,

  -- Metadata
  payment_type STRING,               -- 'Interest Only', 'Principal & Interest', 'Balloon'
  is_forecast BOOLEAN DEFAULT FALSE,
  scenario_id STRING,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY payment_date
CLUSTER BY loan_id;
```

---

### 5. `cash_forecast`
**Purpose**: 13-week rolling cash forecast output

**Schema**:
```sql
CREATE TABLE vochill.revrec.cash_forecast (
  -- Composite key
  forecast_id STRING NOT NULL,
  forecast_date DATE NOT NULL,       -- Date of forecast run
  period_date DATE NOT NULL,         -- Week ending date
  scenario_id STRING NOT NULL,       -- 'base', 'best', 'worst', etc.

  -- Week identification
  week_number INT64,                 -- 1-13 for 13-week forecast
  is_actual BOOLEAN,                 -- TRUE if period is historical

  -- Cash flow by category
  operating_inflows FLOAT64 DEFAULT 0,
  operating_outflows FLOAT64 DEFAULT 0,
  operating_cash_flow FLOAT64,

  investing_outflows FLOAT64 DEFAULT 0,
  financing_inflows FLOAT64 DEFAULT 0,
  financing_outflows FLOAT64 DEFAULT 0,

  net_cash_flow FLOAT64,

  -- Cash position
  beginning_cash FLOAT64 NOT NULL,
  ending_cash FLOAT64 NOT NULL,

  -- Credit availability
  loc_balance FLOAT64,
  loc_available FLOAT64,

  -- Total liquidity (cash + available LOC)
  total_liquidity FLOAT64,

  -- Runway calculation
  avg_weekly_burn FLOAT64,
  weeks_of_runway INT64,

  -- Metadata
  forecast_method STRING,            -- 'Historical Average', 'Regression', 'Manual', etc.
  confidence_level STRING,           -- 'High', 'Medium', 'Low'
  notes STRING,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING DEFAULT 'system'
)
PARTITION BY forecast_date
CLUSTER BY scenario_id, period_date;
```

---

## Supporting Tables

### 6. `gl_transactions`
**Purpose**: QuickBooks general ledger export

**Schema**:
```sql
CREATE TABLE vochill.revrec.gl_transactions (
  -- Primary key
  entry_id STRING NOT NULL,

  -- Transaction details
  transaction_date DATE NOT NULL,
  posting_date DATE,

  -- Account information
  account_number STRING,
  account_name STRING NOT NULL,
  account_type STRING,               -- Asset, Liability, Equity, Revenue, Expense

  -- Amounts
  debit_amount FLOAT64 DEFAULT 0,
  debit_amount FLOAT64 DEFAULT 0,
  amount FLOAT64,                    -- Signed: debit positive, credit negative

  -- Transaction description
  transaction_type STRING,           -- Invoice, Payment, Journal Entry, etc.
  description STRING,
  memo STRING,
  reference_number STRING,

  -- Links
  customer STRING,
  vendor STRING,
  class STRING,                      -- QuickBooks class/department

  -- Source
  source_document STRING,            -- Invoice number, check number, etc.

  -- Reconciliation
  is_reconciled BOOLEAN DEFAULT FALSE,
  reconcile_date DATE,

  -- Audit
  qb_transaction_id STRING,
  imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY transaction_date
CLUSTER BY account_name;
```

---

### 7. `chart_of_accounts`
**Purpose**: Chart of accounts with cash flow category mapping

**Schema**:
```sql
CREATE TABLE vochill.revrec.chart_of_accounts (
  -- Primary key
  account_id STRING NOT NULL,

  -- Account details
  account_number STRING,
  account_name STRING NOT NULL,
  account_type STRING NOT NULL,      -- Asset, Liability, Equity, Revenue, Expense
  account_subtype STRING,

  -- Hierarchy
  parent_account_id STRING,
  account_level INT64,               -- 1 = top level, 2 = sub, etc.

  -- Cash flow mapping
  cash_flow_section STRING,          -- Operating, Investing, Financing, Non-Cash
  cash_flow_category STRING,
  cash_flow_subcategory STRING,
  is_cash_account BOOLEAN DEFAULT TRUE,  -- FALSE for non-cash items like depreciation

  -- Payment timing
  default_payment_timing STRING,     -- References payment_terms table

  -- Status
  is_active BOOLEAN DEFAULT TRUE,

  -- Metadata
  description STRING,
  notes STRING,

  -- QuickBooks sync
  qb_account_id STRING,
  qb_fully_qualified_name STRING,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

ALTER TABLE chart_of_accounts
  ADD CONSTRAINT pk_chart_of_accounts
  PRIMARY KEY (account_id) NOT ENFORCED;
```

---

### 8. `payment_terms`
**Purpose**: Payment timing rules for cash flow forecasting

**Schema**:
```sql
CREATE TABLE vochill.revrec.payment_terms (
  -- Primary key
  term_id STRING NOT NULL,

  -- Term identification
  term_name STRING NOT NULL,         -- 'Amazon Settlement', 'Shopify Payout', 'Net 30', etc.
  term_category STRING,              -- 'Revenue', 'Expense', 'Debt Service'

  -- Timing rules
  cycle_type STRING,                 -- 'Daily', 'Weekly', 'Bi-Weekly', 'Monthly', 'Invoice-Based'
  lag_days INT64,                    -- Days between transaction and cash

  -- For periodic cycles
  payout_days ARRAY<STRING>,         -- ['Monday', 'Wednesday', 'Friday'] for Shopify
  payout_day_of_month INT64,         -- 30 for SBA loan payment

  -- For settlement cycles
  settlement_period_days INT64,      -- 14 for Amazon
  settlement_lag_days INT64,         -- 2 for Amazon

  -- Weekend handling
  weekend_handling STRING,           -- 'Next Business Day', 'Previous Business Day', 'No Adjustment'

  -- Description
  description STRING,
  example STRING,                    -- "Order on Mon → Payout on Wed"

  -- Metadata
  is_active BOOLEAN DEFAULT TRUE,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

---

### 9. `recurring_transactions`
**Purpose**: Known recurring revenue and expenses

**Schema**:
```sql
CREATE TABLE vochill.revrec.recurring_transactions (
  -- Primary key
  recurring_id STRING NOT NULL,

  -- Recurrence details
  transaction_name STRING NOT NULL,
  cash_flow_category STRING NOT NULL,

  -- Amount
  amount FLOAT64 NOT NULL,
  currency STRING DEFAULT 'USD',

  -- Recurrence pattern
  frequency STRING NOT NULL,         -- 'Daily', 'Weekly', 'Monthly', 'Quarterly', 'Annually'
  interval INT64 DEFAULT 1,          -- Every N periods (e.g., every 2 weeks)

  -- Timing
  day_of_week INT64,                 -- 1-7 for weekly
  day_of_month INT64,                -- 1-31 for monthly
  month_of_year INT64,               -- 1-12 for annual

  -- Date range
  start_date DATE NOT NULL,
  end_date DATE,                     -- NULL = indefinite

  -- Counterparty
  counterparty STRING,
  bank_account_id STRING,

  -- Metadata
  description STRING,
  notes STRING,
  is_active BOOLEAN DEFAULT TRUE,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

**Sample Data**:
| recurring_id | transaction_name | cash_flow_category | amount | frequency | day_of_month |
|---|---|---|---|---|---|
| rec_001 | SBA Loan Interest | Financing - Debt Service | -4583.33 | Monthly | 30 |
| rec_002 | Shopify Subscription | OpEx - SG&A - Software | -299.00 | Monthly | 1 |
| rec_003 | Warehouse Rent | OpEx - SG&A - Rent | -5000.00 | Monthly | 1 |

---

### 10. `capex_plan`
**Purpose**: Planned capital expenditures

**Schema**:
```sql
CREATE TABLE vochill.revrec.capex_plan (
  -- Primary key
  capex_id STRING NOT NULL,

  -- Project details
  project_name STRING NOT NULL,
  category STRING NOT NULL,          -- 'Equipment', 'Technology', 'Facility', 'IP', etc.
  description STRING,

  -- Financial details
  estimated_cost FLOAT64 NOT NULL,
  actual_cost FLOAT64,
  variance FLOAT64,

  -- Timing
  planned_date DATE NOT NULL,
  actual_date DATE,

  -- Payment terms
  payment_terms STRING,              -- 'Full upfront', '50% deposit', 'Net 30', etc.
  deposit_amount FLOAT64,
  deposit_date DATE,
  final_payment_amount FLOAT64,
  final_payment_date DATE,

  -- Status
  status STRING NOT NULL,            -- 'Planned', 'Approved', 'In Progress', 'Completed', 'Cancelled'

  -- Approval
  approved_by STRING,
  approved_date DATE,

  -- Metadata
  vendor STRING,
  po_number STRING,
  notes STRING,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY planned_date;
```

---

### 11. `budget`
**Purpose**: Annual and monthly budgets by category

**Schema**:
```sql
CREATE TABLE vochill.revrec.budget (
  -- Composite key
  budget_id STRING NOT NULL,
  fiscal_year INT64 NOT NULL,
  period_type STRING NOT NULL,       -- 'Monthly', 'Quarterly', 'Annual'
  period_start_date DATE NOT NULL,

  -- Category
  cash_flow_section STRING NOT NULL,
  cash_flow_category STRING NOT NULL,
  cash_flow_subcategory STRING,

  -- Budget amounts
  budget_amount FLOAT64 NOT NULL,

  -- Metadata
  version INT64 DEFAULT 1,           -- Budget version (for revisions)
  is_active BOOLEAN DEFAULT TRUE,
  notes STRING,

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING
)
PARTITION BY period_start_date
CLUSTER BY fiscal_year, cash_flow_category;
```

---

### 12. `scenarios`
**Purpose**: Scenario definitions for forecasting

**Schema**:
```sql
CREATE TABLE vochill.revrec.scenarios (
  -- Primary key
  scenario_id STRING NOT NULL,

  -- Scenario details
  scenario_name STRING NOT NULL,
  scenario_type STRING NOT NULL,     -- 'Base', 'Best', 'Worst', 'Custom'
  description STRING,

  -- Assumptions
  revenue_growth_rate FLOAT64,       -- Annual growth rate (0.15 = 15%)
  expense_inflation_rate FLOAT64,

  -- Custom adjustments (JSON)
  custom_assumptions STRING,         -- JSON blob of scenario-specific assumptions

  -- Metadata
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING
);
```

---

### 13. `forecast_assumptions`
**Purpose**: Detailed assumptions driving the forecast

**Schema**:
```sql
CREATE TABLE vochill.revrec.forecast_assumptions (
  -- Composite key
  assumption_id STRING NOT NULL,
  scenario_id STRING NOT NULL,
  forecast_date DATE NOT NULL,

  -- Assumption details
  assumption_category STRING NOT NULL,  -- 'Revenue', 'COGS', 'OpEx', 'CapEx', 'Financing'
  assumption_name STRING NOT NULL,

  -- Value
  assumption_value FLOAT64,
  assumption_value_text STRING,         -- For non-numeric assumptions

  -- Units
  value_type STRING,                    -- 'Percentage', 'Dollar Amount', 'Units', 'Text'

  -- Description
  description STRING,
  rationale STRING,                     -- Why this assumption was chosen

  -- Source
  data_source STRING,                   -- 'Historical Average', 'Management Guidance', 'Market Research', etc.
  confidence_level STRING,              -- 'High', 'Medium', 'Low'

  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING
)
PARTITION BY forecast_date
CLUSTER BY scenario_id, assumption_category;
```

---

## Analytical Views

### v_daily_cash_flow
```sql
CREATE VIEW vochill.revrec.v_daily_cash_flow AS
SELECT
  ct.cash_date,
  ct.cash_flow_section,
  ct.cash_flow_category,
  ct.cash_flow_subcategory,

  SUM(CASE WHEN ct.amount > 0 THEN ct.amount ELSE 0 END) as total_inflows,
  SUM(CASE WHEN ct.amount < 0 THEN ABS(ct.amount) ELSE 0 END) as total_outflows,
  SUM(ct.amount) as net_cash_flow,

  COUNT(*) as transaction_count

FROM vochill.revrec.cash_transactions ct
WHERE ct.is_forecast = FALSE
GROUP BY ct.cash_date, ct.cash_flow_section, ct.cash_flow_category, ct.cash_flow_subcategory
ORDER BY ct.cash_date DESC, ct.cash_flow_section, ct.cash_flow_category;
```

### v_weekly_cash_flow
```sql
CREATE VIEW vochill.revrec.v_weekly_cash_flow AS
SELECT
  DATE_TRUNC(ct.cash_date, WEEK(MONDAY)) as week_start,
  DATE_ADD(DATE_TRUNC(ct.cash_date, WEEK(MONDAY)), INTERVAL 6 DAY) as week_end,
  ct.cash_flow_section,
  ct.cash_flow_category,

  SUM(ct.amount) as net_cash_flow,
  COUNT(*) as transaction_count

FROM vochill.revrec.cash_transactions ct
WHERE ct.is_forecast = FALSE
  AND ct.cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 WEEK)
GROUP BY week_start, week_end, ct.cash_flow_section, ct.cash_flow_category
ORDER BY week_start DESC, ct.cash_flow_section, ct.cash_flow_category;
```

### v_cash_position
```sql
CREATE VIEW vochill.revrec.v_cash_position AS
WITH latest_balances AS (
  SELECT
    bank_account_id,
    bank_account_name,
    account_type,
    ending_balance,
    credit_limit,
    available_credit
  FROM vochill.revrec.cash_balances
  WHERE balance_date = (SELECT MAX(balance_date) FROM vochill.revrec.cash_balances WHERE is_forecast = FALSE)
    AND is_forecast = FALSE
)
SELECT
  SUM(CASE WHEN account_type IN ('Checking', 'Savings', 'Money Market') THEN ending_balance ELSE 0 END) as total_cash,
  SUM(CASE WHEN account_type = 'LOC' THEN ABS(ending_balance) ELSE 0 END) as total_loc_balance,
  SUM(CASE WHEN account_type = 'LOC' THEN available_credit ELSE 0 END) as total_loc_available,
  SUM(CASE WHEN account_type IN ('Checking', 'Savings', 'Money Market') THEN ending_balance ELSE 0 END) +
  SUM(CASE WHEN account_type = 'LOC' THEN available_credit ELSE 0 END) as total_liquidity
FROM latest_balances;
```

---

## ETL Strategy

### Phase 1: Historical Data Load
1. **Export QuickBooks GL** → Populate `gl_transactions` and `chart_of_accounts`
2. **Transform existing deposits data** → Populate `cash_transactions` (revenue)
3. **Transform existing fees/refunds** → Populate `cash_transactions` (COGS, refunds)
4. **Load bank statements** → Populate `cash_balances`
5. **Manual entry** → Populate `bank_accounts`, `debt_schedule`, `recurring_transactions`

### Phase 2: Ongoing Sync
1. **Daily**: Sync new deposits/orders/fees from existing tables → `cash_transactions`
2. **Weekly**: Update `cash_balances` from bank feeds
3. **Monthly**: Generate new `cash_forecast` runs
4. **As needed**: Update `budget`, `capex_plan`, `scenarios`

### Phase 3: Automation
1. Build scheduled BigQuery jobs for daily ETL
2. Create Cloud Functions for real-time updates
3. Build data quality checks and alerts

---

## Next Steps

1. **Review & Approve Schema**: Confirm this structure meets all requirements
2. **Create DDL Scripts**: Generate BigQuery DDL to create tables
3. **Build ETL Pipeline**: Python scripts to populate tables from existing data
4. **Load Historical Data**: Backfill tables with historical transactions
5. **Build Forecast Engine**: Python code to generate `cash_forecast` rows
6. **Create Reports**: Excel workbooks and Hex dashboards querying these tables

---

## Benefits of This Approach

✅ **Clean separation**: Financial data separate from sales/operations data
✅ **Query performance**: Purpose-built tables optimized for cash flow queries
✅ **Forecasting ready**: Structure supports both actuals and projections
✅ **Scenario planning**: Built-in support for multiple scenarios
✅ **Single source of truth**: All cash transactions in one table
✅ **Scalable**: Can add more granularity as needed
✅ **Audit trail**: Full history of forecasts and assumptions
