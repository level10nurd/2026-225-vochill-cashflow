-- Vendor Payments and Commitments Cash Flow Query
--
-- This query calculates cash outflows for vendor payments based on:
-- 1. Invoice dates
-- 2. Vendor payment terms
-- 3. Actual payment timing
--
-- Parameters to replace:
--   {start_date} - Start date filter (YYYY-MM-DD)
--   {end_date} - End date filter (YYYY-MM-DD)

WITH invoices_with_terms AS (
  SELECT
    i.invoice_id,
    i.vendor,
    i.invoice_date,
    i.invoice_number,
    i.po_number,
    i.subtotal,
    i.sales_tax,
    i.total as invoice_amount,

    -- Get vendor payment terms
    v.Terms as payment_terms,
    COALESCE(v.`Actual Days`, v.`Request Days`, 30) as payment_days,

    -- Calculate estimated payment date
    DATE_ADD(i.invoice_date, INTERVAL COALESCE(v.`Actual Days`, v.`Request Days`, 30) DAY) as estimated_payment_date

  FROM `{project_id}.{dataset}.invoices` i
  LEFT JOIN `{project_id}.{dataset}.vendors` v
    ON i.vendor = v.Name
  WHERE i.invoice_date BETWEEN '{start_date}' AND '{end_date}'
),

vendor_payments_by_date AS (
  SELECT
    estimated_payment_date as cash_date,
    vendor,
    payment_terms,

    -- Payment amounts
    SUM(subtotal) as subtotal_amount,
    SUM(sales_tax) as tax_amount,
    SUM(invoice_amount) as total_payment_amount,

    -- Counts
    COUNT(DISTINCT invoice_id) as invoice_count,
    COUNT(DISTINCT po_number) as po_count

  FROM invoices_with_terms
  GROUP BY estimated_payment_date, vendor, payment_terms
  ORDER BY estimated_payment_date DESC, vendor
)

SELECT
  cash_date,
  vendor,
  payment_terms,

  -- Cash flow category (default to COGS - Materials, refine as needed)
  'COGS - Materials' as cash_flow_category,
  'Vendor Payments' as cash_flow_subcategory,

  -- Payment details
  subtotal_amount,
  tax_amount,

  -- CASH AMOUNT (negative = outflow)
  -total_payment_amount as cash_amount,

  -- Supporting data
  invoice_count,
  po_count,

  -- Payment timing metadata
  'ESTIMATED_BY_TERMS' as payment_date_source

FROM vendor_payments_by_date
ORDER BY cash_date DESC, vendor
