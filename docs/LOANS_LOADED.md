# Loans Successfully Added to Debt Schedule

**Date**: 2026-02-25
**Status**: ✅ Complete

---

## 📊 Summary

Successfully loaded **2 loans** with **145 total payments** into `vochill.revrec.debt_schedule`:

| Loan | Lender | Payments | Total Amount | Principal | Interest |
|------|--------|----------|--------------|-----------|----------|
| SBA Loan | Frost Bank | 85 | $532,362 | $350,000 | $182,363 |
| Stearns Equipment Loan | Stearns Bank | 60 | $41,101 | $31,040 | $10,061 |
| **TOTAL** | | **145** | **$573,463** | **$381,040** | **$192,423** |

---

## 1. SBA Loan (Existing)

- **Loan Amount**: $500,000 revolving LOC
- **Current Balance**: $350,000 (drawn amount)
- **Lender**: Frost Bank
- **Rate**: Prime + 2.25% (10.75% initially)
- **Structure**:
  - 24 months Interest-Only (May 2024 - May 2026)
  - 60 months P&I amortization (June 2026 - May 2031)
- **Monthly Payment**:
  - $3,135.42/month (I/O period through May 2026)
  - ~$7,800/month (P&I period starting June 2026)
- **Payment Day**: 30th of month
- **First Payment**: May 30, 2024
- **Final Payment**: May 30, 2031
- **Status**: Already in system (loaded previously)

---

## 2. Stearns Bank Equipment Loan (NEW - Just Added)

- **Agreement #**: 3167670-002
- **Loan Amount**: $31,040.00
- **Lender**: Stearns Bank National Association (via Priority Capital)
- **Rate**: 11.65% APR (back-calculated equivalent)
- **Structure**: 60-month amortization (P&I from start)
- **Monthly Payment**: $685.02
- **Payment Day**: 6th of month
- **First Payment**: March 6, 2025
- **Final Payment**: February 6, 2030
- **Equipment Financed**:
  - 4-Cavity Blow Mold
  - Fill Stations Fixtures
  - Location: 2025 Ragu Drive, Owensboro, KY 42303
- **Personal Guarantors**: Randall Eugene Pawlik & Lisa Michelle Pawlik
- **Early Buyout**: Available with discount (Net Investment + 1-5% based on months remaining)
- **Auto-Pay**: ACH from Frost Bank account (Staychill #592023512)

---

## 📅 Upcoming Debt Payments (Next 90 Days)

| Date | Loan | Type | Payment | Principal | Interest | Balance After |
|------|------|------|---------|-----------|----------|---------------|
| Feb 28, 2026 | SBA Loan | I/O | $3,135.42 | $0.00 | $3,135.42 | $350,000 |
| Mar 6, 2026 | Stearns Equipment | P&I | $685.02 | $430.79 | $254.22 | $25,752 |
| Mar 30, 2026 | SBA Loan | I/O | $3,135.42 | $0.00 | $3,135.42 | $350,000 |
| Apr 6, 2026 | Stearns Equipment | P&I | $685.02 | $434.97 | $250.04 | $25,317 |
| Apr 30, 2026 | SBA Loan | I/O | $3,135.42 | $0.00 | $3,135.42 | $350,000 |
| May 6, 2026 | Stearns Equipment | P&I | $685.02 | $439.20 | $245.82 | $24,878 |

**Monthly Debt Service (Current)**: ~$3,820/month ($3,135 SBA + $685 Stearns)

**NOTE**: SBA payments increase to ~$7,800/month starting June 2026 when P&I period begins.

---

## 📁 Loan Documents Processed

### ✅ Successfully Loaded:
1. **Stearns Bank Loan Docs - EXECUTED.pdf** (1.8 MB)
   - Equipment Finance Agreement
   - Agreement #3167670-002
   - Signed: March 11, 2025
   - Effective: March 6, 2025

2. **Priority Capital Term Sheet - EXECUTED.pdf** (574 KB)
   - Initial approval/term sheet
   - Funded through Stearns Bank
   - Signed: March 13, 2025

3. **SBA Promissory Note Vochill.pdf** (10.5 MB)
   - Already loaded in previous session
   - $500k revolving LOC

### ❌ Could Not Process:
- **VoChill Promissory Note - Robert and Peggy Pawlik.pdf** (0 bytes - empty file)

---

## 🗂️ Configuration Files Created

- `/data/loans/stearns_bank_equipment_2025.yaml` - Loan configuration used to generate payment schedule

---

## ✅ Verification Queries

### View All Debt by Loan
```sql
SELECT
  loan_name,
  lender,
  COUNT(*) as payment_count,
  MIN(payment_date) as first_payment,
  MAX(payment_date) as last_payment,
  SUM(payment_amount) as total_payments,
  SUM(principal_amount) as total_principal,
  SUM(interest_amount) as total_interest
FROM `vochill.revrec.debt_schedule`
GROUP BY loan_name, lender
ORDER BY loan_name;
```

### View Upcoming Payments (Next 13 Weeks)
```sql
SELECT
  payment_date,
  loan_name,
  payment_type,
  ROUND(payment_amount, 2) as payment,
  ROUND(principal_amount, 2) as principal,
  ROUND(interest_amount, 2) as interest,
  ROUND(ending_principal, 2) as remaining_balance
FROM `vochill.revrec.debt_schedule`
WHERE is_paid = FALSE
  AND payment_date >= CURRENT_DATE()
  AND payment_date <= DATE_ADD(CURRENT_DATE(), INTERVAL 13 WEEK)
ORDER BY payment_date;
```

### View Stearns Loan Payment Schedule
```sql
SELECT
  payment_date,
  payment_number,
  ROUND(payment_amount, 2) as payment,
  ROUND(principal_amount, 2) as principal,
  ROUND(interest_amount, 2) as interest,
  ROUND(ending_principal, 2) as balance
FROM `vochill.revrec.debt_schedule`
WHERE loan_id = 'stearns_equipment_2025'
ORDER BY payment_date
LIMIT 20;
```

---

## 🎯 Next Steps

### Recommended Actions:

1. **Verify Monthly Cash Flow Impact**:
   - Current monthly debt service: ~$3,820/month
   - Starting June 2026: ~$8,485/month (when SBA I/O period ends)
   - This is an **increase of $4,665/month** in 4 months!

2. **Run Updated Forecast**:
```bash
uv run python scripts/build_forecast.py --weekly-revenue 75000 --preview
```
This will now include both loan payments in the 13-week forecast.

3. **Review Cash Position**:
   - With $8,485/month in debt service starting June 2026
   - Need to ensure revenue covers: OpEx (~$420k/month) + Debt Service ($8.5k/month)
   - Break-even revenue: ~$428.5k/month = ~$98.8k/week

4. **Add Any Other Loans**:
   - Do you have other equipment loans, credit cards with balances, or term loans?
   - If so, create YAML configs and load them using `scripts/add_loan_schedule.py`

5. **Robert & Peggy Pawlik Promissory Note**:
   - The PDF file is empty (0 bytes)
   - If this is an active loan, please re-upload the document
   - Or provide loan details (amount, rate, term, payment) and I can create a config

---

## 📝 Notes

- **Interest Rate Calculation**: The Stearns Bank equipment loan is a fixed-payment finance agreement. The 11.65% APR was back-calculated to match the actual monthly payment of $684.99 (contract shows $684.99, our calculation shows $685.02 - $0.03 rounding difference).

- **Early Payoff**: The Stearns loan has an early buyout discount schedule:
  - 1-12 months remaining: Net Investment + 5%
  - 13-24 months: Net Investment + 4%
  - 25-36 months: Net Investment + 3%
  - 37-48 months: Net Investment + 2%
  - 49-60 months: Net Investment + 1%

- **ACH Auto-Pay**: Both loans have ACH auto-pay set up from Frost Bank checking account.

- **Personal Guarantees**: Both Randy and Lisa have personally guaranteed the Stearns loan.

---

**Last Updated**: 2026-02-25
**Total Debt Payments Tracked**: 145 payments through May 2031
**Total Debt Service Obligation**: $573,463 (principal + interest)
