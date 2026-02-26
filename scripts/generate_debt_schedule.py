"""
Generate SBA loan payment schedule and insert into debt_schedule table

SBA Loan Terms (from promissory note):
- Loan amount: $500,000 revolving LOC
- Rate: Prime + 2.25% (initially 10.75%)
- I/O Period: 24 months (May 2024 - May 2026)
- Amortization: 60 months (June 2026 - May 2031)
- Payment day: 30th of month

Usage:
    python scripts/generate_debt_schedule.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def calculate_monthly_interest(principal, annual_rate, days_in_month=30):
    """Calculate monthly interest using actual/360 convention"""
    daily_rate = annual_rate / 360
    return principal * daily_rate * days_in_month


def calculate_monthly_pi_payment(principal, annual_rate, months_remaining):
    """Calculate monthly P&I payment using amortization formula"""
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / months_remaining

    payment = principal * (monthly_rate * (1 + monthly_rate)**months_remaining) / \
              ((1 + monthly_rate)**months_remaining - 1)
    return payment


def generate_sba_schedule():
    """Generate SBA loan payment schedule"""

    # Loan parameters
    loan_amount = 500000.00
    initial_rate = 0.1075  # 10.75% (Prime + 2.25%)
    loan_start = date(2024, 5, 30)

    # I/O period: 24 months
    io_end = date(2026, 5, 30)

    # Amortization period: 60 months after I/O
    amort_months = 60
    loan_maturity = date(2031, 5, 30)

    # Assume current balance for demo (adjust as needed)
    current_balance = 350000.00  # ADJUST THIS based on actual drawn amount

    schedule = []
    payment_number = 1
    current_date = loan_start
    balance = current_balance

    print(f"Generating payment schedule:")
    print(f"  Loan amount: ${loan_amount:,.2f}")
    print(f"  Current balance: ${current_balance:,.2f}")
    print(f"  Rate: {initial_rate*100:.2f}%")
    print(f"  I/O period: {loan_start} to {io_end}")
    print(f"  Amortization: {amort_months} months")
    print()

    # Generate I/O payments
    while current_date <= io_end:
        # Handle day 30 for months that don't have 30 days
        try:
            payment_date = current_date.replace(day=30)
        except ValueError:
            # Month doesn't have day 30, use last day of month
            next_month = current_date.replace(day=1) + relativedelta(months=1)
            payment_date = next_month - relativedelta(days=1)

        # Calculate interest
        days_in_period = 30  # Approximate
        interest = calculate_monthly_interest(balance, initial_rate, days_in_period)

        schedule.append({
            'schedule_id': str(uuid.uuid4()),
            'loan_id': 'sba_loc_001',
            'loan_name': 'SBA Loan',
            'lender': 'Frost Bank',
            'payment_date': payment_date.isoformat(),
            'payment_number': payment_number,
            'payment_amount': round(interest, 2),
            'principal_amount': 0.00,
            'interest_amount': round(interest, 2),
            'fees_amount': 0.00,
            'beginning_principal': round(balance, 2),
            'ending_principal': round(balance, 2),
            'interest_rate': initial_rate,
            'days_in_period': days_in_period,
            'is_paid': current_date < date.today(),
            'payment_type': 'Interest Only',
            'is_forecast': current_date >= date.today(),
        })

        payment_number += 1
        current_date = current_date + relativedelta(months=1)

    # Generate P&I payments
    months_remaining = amort_months
    amort_start = io_end + relativedelta(months=1)
    current_date = amort_start

    while months_remaining > 0 and current_date <= loan_maturity:
        # Handle day 30 for months that don't have 30 days
        try:
            payment_date = current_date.replace(day=30)
        except ValueError:
            # Month doesn't have day 30, use last day of month
            next_month = current_date.replace(day=1) + relativedelta(months=1)
            payment_date = next_month - relativedelta(days=1)

        # Calculate P&I payment
        monthly_payment = calculate_monthly_pi_payment(balance, initial_rate, months_remaining)
        interest = calculate_monthly_interest(balance, initial_rate, 30)
        principal = monthly_payment - interest

        # Ensure we don't overpay on last payment
        if principal > balance:
            principal = balance
            monthly_payment = principal + interest

        new_balance = max(0, balance - principal)

        schedule.append({
            'schedule_id': str(uuid.uuid4()),
            'loan_id': 'sba_loc_001',
            'loan_name': 'SBA Loan',
            'lender': 'Frost Bank',
            'payment_date': payment_date.isoformat(),
            'payment_number': payment_number,
            'payment_amount': round(monthly_payment, 2),
            'principal_amount': round(principal, 2),
            'interest_amount': round(interest, 2),
            'fees_amount': 0.00,
            'beginning_principal': round(balance, 2),
            'ending_principal': round(new_balance, 2),
            'interest_rate': initial_rate,
            'days_in_period': 30,
            'is_paid': current_date < date.today(),
            'payment_type': 'Principal & Interest',
            'is_forecast': current_date >= date.today(),
        })

        balance = new_balance
        payment_number += 1
        months_remaining -= 1
        current_date = current_date + relativedelta(months=1)

    return schedule


def main():
    print("=" * 60)
    print("VoChill SBA Loan - Payment Schedule Generator")
    print("=" * 60)
    print()

    # Generate schedule
    schedule = generate_sba_schedule()

    print(f"Generated {len(schedule)} payment records")
    print()

    # Show first few and last few payments
    print("First 3 payments (I/O period):")
    for pmt in schedule[:3]:
        print(f"  {pmt['payment_date']}: ${pmt['payment_amount']:,.2f} " +
              f"(Principal: ${pmt['principal_amount']:,.2f}, Interest: ${pmt['interest_amount']:,.2f})")
    print()

    print("Last 3 payments (Amortization):")
    for pmt in schedule[-3:]:
        print(f"  {pmt['payment_date']}: ${pmt['payment_amount']:,.2f} " +
              f"(Principal: ${pmt['principal_amount']:,.2f}, Interest: ${pmt['interest_amount']:,.2f})")
    print()

    response = input("Insert schedule into BigQuery? (y/n): ").strip().lower()
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

    print("Inserting payment schedule...")
    print()

    success_count = 0
    error_count = 0

    for i, pmt in enumerate(schedule, 1):
        if i % 12 == 0:  # Progress indicator every 12 payments
            print(f"  Processed {i}/{len(schedule)} payments...")

        # Build INSERT statement
        columns = ', '.join(pmt.keys())

        # Build values with proper SQL formatting
        values = []
        for key, value in pmt.items():
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
        INSERT INTO `vochill.revrec.debt_schedule` ({columns})
        VALUES ({values_str})
        """

        try:
            bq.query(sql)
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                success_count += 1
            else:
                print(f"❌ Error on payment {i}: {error_msg[:80]}")
                error_count += 1

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Success: {success_count}/{len(schedule)}")
    print(f"❌ Errors:  {error_count}/{len(schedule)}")
    print()

    if error_count == 0:
        print("✅ SUCCESS: SBA loan schedule populated!")
        print()
        print("Verify with this query:")
        print("  SELECT payment_date, payment_type, payment_amount,")
        print("         principal_amount, interest_amount, ending_principal")
        print("  FROM `vochill.revrec.debt_schedule`")
        print("  WHERE loan_id = 'sba_loc_001'")
        print("  ORDER BY payment_date")
        print("  LIMIT 10;")
        print()
        print("✅ Master data population complete!")
        print()
        print("Next steps:")
        print("  1. Review and adjust recurring amounts if needed")
        print("  2. Begin ETL from existing tables → cash_transactions")
        print("  3. Build forecast engine")
        print()
    else:
        print("⚠️  Some payments failed to insert. Review errors above.")
        print()


if __name__ == "__main__":
    main()
