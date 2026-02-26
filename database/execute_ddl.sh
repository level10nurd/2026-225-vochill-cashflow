#!/bin/bash
# Execute BigQuery DDL to create financial tables
#
# Usage: ./database/execute_ddl.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - bq CLI available (comes with gcloud)
#   - Access to vochill.revrec dataset

set -e  # Exit on error

echo "=================================================="
echo "VoChill Financial Tables - DDL Execution"
echo "=================================================="
echo ""

# Check if bq command is available
if ! command -v bq &> /dev/null; then
    echo "❌ ERROR: 'bq' command not found"
    echo "   Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Confirm project
echo "Target: vochill.revrec dataset"
echo ""
read -p "Continue with DDL execution? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🚀 Executing DDL..."
echo ""

# Execute the DDL script
bq query \
    --project_id=vochill \
    --use_legacy_sql=false \
    --format=prettyjson \
    < database/create_financial_tables.sql

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ SUCCESS: All financial tables created!"
    echo "=================================================="
    echo ""
    echo "Next steps:"
    echo "  1. Verify tables: ./database/verify_tables.sh"
    echo "  2. View in BigQuery Console: https://console.cloud.google.com/bigquery?project=vochill&ws=!1m5!1m4!4m3!1svochill!2srevrec"
    echo ""
else
    echo ""
    echo "=================================================="
    echo "❌ ERROR: DDL execution failed"
    echo "=================================================="
    echo ""
    echo "Troubleshooting:"
    echo "  - Check your GCP authentication: gcloud auth list"
    echo "  - Verify project access: gcloud projects describe vochill"
    echo "  - Check dataset exists: bq ls --project_id=vochill"
    echo ""
    exit 1
fi
