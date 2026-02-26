"""
Populate bank_accounts table with VoChill's accounts

Usage:
    python scripts/populate_bank_accounts.py
"""

import sys
from pathlib import Path
from datetime import date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def main():
    print("=" * 60)
    print("VoChill Bank Accounts - Population Script")
    print("=" * 60)
    print()

    # Define VoChill's bank accounts
    bank_accounts = [
        {
            'account_id': 'frost_checking',
            'account_name': 'VoChill Checking',
            'account_number': 'XXXX8017',
            'account_type': 'Checking',
            'institution_name': 'Frost Bank',
            'is_credit_line': False,
            'credit_limit': None,
            'interest_rate': None,
            'qb_account_name': 'VoChill Checking',
            'qb_account_number': '8017',
            'is_active': True,
            'notes': 'Primary operating checking account'
        },
        {
            'account_id': 'frost_money_market',
            'account_name': 'Money Market',
            'account_number': 'XXXX8931',
            'account_type': 'Money Market',
            'institution_name': 'Frost Bank',
            'is_credit_line': False,
            'credit_limit': None,
            'interest_rate': None,
            'qb_account_name': 'Money Market',
            'qb_account_number': '8931',
            'is_active': True,
            'notes': 'Money market savings account'
        },
        {
            'account_id': 'sba_loc',
            'account_name': 'SBA Loan',
            'account_number': '5853239110',
            'account_type': 'LOC',
            'institution_name': 'Frost Bank',
            'is_credit_line': True,
            'credit_limit': 500000.00,
            'interest_rate': 0.1075,  # Prime + 2.25%, currently 10.75%
            'qb_account_name': 'SBA Loan',
            'is_active': True,
            'notes': '$500k SBA revolving LOC, Prime + 2.25%, I/O through May 2026'
        },
        {
            'account_id': 'amex_gold',
            'account_name': 'AMEX Gold Card',
            'account_type': 'Credit Card',
            'institution_name': 'American Express',
            'is_credit_line': True,
            'credit_limit': 50000.00,  # Estimate - adjust as needed
            'qb_account_name': 'AMEX Gold Card',
            'is_active': True,
            'notes': 'Primary business credit card'
        },
        {
            'account_id': 'chase_inc',
            'account_name': 'Chase Inc',
            'account_type': 'Credit Card',
            'institution_name': 'Chase',
            'is_credit_line': True,
            'credit_limit': 25000.00,  # Estimate - adjust as needed
            'qb_account_name': 'Chase Inc',
            'is_active': True,
            'notes': 'Business credit card'
        },
        {
            'account_id': 'shopify_card',
            'account_name': 'Shopify Credit Card',
            'account_type': 'Credit Card',
            'institution_name': 'Shopify',
            'is_credit_line': True,
            'credit_limit': 10000.00,  # Estimate - adjust as needed
            'qb_account_name': 'Shopify Credit Card',
            'is_active': True,
            'notes': 'Shopify business credit card'
        },
        {
            'account_id': 'southwest_card',
            'account_name': 'Southwest Card',
            'account_type': 'Credit Card',
            'institution_name': 'Southwest',
            'is_credit_line': True,
            'credit_limit': 15000.00,  # Estimate - adjust as needed
            'qb_account_name': 'Southwest Card',
            'is_active': True,
            'notes': 'Southwest business credit card (multiple employee cards)'
        },
    ]

    print(f"Preparing to insert {len(bank_accounts)} bank accounts:")
    for acc in bank_accounts:
        status = "LOC" if acc['is_credit_line'] and acc['account_type'] == 'LOC' else acc['account_type']
        limit = f"${acc['credit_limit']:,.0f}" if acc.get('credit_limit') else "N/A"
        print(f"  • {acc['account_name']} ({status}) - Limit: {limit}")
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

    print("Inserting bank accounts...")
    print()

    success_count = 0
    error_count = 0

    for acc in bank_accounts:
        print(f"  {acc['account_name']}...", end=' ')

        # Build INSERT statement
        columns = ', '.join(acc.keys())

        # Build values with proper SQL formatting
        values = []
        for key, value in acc.items():
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
        INSERT INTO `vochill.revrec.bank_accounts` ({columns})
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
    print(f"✅ Success: {success_count}/{len(bank_accounts)}")
    print(f"❌ Errors:  {error_count}/{len(bank_accounts)}")
    print()

    if error_count == 0:
        print("✅ SUCCESS: All bank accounts populated!")
        print()
        print("Verify with this query:")
        print("  SELECT account_name, account_type, institution_name,")
        print("         CASE WHEN is_credit_line THEN credit_limit ELSE NULL END as limit")
        print("  FROM `vochill.revrec.bank_accounts`")
        print("  ORDER BY account_type, account_name;")
        print()
        print("Next steps:")
        print("  1. Populate recurring transactions: python scripts/populate_recurring_transactions.py")
        print("  2. Generate debt schedule: python scripts/generate_debt_schedule.py")
        print()
    else:
        print("⚠️  Some accounts failed to insert. Review errors above.")
        print()


if __name__ == "__main__":
    main()
