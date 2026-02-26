# Loan Schedules - Configuration & Usage

This directory contains loan configuration files for generating payment schedules.

## 📁 Directory Purpose

Store YAML configuration files for each loan here. The `add_loan_schedule.py` script reads these files and generates complete payment schedules in BigQuery.

---

## 🚀 Quick Start

### Method 1: Interactive Mode (Easiest)
```bash
cd /Users/dalton/Documents/projects/2026-225-vochill-cashflow
uv run python scripts/add_loan_schedule.py --interactive
```

Follow the prompts to enter loan details. Best for one-off loans.

### Method 2: YAML Config File (Recommended for Multiple Loans)
```bash
# 1. Copy an example file
cp data/loans/example_equipment_loan.yaml data/loans/my_actual_loan.yaml

# 2. Edit with your loan details
nano data/loans/my_actual_loan.yaml

# 3. Generate schedule
uv run python scripts/add_loan_schedule.py --config data/loans/my_actual_loan.yaml
```

---

## 📋 Loan Types Supported

### 1. Equipment Loans
- **Typical Structure**: P&I amortization from start
- **Term**: 3-7 years
- **Collateral**: Equipment purchased
- **Example**: `example_equipment_loan.yaml`

### 2. Balloon Loans
- **Typical Structure**: Low monthly payments + large final payment
- **Term**: 3-10 years
- **Use Case**: Real estate, large equipment
- **Example**: `example_balloon_loan.yaml`

### 3. Term Loans (Unsecured)
- **Typical Structure**: Fixed P&I amortization
- **Term**: 1-5 years
- **Rate**: Higher (no collateral)
- **Example**: `example_unsecured_term_loan.yaml`

### 4. Lines of Credit
- **Structure**: Interest-only, revolving
- **Use**: Working capital, seasonal needs
- **Note**: SBA LOC already configured (see `scripts/generate_debt_schedule.py`)

### 5. Credit Cards
- **Structure**: Minimum payments (% of balance)
- **Use**: Ongoing expenses, rewards
- **Note**: Create as recurring transaction if paying off monthly

---

## 🛠️ YAML Configuration Fields

### Required Fields
```yaml
loan_id: "unique_identifier"           # Auto-generated if blank
loan_name: "Descriptive name"          # What you call it
lender: "Lender name"                  # Who you owe
loan_type: "Equipment Loan"            # Type for categorization

original_amount: 150000.00             # Initial loan amount
current_balance: 125000.00             # Remaining balance (get from statement)

annual_rate: 0.0725                    # Interest rate (7.25% = 0.0725)

payment_day: 15                        # Day of month (1-31)

start_date: "2023-06-15"              # Loan origination (YYYY-MM-DD)
maturity_date: "2028-06-15"           # Final payment date (YYYY-MM-DD)
```

### Payment Structure Options

**Option 1: I/O then P&I**
```yaml
structure_choice: "1"
io_months: 24                          # Interest-only months
amort_months: 36                       # P&I months after I/O
fixed_payment: null
balloon_amount: null
```

**Option 2: P&I from Start**
```yaml
structure_choice: "2"
io_months: 0
amort_months: 60                       # Total months
fixed_payment: null
balloon_amount: null
```

**Option 3: Fixed Payment**
```yaml
structure_choice: "3"
io_months: 0
amort_months: 0
fixed_payment: 2500.00                # Fixed monthly payment
balloon_amount: null
```

**Option 4: Balloon Payment**
```yaml
structure_choice: "4"
io_months: 0
amort_months: 0
fixed_payment: 1500.00                # Monthly before balloon
balloon_amount: 200000.00             # Final balloon amount
```

---

## 📊 What Gets Generated

For each loan, the script generates a complete payment schedule with:

- **Payment dates**: Based on `payment_day` (handles month-end correctly)
- **Payment amounts**: Principal + Interest for each month
- **Balance tracking**: Beginning/ending principal balance
- **Payment types**: "Interest Only", "Principal & Interest", "Balloon Payment"
- **Paid vs Forecast**: Marks past payments as paid, future as forecast

All data inserted into: `vochill.revrec.debt_schedule`

---

## 🔍 Verify After Loading

```sql
-- View all payments for a specific loan
SELECT
  payment_date,
  payment_type,
  payment_amount,
  principal_amount,
  interest_amount,
  ending_principal
FROM `vochill.revrec.debt_schedule`
WHERE loan_id = 'your_loan_id'
ORDER BY payment_date;

-- Summary of all active loans
SELECT
  loan_name,
  lender,
  COUNT(*) as total_payments,
  SUM(payment_amount) as total_payments_amount,
  MAX(payment_date) as final_payment_date
FROM `vochill.revrec.debt_schedule`
WHERE is_paid = FALSE
GROUP BY loan_name, lender
ORDER BY loan_name;
```

---

## 📝 Step-by-Step: Adding Your First Loan

### Example: Equipment Loan

1. **Gather loan documents**:
   - Most recent loan statement
   - Original loan agreement
   - Payoff statement (if available)

2. **Extract key info**:
   - Current balance: $125,432.18
   - Original amount: $150,000.00
   - Interest rate: 7.25%
   - Monthly payment: $2,987.54
   - Payment date: 15th of month
   - Loan started: June 15, 2023
   - Loan ends: June 15, 2028

3. **Create config file**:
```bash
cp data/loans/example_equipment_loan.yaml data/loans/equipment_reflex_2023.yaml
nano data/loans/equipment_reflex_2023.yaml
```

4. **Edit the file**:
```yaml
loan_id: "equipment_reflex_2023"
loan_name: "Equipment Loan - Reflex Medical Equipment"
lender: "Wells Fargo Equipment Finance"
loan_type: "Equipment Loan"

original_amount: 150000.00
current_balance: 125432.18  # FROM STATEMENT

annual_rate: 0.0725  # 7.25%

payment_day: 15

start_date: "2023-06-15"
maturity_date: "2028-06-15"

structure_choice: "2"  # P&I from start
io_months: 0
amort_months: 60
fixed_payment: null
balloon_amount: null
```

5. **Generate schedule**:
```bash
uv run python scripts/add_loan_schedule.py --config data/loans/equipment_reflex_2023.yaml
```

6. **Review preview** → Confirm → Done!

---

## ⚠️ Important Notes

### Current Balance is Critical
- Always use the **current balance** from your most recent statement
- Don't use the original loan amount (unless brand new loan)
- Get a payoff statement if unsure

### Payment Day Handling
- Script handles months without day 30/31 automatically
- Uses last day of month if specified day doesn't exist
- Example: Payment day 31 in February → Feb 28

### Interest Rate Format
- Use decimal format: 7.25% = 0.0725
- Don't multiply by 100

### Past vs Future Payments
- Payments before today: `is_paid = TRUE`
- Payments today or later: `is_forecast = TRUE`
- This affects cash flow forecasting

---

## 🗂️ Organizing Multiple Loans

### Naming Convention
```
{loan_type}_{lender}_{year}.yaml

Examples:
- equipment_wells_fargo_2023.yaml
- balloon_texas_regional_2024.yaml
- unsecured_bluevine_2024.yaml
- loc_frost_bank_2024.yaml
```

### Batch Loading
```bash
# Load all loan configs at once
for file in data/loans/*.yaml; do
  if [[ $file != *"example"* ]]; then
    echo "Loading $file..."
    uv run python scripts/add_loan_schedule.py --config "$file"
  fi
done
```

---

## 🆘 Troubleshooting

**Error: "Loan already exists"**
- Delete existing schedule first:
```sql
DELETE FROM `vochill.revrec.debt_schedule`
WHERE loan_id = 'your_loan_id';
```

**Monthly payment doesn't match statement**
- Slight differences ($1-5) are normal due to:
  - Different day-count conventions
  - Rounding differences
  - Fees not included in calculation
- If more than $10 off, verify loan terms

**Balloon payment amount wrong**
- Verify balloon amount from loan agreement
- Some loans amortize over longer period than actual term
- Example: 5-year balloon with 20-year amortization schedule

---

## 📚 Additional Resources

- **Main script**: `scripts/add_loan_schedule.py`
- **SBA loan example**: `scripts/generate_debt_schedule.py`
- **Data requirements doc**: `docs/DATA_REQUIREMENTS.md`

---

**Last Updated**: 2026-02-25
**Maintained By**: Dalton (VoChill CFO)
