"""
Build 13-Week Rolling Cash Flow Forecast

This script generates a 13-week forward-looking cash flow forecast by:
1. Analyzing historical revenue trends (deposits)
2. Projecting operating expenses based on recent averages
3. Adding recurring transactions (SBA loan, subscriptions)
4. Adding scheduled debt payments
5. Calculating weekly cash position and runway

Supports multiple scenarios: base (conservative), best, worst

Usage:
    python scripts/build_forecast.py [--weeks 13] [--scenario base]
"""

import sys
import argparse
from pathlib import Path
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def get_historical_actuals(bq, lookback_weeks=12):
    """Get historical cash transactions for analysis"""

    query = f"""
    SELECT
      cash_date,
      cash_flow_section,
      cash_flow_category,
      counterparty,
      amount
    FROM `vochill.revrec.cash_transactions`
    WHERE is_forecast = FALSE
      AND cash_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {lookback_weeks} WEEK)
    ORDER BY cash_date
    """

    return bq.query(query)


def analyze_revenue_trends(actuals_df):
    """Analyze historical revenue patterns"""

    revenue = actuals_df[actuals_df['amount'] > 0].copy()

    if len(revenue) == 0:
        return {
            'weekly_avg': 0,
            'weekly_std': 0,
            'platform_split': {}
        }

    # Calculate date range
    revenue['cash_date'] = pd.to_datetime(revenue['cash_date'])
    date_range = (revenue['cash_date'].max() - revenue['cash_date'].min()).days
    weeks_in_range = max(date_range / 7, 1)

    # Total revenue divided by actual weeks (more conservative than weekly grouping)
    total_revenue = revenue['amount'].sum()
    weekly_avg = total_revenue / weeks_in_range

    # Platform split
    platform_revenue = revenue.groupby('cash_flow_category')['amount'].sum()
    platform_pct = (platform_revenue / total_revenue * 100).to_dict() if total_revenue > 0 else {}

    return {
        'weekly_avg': weekly_avg,
        'weekly_std': 0,  # Simplified for now
        'platform_split': platform_pct,
        'total_revenue': total_revenue,
        'weeks_in_range': weeks_in_range
    }


def analyze_expense_patterns(actuals_df):
    """Analyze historical expense patterns by category"""

    expenses = actuals_df[actuals_df['amount'] < 0].copy()

    if len(expenses) == 0:
        return {'weekly_avg': 0, 'by_category': {}}

    # Calculate date range
    expenses['cash_date'] = pd.to_datetime(expenses['cash_date'])
    date_range = (expenses['cash_date'].max() - expenses['cash_date'].min()).days
    weeks_in_range = max(date_range / 7, 1)

    # Total expenses divided by actual weeks
    total_expenses = abs(expenses['amount'].sum())
    weekly_avg = total_expenses / weeks_in_range

    # By category
    category_expenses = expenses.groupby('cash_flow_category')['amount'].sum().to_dict()

    return {
        'weekly_avg': weekly_avg,
        'weekly_std': 0,  # Simplified
        'by_category': category_expenses,
        'total_expenses': total_expenses,
        'weeks_in_range': weeks_in_range
    }


def get_recurring_transactions(bq):
    """Get active recurring transactions"""

    query = """
    SELECT
      recurring_id,
      transaction_name as description,
      amount,
      cash_flow_category,
      frequency,
      recurrence_interval,
      day_of_month,
      start_date,
      end_date
    FROM `vochill.revrec.recurring_transactions`
    WHERE is_active = TRUE
      AND start_date <= CURRENT_DATE()
      AND (end_date IS NULL OR end_date >= CURRENT_DATE())
    """

    return bq.query(query)


def get_debt_schedule(bq, weeks=13):
    """Get upcoming debt payments"""

    query = f"""
    SELECT
      payment_date,
      loan_name,
      lender,
      payment_amount,
      principal_amount,
      interest_amount
    FROM `vochill.revrec.debt_schedule`
    WHERE payment_date >= CURRENT_DATE()
      AND payment_date <= DATE_ADD(CURRENT_DATE(), INTERVAL {weeks} WEEK)
      AND is_paid = FALSE
    ORDER BY payment_date
    """

    return bq.query(query)


def generate_weekly_forecast(bq, weeks=13, scenario='base', weekly_revenue=0):
    """
    Generate weekly cash flow forecast

    Args:
        bq: BigQueryConnector instance
        weeks: Number of weeks to forecast (default 13)
        scenario: 'base', 'best', or 'worst'
        weekly_revenue: Manual weekly revenue input (default 0 - revenue calculated separately)

    Returns:
        DataFrame with weekly forecast
    """

    print(f"Generating {weeks}-week {scenario} scenario forecast...")
    print()

    # Get historical data for expense analysis only
    print("Analyzing historical expenses...")
    actuals = get_historical_actuals(bq, lookback_weeks=12)

    if len(actuals) == 0:
        print("⚠️  WARNING: No historical actuals found!")
        print("   Forecast will be based on recurring transactions and debt payments only.")
        expense_patterns = {'weekly_avg': 0, 'by_category': {}}
    else:
        expense_patterns = analyze_expense_patterns(actuals)
        print(f"  Expenses: ${expense_patterns['weekly_avg']:,.0f}/week (avg)")

    # Revenue is provided manually or calculated separately
    if weekly_revenue > 0:
        print(f"  Revenue: ${weekly_revenue:,.0f}/week (manual input)")
    else:
        print(f"  Revenue: $0/week (revenue calculated in separate model)")
    print()

    # Get recurring and debt
    print("Loading recurring transactions and debt schedule...")
    recurring = get_recurring_transactions(bq)
    debt_schedule = get_debt_schedule(bq, weeks=weeks)
    print(f"  Recurring: {len(recurring)} items")
    print(f"  Debt payments: {len(debt_schedule)} scheduled")
    print()

    # Scenario multipliers
    scenario_factors = {
        'base': {'revenue': 1.0, 'expenses': 1.0},
        'best': {'revenue': 1.15, 'expenses': 0.90},
        'worst': {'revenue': 0.85, 'expenses': 1.10}
    }

    factors = scenario_factors.get(scenario, scenario_factors['base'])

    # Generate weekly forecast
    forecast_rows = []
    start_date = date.today()

    for week_num in range(1, weeks + 1):
        week_start = start_date + timedelta(weeks=week_num - 1)
        week_end = week_start + timedelta(days=6)

        # Revenue forecast (from manual input)
        if weekly_revenue > 0:
            weekly_revenue_forecast = weekly_revenue * factors['revenue']

            forecast_rows.append({
                'week_number': week_num,
                'week_start': week_start,
                'week_end': week_end,
                'transaction_date': week_end,
                'cash_flow_section': 'Operating',
                'cash_flow_category': 'Revenue - Ecommerce',
                'description': f'Week {week_num} - Revenue (forecast)',
                'amount': weekly_revenue_forecast,
                'scenario': scenario
            })

        # Operating expenses (weekly average)
        weekly_expenses = expense_patterns['weekly_avg'] * factors['expenses']

        forecast_rows.append({
            'week_number': week_num,
            'week_start': week_start,
            'week_end': week_end,
            'transaction_date': week_end,
            'cash_flow_section': 'Operating',
            'cash_flow_category': 'Operating Expenses',
            'description': f'Week {week_num} - OpEx (forecast)',
            'amount': -weekly_expenses,
            'scenario': scenario
        })

    # Add recurring transactions (monthly items allocated to weeks)
    for _, rec in recurring.iterrows():
        # Calculate which weeks this payment falls in
        day_of_month = rec['day_of_month']

        for week_num in range(1, weeks + 1):
            week_start = start_date + timedelta(weeks=week_num - 1)
            week_end = week_start + timedelta(days=6)

            # Check if this week contains the payment day
            payment_date = None
            for d in range(7):
                check_date = week_start + timedelta(days=d)
                if check_date.day == day_of_month:
                    payment_date = check_date
                    break

            if payment_date:
                # Determine section based on category
                section = 'Financing' if 'Debt' in rec['cash_flow_category'] or 'Loan' in rec['cash_flow_category'] else 'Operating'

                forecast_rows.append({
                    'week_number': week_num,
                    'week_start': week_start,
                    'week_end': week_end,
                    'transaction_date': payment_date,
                    'cash_flow_section': section,
                    'cash_flow_category': rec['cash_flow_category'],
                    'description': f"{rec['description']} (recurring)",
                    'amount': rec['amount'],
                    'scenario': scenario
                })

    # Add debt payments
    for _, debt in debt_schedule.iterrows():
        payment_date = debt['payment_date']

        # Find which week this falls in
        week_num = ((payment_date - start_date).days // 7) + 1

        if 1 <= week_num <= weeks:
            week_start = start_date + timedelta(weeks=week_num - 1)
            week_end = week_start + timedelta(days=6)

            forecast_rows.append({
                'week_number': week_num,
                'week_start': week_start,
                'week_end': week_end,
                'transaction_date': payment_date,
                'cash_flow_section': 'Financing',
                'cash_flow_category': 'Debt Service',
                'description': f"{debt['loan_name']} - {debt['lender']}",
                'amount': -debt['payment_amount'],
                'scenario': scenario
            })

    forecast_df = pd.DataFrame(forecast_rows)

    return forecast_df


def calculate_cash_position(bq, forecast_df):
    """Calculate weekly cash position and runway"""

    # Get current cash balance
    # For now, assume starting balance (we'll calculate from actuals later)
    # TODO: Query actual bank balances
    starting_balance = 250000.00  # PLACEHOLDER - adjust based on actual bank balance

    print(f"Starting cash balance: ${starting_balance:,.2f}")
    print()

    # Aggregate by week
    weekly_summary = forecast_df.groupby(['week_number', 'week_start', 'week_end']).agg({
        'amount': 'sum'
    }).reset_index()

    weekly_summary.columns = ['week_number', 'week_start', 'week_end', 'net_cash_flow']

    # Calculate running balance
    weekly_summary['cash_balance'] = starting_balance + weekly_summary['net_cash_flow'].cumsum()

    # Calculate runway (weeks until cash < 0)
    runway_weeks = None
    for idx, row in weekly_summary.iterrows():
        if row['cash_balance'] < 0:
            runway_weeks = row['week_number']
            break

    return weekly_summary, runway_weeks


def insert_forecast_to_bigquery(bq, forecast_df, scenario='base'):
    """Insert forecast into cash_transactions table with is_forecast=TRUE"""

    print(f"Inserting {len(forecast_df)} forecast transactions into BigQuery...")
    print()

    # Delete existing forecasts for this scenario
    delete_query = f"""
    DELETE FROM `vochill.revrec.cash_transactions`
    WHERE is_forecast = TRUE
      AND scenario_id = '{scenario}'
    """

    try:
        bq.query(delete_query)
        print(f"✅ Cleared existing {scenario} forecast")
    except Exception as e:
        print(f"⚠️  Warning: Could not clear existing forecast: {e}")

    print()

    # Build INSERT query
    # Using server-side INSERT for efficiency
    insert_query = """
    INSERT INTO `vochill.revrec.cash_transactions` (
      transaction_id, transaction_date, cash_date, value_date,
      source_system, source_table,
      bank_account_id, bank_account_name,
      cash_flow_section, cash_flow_category,
      amount, currency,
      description,
      is_forecast, scenario_id,
      created_at, updated_at, created_by
    )
    VALUES
    """

    # Build VALUES for each row
    values_rows = []
    for _, row in forecast_df.iterrows():
        trans_date = row['transaction_date'].strftime('%Y-%m-%d')
        description = row['description'].replace("'", "\\'")
        category = row['cash_flow_category'].replace("'", "\\'")
        section = row['cash_flow_section'].replace("'", "\\'")
        scenario_val = row['scenario']

        values_rows.append(f"""(
          GENERATE_UUID(),
          DATE('{trans_date}'),
          DATE('{trans_date}'),
          DATE('{trans_date}'),
          'forecast',
          'forecast_engine',
          'frost_checking',
          'VoChill Checking',
          '{section}',
          '{category}',
          {row['amount']},
          'USD',
          '{description}',
          TRUE,
          '{scenario_val}',
          CURRENT_TIMESTAMP(),
          CURRENT_TIMESTAMP(),
          'forecast_engine'
        )""")

    full_query = insert_query + ",\n".join(values_rows)

    try:
        bq.query(full_query)
        print(f"✅ Inserted {len(forecast_df)} forecast transactions")
        return True
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Build 13-Week Cash Flow Forecast')
    parser.add_argument('--weeks', type=int, default=13, help='Number of weeks to forecast')
    parser.add_argument('--scenario', default='base', choices=['base', 'best', 'worst'],
                        help='Forecast scenario')
    parser.add_argument('--weekly-revenue', type=float, default=0,
                        help='Manual weekly revenue input (default 0 - revenue calculated separately)')
    parser.add_argument('--preview', action='store_true', help='Preview only, do not insert')

    args = parser.parse_args()

    print("=" * 60)
    print(f"VoChill Cash Flow Forecast - {args.weeks} Weeks")
    print("=" * 60)
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

    # Generate forecast
    forecast_df = generate_weekly_forecast(
        bq,
        weeks=args.weeks,
        scenario=args.scenario,
        weekly_revenue=args.weekly_revenue
    )

    print("=" * 60)
    print("Forecast Summary")
    print("=" * 60)
    print()

    # Show weekly summary
    weekly_summary, runway_weeks = calculate_cash_position(bq, forecast_df)

    print(f"{'Week':<8} {'Dates':<25} {'Net Cash Flow':<18} {'Balance':<15}")
    print("-" * 70)

    for _, row in weekly_summary.head(args.weeks).iterrows():
        week_dates = f"{row['week_start'].strftime('%m/%d')} - {row['week_end'].strftime('%m/%d')}"
        net_flow = f"${row['net_cash_flow']:>12,.0f}"
        balance = f"${row['cash_balance']:>12,.0f}"

        print(f"{int(row['week_number']):<8} {week_dates:<25} {net_flow:<18} {balance:<15}")

    print()
    print(f"Total forecast transactions: {len(forecast_df)}")
    print()

    if runway_weeks:
        print(f"⚠️  RUNWAY: {runway_weeks} weeks until cash runs out")
    else:
        print(f"✅ RUNWAY: {args.weeks}+ weeks (cash remains positive)")
    print()

    # Preview mode
    if args.preview:
        print("⚠️  PREVIEW MODE - No data inserted")
        print()
        print("Sample forecast transactions:")
        print(forecast_df[['week_number', 'transaction_date', 'cash_flow_category', 'amount']].head(10))
        print()
        print("To insert forecast, run without --preview flag")
        sys.exit(0)

    # Confirm before inserting
    response = input(f"Insert {args.scenario} scenario forecast into BigQuery? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)

    print()

    # Insert forecast
    success = insert_forecast_to_bigquery(bq, forecast_df, scenario=args.scenario)

    print()
    print("=" * 60)
    print("Complete")
    print("=" * 60)

    if success:
        print("✅ SUCCESS: Forecast loaded!")
        print()
        print("View forecast with this query:")
        print(f"  SELECT cash_date, cash_flow_category, amount")
        print(f"  FROM `vochill.revrec.cash_transactions`")
        print(f"  WHERE is_forecast = TRUE")
        print(f"    AND scenario_id = '{args.scenario}'")
        print(f"  ORDER BY cash_date")
        print(f"  LIMIT 50;")
        print()
        print("Next steps:")
        print("  1. Generate other scenarios: python scripts/build_forecast.py --scenario best")
        print("  2. Build Excel reports: python scripts/generate_excel_report.py")
        print("  3. Query weekly summary view for analysis")
        print()
    else:
        print("❌ FAILED: Error occurred during insert")
        print()


if __name__ == "__main__":
    main()
