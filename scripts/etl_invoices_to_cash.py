"""
ETL: Transform invoices → cash_transactions

This script reads from the invoices table (vendor payments)
and transforms it into cash_transactions with proper cash timing.

Logic:
- Join with vendors table to get payment terms
- Calculate cash_date: invoice_date + payment_days (from vendor terms)
- Default to Net 30 if no terms specified
- Map to COGS category (can be refined later)

Usage:
    python scripts/etl_invoices_to_cash.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--dry-run]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def preview_invoices_to_cash(bq, start_date=None, end_date=None):
    """Preview the transformation without inserting"""

    # Build WHERE clause
    where_conditions = []
    if start_date:
        where_conditions.append(f"i.invoice_date >= '{start_date}'")
    if end_date:
        where_conditions.append(f"i.invoice_date <= '{end_date}'")

    where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""

    query = f"""
    WITH invoice_payments AS (
      SELECT
        i.invoice_id,
        i.vendor,
        i.invoice_date,
        i.invoice_number,
        i.po_number,
        i.subtotal,
        i.sales_tax,
        i.total,

        -- Get vendor payment terms
        v.Terms as payment_terms,
        COALESCE(v.`Actual Days`, v.`Request Days`, 30) as payment_days,

        -- Calculate cash date: invoice_date + payment_days
        DATE_ADD(i.invoice_date, INTERVAL COALESCE(v.`Actual Days`, v.`Request Days`, 30) DAY) as cash_date

      FROM `vochill.revrec.invoices` i
      LEFT JOIN `vochill.revrec.vendors` v
        ON i.vendor = v.Name
      WHERE 1=1 {where_clause}
        AND i.invoice_date IS NOT NULL  -- Exclude records with no date
    )

    SELECT
      invoice_date as transaction_date,
      cash_date,
      vendor as counterparty,
      payment_terms,
      payment_days,
      -total as amount,  -- Negative for cash outflow
      COUNT(*) OVER() as total_count,
      SUM(total) OVER() as total_amount
    FROM invoice_payments
    WHERE total > 0  -- Exclude credits/reversals
    ORDER BY cash_date DESC
    """

    print("Executing preview query...")
    print()

    results = bq.query(query)
    return results


def insert_invoices_to_cash(bq, start_date=None, end_date=None):
    """
    Insert transformed invoices directly into cash_transactions using server-side INSERT
    """

    # Build WHERE clause
    where_conditions = []
    if start_date:
        where_conditions.append(f"i.invoice_date >= '{start_date}'")
    if end_date:
        where_conditions.append(f"i.invoice_date <= '{end_date}'")

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

    WITH invoice_payments AS (
      SELECT
        i.invoice_id,
        i.vendor,
        i.invoice_date,
        i.invoice_number,
        i.po_number,
        i.subtotal,
        i.sales_tax,
        i.total,

        -- Get vendor payment terms
        v.Terms as payment_terms,
        COALESCE(v.`Actual Days`, v.`Request Days`, 30) as payment_days,

        -- Calculate cash date: invoice_date + payment_days
        DATE_ADD(i.invoice_date, INTERVAL COALESCE(v.`Actual Days`, v.`Request Days`, 30) DAY) as cash_date

      FROM `vochill.revrec.invoices` i
      LEFT JOIN `vochill.revrec.vendors` v
        ON i.vendor = v.Name
      WHERE 1=1 {where_clause}
        AND i.total > 0  -- Exclude credits/reversals
        AND i.invoice_date IS NOT NULL  -- Exclude records with no date
        AND i.invoice_id IS NOT NULL  -- Exclude records with no ID
    )

    SELECT
      GENERATE_UUID() as transaction_id,

      invoice_date as transaction_date,
      cash_date,
      cash_date as value_date,

      'invoices' as source_system,
      invoice_id as source_id,
      'invoices' as source_table,

      'frost_checking' as bank_account_id,
      'VoChill Checking' as bank_account_name,

      'Operating' as cash_flow_section,

      -- Default to COGS - Materials (can be refined with chart of accounts mapping)
      'COGS - Materials' as cash_flow_category,
      'Vendor Payments' as cash_flow_subcategory,

      -- NEGATIVE amount (cash outflow)
      -total as amount,
      'USD' as currency,

      vendor as counterparty,
      'Vendor' as counterparty_type,

      CONCAT(
        'Invoice ', invoice_number,
        CASE WHEN po_number IS NOT NULL THEN CONCAT(' (PO: ', po_number, ')') ELSE '' END
      ) as description,

      CONCAT(
        'Payment terms: ', COALESCE(payment_terms, 'Net 30'),
        ', Due: ', CAST(cash_date AS STRING),
        ', Subtotal: $', ROUND(subtotal, 2),
        ', Tax: $', ROUND(sales_tax, 2)
      ) as notes,

      FALSE as is_forecast,
      FALSE as is_recurring,
      CAST(NULL AS STRING) as recurring_id,
      CAST(NULL AS STRING) as scenario_id,

      ['vendor', 'expense', 'cogs'] as tags,

      CURRENT_TIMESTAMP() as created_at,
      CURRENT_TIMESTAMP() as updated_at,
      'etl_invoices' as created_by

    FROM invoice_payments
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
    parser = argparse.ArgumentParser(description='ETL: Invoices → Cash Transactions')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not insert')

    args = parser.parse_args()

    print("=" * 60)
    print("ETL: Invoices → Cash Transactions")
    print("=" * 60)
    print()

    # Display filters
    if args.start_date or args.end_date:
        print("Filters:")
        if args.start_date:
            print(f"  Start date: {args.start_date}")
        if args.end_date:
            print(f"  End date: {args.end_date}")
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
            df = preview_invoices_to_cash(
                bq,
                start_date=args.start_date,
                end_date=args.end_date
            )

            print(f"✅ Preview complete: {len(df)} vendor payments would be generated")
            print()

            if len(df) == 0:
                print("No records found matching criteria.")
                sys.exit(0)

            # Show summary
            print("Summary by vendor (top 10):")
            try:
                summary = df.groupby('counterparty').agg({
                    'amount': ['count', 'sum']
                }).sort_values(('amount', 'sum')).head(10)
                print(summary)
            except Exception as e:
                print(f"  (Unable to generate summary: {e})")
            print()

            # Show totals
            print(f"Total payments: ${abs(df['amount'].sum()):,.2f}")
            print(f"Transactions: {len(df)}")
            print()

            # Show sample records
            print("Sample records (first 5):")
            sample_cols = [col for col in ['transaction_date', 'cash_date', 'counterparty', 'payment_terms', 'amount'] if col in df.columns]
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
    response = input(f"Insert vendor payment transactions into cash_transactions? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)

    print()

    # Insert into cash_transactions (server-side)
    success = insert_invoices_to_cash(
        bq,
        start_date=args.start_date,
        end_date=args.end_date
    )

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    if success:
        print("✅ SUCCESS: All vendor payments loaded!")
        print()
        print("Verify with this query:")
        print("  SELECT cash_date, counterparty, COUNT(*) as count,")
        print("         SUM(amount) as total_payments")
        print("  FROM `vochill.revrec.cash_transactions`")
        print("  WHERE cash_flow_section = 'Operating'")
        print("    AND amount < 0  -- Outflows")
        print("  GROUP BY cash_date, counterparty")
        print("  ORDER BY cash_date DESC")
        print("  LIMIT 20;")
        print()
        print("Next steps:")
        print("  1. View all cash flows: SELECT * FROM `vochill.revrec.cash_transactions` ORDER BY cash_date DESC LIMIT 100")
        print("  2. Build forecast engine: python scripts/build_forecast.py")
        print()
    else:
        print("❌ FAILED: Error occurred during insert")
        print()
        print("Check the error message above for details")
        print()


if __name__ == "__main__":
    main()
