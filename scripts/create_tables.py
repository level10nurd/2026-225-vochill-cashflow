"""
Create BigQuery financial tables using Python

This script reads the DDL file and executes each CREATE statement
using the BigQueryConnector.

Usage:
    python scripts/create_tables.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import BigQueryConnector


def parse_ddl_statements(ddl_file_path):
    """Parse DDL file into individual CREATE statements"""
    with open(ddl_file_path, 'r') as f:
        content = f.read()

    # Split on semicolons to get statements
    raw_statements = content.split(';')

    statements = []
    for stmt in raw_statements:
        # Clean up the statement
        stmt = stmt.strip()

        # Skip empty statements
        if not stmt:
            continue

        # Skip pure comment blocks
        lines = [line.strip() for line in stmt.split('\n') if line.strip()]
        non_comment_lines = [line for line in lines if not line.startswith('--')]

        if not non_comment_lines:
            continue

        # Keep statements that have actual SQL
        if any(keyword in stmt.upper() for keyword in ['CREATE', 'INSERT', 'DROP', 'ALTER']):
            statements.append(stmt)

    return statements


def main():
    print("=" * 60)
    print("VoChill Financial Tables - Creation Script")
    print("=" * 60)
    print()

    # Path to DDL file
    ddl_file = Path(__file__).parent.parent / 'database' / 'create_financial_tables.sql'

    if not ddl_file.exists():
        print(f"❌ ERROR: DDL file not found at {ddl_file}")
        sys.exit(1)

    print(f"Reading DDL from: {ddl_file.name}")
    print()

    # Parse statements
    statements = parse_ddl_statements(ddl_file)
    print(f"Found {len(statements)} DDL statements to execute")
    print()

    # Confirm
    response = input("Continue with table creation? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)

    print()
    print("Connecting to BigQuery...")

    try:
        bq = BigQueryConnector()
        print("✅ Connected to BigQuery")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to BigQuery")
        print(f"   {str(e)}")
        print()
        print("Make sure:")
        print("  1. GCP_CREDENTIALS_PATH is set in .env")
        print("  2. Service account has BigQuery permissions")
        sys.exit(1)

    # Execute each statement
    print("=" * 60)
    print("Executing DDL Statements...")
    print("=" * 60)
    print()

    success_count = 0
    error_count = 0
    errors = []

    for i, stmt in enumerate(statements, 1):
        # Extract table/view name for display
        if 'CREATE TABLE' in stmt:
            name = stmt.split('`')[1].split('.')[-1] if '`' in stmt else f"statement_{i}"
            type_str = "TABLE"
        elif 'CREATE VIEW' in stmt or 'CREATE OR REPLACE VIEW' in stmt:
            name = stmt.split('`')[1].split('.')[-1] if '`' in stmt else f"statement_{i}"
            type_str = "VIEW"
        elif 'INSERT INTO' in stmt:
            name = stmt.split('`')[1].split('.')[-1] if '`' in stmt else "seed_data"
            type_str = "INSERT"
        else:
            name = f"statement_{i}"
            type_str = "SQL"

        print(f"[{i}/{len(statements)}] Creating {type_str}: {name}...", end=' ')

        try:
            bq.query(stmt)
            print("✅")
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            # Check if it's "already exists" error (which is OK)
            if 'already exists' in error_msg.lower():
                print("⚠️  (already exists)")
                success_count += 1
            else:
                print(f"❌ ERROR")
                print(f"     {error_msg[:100]}")
                error_count += 1
                errors.append({
                    'name': name,
                    'error': error_msg
                })

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Success: {success_count}/{len(statements)}")
    print(f"❌ Errors:  {error_count}/{len(statements)}")
    print()

    if error_count > 0:
        print("Errors encountered:")
        for err in errors:
            print(f"  • {err['name']}: {err['error'][:80]}")
        print()
        print("⚠️  Some tables may not have been created.")
        print("   Review errors above and check BigQuery console.")
    else:
        print("✅ SUCCESS: All tables and views created!")
        print()
        print("Next steps:")
        print("  1. Verify tables: python scripts/verify_tables.py")
        print("  2. View in BigQuery Console:")
        print("     https://console.cloud.google.com/bigquery?project=vochill&ws=!1m5!1m4!4m3!1svochill!2srevrec")
        print()
        print("  3. Populate master data:")
        print("     - python scripts/populate_bank_accounts.py")
        print("     - python scripts/populate_chart_of_accounts.py")
        print()


if __name__ == "__main__":
    main()
