#!/bin/bash
# Verify that all financial tables were created successfully
#
# Usage: ./database/verify_tables.sh

set -e

echo "=================================================="
echo "VoChill Financial Tables - Verification"
echo "=================================================="
echo ""

# Expected tables
EXPECTED_TABLES=(
    "bank_accounts"
    "chart_of_accounts"
    "payment_terms"
    "cash_transactions"
    "cash_balances"
    "debt_schedule"
    "cash_forecast"
    "gl_transactions"
    "recurring_transactions"
    "capex_plan"
    "budget"
    "scenarios"
    "forecast_assumptions"
)

# Expected views
EXPECTED_VIEWS=(
    "v_daily_cash_flow"
    "v_weekly_cash_flow"
    "v_cash_position"
)

echo "Checking tables in vochill.revrec..."
echo ""

# Get list of tables
EXISTING_TABLES=$(bq ls --project_id=vochill --max_results=100 revrec | grep -E "TABLE|VIEW" | awk '{print $1}' | tail -n +3 || true)

# Check each expected table
MISSING_TABLES=()
FOUND_TABLES=()

for table in "${EXPECTED_TABLES[@]}"; do
    if echo "$EXISTING_TABLES" | grep -q "^${table}$"; then
        FOUND_TABLES+=("$table")
        echo "✅ $table"
    else
        MISSING_TABLES+=("$table")
        echo "❌ $table - MISSING"
    fi
done

echo ""
echo "Checking views..."
echo ""

MISSING_VIEWS=()
FOUND_VIEWS=()

for view in "${EXPECTED_VIEWS[@]}"; do
    if echo "$EXISTING_TABLES" | grep -q "^${view}$"; then
        FOUND_VIEWS+=("$view")
        echo "✅ $view"
    else
        MISSING_VIEWS+=("$view")
        echo "❌ $view - MISSING"
    fi
done

echo ""
echo "=================================================="
echo "Summary"
echo "=================================================="
echo "Tables: ${#FOUND_TABLES[@]}/${#EXPECTED_TABLES[@]} created"
echo "Views:  ${#FOUND_VIEWS[@]}/${#EXPECTED_VIEWS[@]} created"
echo ""

if [ ${#MISSING_TABLES[@]} -eq 0 ] && [ ${#MISSING_VIEWS[@]} -eq 0 ]; then
    echo "✅ SUCCESS: All tables and views created!"
    echo ""
    echo "Next steps:"
    echo "  1. Populate bank_accounts: python notebooks/populate_bank_accounts.py"
    echo "  2. Load chart_of_accounts: python notebooks/populate_chart_of_accounts.py"
    echo "  3. Test queries: python notebooks/bigquery_example.py"
    echo ""
else
    echo "⚠️  WARNING: Some tables/views are missing"
    echo ""
    if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
        echo "Missing tables:"
        for table in "${MISSING_TABLES[@]}"; do
            echo "  - $table"
        done
        echo ""
    fi
    if [ ${#MISSING_VIEWS[@]} -gt 0 ]; then
        echo "Missing views:"
        for view in "${MISSING_VIEWS[@]}"; do
            echo "  - $view"
        done
        echo ""
    fi
    echo "Re-run DDL execution: ./database/execute_ddl.sh"
    echo ""
fi
