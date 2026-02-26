"""
Verify that all financial tables were created successfully in BigQuery

Usage:
    python scripts/verify_tables.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def main():
    print("=" * 60)
    print("VoChill Financial Tables - Verification")
    print("=" * 60)
    print()

    # Expected tables and views
    expected_tables = [
        'bank_accounts',
        'chart_of_accounts',
        'payment_terms',
        'cash_transactions',
        'cash_balances',
        'debt_schedule',
        'cash_forecast',
        'gl_transactions',
        'recurring_transactions',
        'capex_plan',
        'budget',
        'scenarios',
        'forecast_assumptions',
    ]

    expected_views = [
        'v_daily_cash_flow',
        'v_weekly_cash_flow',
        'v_cash_position',
    ]

    print("Connecting to BigQuery...")

    try:
        bq = BigQueryConnector()
        print("✅ Connected")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to BigQuery")
        print(f"   {str(e)}")
        sys.exit(1)

    # Get list of tables
    print("Fetching table list from vochill.revrec...")

    try:
        tables = bq.get_available_tables()
        print(f"Found {len(tables)} objects in dataset")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to list tables")
        print(f"   {str(e)}")
        sys.exit(1)

    # Check tables
    print("Checking TABLES:")
    print("-" * 60)

    found_tables = []
    missing_tables = []

    for table_name in expected_tables:
        if table_name in tables:
            found_tables.append(table_name)
            print(f"✅ {table_name}")
        else:
            missing_tables.append(table_name)
            print(f"❌ {table_name} - MISSING")

    print()
    print("Checking VIEWS:")
    print("-" * 60)

    found_views = []
    missing_views = []

    for view_name in expected_views:
        if view_name in tables:
            found_views.append(view_name)
            print(f"✅ {view_name}")
        else:
            missing_views.append(view_name)
            print(f"❌ {view_name} - MISSING")

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Tables: {len(found_tables)}/{len(expected_tables)} created")
    print(f"Views:  {len(found_views)}/{len(expected_views)} created")
    print()

    if not missing_tables and not missing_views:
        print("✅ SUCCESS: All tables and views created!")
        print()
        print("Next steps:")
        print("  1. Test queries: python notebooks/bigquery_example.py")
        print("  2. Populate data:")
        print("     - python scripts/populate_bank_accounts.py")
        print("     - python scripts/populate_chart_of_accounts.py")
        print()

        # Check seed data
        print("Checking seed data...")
        print()

        try:
            # Check payment_terms
            payment_terms = bq.query("SELECT COUNT(*) as count FROM `vochill.revrec.payment_terms`")
            pt_count = payment_terms.iloc[0]['count']
            print(f"  payment_terms: {pt_count} rows {'✅' if pt_count >= 7 else '⚠️  (expected 7)'}")

            # Check scenarios
            scenarios = bq.query("SELECT COUNT(*) as count FROM `vochill.revrec.scenarios`")
            sc_count = scenarios.iloc[0]['count']
            print(f"  scenarios: {sc_count} rows {'✅' if sc_count >= 3 else '⚠️  (expected 3)'}")
            print()
        except Exception as e:
            print(f"  ⚠️  Could not check seed data: {e}")
            print()

        return 0
    else:
        print("⚠️  WARNING: Some tables/views are missing")
        print()

        if missing_tables:
            print("Missing tables:")
            for table in missing_tables:
                print(f"  - {table}")
            print()

        if missing_views:
            print("Missing views:")
            for view in missing_views:
                print(f"  - {view}")
            print()

        print("To fix:")
        print("  Re-run: python scripts/create_tables.py")
        print()

        return 1


if __name__ == "__main__":
    sys.exit(main())
