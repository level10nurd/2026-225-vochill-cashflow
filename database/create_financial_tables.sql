-- VoChill Financial Tables DDL
-- Create financial tables in BigQuery: vochill.revrec dataset
--
-- Execute in order (dependencies managed by order)
-- Run in Google Cloud Console BigQuery or via bq CLI

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- 1. BANK ACCOUNTS (master table, no dependencies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.bank_accounts` (
  account_id STRING NOT NULL OPTIONS(description="Unique account identifier"),
  account_name STRING NOT NULL OPTIONS(description="Display name of account"),
  account_number STRING OPTIONS(description="Masked account number (XXXX1234)"),
  account_type STRING NOT NULL OPTIONS(description="Checking, Savings, Money Market, LOC, Credit Card"),

  institution_name STRING NOT NULL OPTIONS(description="Bank or financial institution"),
  institution_routing STRING OPTIONS(description="Bank routing number"),

  is_credit_line BOOLEAN DEFAULT FALSE OPTIONS(description="TRUE for lines of credit"),
  credit_limit FLOAT64 OPTIONS(description="Credit limit for LOCs and credit cards"),
  interest_rate FLOAT64 OPTIONS(description="Annual interest rate as decimal (0.1075 = 10.75%)"),

  qb_account_name STRING OPTIONS(description="QuickBooks account name"),
  qb_account_number STRING OPTIONS(description="QuickBooks account number"),

  is_active BOOLEAN DEFAULT TRUE,
  opened_date DATE,
  closed_date DATE,

  notes STRING,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
  description="Master list of all bank accounts and credit lines"
);


-- 2. CHART OF ACCOUNTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.chart_of_accounts` (
  account_id STRING NOT NULL OPTIONS(description="Unique account identifier"),
  account_number STRING OPTIONS(description="Account number from accounting system"),
  account_name STRING NOT NULL OPTIONS(description="Account name"),
  account_type STRING NOT NULL OPTIONS(description="Asset, Liability, Equity, Revenue, Expense"),
  account_subtype STRING OPTIONS(description="Detailed account classification"),

  parent_account_id STRING OPTIONS(description="Parent account for hierarchical structure"),
  account_level INT64 OPTIONS(description="1 = top level, 2 = sub-account, etc."),

  cash_flow_section STRING OPTIONS(description="Operating, Investing, Financing, Non-Cash"),
  cash_flow_category STRING OPTIONS(description="Detailed cash flow category"),
  cash_flow_subcategory STRING OPTIONS(description="Additional categorization"),
  is_cash_account BOOLEAN DEFAULT TRUE OPTIONS(description="FALSE for non-cash items like depreciation"),

  default_payment_timing STRING OPTIONS(description="Default payment timing rule"),

  is_active BOOLEAN DEFAULT TRUE,
  description STRING,
  notes STRING,

  qb_account_id STRING,
  qb_fully_qualified_name STRING,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
  description="Chart of accounts with cash flow category mapping"
);


-- 3. PAYMENT TERMS
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.payment_terms` (
  term_id STRING NOT NULL OPTIONS(description="Unique term identifier"),
  term_name STRING NOT NULL OPTIONS(description="Amazon Settlement, Shopify Payout, Net 30, etc."),
  term_category STRING OPTIONS(description="Revenue, Expense, Debt Service"),

  cycle_type STRING OPTIONS(description="Daily, Weekly, Bi-Weekly, Monthly, Invoice-Based"),
  lag_days INT64 OPTIONS(description="Days between transaction and cash"),

  payout_days ARRAY<STRING> OPTIONS(description="Days of week for payouts, e.g., [Monday, Wednesday, Friday]"),
  payout_day_of_month INT64 OPTIONS(description="Day of month for monthly payments"),

  settlement_period_days INT64 OPTIONS(description="Length of settlement period (e.g., 14 for Amazon)"),
  settlement_lag_days INT64 OPTIONS(description="Days after settlement close until deposit"),

  weekend_handling STRING OPTIONS(description="Next Business Day, Previous Business Day, No Adjustment"),

  description STRING,
  example STRING OPTIONS(description="Example: Order on Mon → Payout on Wed"),

  is_active BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
  description="Payment timing rules for cash flow forecasting"
);


-- 4. CASH TRANSACTIONS (main fact table)
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.cash_transactions` (
  transaction_id STRING NOT NULL OPTIONS(description="Unique transaction identifier"),

  transaction_date DATE NOT NULL OPTIONS(description="When transaction occurred"),
  cash_date DATE NOT NULL OPTIONS(description="When cash actually moved"),
  value_date DATE OPTIONS(description="Bank value date (if different)"),

  source_system STRING NOT NULL OPTIONS(description="QuickBooks, Amazon, Shopify, Manual, etc."),
  source_id STRING OPTIONS(description="ID from source system"),
  source_table STRING OPTIONS(description="Which source table this came from"),

  bank_account_id STRING OPTIONS(description="FK to bank_accounts"),
  bank_account_name STRING OPTIONS(description="Denormalized for convenience"),

  cash_flow_section STRING NOT NULL OPTIONS(description="Operating, Investing, Financing"),
  cash_flow_category STRING NOT NULL OPTIONS(description="Revenue - Amazon, COGS - Materials, etc."),
  cash_flow_subcategory STRING OPTIONS(description="Additional detail"),

  amount FLOAT64 NOT NULL OPTIONS(description="Positive = inflow, Negative = outflow"),
  currency STRING DEFAULT 'USD',

  counterparty STRING OPTIONS(description="Customer, vendor, lender, etc."),
  counterparty_type STRING OPTIONS(description="Customer, Vendor, Bank, Owner, etc."),

  description STRING,
  notes STRING,

  is_forecast BOOLEAN DEFAULT FALSE OPTIONS(description="TRUE for forecasted transactions"),
  is_recurring BOOLEAN DEFAULT FALSE OPTIONS(description="TRUE for recurring transactions"),
  recurring_id STRING OPTIONS(description="FK to recurring_transactions"),
  scenario_id STRING OPTIONS(description="FK to scenarios (for forecasts)"),

  tags ARRAY<STRING> OPTIONS(description="Tags for analysis, e.g., [marketing, amazon_ppc]"),

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING DEFAULT 'system'
)
PARTITION BY cash_date
CLUSTER BY bank_account_id, cash_flow_category
OPTIONS(
  description="Single source of truth for all cash inflows and outflows"
);


-- 5. CASH BALANCES
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.cash_balances` (
  balance_date DATE NOT NULL OPTIONS(description="Date of balance"),
  bank_account_id STRING NOT NULL OPTIONS(description="FK to bank_accounts"),

  bank_account_name STRING,
  account_type STRING OPTIONS(description="Checking, Money Market, LOC, etc."),

  beginning_balance FLOAT64 NOT NULL,
  ending_balance FLOAT64 NOT NULL,

  total_inflows FLOAT64 DEFAULT 0,
  total_outflows FLOAT64 DEFAULT 0,
  net_change FLOAT64 OPTIONS(description="ending_balance - beginning_balance"),

  credit_limit FLOAT64 OPTIONS(description="NULL for non-LOC accounts"),
  available_credit FLOAT64 OPTIONS(description="credit_limit - ending_balance for LOCs"),

  is_forecast BOOLEAN DEFAULT FALSE,
  scenario_id STRING,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY balance_date
CLUSTER BY bank_account_id
OPTIONS(
  description="Daily cash position across all accounts"
);


-- 6. DEBT SCHEDULE
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.debt_schedule` (
  schedule_id STRING NOT NULL OPTIONS(description="Unique schedule entry ID"),

  loan_id STRING NOT NULL OPTIONS(description="Loan identifier"),
  loan_name STRING NOT NULL OPTIONS(description="SBA Loan, Equipment Loan, etc."),
  lender STRING NOT NULL,

  payment_date DATE NOT NULL,
  payment_number INT64,

  payment_amount FLOAT64 NOT NULL,
  principal_amount FLOAT64 NOT NULL,
  interest_amount FLOAT64 NOT NULL,
  fees_amount FLOAT64 DEFAULT 0,

  beginning_principal FLOAT64 NOT NULL,
  ending_principal FLOAT64 NOT NULL,

  interest_rate FLOAT64 NOT NULL OPTIONS(description="Rate at time of payment"),
  days_in_period INT64,

  is_paid BOOLEAN DEFAULT FALSE,
  actual_payment_date DATE,
  actual_payment_amount FLOAT64,

  payment_type STRING OPTIONS(description="Interest Only, Principal & Interest, Balloon"),
  is_forecast BOOLEAN DEFAULT FALSE,
  scenario_id STRING,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY payment_date
CLUSTER BY loan_id
OPTIONS(
  description="Detailed loan payment schedule with principal/interest split"
);


-- 7. CASH FORECAST
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.cash_forecast` (
  forecast_id STRING NOT NULL OPTIONS(description="Unique forecast run ID"),
  forecast_date DATE NOT NULL OPTIONS(description="Date of forecast run"),
  period_date DATE NOT NULL OPTIONS(description="Week ending date being forecasted"),
  scenario_id STRING NOT NULL OPTIONS(description="base, best, worst, etc."),

  week_number INT64 OPTIONS(description="1-13 for 13-week forecast"),
  is_actual BOOLEAN OPTIONS(description="TRUE if period is historical"),

  operating_inflows FLOAT64 DEFAULT 0,
  operating_outflows FLOAT64 DEFAULT 0,
  operating_cash_flow FLOAT64,

  investing_outflows FLOAT64 DEFAULT 0,
  financing_inflows FLOAT64 DEFAULT 0,
  financing_outflows FLOAT64 DEFAULT 0,

  net_cash_flow FLOAT64,

  beginning_cash FLOAT64 NOT NULL,
  ending_cash FLOAT64 NOT NULL,

  loc_balance FLOAT64,
  loc_available FLOAT64,
  total_liquidity FLOAT64,

  avg_weekly_burn FLOAT64,
  weeks_of_runway INT64,

  forecast_method STRING OPTIONS(description="Historical Average, Regression, Manual, etc."),
  confidence_level STRING OPTIONS(description="High, Medium, Low"),
  notes STRING,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING DEFAULT 'system'
)
PARTITION BY forecast_date
CLUSTER BY scenario_id, period_date
OPTIONS(
  description="13-week rolling cash forecast output"
);


-- =============================================================================
-- SUPPORTING TABLES
-- =============================================================================

-- 8. GL TRANSACTIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.gl_transactions` (
  entry_id STRING NOT NULL OPTIONS(description="Unique GL entry ID"),

  transaction_date DATE NOT NULL,
  posting_date DATE,

  account_number STRING,
  account_name STRING NOT NULL,
  account_type STRING OPTIONS(description="Asset, Liability, Equity, Revenue, Expense"),

  debit_amount FLOAT64 DEFAULT 0,
  credit_amount FLOAT64 DEFAULT 0,
  amount FLOAT64 OPTIONS(description="Signed: debit positive, credit negative"),

  transaction_type STRING OPTIONS(description="Invoice, Payment, Journal Entry, etc."),
  description STRING,
  memo STRING,
  reference_number STRING,

  customer STRING,
  vendor STRING,
  class STRING OPTIONS(description="QuickBooks class/department"),

  source_document STRING OPTIONS(description="Invoice number, check number, etc."),

  is_reconciled BOOLEAN DEFAULT FALSE,
  reconcile_date DATE,

  qb_transaction_id STRING,
  imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY transaction_date
CLUSTER BY account_name
OPTIONS(
  description="QuickBooks general ledger export"
);


-- 9. RECURRING TRANSACTIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.recurring_transactions` (
  recurring_id STRING NOT NULL OPTIONS(description="Unique recurring transaction ID"),

  transaction_name STRING NOT NULL,
  cash_flow_category STRING NOT NULL,

  amount FLOAT64 NOT NULL,
  currency STRING DEFAULT 'USD',

  frequency STRING NOT NULL OPTIONS(description="Daily, Weekly, Monthly, Quarterly, Annually"),
  recurrence_interval INT64 DEFAULT 1 OPTIONS(description="Every N periods (e.g., every 2 weeks)"),

  day_of_week INT64 OPTIONS(description="1-7 for weekly"),
  day_of_month INT64 OPTIONS(description="1-31 for monthly"),
  month_of_year INT64 OPTIONS(description="1-12 for annual"),

  start_date DATE NOT NULL,
  end_date DATE OPTIONS(description="NULL = indefinite"),

  counterparty STRING,
  bank_account_id STRING,

  description STRING,
  notes STRING,
  is_active BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
  description="Known recurring revenue and expenses"
);


-- 10. CAPEX PLAN
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.capex_plan` (
  capex_id STRING NOT NULL OPTIONS(description="Unique CapEx project ID"),

  project_name STRING NOT NULL,
  category STRING NOT NULL OPTIONS(description="Equipment, Technology, Facility, IP, etc."),
  description STRING,

  estimated_cost FLOAT64 NOT NULL,
  actual_cost FLOAT64,
  variance FLOAT64,

  planned_date DATE NOT NULL,
  actual_date DATE,

  payment_terms STRING OPTIONS(description="Full upfront, 50% deposit, Net 30, etc."),
  deposit_amount FLOAT64,
  deposit_date DATE,
  final_payment_amount FLOAT64,
  final_payment_date DATE,

  status STRING NOT NULL OPTIONS(description="Planned, Approved, In Progress, Completed, Cancelled"),

  approved_by STRING,
  approved_date DATE,

  vendor STRING,
  po_number STRING,
  notes STRING,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY planned_date
OPTIONS(
  description="Planned capital expenditures"
);


-- 11. BUDGET
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.budget` (
  budget_id STRING NOT NULL OPTIONS(description="Unique budget entry ID"),
  fiscal_year INT64 NOT NULL,
  period_type STRING NOT NULL OPTIONS(description="Monthly, Quarterly, Annual"),
  period_start_date DATE NOT NULL,

  cash_flow_section STRING NOT NULL,
  cash_flow_category STRING NOT NULL,
  cash_flow_subcategory STRING,

  budget_amount FLOAT64 NOT NULL,

  version INT64 DEFAULT 1 OPTIONS(description="Budget version for revisions"),
  is_active BOOLEAN DEFAULT TRUE,
  notes STRING,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING
)
PARTITION BY period_start_date
CLUSTER BY fiscal_year, cash_flow_category
OPTIONS(
  description="Annual and monthly budgets by category"
);


-- 12. SCENARIOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.scenarios` (
  scenario_id STRING NOT NULL OPTIONS(description="Unique scenario identifier"),

  scenario_name STRING NOT NULL,
  scenario_type STRING NOT NULL OPTIONS(description="Base, Best, Worst, Custom"),
  description STRING,

  revenue_growth_rate FLOAT64 OPTIONS(description="Annual growth rate (0.15 = 15%)"),
  expense_inflation_rate FLOAT64,

  custom_assumptions STRING OPTIONS(description="JSON blob of scenario-specific assumptions"),

  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING
)
OPTIONS(
  description="Scenario definitions for forecasting"
);


-- 13. FORECAST ASSUMPTIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS `vochill.revrec.forecast_assumptions` (
  assumption_id STRING NOT NULL OPTIONS(description="Unique assumption ID"),
  scenario_id STRING NOT NULL,
  forecast_date DATE NOT NULL,

  assumption_category STRING NOT NULL OPTIONS(description="Revenue, COGS, OpEx, CapEx, Financing"),
  assumption_name STRING NOT NULL,

  assumption_value FLOAT64,
  assumption_value_text STRING OPTIONS(description="For non-numeric assumptions"),

  value_type STRING OPTIONS(description="Percentage, Dollar Amount, Units, Text"),

  description STRING,
  rationale STRING OPTIONS(description="Why this assumption was chosen"),

  data_source STRING OPTIONS(description="Historical Average, Management Guidance, Market Research, etc."),
  confidence_level STRING OPTIONS(description="High, Medium, Low"),

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING
)
PARTITION BY forecast_date
CLUSTER BY scenario_id, assumption_category
OPTIONS(
  description="Detailed assumptions driving the forecast"
);


-- =============================================================================
-- ANALYTICAL VIEWS
-- =============================================================================

-- Daily Cash Flow Summary
CREATE OR REPLACE VIEW `vochill.revrec.v_daily_cash_flow` AS
SELECT
  cash_date,
  cash_flow_section,
  cash_flow_category,
  cash_flow_subcategory,

  SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_inflows,
  SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_outflows,
  SUM(amount) as net_cash_flow,

  COUNT(*) as transaction_count

FROM `vochill.revrec.cash_transactions`
WHERE is_forecast = FALSE
GROUP BY cash_date, cash_flow_section, cash_flow_category, cash_flow_subcategory
ORDER BY cash_date DESC, cash_flow_section, cash_flow_category;


-- Weekly Cash Flow (13-week view)
CREATE OR REPLACE VIEW `vochill.revrec.v_weekly_cash_flow` AS
SELECT
  DATE_TRUNC(cash_date, WEEK(MONDAY)) as week_start,
  DATE_ADD(DATE_TRUNC(cash_date, WEEK(MONDAY)), INTERVAL 6 DAY) as week_end,
  cash_flow_section,
  cash_flow_category,

  SUM(amount) as net_cash_flow,
  COUNT(*) as transaction_count

FROM `vochill.revrec.cash_transactions`
WHERE is_forecast = FALSE
  AND cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 WEEK)
GROUP BY week_start, week_end, cash_flow_section, cash_flow_category
ORDER BY week_start DESC, cash_flow_section, cash_flow_category;


-- Current Cash Position
CREATE OR REPLACE VIEW `vochill.revrec.v_cash_position` AS
WITH latest_balances AS (
  SELECT
    bank_account_id,
    bank_account_name,
    account_type,
    ending_balance,
    credit_limit,
    available_credit
  FROM `vochill.revrec.cash_balances`
  WHERE balance_date = (
    SELECT MAX(balance_date)
    FROM `vochill.revrec.cash_balances`
    WHERE is_forecast = FALSE
  )
  AND is_forecast = FALSE
)
SELECT
  SUM(CASE WHEN account_type IN ('Checking', 'Savings', 'Money Market') THEN ending_balance ELSE 0 END) as total_cash,
  SUM(CASE WHEN account_type = 'LOC' THEN ABS(ending_balance) ELSE 0 END) as total_loc_balance,
  SUM(CASE WHEN account_type = 'LOC' THEN available_credit ELSE 0 END) as total_loc_available,
  SUM(CASE WHEN account_type IN ('Checking', 'Savings', 'Money Market') THEN ending_balance ELSE 0 END) +
    SUM(CASE WHEN account_type = 'LOC' THEN available_credit ELSE 0 END) as total_liquidity
FROM latest_balances;


-- =============================================================================
-- SEED DATA (Optional - run after tables created)
-- =============================================================================

-- Insert default payment terms
INSERT INTO `vochill.revrec.payment_terms` (term_id, term_name, term_category, cycle_type, settlement_period_days, settlement_lag_days, description) VALUES
('amazon_settlement', 'Amazon Settlement', 'Revenue', 'Bi-Weekly', 14, 2, 'Amazon bi-weekly settlement cycle'),
('shopify_payout', 'Shopify Payout', 'Revenue', 'Daily', NULL, 2, 'Shopify daily payout (weekdays)'),
('net_30', 'Net 30', 'Expense', 'Invoice-Based', NULL, 30, 'Payment due 30 days after invoice'),
('net_15', 'Net 15', 'Expense', 'Invoice-Based', NULL, 15, 'Payment due 15 days after invoice'),
('net_60', 'Net 60', 'Expense', 'Invoice-Based', NULL, 60, 'Payment due 60 days after invoice'),
('credit_card', 'Credit Card', 'Expense', 'Monthly', NULL, 30, 'Credit card payment ~30 days after charge'),
('sba_loan_monthly', 'SBA Loan Monthly', 'Debt Service', 'Monthly', NULL, 0, 'SBA loan monthly payment on day 30');

-- Insert default scenarios
INSERT INTO `vochill.revrec.scenarios` (scenario_id, scenario_name, scenario_type, description, revenue_growth_rate, expense_inflation_rate) VALUES
('base', 'Base Case', 'Base', 'Conservative baseline forecast', 0.0, 0.03),
('best', 'Best Case', 'Best', 'Optimistic scenario', 0.20, 0.03),
('worst', 'Worst Case', 'Worst', 'Pessimistic scenario', -0.15, 0.05);


-- =============================================================================
-- COMPLETED
-- =============================================================================
-- All financial tables created successfully
-- Next steps:
--   1. Populate bank_accounts table with VoChill accounts
--   2. Load chart_of_accounts from existing CoA
--   3. Begin ETL from deposits/orders tables into cash_transactions
--   4. Build forecast engine to populate cash_forecast table
