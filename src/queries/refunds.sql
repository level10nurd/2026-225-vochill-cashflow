-- Refunds Cash Flow Query
--
-- This query aggregates customer refunds which reduce cash inflows.
-- Refunds are typically processed within the same settlement/payout cycle.
--
-- Parameters to replace:
--   {start_date} - Start date filter (YYYY-MM-DD)
--   {end_date} - End date filter (YYYY-MM-DD)

WITH refund_details AS (
  SELECT
    platform,
    DATE(date_time) as transaction_date,
    DATE_ADD(DATE(date_time), INTERVAL 2 DAY) as estimated_cash_date,
    settlement_id,
    order_id,
    sku,
    description,
    type,
    quantity,
    marketplace,
    fulfillment,

    -- Refund components (typically negative values)
    product_sales as refund_amount,
    product_sales_tax as refund_tax,
    shipping_credits as shipping_refund,
    selling_fees as fee_reversal,
    fba_fees as fba_fee_reversal,

    -- Total refund impact
    total as net_refund_impact

  FROM `{project_id}.{dataset}.refunds`
  WHERE DATE(date_time) BETWEEN '{start_date}' AND '{end_date}'
),

refunds_by_platform AS (
  SELECT
    estimated_cash_date as cash_date,
    platform,

    -- Refund amounts
    SUM(ABS(refund_amount)) as total_refund_amount,
    SUM(ABS(shipping_refund)) as shipping_refunds,

    -- Fee reversals (credit back on refunds)
    SUM(ABS(fee_reversal)) as fee_reversals,
    SUM(ABS(fba_fee_reversal)) as fba_fee_reversals,

    -- Net impact on cash (includes fee reversals)
    SUM(net_refund_impact) as net_cash_impact,

    -- Counts
    COUNT(DISTINCT order_id) as refund_count,
    SUM(ABS(quantity)) as units_refunded

  FROM refund_details
  GROUP BY cash_date, platform
  ORDER BY cash_date DESC, platform
)

SELECT
  cash_date,
  platform,

  -- Cash flow category
  CASE
    WHEN platform = 'Amazon' THEN 'Operating Inflows - Revenue - Amazon'
    WHEN platform = 'Shopify' THEN 'Operating Inflows - Revenue - Shopify'
    WHEN platform = 'TikTok' THEN 'Operating Inflows - Revenue - TikTok'
    ELSE 'Operating Inflows - Revenue - Other'
  END as cash_flow_category,

  'Refunds (Contra-Revenue)' as cash_flow_subcategory,

  -- Refund details
  total_refund_amount,
  shipping_refunds,
  fee_reversals,
  fba_fee_reversals,

  -- Net cash impact (NEGATIVE = cash reduction)
  net_cash_impact as cash_amount,

  -- Supporting data
  refund_count,
  units_refunded,

  -- Refund rate (will need to join to revenue)
  CAST(NULL as FLOAT64) as refund_rate_pct

FROM refunds_by_platform
ORDER BY cash_date DESC, platform
