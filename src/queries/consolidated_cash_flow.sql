-- Consolidated Cash Flow Query
--
-- This query brings together all cash flow components:
-- - Operating inflows (revenue by channel)
-- - Operating outflows (COGS, OpEx)
-- - Investing activities (CapEx)
-- - Financing activities (debt, equity, distributions)
--
-- Result: Daily cash flow statement with beginning/ending cash positions
--
-- Parameters to replace:
--   {start_date} - Start date filter (YYYY-MM-DD)
--   {end_date} - End date filter (YYYY-MM-DD)
--   {starting_cash_balance} - Starting cash balance

WITH

-- Operating Inflows: Revenue from deposits (net proceeds)
operating_inflows AS (
  SELECT
    DATE_ADD(DATE(date_time), INTERVAL 2 DAY) as cash_date,
    platform,
    'Operating Inflows' as cash_flow_section,
    CASE
      WHEN platform = 'Amazon' THEN 'Revenue - Amazon'
      WHEN platform = 'Shopify' THEN 'Revenue - Shopify'
      WHEN platform = 'TikTok' THEN 'Revenue - TikTok'
      ELSE 'Revenue - Other'
    END as cash_flow_category,
    SUM(total) as cash_amount
  FROM `{project_id}.{dataset}.deposits`
  WHERE DATE(date_time) BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY cash_date, platform
),

-- Operating Outflows: Refunds (reduce revenue)
refunds AS (
  SELECT
    DATE_ADD(DATE(date_time), INTERVAL 2 DAY) as cash_date,
    platform,
    'Operating Inflows' as cash_flow_section,
    'Refunds' as cash_flow_category,
    SUM(total) as cash_amount  -- Typically negative
  FROM `{project_id}.{dataset}.refunds`
  WHERE DATE(date_time) BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY cash_date, platform
),

-- Operating Outflows: Vendor payments
vendor_payments AS (
  SELECT
    DATE_ADD(i.invoice_date, INTERVAL COALESCE(v.`Actual Days`, v.`Request Days`, 30) DAY) as cash_date,
    i.vendor as platform,
    'Operating Outflows' as cash_flow_section,
    'Vendor Payments' as cash_flow_category,
    -SUM(i.total) as cash_amount  -- Negative for outflow
  FROM `{project_id}.{dataset}.invoices` i
  LEFT JOIN `{project_id}.{dataset}.vendors` v ON i.vendor = v.Name
  WHERE i.invoice_date BETWEEN '{start_date}' AND '{end_date}'
  GROUP BY cash_date, i.vendor
),

-- Combine all cash flows
all_cash_flows AS (
  SELECT * FROM operating_inflows
  UNION ALL
  SELECT * FROM refunds
  UNION ALL
  SELECT * FROM vendor_payments
  -- TODO: Add OpEx, CapEx, Financing when data available
),

-- Aggregate by date
daily_cash_flow AS (
  SELECT
    cash_date,
    cash_flow_section,
    cash_flow_category,
    SUM(cash_amount) as cash_amount
  FROM all_cash_flows
  GROUP BY cash_date, cash_flow_section, cash_flow_category
  ORDER BY cash_date DESC, cash_flow_section, cash_flow_category
),

-- Calculate cumulative cash position
cash_position AS (
  SELECT
    cash_date,
    cash_flow_section,
    cash_flow_category,
    cash_amount,

    -- Running total (cumulative cash position)
    {starting_cash_balance} + SUM(cash_amount) OVER (
      ORDER BY cash_date
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as ending_cash_balance

  FROM daily_cash_flow
)

SELECT
  cash_date,
  cash_flow_section,
  cash_flow_category,
  cash_amount,
  ending_cash_balance,

  -- Calculate beginning balance (ending balance of previous day)
  LAG(ending_cash_balance, 1, {starting_cash_balance}) OVER (ORDER BY cash_date) as beginning_cash_balance

FROM cash_position
ORDER BY cash_date DESC, cash_flow_section, cash_flow_category
