"""
Populate recurring_transactions table with known recurring items

Usage:
    python scripts/populate_recurring_transactions.py
"""

import sys
from pathlib import Path
from datetime import date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def main():
    print("=" * 60)
    print("VoChill Recurring Transactions - Population Script")
    print("=" * 60)
    print()

    # Define recurring transactions
    # NOTE: Adjust amounts and dates as needed for VoChill's actual recurring items
    recurring_items = [
        {
            'recurring_id': 'rec_sba_interest',
            'transaction_name': 'SBA Loan Interest Payment',
            'cash_flow_category': 'Financing - Debt Service',
            'amount': -4583.33,  # Approximate based on ~$500k at 10.75% / 12
            'currency': 'USD',
            'frequency': 'Monthly',
            'recurrence_interval': 1,
            'day_of_month': 30,
            'start_date': '2024-05-30',
            'counterparty': 'Frost Bank',
            'bank_account_id': 'frost_checking',
            'description': 'SBA LOC monthly interest payment (I/O period)',
            'notes': 'Interest-only through May 2026, then converts to P&I',
            'is_active': True
        },
        {
            'recurring_id': 'rec_shopify_subscription',
            'transaction_name': 'Shopify Subscription',
            'cash_flow_category': 'OpEx - SG&A - Software',
            'amount': -299.00,  # Typical Shopify Plus pricing
            'currency': 'USD',
            'frequency': 'Monthly',
            'recurrence_interval': 1,
            'day_of_month': 1,
            'start_date': '2024-01-01',
            'counterparty': 'Shopify',
            'description': 'Monthly Shopify platform subscription',
            'is_active': True
        },
        # Add more recurring items as needed:
        # - Warehouse rent
        # - Insurance premiums
        # - Software subscriptions (QB, accounting software, etc.)
        # - Payroll (if consistent amount)
    ]

    print(f"Preparing to insert {len(recurring_items)} recurring transactions:")
    for item in recurring_items:
        freq = f"{item['frequency']}"
        if item.get('day_of_month'):
            freq += f" (day {item['day_of_month']})"
        print(f"  • {item['transaction_name']}: ${abs(item['amount']):,.2f} {freq}")
    print()
    print("⚠️  NOTE: Review amounts and adjust as needed for VoChill's actual costs")
    print()

    response = input("Continue with population? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)

    print()
    print("Connecting to BigQuery...")

    try:
        bq = BigQueryConnector()
        print("✅ Connected")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to BigQuery")
        print(f"   {str(e)}")
        sys.exit(1)

    print("Inserting recurring transactions...")
    print()

    success_count = 0
    error_count = 0

    for item in recurring_items:
        print(f"  {item['transaction_name']}...", end=' ')

        # Build INSERT statement
        columns = ', '.join(item.keys())

        # Build values with proper SQL formatting
        values = []
        for key, value in item.items():
            if value is None:
                values.append('NULL')
            elif isinstance(value, bool):
                values.append('TRUE' if value else 'FALSE')
            elif isinstance(value, (int, float)):
                values.append(str(value))
            else:
                # String - escape single quotes
                escaped = str(value).replace("'", "\\'")
                values.append(f"'{escaped}'")

        values_str = ', '.join(values)

        sql = f"""
        INSERT INTO `vochill.revrec.recurring_transactions` ({columns})
        VALUES ({values_str})
        """

        try:
            bq.query(sql)
            print("✅")
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("⚠️  (already exists)")
                success_count += 1
            else:
                print(f"❌")
                print(f"     Error: {error_msg[:80]}")
                error_count += 1

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Success: {success_count}/{len(recurring_items)}")
    print(f"❌ Errors:  {error_count}/{len(recurring_items)}")
    print()

    if error_count == 0:
        print("✅ SUCCESS: All recurring transactions populated!")
        print()
        print("Verify with this query:")
        print("  SELECT transaction_name, amount, frequency, day_of_month")
        print("  FROM `vochill.revrec.recurring_transactions`")
        print("  WHERE is_active = TRUE")
        print("  ORDER BY ABS(amount) DESC;")
        print()
        print("Next steps:")
        print("  1. Generate SBA debt schedule: python scripts/generate_debt_schedule.py")
        print("  2. Add more recurring items as needed")
        print()
    else:
        print("⚠️  Some items failed to insert. Review errors above.")
        print()


if __name__ == "__main__":
    main()
