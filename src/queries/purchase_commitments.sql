-- Purchase Order Commitments Cash Flow Query
--
-- This query identifies open purchase orders that represent
-- future cash outflow commitments.
--
-- Used for forward-looking cash planning.
--
-- Parameters to replace:
--   {start_date} - Start date filter (YYYY-MM-DD)
--   {end_date} - End date filter (YYYY-MM-DD)

WITH open_po_lines AS (
  SELECT
    pol.po_no,
    pol.order_date,
    pol.status,
    pol.vendor,
    pol.sku,
    pol.qty_ordered,
    pol.qty_received,

    -- Outstanding quantity
    pol.qty_ordered - COALESCE(pol.qty_received, 0) as qty_outstanding,

    -- Get item pricing
    i.item_price,
    i.build_cost,

    -- Calculate commitment value
    (pol.qty_ordered - COALESCE(pol.qty_received, 0)) * COALESCE(i.item_price, i.build_cost, 0) as commitment_value,

    -- Get vendor payment terms
    v.Terms as payment_terms,
    COALESCE(v.`Actual Days`, v.`Request Days`, 30) as payment_days

  FROM `{project_id}.{dataset}.po_line_item` pol
  LEFT JOIN `{project_id}.{dataset}.item` i
    ON pol.sku = i.sku
  LEFT JOIN `{project_id}.{dataset}.vendors` v
    ON pol.vendor = v.Name
  WHERE pol.status = 'Open'
    AND pol.order_date BETWEEN '{start_date}' AND '{end_date}'
    AND (pol.qty_ordered - COALESCE(pol.qty_received, 0)) > 0
),

po_commitments_summary AS (
  SELECT
    -- Estimated delivery date (TBD - could add lead time logic)
    DATE_ADD(order_date, INTERVAL 30 DAY) as estimated_delivery_date,

    -- Estimated payment date (delivery + payment terms)
    DATE_ADD(
      DATE_ADD(order_date, INTERVAL 30 DAY),
      INTERVAL payment_days DAY
    ) as estimated_payment_date,

    vendor,
    payment_terms,

    -- Commitment amounts
    SUM(commitment_value) as total_commitment,
    SUM(qty_outstanding) as total_units_outstanding,

    -- Counts
    COUNT(DISTINCT po_no) as po_count,
    COUNT(*) as line_count

  FROM open_po_lines
  GROUP BY estimated_delivery_date, estimated_payment_date, vendor, payment_terms
  ORDER BY estimated_payment_date, vendor
)

SELECT
  estimated_payment_date as cash_date,
  vendor,
  payment_terms,

  -- Cash flow category
  'COGS - Materials' as cash_flow_category,
  'Inventory Purchases (Committed)' as cash_flow_subcategory,

  -- Commitment amount (negative = future cash outflow)
  -total_commitment as cash_amount,

  -- Supporting data
  total_units_outstanding as units,
  po_count,
  line_count,

  -- Metadata
  estimated_delivery_date,
  'FORECAST_FROM_OPEN_PO' as source

FROM po_commitments_summary
ORDER BY cash_date, vendor
