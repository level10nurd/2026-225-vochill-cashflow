"""
ETL: Transform deposits → cash_transactions

This script reads from the deposits table (Amazon/Shopify revenue)
and transforms it into cash_transactions with proper cash timing.

Logic:
- Amazon: Settlement-based, bi-weekly cycle + 2 day payout lag
- Shopify: Daily payouts, 2-3 day lag
- Net proceeds used (fees already deducted from deposits.total)

Usage:
    python scripts/etl_deposits_to_cash.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--platform PLATFORM]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def preview_deposits_to_cash(bq, start_date=None, end_date=None, platform=None):
    """
    Transform deposits into cash_transactions

    Args:
        bq: BigQueryConnector instance
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        platform: Optional platform filter (Amazon, Shopify, etc.)
    """

    # Build WHERE clause
    where_conditions = []
    if start_date:
        where_conditions.append(f"DATE(date_time) >= '{start_date}'")
    if end_date:
        where_conditions.append(f"DATE(date_time) <= '{end_date}'")
    if platform:
        where_conditions.append(f"platform = '{platform}'")

    where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""

    # Query to transform deposits
    # Group by settlement_id and platform to get settlement-level cash flows
    query = f"""
    WITH deposit_settlements AS (
      SELECT
        platform,
        settlement_id,
        MIN(DATE(date_time)) as settlement_start,
        MAX(DATE(date_time)) as settlement_end,

        -- Calculate cash date based on platform timing
        CASE
          -- Amazon: settlement_end + 2 days
          WHEN platform = 'Amazon' THEN DATE_ADD(MAX(DATE(date_time)), INTERVAL 2 DAY)

          -- Shopify: settlement_end + 2 days (daily payouts)
          WHEN platform = 'Shopify' THEN DATE_ADD(MAX(DATE(date_time)), INTERVAL 2 DAY)

          -- TikTok: assume similar to Shopify
          WHEN platform = 'TikTok' THEN DATE_ADD(MAX(DATE(date_time)), INTERVAL 2 DAY)

          -- Default: same as transaction date
          ELSE MAX(DATE(date_time))
        END as cash_date,

        -- Sum up all amounts in the settlement
        SUM(product_sales) as gross_product_sales,
        SUM(shipping_credits) as gross_shipping,
        SUM(gift_wrap_credits) as gross_gift_wrap,
        SUM(promotional_rebates) as promotional_rebates,
        SUM(marketplace_tax) as taxes_collected,
        SUM(selling_fees) as platform_fees,
        SUM(fba_fees) as fulfillment_fees,
        SUM(other_transaction_fees) as other_fees,

        -- NET PROCEEDS (what actually hit the bank)
        SUM(total) as net_cash_received,

        COUNT(DISTINCT order_id) as order_count,
        SUM(quantity) as units_sold

      FROM `vochill.revrec.deposits`
      WHERE 1=1 {where_clause}
      GROUP BY platform, settlement_id
      HAVING SUM(total) != 0  -- Exclude zero settlements
    )

    SELECT
      -- Generate transaction_id
      GENERATE_UUID() as transaction_id,

      -- Dates
      settlement_end as transaction_date,
      cash_date,
      cash_date as value_date,

      -- Source tracking
      'deposits' as source_system,
      CAST(settlement_id AS STRING) as source_id,
      'deposits' as source_table,

      -- Account (deposits typically go to checking)
      'frost_checking' as bank_account_id,
      'VoChill Checking' as bank_account_name,

      -- Cash flow classification
      'Operating' as cash_flow_section,
      CASE
        WHEN platform = 'Amazon' THEN 'Revenue - Amazon'
        WHEN platform = 'Shopify' THEN 'Revenue - Shopify'
        WHEN platform = 'TikTok' THEN 'Revenue - TikTok'
        ELSE CONCAT('Revenue - ', platform)
      END as cash_flow_category,
      'Ecommerce Revenue' as cash_flow_subcategory,

      -- Amount (NET PROCEEDS - what actually hit the bank)
      net_cash_received as amount,
      'USD' as currency,

      -- Counterparty
      platform as counterparty,
      'Platform' as counterparty_type,

      -- Description
      CONCAT(
        platform, ' Settlement ', settlement_id,
        ' (', order_count, ' orders, ', units_sold, ' units)'
      ) as description,

      CONCAT(
        'Gross: $', ROUND(gross_product_sales, 2),
        ', Fees: $', ROUND(ABS(platform_fees + fulfillment_fees + other_fees), 2),
        ', Net: $', ROUND(net_cash_received, 2)
      ) as notes,

      -- Metadata
      FALSE as is_forecast,
      FALSE as is_recurring,
      CAST(NULL AS STRING) as recurring_id,
      CAST(NULL AS STRING) as scenario_id,

      -- Tags
      [platform, 'ecommerce', 'revenue'] as tags,

      -- Audit
      CURRENT_TIMESTAMP() as created_at,
      CURRENT_TIMESTAMP() as updated_at,
      'etl_deposits' as created_by

    FROM deposit_settlements
    ORDER BY cash_date DESC, platform
    """

    print("Executing transformation query...")
    print()

    results = bq.query(query)

    return results


def insert_deposits_to_cash(bq, start_date=None, end_date=None, platform=None):
    """
    Insert transformed deposits directly into cash_transactions using server-side INSERT INTO ... SELECT
    This is much faster and avoids type conversion issues
    """

    # Build WHERE clause
    where_conditions = []
    if start_date:
        where_conditions.append(f"DATE(date_time) >= '{start_date}'")
    if end_date:
        where_conditions.append(f"DATE(date_time) <= '{end_date}'")
    if platform:
        where_conditions.append(f"platform = '{platform}'")

    where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""

    # Server-side INSERT INTO ... SELECT
    insert_query = f"""
    INSERT INTO `vochill.revrec.cash_transactions` (
      transaction_id, transaction_date, cash_date, value_date,
      source_system, source_id, source_table,
      bank_account_id, bank_account_name,
      cash_flow_section, cash_flow_category, cash_flow_subcategory,
      amount, currency,
      counterparty, counterparty_type,
      description, notes,
      is_forecast, is_recurring, recurring_id, scenario_id,
      tags,
      created_at, updated_at, created_by
    )

    WITH deposit_settlements AS (
      SELECT
        platform,
        settlement_id,
        MIN(DATE(date_time)) as settlement_start,
        MAX(DATE(date_time)) as settlement_end,

        -- Calculate cash date based on platform timing
        CASE
          WHEN platform = 'Amazon' THEN DATE_ADD(MAX(DATE(date_time)), INTERVAL 2 DAY)
          WHEN platform = 'Shopify' THEN DATE_ADD(MAX(DATE(date_time)), INTERVAL 2 DAY)
          WHEN platform = 'TikTok' THEN DATE_ADD(MAX(DATE(date_time)), INTERVAL 2 DAY)
          ELSE MAX(DATE(date_time))
        END as cash_date,

        SUM(product_sales) as gross_product_sales,
        SUM(shipping_credits) as gross_shipping,
        SUM(selling_fees) as platform_fees,
        SUM(fba_fees) as fulfillment_fees,
        SUM(other_transaction_fees) as other_fees,
        SUM(total) as net_cash_received,

        COUNT(DISTINCT order_id) as order_count,
        SUM(quantity) as units_sold

      FROM `vochill.revrec.deposits`
      WHERE 1=1 {where_clause}
      GROUP BY platform, settlement_id
      HAVING SUM(total) != 0
    )

    SELECT
      GENERATE_UUID() as transaction_id,
      settlement_end as transaction_date,
      cash_date,
      cash_date as value_date,

      'deposits' as source_system,
      CAST(settlement_id AS STRING) as source_id,
      'deposits' as source_table,

      'frost_checking' as bank_account_id,
      'VoChill Checking' as bank_account_name,

      'Operating' as cash_flow_section,
      CASE
        WHEN platform = 'Amazon' THEN 'Revenue - Amazon'
        WHEN platform = 'Shopify' THEN 'Revenue - Shopify'
        WHEN platform = 'TikTok' THEN 'Revenue - TikTok'
        ELSE CONCAT('Revenue - ', platform)
      END as cash_flow_category,
      'Ecommerce Revenue' as cash_flow_subcategory,

      net_cash_received as amount,
      'USD' as currency,

      platform as counterparty,
      'Platform' as counterparty_type,

      CONCAT(
        platform, ' Settlement ', settlement_id,
        ' (', order_count, ' orders, ', units_sold, ' units)'
      ) as description,

      CONCAT(
        'Gross: $', ROUND(gross_product_sales, 2),
        ', Fees: $', ROUND(ABS(platform_fees + fulfillment_fees + other_fees), 2),
        ', Net: $', ROUND(net_cash_received, 2)
      ) as notes,

      FALSE as is_forecast,
      FALSE as is_recurring,
      CAST(NULL AS STRING) as recurring_id,
      CAST(NULL AS STRING) as scenario_id,

      [platform, 'ecommerce', 'revenue'] as tags,

      CURRENT_TIMESTAMP() as created_at,
      CURRENT_TIMESTAMP() as updated_at,
      'etl_deposits' as created_by

    FROM deposit_settlements
    """

    print("Executing server-side INSERT INTO ... SELECT...")
    print()

    try:
        result = bq.query(insert_query)
        return True
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='ETL: Deposits → Cash Transactions')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--platform', help='Platform filter (Amazon, Shopify, etc.)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not insert')

    args = parser.parse_args()

    print("=" * 60)
    print("ETL: Deposits → Cash Transactions")
    print("=" * 60)
    print()

    # Display filters
    if args.start_date or args.end_date or args.platform:
        print("Filters:")
        if args.start_date:
            print(f"  Start date: {args.start_date}")
        if args.end_date:
            print(f"  End date: {args.end_date}")
        if args.platform:
            print(f"  Platform: {args.platform}")
        print()

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No data will be inserted")
        print()

    # Connect to BigQuery
    print("Connecting to BigQuery...")
    try:
        bq = BigQueryConnector()
        print("✅ Connected")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to BigQuery")
        print(f"   {str(e)}")
        sys.exit(1)

    # Preview transformation
    if args.dry_run:
        print("Preview mode - querying sample data...")
        try:
            df = preview_deposits_to_cash(
                bq,
                start_date=args.start_date,
                end_date=args.end_date,
                platform=args.platform
            )

            print(f"✅ Preview complete: {len(df)} cash transactions would be generated")
            print()

            if len(df) == 0:
                print("No records found matching criteria.")
                sys.exit(0)

            # Show summary
            print("Summary by platform:")
            try:
                summary = df.groupby('counterparty').agg({
                    'amount': ['count', 'sum']
                })
                print(summary)
            except Exception as e:
                print(f"  (Unable to generate summary: {e})")
            print()

            # Show total revenue
            print(f"Total revenue: ${df['amount'].sum():,.2f}")
            print(f"Transactions: {len(df)}")
            print()

            # Show sample records
            print("Sample records (first 5):")
            sample_cols = [col for col in ['cash_date', 'counterparty', 'amount', 'description'] if col in df.columns]
            print(df[sample_cols].head(5).to_string())
            print()

        except Exception as e:
            print(f"❌ ERROR: Preview failed")
            print(f"   {str(e)}")
            sys.exit(1)

        print("✅ DRY RUN COMPLETE - No data inserted")
        print()
        print("To insert data, run without --dry-run flag")
        sys.exit(0)

    # Confirm before inserting
    response = input(f"Insert revenue transactions into cash_transactions? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)

    print()

    # Insert into cash_transactions (server-side)
    success = insert_deposits_to_cash(
        bq,
        start_date=args.start_date,
        end_date=args.end_date,
        platform=args.platform
    )

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    if success:
        print("✅ SUCCESS: All revenue transactions loaded!")
        print()
        print("Verify with this query:")
        print("  SELECT cash_date, cash_flow_category, COUNT(*) as count,")
        print("         SUM(amount) as total_revenue")
        print("  FROM `vochill.revrec.cash_transactions`")
        print("  WHERE cash_flow_section = 'Operating'")
        print("    AND cash_flow_category LIKE 'Revenue%'")
        print("  GROUP BY cash_date, cash_flow_category")
        print("  ORDER BY cash_date DESC")
        print("  LIMIT 20;")
        print()
        print("Next steps:")
        print("  1. View cash_transactions: SELECT * FROM `vochill.revrec.cash_transactions` LIMIT 100")
        print("  2. ETL refunds (if needed): python scripts/etl_refunds_to_cash.py")
        print("  3. ETL vendor invoices: python scripts/etl_invoices_to_cash.py")
        print()
    else:
        print("❌ FAILED: Error occurred during insert")
        print()
        print("Check the error message above for details")
        print()


if __name__ == "__main__":
    main()
