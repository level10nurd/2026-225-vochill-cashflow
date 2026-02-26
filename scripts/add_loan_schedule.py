"""
Universal Loan Payment Schedule Generator

Generates payment schedules for ANY type of loan and inserts into debt_schedule table:
- Equipment loans
- Balloon loans
- Unsecured term loans
- Lines of credit
- Credit card minimum payments

Supports:
- Interest-only periods
- Principal & interest amortization
- Balloon payments
- Fixed payments
- Revolving credit (minimum payments)

Usage:
    python scripts/add_loan_schedule.py --loan-type equipment --interactive
    python scripts/add_loan_schedule.py --config loans/equipment_loan_001.yaml
"""

import sys
import argparse
from pathlib import Path
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import uuid
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def calculate_monthly_interest(principal, annual_rate, days_in_month=30):
    """Calculate monthly interest using actual/360 convention"""
    daily_rate = annual_rate / 360
    return principal * daily_rate * days_in_month


def calculate_monthly_pi_payment(principal, annual_rate, months_remaining):
    """Calculate monthly P&I payment using amortization formula"""
    if months_remaining == 0:
        return principal

    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / months_remaining

    payment = principal * (monthly_rate * (1 + monthly_rate)**months_remaining) / \
              ((1 + monthly_rate)**months_remaining - 1)
    return payment


def generate_payment_date(start_date, months_ahead, day_of_month):
    """Generate payment date for a given month, handling month-end cases"""
    target_date = start_date + relativedelta(months=months_ahead)

    try:
        return target_date.replace(day=day_of_month)
    except ValueError:
        # Month doesn't have this day, use last day of month
        next_month = target_date.replace(day=1) + relativedelta(months=1)
        return next_month - relativedelta(days=1)


def interactive_loan_input():
    """Interactive prompts to gather loan details"""

    print("=" * 60)
    print("Universal Loan Schedule Generator - Interactive Mode")
    print("=" * 60)
    print()

    # Basic loan info
    loan_name = input("Loan name (e.g., 'Equipment Loan - Reflex 2024'): ").strip()
    lender = input("Lender name: ").strip()
    loan_id = input("Loan ID (leave blank to auto-generate): ").strip()

    if not loan_id:
        loan_id = f"loan_{uuid.uuid4().hex[:8]}"
        print(f"  → Generated loan_id: {loan_id}")

    print()

    # Loan type
    print("Loan Types:")
    print("  1. Equipment Loan (fixed term, amortizing)")
    print("  2. Balloon Loan (low payments, lump sum at end)")
    print("  3. Term Loan (standard amortization)")
    print("  4. Line of Credit (interest-only, revolving)")
    print("  5. Credit Card (minimum payments)")

    loan_type_map = {
        '1': 'Equipment Loan',
        '2': 'Balloon Loan',
        '3': 'Term Loan',
        '4': 'Line of Credit',
        '5': 'Credit Card'
    }

    loan_type_choice = input("Select loan type (1-5): ").strip()
    loan_type = loan_type_map.get(loan_type_choice, 'Term Loan')
    print(f"  → Loan type: {loan_type}")
    print()

    # Amounts
    original_amount = float(input("Original loan amount: $").strip().replace(',', ''))
    current_balance = float(input("Current balance (press Enter if same as original): $").strip().replace(',', '') or original_amount)

    print()

    # Rate
    annual_rate = float(input("Annual interest rate (e.g., 8.5 for 8.5%): ").strip()) / 100
    print(f"  → Rate: {annual_rate*100:.2f}%")
    print()

    # Payment details
    payment_day = int(input("Payment day of month (1-31): ").strip())

    print()
    print("Payment Structure:")
    print("  1. Interest-Only (IO) period, then Principal & Interest (P&I)")
    print("  2. Principal & Interest (P&I) from start")
    print("  3. Fixed monthly payment amount")
    print("  4. Balloon payment (small payments, large final payment)")

    structure_choice = input("Select payment structure (1-4): ").strip()
    print()

    # Dates
    start_date_str = input("Loan start date (YYYY-MM-DD): ").strip()
    start_date = date.fromisoformat(start_date_str)

    maturity_date_str = input("Loan maturity date (YYYY-MM-DD): ").strip()
    maturity_date = date.fromisoformat(maturity_date_str)

    print()

    # Structure-specific parameters
    io_months = 0
    amort_months = 0
    fixed_payment = None
    balloon_amount = None

    if structure_choice == '1':
        # IO then P&I
        io_months = int(input("Interest-only period (months): ").strip())

        total_months = ((maturity_date.year - start_date.year) * 12 +
                       (maturity_date.month - start_date.month))
        amort_months = total_months - io_months

        print(f"  → {io_months} months I/O, then {amort_months} months P&I")

    elif structure_choice == '2':
        # P&I from start
        amort_months = ((maturity_date.year - start_date.year) * 12 +
                       (maturity_date.month - start_date.month))
        print(f"  → {amort_months} months amortization")

    elif structure_choice == '3':
        # Fixed payment
        fixed_payment = float(input("Monthly payment amount: $").strip().replace(',', ''))
        print(f"  → Fixed payment: ${fixed_payment:,.2f}/month")

    elif structure_choice == '4':
        # Balloon
        fixed_payment = float(input("Monthly payment amount (before balloon): $").strip().replace(',', ''))
        balloon_amount = float(input("Balloon payment amount: $").strip().replace(',', ''))

        print(f"  → Monthly: ${fixed_payment:,.2f}, Balloon: ${balloon_amount:,.2f}")

    print()

    return {
        'loan_id': loan_id,
        'loan_name': loan_name,
        'lender': lender,
        'loan_type': loan_type,
        'original_amount': original_amount,
        'current_balance': current_balance,
        'annual_rate': annual_rate,
        'payment_day': payment_day,
        'start_date': start_date,
        'maturity_date': maturity_date,
        'io_months': io_months,
        'amort_months': amort_months,
        'fixed_payment': fixed_payment,
        'balloon_amount': balloon_amount,
        'structure_choice': structure_choice
    }


def generate_loan_schedule(config):
    """Generate payment schedule based on loan configuration"""

    schedule = []
    payment_number = 1
    current_date = config['start_date']
    balance = config['current_balance']

    print(f"Generating payment schedule for {config['loan_name']}...")
    print(f"  Balance: ${balance:,.2f}")
    print(f"  Rate: {config['annual_rate']*100:.2f}%")
    print()

    # Interest-only period
    if config['io_months'] > 0:
        print(f"  Generating {config['io_months']} I/O payments...")

        for _ in range(config['io_months']):
            payment_date = generate_payment_date(
                config['start_date'],
                payment_number - 1,
                config['payment_day']
            )

            interest = calculate_monthly_interest(balance, config['annual_rate'], 30)

            schedule.append({
                'schedule_id': str(uuid.uuid4()),
                'loan_id': config['loan_id'],
                'loan_name': config['loan_name'],
                'lender': config['lender'],
                'payment_date': payment_date.isoformat(),
                'payment_number': payment_number,
                'payment_amount': round(interest, 2),
                'principal_amount': 0.00,
                'interest_amount': round(interest, 2),
                'fees_amount': 0.00,
                'beginning_principal': round(balance, 2),
                'ending_principal': round(balance, 2),
                'interest_rate': config['annual_rate'],
                'days_in_period': 30,
                'is_paid': payment_date < date.today(),
                'payment_type': 'Interest Only',
                'is_forecast': payment_date >= date.today(),
            })

            payment_number += 1

    # Principal & Interest period
    if config['amort_months'] > 0:
        print(f"  Generating {config['amort_months']} P&I payments...")

        months_remaining = config['amort_months']

        for _ in range(config['amort_months']):
            payment_date = generate_payment_date(
                config['start_date'],
                payment_number - 1,
                config['payment_day']
            )

            monthly_payment = calculate_monthly_pi_payment(
                balance,
                config['annual_rate'],
                months_remaining
            )

            interest = calculate_monthly_interest(balance, config['annual_rate'], 30)
            principal = monthly_payment - interest

            # Ensure we don't overpay on last payment
            if principal > balance:
                principal = balance
                monthly_payment = principal + interest

            new_balance = max(0, balance - principal)

            schedule.append({
                'schedule_id': str(uuid.uuid4()),
                'loan_id': config['loan_id'],
                'loan_name': config['loan_name'],
                'lender': config['lender'],
                'payment_date': payment_date.isoformat(),
                'payment_number': payment_number,
                'payment_amount': round(monthly_payment, 2),
                'principal_amount': round(principal, 2),
                'interest_amount': round(interest, 2),
                'fees_amount': 0.00,
                'beginning_principal': round(balance, 2),
                'ending_principal': round(new_balance, 2),
                'interest_rate': config['annual_rate'],
                'days_in_period': 30,
                'is_paid': payment_date < date.today(),
                'payment_type': 'Principal & Interest',
                'is_forecast': payment_date >= date.today(),
            })

            balance = new_balance
            months_remaining -= 1
            payment_number += 1

    # Fixed payment structure
    elif config['fixed_payment'] is not None and config['balloon_amount'] is None:
        print(f"  Generating fixed payments of ${config['fixed_payment']:,.2f}...")

        current_date = config['start_date']

        while balance > 0 and current_date <= config['maturity_date']:
            payment_date = generate_payment_date(
                config['start_date'],
                payment_number - 1,
                config['payment_day']
            )

            interest = calculate_monthly_interest(balance, config['annual_rate'], 30)
            principal = min(config['fixed_payment'] - interest, balance)
            monthly_payment = principal + interest

            new_balance = max(0, balance - principal)

            schedule.append({
                'schedule_id': str(uuid.uuid4()),
                'loan_id': config['loan_id'],
                'loan_name': config['loan_name'],
                'lender': config['lender'],
                'payment_date': payment_date.isoformat(),
                'payment_number': payment_number,
                'payment_amount': round(monthly_payment, 2),
                'principal_amount': round(principal, 2),
                'interest_amount': round(interest, 2),
                'fees_amount': 0.00,
                'beginning_principal': round(balance, 2),
                'ending_principal': round(new_balance, 2),
                'interest_rate': config['annual_rate'],
                'days_in_period': 30,
                'is_paid': payment_date < date.today(),
                'payment_type': 'Fixed Payment',
                'is_forecast': payment_date >= date.today(),
            })

            balance = new_balance
            payment_number += 1
            current_date = payment_date

    # Balloon payment structure
    elif config['balloon_amount'] is not None:
        print(f"  Generating monthly payments + balloon...")

        current_date = config['start_date']

        # Generate monthly payments until maturity
        while current_date < config['maturity_date']:
            payment_date = generate_payment_date(
                config['start_date'],
                payment_number - 1,
                config['payment_day']
            )

            if payment_date >= config['maturity_date']:
                break

            interest = calculate_monthly_interest(balance, config['annual_rate'], 30)

            # Fixed payment is interest + small principal
            principal = config['fixed_payment'] - interest
            monthly_payment = config['fixed_payment']

            new_balance = max(0, balance - principal)

            schedule.append({
                'schedule_id': str(uuid.uuid4()),
                'loan_id': config['loan_id'],
                'loan_name': config['loan_name'],
                'lender': config['lender'],
                'payment_date': payment_date.isoformat(),
                'payment_number': payment_number,
                'payment_amount': round(monthly_payment, 2),
                'principal_amount': round(principal, 2),
                'interest_amount': round(interest, 2),
                'fees_amount': 0.00,
                'beginning_principal': round(balance, 2),
                'ending_principal': round(new_balance, 2),
                'interest_rate': config['annual_rate'],
                'days_in_period': 30,
                'is_paid': payment_date < date.today(),
                'payment_type': 'Regular Payment',
                'is_forecast': payment_date >= date.today(),
            })

            balance = new_balance
            payment_number += 1
            current_date = payment_date

        # Add balloon payment
        balloon_principal = balance
        balloon_interest = calculate_monthly_interest(balance, config['annual_rate'], 30)
        balloon_total = config['balloon_amount']

        schedule.append({
            'schedule_id': str(uuid.uuid4()),
            'loan_id': config['loan_id'],
            'loan_name': config['loan_name'],
            'lender': config['lender'],
            'payment_date': config['maturity_date'].isoformat(),
            'payment_number': payment_number,
            'payment_amount': round(balloon_total, 2),
            'principal_amount': round(balloon_principal, 2),
            'interest_amount': round(balloon_interest, 2),
            'fees_amount': 0.00,
            'beginning_principal': round(balance, 2),
            'ending_principal': 0.00,
            'interest_rate': config['annual_rate'],
            'days_in_period': 30,
            'is_paid': config['maturity_date'] < date.today(),
            'payment_type': 'Balloon Payment',
            'is_forecast': config['maturity_date'] >= date.today(),
        })

    print(f"  → Generated {len(schedule)} payments")
    print()

    return schedule


def insert_schedule_to_bigquery(bq, schedule):
    """Insert loan schedule into debt_schedule table"""

    print(f"Inserting {len(schedule)} payments into BigQuery...")
    print()

    success_count = 0
    error_count = 0

    for i, pmt in enumerate(schedule, 1):
        if i % 12 == 0:
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
    print(f"✅ Success: {success_count}/{len(schedule)}")
    print(f"❌ Errors:  {error_count}/{len(schedule)}")
    print()

    return error_count == 0


def main():
    parser = argparse.ArgumentParser(description='Universal Loan Schedule Generator')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode (prompts for loan details)')
    parser.add_argument('--config', help='Load loan details from YAML config file')
    parser.add_argument('--loan-type', help='Loan type (for interactive mode)')

    args = parser.parse_args()

    print("=" * 60)
    print("Universal Loan Payment Schedule Generator")
    print("=" * 60)
    print()

    # Get loan configuration
    if args.config:
        # Load from YAML file
        print(f"Loading configuration from {args.config}...")
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

        # Convert date strings to date objects
        config['start_date'] = date.fromisoformat(config['start_date'])
        config['maturity_date'] = date.fromisoformat(config['maturity_date'])

    elif args.interactive:
        # Interactive prompts
        config = interactive_loan_input()

    else:
        print("❌ ERROR: Must specify either --interactive or --config")
        print()
        print("Examples:")
        print("  python scripts/add_loan_schedule.py --interactive")
        print("  python scripts/add_loan_schedule.py --config loans/equipment_loan.yaml")
        sys.exit(1)

    # Generate schedule
    schedule = generate_loan_schedule(config)

    # Show preview
    print("=" * 60)
    print("Payment Schedule Preview")
    print("=" * 60)
    print()

    print("First 3 payments:")
    for pmt in schedule[:3]:
        print(f"  {pmt['payment_date']}: ${pmt['payment_amount']:>10,.2f} " +
              f"(P: ${pmt['principal_amount']:>8,.2f}, I: ${pmt['interest_amount']:>8,.2f}) " +
              f"- {pmt['payment_type']}")
    print()

    if len(schedule) > 6:
        print("Last 3 payments:")
        for pmt in schedule[-3:]:
            print(f"  {pmt['payment_date']}: ${pmt['payment_amount']:>10,.2f} " +
                  f"(P: ${pmt['principal_amount']:>8,.2f}, I: ${pmt['interest_amount']:>8,.2f}) " +
                  f"- {pmt['payment_type']}")
        print()

    # Summary
    total_principal = sum(p['principal_amount'] for p in schedule)
    total_interest = sum(p['interest_amount'] for p in schedule)
    total_payments = sum(p['payment_amount'] for p in schedule)

    print(f"Total Principal: ${total_principal:,.2f}")
    print(f"Total Interest:  ${total_interest:,.2f}")
    print(f"Total Payments:  ${total_payments:,.2f}")
    print(f"Number of Payments: {len(schedule)}")
    print()

    # Confirm
    response = input(f"Insert {config['loan_name']} schedule into BigQuery? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)

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

    # Insert schedule
    success = insert_schedule_to_bigquery(bq, schedule)

    print()
    print("=" * 60)
    print("Complete")
    print("=" * 60)

    if success:
        print("✅ SUCCESS: Loan schedule loaded!")
        print()
        print("Verify with this query:")
        print(f"  SELECT payment_date, payment_type, payment_amount,")
        print(f"         principal_amount, interest_amount, ending_principal")
        print(f"  FROM `vochill.revrec.debt_schedule`")
        print(f"  WHERE loan_id = '{config['loan_id']}'")
        print(f"  ORDER BY payment_date")
        print(f"  LIMIT 10;")
        print()
    else:
        print("❌ FAILED: Some errors occurred")
        print()


if __name__ == "__main__":
    main()
