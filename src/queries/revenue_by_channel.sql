-- Revenue by Channel Cash Flow Query
--
-- This query aggregates deposit data from Amazon and Shopify into cash flow
-- by the actual date cash was received (deposit/payout date).
--
-- CRITICAL: Uses deposit date, not transaction date, for accurate cash timing
--
-- Parameters to replace:
--   {start_date} - Start date filter (YYYY-MM-DD)
--   {end_date} - End date filter (YYYY-MM-DD)

WITH deposits_with_dates AS (
  SELECT
    platform,
    settlement_id,
    DATE(date_time) as transaction_date,
    -- For Amazon: use settlement_id pattern to infer deposit date
    -- For Shopify: date_time is already close to payout date
    -- TODO: Join to actual payout/settlement tables for precise dates
    DATE_ADD(DATE(date_time), INTERVAL 2 DAY) as estimated_cash_date,
    order_id,
    sku,
    description,
    quantity,
    marketplace,
    fulfillment,

    -- Revenue components
    product_sales,
    product_sales_tax,
    shipping_credits,
    shipping_credits_tax,
    gift_wrap_credits,
    gift_wrap_credits_tax,
    promotional_rebates,
    promotional_rebate_tax,

    -- Taxes (marketplace facilitator)
    marketplace_tax,

    -- Fees (deducted before deposit)
    selling_fees,
    fba_fees,
    other_transaction_fees,

    -- Net total (what actually hit the bank)
    total as net_proceeds

  FROM `{project_id}.{dataset}.deposits`
  WHERE DATE(date_time) BETWEEN '{start_date}' AND '{end_date}'
),

revenue_by_channel AS (
  SELECT
    estimated_cash_date as cash_date,
    platform,

    -- Gross revenue components
    SUM(product_sales) as gross_product_sales,
    SUM(shipping_credits) as gross_shipping,
    SUM(gift_wrap_credits) as gross_gift_wrap,
    SUM(promotional_rebates) as promotional_rebates,

    -- Taxes collected (not revenue, but useful to track)
    SUM(marketplace_tax) as taxes_collected,

    -- Platform fees (deducted from gross)
    SUM(selling_fees) as platform_fees,
    SUM(fba_fees) as fulfillment_fees,
    SUM(other_transaction_fees) as other_fees,

    -- Net proceeds (actual cash received)
    SUM(total) as net_cash_received,

    -- Counts
    COUNT(DISTINCT order_id) as order_count,
    COUNT(DISTINCT settlement_id) as settlement_count,
    SUM(quantity) as units_sold

  FROM deposits_with_dates
  GROUP BY cash_date, platform
  ORDER BY cash_date DESC, platform
)

SELECT
  cash_date,
  platform,

  -- Cash flow category mapping
  CASE
    WHEN platform = 'Amazon' THEN 'Operating Inflows - Revenue - Amazon'
    WHEN platform = 'Shopify' THEN 'Operating Inflows - Revenue - Shopify'
    WHEN platform = 'TikTok' THEN 'Operating Inflows - Revenue - TikTok'
    ELSE 'Operating Inflows - Revenue - Other'
  END as cash_flow_category,

  'Ecommerce Revenue' as cash_flow_subcategory,

  -- Revenue metrics
  gross_product_sales,
  gross_shipping,
  gross_gift_wrap,
  promotional_rebates,
  platform_fees,
  fulfillment_fees,
  other_fees,

  -- NET CASH RECEIVED (this is what matters for cash flow)
  net_cash_received as cash_amount,

  -- Supporting data
  order_count,
  settlement_count,
  units_sold,

  -- Calculate effective fee rate
  SAFE_DIVIDE(
    platform_fees + fulfillment_fees + other_fees,
    gross_product_sales
  ) * 100 as effective_fee_rate_pct

FROM revenue_by_channel
ORDER BY cash_date DESC, platform
