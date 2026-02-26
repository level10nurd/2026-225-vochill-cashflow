"""
Example: Using the BigQuery Connector

This script demonstrates how to connect to BigQuery and fetch VoChill data.
"""

from src.data import BigQueryConnector
import pandas as pd

def main():
    # Initialize connector
    print("Connecting to BigQuery...")
    bq = BigQueryConnector()

    # Test connection
    if bq.test_connection():
        print("✓ Connection successful!")
    else:
        print("✗ Connection failed!")
        return

    # List available tables
    print("\nAvailable tables:")
    tables = bq.get_available_tables()
    for table in tables:
        print(f"  • {table}")

    # Example 1: Get deposits for last 30 days
    print("\n" + "="*60)
    print("Example 1: Recent Amazon deposits")
    print("="*60)

    deposits = bq.get_deposits(
        start_date="2026-02-01",
        end_date="2026-02-28",
        platform="Amazon"
    )

    print(f"\nFetched {len(deposits):,} deposit transactions")
    print("\nSample data:")
    print(deposits[['platform', 'date_time', 'settlement_id', 'total']].head(10))

    # Example 2: Get revenue summary by platform
    print("\n" + "="*60)
    print("Example 2: Revenue summary by platform (Feb 2026)")
    print("="*60)

    revenue_sql = """
    SELECT
        platform,
        DATE(date_time) as date,
        COUNT(DISTINCT order_id) as order_count,
        SUM(product_sales) as gross_sales,
        SUM(selling_fees) as platform_fees,
        SUM(fba_fees) as fulfillment_fees,
        SUM(total) as net_proceeds
    FROM vochill.revrec.deposits
    WHERE DATE(date_time) BETWEEN '2026-02-01' AND '2026-02-28'
    GROUP BY platform, DATE(date_time)
    ORDER BY date DESC, platform
    """

    revenue = bq.query(revenue_sql)
    print(f"\nFetched {len(revenue)} daily platform summaries")
    print(revenue)

    # Example 3: Get forecast data
    print("\n" + "="*60)
    print("Example 3: SKU-level forecast for next 3 months")
    print("="*60)

    forecast = bq.get_forecast(
        start_month="2026-03-01",
        end_month="2026-05-31"
    )

    if len(forecast) > 0:
        print(f"\nFetched {len(forecast)} forecast records")
        print("\nSample forecast data:")
        print(forecast[['month', 'platform', 'sku', 'forecast_units', 'forecast_revenue']].head(10))
    else:
        print("\nNo forecast data found for this period")

    # Example 4: Get vendor payment terms
    print("\n" + "="*60)
    print("Example 4: Vendor payment terms")
    print("="*60)

    vendors = bq.get_vendors()
    print(f"\nFetched {len(vendors)} vendors")
    print("\nVendors with payment terms:")
    vendor_terms = vendors[['Name', 'Terms', 'Actual Days']].dropna(subset=['Terms'])
    print(vendor_terms)

    # Example 5: Get open purchase orders (commitments)
    print("\n" + "="*60)
    print("Example 5: Open purchase orders")
    print("="*60)

    open_pos = bq.get_purchase_orders(status="Open")
    print(f"\nFetched {len(open_pos)} open PO line items")

    if len(open_pos) > 0:
        po_summary = open_pos.groupby('vendor').agg({
            'po_no': 'count',
            'qty_ordered': 'sum',
            'qty_received': 'sum'
        }).reset_index()
        po_summary.columns = ['Vendor', 'PO Lines', 'Qty Ordered', 'Qty Received']
        print("\nPO summary by vendor:")
        print(po_summary)

    print("\n" + "="*60)
    print("Done!")
    print("="*60)


if __name__ == "__main__":
    main()
