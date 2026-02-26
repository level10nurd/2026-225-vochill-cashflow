# Questions & Answers - VoChill Cash Flow Model

**Date**: 2026-02-25

---

## 1. Loans - Multiple Debt Types

### ❓ Question
> "We have more than just the SBA loan. We have equipment loans, balloon loans, and other unsecured debt. Need functionality to add more."

### ✅ Answer

**NEW: Universal Loan Scheduler Created**

I've built a universal loan payment schedule generator that handles ALL loan types:
- ✅ Equipment loans
- ✅ Balloon loans
- ✅ Unsecured term loans
- ✅ Lines of credit
- ✅ Credit cards (minimum payments)

**Two Ways to Add Loans:**

**Option 1: Interactive Mode**
```bash
uv run python scripts/add_loan_schedule.py --interactive
```
Follow prompts to enter loan details. Best for one-off loans.

**Option 2: YAML Config Files (Recommended)**
```bash
# 1. Copy example template
cp data/loans/example_equipment_loan.yaml data/loans/my_loan.yaml

# 2. Edit with your loan details
nano data/loans/my_loan.yaml

# 3. Generate schedule
uv run python scripts/add_loan_schedule.py --config data/loans/my_loan.yaml
```

**Example configs provided**:
- `data/loans/example_equipment_loan.yaml`
- `data/loans/example_balloon_loan.yaml`
- `data/loans/example_unsecured_term_loan.yaml`

**Full documentation**: `data/loans/README.md`

---

## 2. What Does `etl_invoices_to_cash.py` Do?

### ❓ Question
> "What does uv run python scripts/etl_invoices_to_cash.py do? Where is payment data coming from? Is it actual payments or calculated based on due date?"

### ✅ Answer

**What It Does:**
- Reads from your EXISTING `vochill.revrec.invoices` table (already in BigQuery)
- Joins with `vochill.revrec.vendors` table to get payment terms
- **CALCULATES** projected cash dates (not actual payments)
- Inserts into `cash_transactions` table

**Payment Timing Logic:**
```
cash_date = invoice_date + vendor_payment_days

Examples:
- Invoice: Jan 15, Terms: Net 30 → Cash Date: Feb 14
- Invoice: Mar 1, Terms: Net 15 → Cash Date: Mar 16
- Invoice: Apr 10, Terms: Net 60 → Cash Date: Jun 9
```

**Key Points:**
1. **CALCULATED, not actual** - Uses due dates based on terms, not when you actually paid
2. **Source data** - The `invoices` and `vendors` tables were already in your BigQuery (from previous data loads)
3. **For forecasting** - This is PROJECTED payment timing for future cash planning

**To Get ACTUAL Payments:**
- Need to load Bill.com payment data (actual payment dates)
- See: `docs/DATA_REQUIREMENTS.md` section on Bill.com integration

---

## 3. Additional Accounting/Finance Data Needed

### ❓ Question
> "What additional accounting/finance data do we need to add? Provide checklist so I can pull data together."

### ✅ Answer

**COMPREHENSIVE CHECKLIST CREATED**

See full document: **`docs/DATA_REQUIREMENTS.md`**

**Summary of Critical Data Needed:**

### 🔴 CRITICAL (Need This Week)
1. **All loan schedules** (equipment, balloon, unsecured)
   - Most recent statements
   - Payoff statements
   - Current balances

2. **Bill.com payment history** (actual payments, 12 months)
   - Payment ID, date, vendor, amount
   - Export: Bill.com → Reports → Payments → CSV

3. **QuickBooks Chart of Accounts**
   - QBO → Reports → Chart of Accounts → Export

4. **Bank statements** (all accounts, 12 months)
   - Checking, savings, credit cards
   - Download as CSV/Excel

### 🟡 IMPORTANT (Do This Month)
5. **QuickBooks General Ledger** (12 months)
   - QBO → Reports → General Ledger → Export

6. **Recurring expenses** (not in Bill.com)
   - Payroll, insurance, subscriptions

7. **Committed future expenses**
   - Equipment orders, contracts, leases

8. **Tax payment schedules**
   - Sales tax, payroll tax, estimated tax

### 🟢 NICE TO HAVE
9. Customer refunds (in `refunds` table, can ETL later)
10. Inventory purchase orders (future cash needs)
11. Credit card transactions (non-invoiced expenses)

**Full details, export instructions, and automation options**: `docs/DATA_REQUIREMENTS.md`

---

## 4. Where Did the $105,137/week Expense Data Come From?

### ❓ Question
> "You mentioned current cashflow shows Weekly Expenses: $105,137/week. How can you possibly know that? We haven't uploaded data. Where is this coming from?"

### ✅ Answer

**You DID have data - it was already in BigQuery before we started!**

**Existing Tables (Already Loaded):**
- `vochill.revrec.invoices` - 167 vendor invoices
- `vochill.revrec.vendors` - Vendor payment terms
- `vochill.revrec.deposits` - ~200 Amazon/Shopify settlements
- Plus: orders, fees, refunds, etc.

**What We Did:**
1. You started this project saying "I have data in BigQuery"
2. We built NEW financial tables (`cash_transactions`, `debt_schedule`, etc.)
3. We wrote ETL scripts to TRANSFORM existing data:
   - `invoices` table → `cash_transactions` (167 invoices = $701,601)
   - `deposits` table → `cash_transactions` (~200 settlements = $1.6M)

**The $105,137/week calculation:**
- Total vendor payments: $701,601
- Date range in data: ~6.7 weeks
- Weekly average: $701,601 ÷ 6.7 weeks ≈ $105,137/week

**We didn't create new data - we restructured what you already had.**

**For more accurate expense forecasting:**
- Load QuickBooks GL (captures ALL expenses, not just vendor invoices)
- Load Bill.com actual payments (precise timing)
- Load payroll data (if not in invoices)

---

## 5. Automate/Integrate Bill.com and QuickBooks → BigQuery

### ❓ Question
> "What is the best way to automate/integrate the flow of this data from Bill.com and QuickBooks Online into BigQuery?"

### ✅ Answer

**Three Options - Pick Based on Your Needs:**

### Option 1: API Integration (Best Long-Term)

**Bill.com API**
- REST API with payment data endpoints
- Build Python script using `requests` library
- Schedule with Google Cloud Functions (daily/weekly)
- Direct insert into BigQuery

**Pros:**
- Free (no additional tools)
- Full control over data
- Real-time or scheduled sync

**Cons:**
- Requires Python development (I can help)
- OAuth setup required
- Maintenance if APIs change

**QuickBooks Online API**
- QBO has REST API (OAuth 2.0)
- Python library: `python-quickbooks`
- Fetch: Chart of Accounts, GL, Invoices, Bills, Payments

**Pros:**
- Free
- Comprehensive data access
- Can query specific date ranges

**Cons:**
- OAuth setup more complex than Bill.com
- Rate limits (500 requests/minute)
- Token refresh handling

### Option 2: Third-Party ETL Tools (Easiest)

**Fivetran** (Recommended)
- Has native Bill.com connector
- Has native QuickBooks Online connector
- Direct sync to BigQuery
- Cost: ~$100-300/month

**Pros:**
- No coding required
- Automatic schema handling
- Handles API changes
- Monitoring/alerting built-in

**Cons:**
- Monthly cost
- Less flexible than custom API

**Alternatives:**
- Stitch Data (similar to Fivetran)
- Airbyte (open source, self-hosted)

### Option 3: Manual Export (Interim/Budget)

**Workflow:**
1. Bill.com → Reports → Payments → Export CSV (monthly)
2. QBO → Reports → General Ledger → Export Excel (monthly)
3. Upload to BigQuery manually
4. Run ETL scripts

**Pros:**
- Free
- Simple
- Full control

**Cons:**
- Manual work every month
- Prone to delays/errors
- Not real-time

---

### Recommended Approach

**Phase 1 (Now - This Month):**
- Manual exports for initial data load
- Get complete historical data in place
- Validate cash flow model accuracy

**Phase 2 (Next Month):**
- Build Bill.com API integration (payments only - most critical)
- Schedule weekly via Cloud Functions
- Manual QBO export monthly (GL less time-sensitive)

**Phase 3 (Month 3+):**
- Build QBO API integration OR subscribe to Fivetran
- Fully automated daily/weekly syncs
- Focus on analysis, not data loading

**I can help build the API integrations if you want to go that route.**

---

### Example Architecture

```
┌─────────────────────────────────────────────────┐
│              DATA SOURCES                       │
├─────────────────────────────────────────────────┤
│  Bill.com         QuickBooks Online   Banks     │
│  (Payments)       (GL, COA, A/P)      (CSVs)    │
└────────┬────────────────┬────────────────┬──────┘
         │                │                │
    API calls        API calls         Manual
    (Cloud Fn)       (Cloud Fn)        upload
         │                │                │
         ▼                ▼                ▼
    ┌────────────────────────────────────────┐
    │      Python ETL Scripts               │
    │      (Cloud Functions, scheduled)      │
    └──────────────────┬─────────────────────┘
                       │
                       │ INSERT INTO
                       │
                       ▼
           ┌─────────────────────────┐
           │  BigQuery               │
           │  vochill.revrec.*       │
           │                         │
           │  - cash_transactions    │
           │  - payments_actual      │
           │  - gl_transactions      │
           │  - debt_schedule        │
           └───────────┬─────────────┘
                       │
                       │ QUERY/ANALYZE
                       │
                       ▼
           ┌─────────────────────────┐
           │  Cash Flow Model        │
           │  Hex / Python Scripts   │
           │  Excel Reports          │
           └─────────────────────────┘
```

---

## 📚 New Documentation Created

In response to your questions, I've created:

1. **`docs/DATA_REQUIREMENTS.md`** - Complete data checklist + integration guide
2. **`scripts/add_loan_schedule.py`** - Universal loan scheduler (any loan type)
3. **`data/loans/README.md`** - How to use loan scheduler
4. **`data/loans/example_*.yaml`** - Example loan configs (equipment, balloon, unsecured)
5. **`docs/QUESTIONS_ANSWERED.md`** - This file

---

## 🎯 Recommended Next Steps

**This Week:**
1. Gather all loan documents (statements, agreements)
2. Use loan scheduler to add all debt to `debt_schedule` table
3. Export Bill.com payment history (12 months)
4. Export QuickBooks Chart of Accounts

**Next Week:**
5. Load Bill.com payments (I'll build ETL script)
6. Load QBO Chart of Accounts
7. Review/refine expense categorization

**Next Month:**
8. Build Bill.com API connector (automate payment sync)
9. Generate first complete 13-week forecast with real data
10. Build Excel report generator

Let me know which items you want to tackle first!

---

**Questions?** Let me know if you need clarification on any of these answers.
