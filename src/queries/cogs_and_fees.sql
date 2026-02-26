-- COGS and Platform Fees Cash Flow Query
--
-- This query aggregates cost of goods sold including:
-- - Platform selling fees (Amazon referral, Shopify transaction fees)
-- - Fulfillment fees (FBA, 3PL)
-- - Other transaction fees
--
-- NOTE: These fees are typically deducted from revenue deposits,
-- so they don't hit cash separately. This query is for P&L allocation.
--
-- For cash flow forecasting, use NET PROCEEDS from revenue query.
--
-- Parameters to replace:
--   {start_date} - Start date filter (YYYY-MM-DD)
--   {end_date} - End date filter (YYYY-MM-DD)

WITH fee_details AS (
  SELECT
    platform,
    DATE(date_time) as transaction_date,
    DATE_ADD(DATE(date_time), INTERVAL 2 DAY) as estimated_cash_date,
    settlement_id,
    order_id,
    sku,
    description,
    type,
    marketplace,
    fulfillment,

    -- Fee components
    selling_fees,
    fba_fees,
    other_transaction_fees,

    -- Total fees
    ABS(selling_fees) + ABS(fba_fees) + ABS(other_transaction_fees) as total_fees

  FROM `{project_id}.{dataset}.fees`
  WHERE DATE(date_time) BETWEEN '{start_date}' AND '{end_date}'
),

fees_by_category AS (
  SELECT
    estimated_cash_date as cash_date,
    platform,

    -- Platform selling fees (referral fees)
    SUM(ABS(selling_fees)) as platform_selling_fees,

    -- Fulfillment fees (FBA, 3PL)
    SUM(ABS(fba_fees)) as fulfillment_fees,

    -- Other transaction fees
    SUM(ABS(other_transaction_fees)) as other_fees,

    -- Total fees
    SUM(total_fees) as total_fees,

    -- Counts
    COUNT(DISTINCT order_id) as order_count,
    COUNT(DISTINCT settlement_id) as settlement_count

  FROM fee_details
  GROUP BY cash_date, platform
  ORDER BY cash_date DESC, platform
)

SELECT
  cash_date,
  platform,

  -- Platform selling fees
  platform_selling_fees,
  'COGS - Platform Fees' as selling_fee_category,

  -- Fulfillment fees
  fulfillment_fees,
  'COGS - Fulfillment' as fulfillment_fee_category,

  -- Other fees
  other_fees,
  'COGS - Other Transaction Fees' as other_fee_category,

  -- Total fees for the day/platform
  total_fees,

  -- Supporting data
  order_count,
  settlement_count,

  -- NOTE: These fees are typically deducted from deposits
  -- For cash flow, use NET PROCEEDS from revenue query
  'DEDUCTED_FROM_DEPOSITS' as cash_treatment

FROM fees_by_category
ORDER BY cash_date DESC, platform
