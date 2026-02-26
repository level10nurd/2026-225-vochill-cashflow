# BigQuery DDL Execution Guide

## Quick Start (Recommended)

### Option 1: Command Line (Fastest)

```bash
# Make scripts executable
chmod +x database/execute_ddl.sh database/verify_tables.sh

# Execute DDL
./database/execute_ddl.sh

# Verify tables created
./database/verify_tables.sh
```

---

## Option 2: BigQuery Console (Manual)

### Step 1: Open BigQuery Console
Navigate to: https://console.cloud.google.com/bigquery?project=vochill

### Step 2: Create Tables
Copy and paste the entire contents of `database/create_financial_tables.sql` into the BigQuery query editor and click "Run".

**OR** run table-by-table:

#### Create bank_accounts
```sql
CREATE TABLE IF NOT EXISTS `vochill.revrec.bank_accounts` (
  account_id STRING NOT NULL,
  account_name STRING NOT NULL,
  account_number STRING,
  account_type STRING NOT NULL,
  institution_name STRING NOT NULL,
  institution_routing STRING,
  is_credit_line BOOLEAN DEFAULT FALSE,
  credit_limit FLOAT64,
  interest_rate FLOAT64,
  qb_account_name STRING,
  qb_account_number STRING,
  is_active BOOLEAN DEFAULT TRUE,
  opened_date DATE,
  closed_date DATE,
  notes STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

#### Create other tables
Continue with remaining tables from `create_financial_tables.sql`...

### Step 3: Verify
Run this query to list all new tables:
```sql
SELECT table_name, table_type
FROM `vochill.revrec.INFORMATION_SCHEMA.TABLES`
WHERE table_name IN (
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
  'v_daily_cash_flow',
  'v_weekly_cash_flow',
  'v_cash_position'
)
ORDER BY table_name;
```

Expected: 13 tables + 3 views = 16 rows

---

## Option 3: Python Script

```python
from src.data import BigQueryConnector

# Read DDL file
with open('database/create_financial_tables.sql', 'r') as f:
    ddl = f.read()

# Split into individual statements
statements = ddl.split(';')

# Execute each statement
bq = BigQueryConnector()
for i, stmt in enumerate(statements):
    stmt = stmt.strip()
    if stmt and not stmt.startswith('--'):
        print(f"Executing statement {i+1}...")
        try:
            bq.query(stmt)
            print(f"✅ Success")
        except Exception as e:
            print(f"❌ Error: {e}")
```

---

## Troubleshooting

### "Permission denied"
```bash
# Check authentication
gcloud auth list

# Re-authenticate if needed
gcloud auth login
```

### "Dataset not found"
```bash
# Verify dataset exists
bq ls --project_id=vochill

# Create dataset if needed
bq mk --project_id=vochill --location=US revrec
```

### "Table already exists"
The DDL uses `CREATE TABLE IF NOT EXISTS`, so it's safe to re-run. Existing tables won't be modified.

To drop and recreate:
```sql
DROP TABLE IF EXISTS `vochill.revrec.bank_accounts`;
-- Then re-run CREATE TABLE statement
```

### Partial execution
If script fails partway through, you can:
1. Check which tables were created: `./database/verify_tables.sh`
2. Re-run the full script (safe due to `IF NOT EXISTS`)
3. Or manually create just the missing tables

---

## Post-Execution Checklist

- [ ] All 13 tables created
- [ ] All 3 views created
- [ ] Seed data loaded (payment_terms, scenarios)
- [ ] Can query tables successfully

### Quick Test Query
```sql
-- Should return 7 rows
SELECT term_name, cycle_type, lag_days
FROM `vochill.revrec.payment_terms`
ORDER BY term_name;

-- Should return 3 rows
SELECT scenario_name, scenario_type, revenue_growth_rate
FROM `vochill.revrec.scenarios`
ORDER BY scenario_id;
```

---

## Next Steps After Execution

1. **Populate bank_accounts**
   ```bash
   python notebooks/populate_bank_accounts.py
   ```

2. **Load chart_of_accounts**
   ```bash
   python notebooks/populate_chart_of_accounts.py
   ```

3. **Test BigQuery connection**
   ```bash
   python notebooks/bigquery_example.py
   ```

4. **Begin ETL**
   - Transform deposits → cash_transactions
   - Transform invoices → cash_transactions
   - Load cash_balances from bank data

---

## Helpful Commands

```bash
# List all tables in dataset
bq ls --project_id=vochill revrec

# Describe a table schema
bq show --project_id=vochill revrec.cash_transactions

# Get table row count
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`vochill.revrec.cash_transactions\`"

# Delete a table (if needed)
bq rm --project_id=vochill revrec.table_name

# Delete all financial tables (CAREFUL!)
# for table in bank_accounts chart_of_accounts ...; do
#   bq rm --project_id=vochill revrec.$table
# done
```

---

## BigQuery Console Links

- **Dataset**: https://console.cloud.google.com/bigquery?project=vochill&ws=!1m5!1m4!4m3!1svochill!2srevrec
- **Query Editor**: https://console.cloud.google.com/bigquery?project=vochill
- **Table Browser**: https://console.cloud.google.com/bigquery?project=vochill&page=dataset&d=revrec
