# Data Requirements & Integration Guide

## Questions Answered

### 1. What does `etl_invoices_to_cash.py` do?

**Answer**: This script reads from your EXISTING `vochill.revrec.invoices` table in BigQuery (which you already had before we started) and transforms it into cash flow transactions.

**Key Points**:
- **Source**: `vochill.revrec.invoices` table (your existing invoice data)
- **Payment Timing**: CALCULATED, not actual payments
- **Logic**: `cash_date = invoice_date + vendor_payment_days`
  - Joins with `vendors` table to get payment terms (Net 30, Net 15, Net 60, etc.)
  - If no terms found, defaults to Net 30
  - Example: Invoice dated Jan 15 with Net 30 terms → cash_date = Feb 14

**This is NOT actual payment data** - it's PROJECTED payment timing based on when invoices are DUE. For true cash flow forecasting, you'll eventually want to load ACTUAL payment dates from Bill.com.

---

### 2. Where is the $105,137/week expense data coming from?

**Answer**: From your EXISTING BigQuery tables that were already loaded:

- **`vochill.revrec.invoices`** table: 167 invoices totaling $701,601
- **`vochill.revrec.deposits`** table: ~200 settlements totaling $1.6M

These tables existed in your BigQuery project before we started building the cash flow model. The ETL scripts transformed them into `cash_transactions`. We didn't upload new data - we restructured what was already there.

---

### 3. Multiple Loans - How to Add Equipment Loans, Balloon Loans, Unsecured Debt?

**Current State**: Only SBA loan is in `debt_schedule` table (84 payments).

**Solution**: Create a universal loan scheduler script.

---

## 📋 Complete Data Requirements Checklist

To build a comprehensive cash flow model, gather the following data:

### ✅ Already Loaded
- [x] Vendor invoices (from `invoices` table)
- [x] Ecommerce deposits (from `deposits` table)
- [x] SBA loan schedule
- [x] Bank account details (7 accounts)
- [x] Recurring transactions (SBA interest, Shopify subscription)

---

### 🔴 CRITICAL - Need to Load

#### **1. ACTUAL Payment Data (Bill.com)**
**Why**: Current model uses CALCULATED payment dates (invoice_date + Net 30). Real cash flow requires ACTUAL payment dates.

**Required Fields**:
- Payment ID
- Vendor name
- Invoice number (to link to invoices table)
- Payment date (actual date money left bank)
- Payment amount
- Payment method (ACH, check, card)
- Bank account paid from

**How to Get**:
- Export from Bill.com: Payments → Export to CSV
- Date range: Last 12 months minimum
- Include: Paid invoices only (exclude pending/scheduled)

---

#### **2. ALL Debt Schedules**

**Equipment Loans**:
- Lender name
- Loan amount
- Interest rate
- Monthly payment
- Start date / maturity date
- Current balance
- Collateral description

**Balloon Loans**:
- Same as equipment loans
- Balloon payment date
- Balloon payment amount

**Unsecured Debt**:
- Lender name
- Original amount
- Interest rate
- Monthly payment
- Start/end dates
- Current balance

**Credit Cards** (if carrying balances):
- Card name (AMEX Gold, Chase Inc, etc.)
- Current balance
- Minimum payment amount
- APR
- Due date (day of month)

**How to Get**:
- Most recent loan statements for each debt
- Current payoff statements (call lenders if needed)
- Payment schedules if available

---

#### **3. QuickBooks Online - Chart of Accounts & GL**

**Chart of Accounts**:
- Account number
- Account name
- Account type (Asset, Liability, Income, Expense)
- Account subtype
- Current balance

**General Ledger Export** (Last 12 months):
- Transaction date
- Account number & name
- Debit/Credit amounts
- Description/memo
- Vendor/Customer
- Transaction type

**Why**: Maps GL accounts to cash flow categories for precise expense categorization beyond just "vendor invoices."

**How to Get**:
- QBO → Reports → Chart of Accounts → Export
- QBO → Reports → General Ledger → Last 12 months → Export

---

#### **4. Bank Statements (All Accounts)**

**For Each Account** (Checking, Money Market, Credit Cards):
- Statement period: Last 12 months
- All transactions with:
  - Date
  - Description
  - Amount (debit/credit)
  - Balance
  - Transaction type

**Why**:
- Validate invoice/deposit data completeness
- Catch non-invoiced expenses (payroll, taxes, owner draws)
- Identify unrecorded revenue
- Calculate accurate starting cash balance

**Accounts Needed**:
1. Frost Bank Checking
2. Frost Bank Money Market
3. Frost Bank SBA LOC
4. AMEX Gold Card
5. Chase Inc Card
6. Shopify Card (if separate)
7. Southwest Card

**How to Get**:
- Download from online banking as CSV/Excel
- Or request from bank (may charge fee for old statements)

---

#### **5. Payroll Data**

**If payroll is NOT in Bill.com invoices**, need:
- Payroll provider (Gusto, ADP, Paychex, etc.)
- Employee gross pay by pay period
- Employer taxes by pay period
- Pay frequency (weekly, bi-weekly, semi-monthly, monthly)
- Pay dates for last 12 months

**Why**: Payroll is often the largest OpEx and has precise timing.

**How to Get**:
- Payroll provider → Reports → Payroll Summary by Period
- Last 12 months

---

#### **6. Committed Future Expenses**

**Equipment Orders / CapEx**:
- Description
- Vendor
- Purchase price
- Expected payment date
- Terms (50% deposit, Net 30, etc.)

**Contracts / Retainers**:
- Service description
- Monthly/annual amount
- Payment schedule
- Contract start/end dates
- Auto-renewal?

**Leases** (if not already captured):
- Property/equipment description
- Monthly payment
- Lease start/end dates
- Renewal terms

**Insurance Premiums**:
- Policy types (liability, property, health, etc.)
- Annual premium
- Payment schedule (monthly, quarterly, annual)
- Next payment date

**Why**: Forward-looking forecast needs known future commitments.

**How to Get**:
- Review contracts folder
- List all active vendor agreements
- Insurance policy summaries

---

#### **7. Sales Tax & Other Tax Obligations**

**Sales Tax**:
- States collected in
- Filing frequency (monthly, quarterly)
- Typical amount due
- Due dates

**Federal Payroll Tax**:
- FICA withholding deposit schedule
- Quarterly 941 payment amounts/dates

**State Payroll Tax**:
- State withholding deposit schedule
- UI tax payments

**Why**: Tax payments are large, irregular, and non-negotiable. Missing them in forecast causes major surprises.

**How to Get**:
- Review QBO sales tax reports
- Review payroll tax filing history
- CPA records if outsourced

---

#### **8. Owner Distributions / Draws**

**If applicable**:
- Historical owner draw amounts by date
- Expected future distribution schedule
- Tax payment estimates (if S-corp/partnership)

**Why**: Cash leaving business for owners isn't captured in invoices/expenses.

**How to Get**:
- Review bank statements for owner draws
- QBO equity account transactions

---

### 🟡 NICE TO HAVE - Improve Accuracy

#### **9. Customer Refunds**
- Currently available in `vochill.revrec.refunds` table
- Can ETL similar to deposits
- Impact: Usually small for most businesses

#### **10. Inventory Purchase Orders**
- Upcoming inventory orders not yet invoiced
- Expected delivery/payment dates
- Critical for ecommerce cash planning

#### **11. Credit Card Transactions** (Non-invoiced)
- Small purchases made directly on credit cards
- Subscriptions, software, misc expenses
- Not captured in Bill.com invoices

#### **12. Intercompany Transfers**
- Money moved between bank accounts
- Need to exclude from cash flow (not income/expense)

---

## 🤖 Automation & Integration Options

### How to Get Data from Bill.com → BigQuery

**Option 1: Bill.com API (Recommended)**
- Bill.com has REST API with payment data
- Build Python script using `requests` library
- Schedule with Cloud Functions or Cloud Run (daily/weekly)
- Direct insert into BigQuery

**Option 2: Manual Export (Interim)**
- Bill.com → Reports → Payments → Export CSV
- Upload to BigQuery manually
- Repeat monthly until automation built

**Option 3: Third-Party ETL Tools**
- Fivetran (has Bill.com connector) → BigQuery
- Stitch Data
- Airbyte (open source)
- Cost: ~$100-500/month

---

### How to Get Data from QuickBooks Online → BigQuery

**Option 1: QBO API (Recommended)**
- QuickBooks Online API (OAuth 2.0)
- Python library: `python-quickbooks`
- Fetch: Chart of Accounts, GL Transactions, Invoices, Bills, Payments
- Schedule with Cloud Functions

**Option 2: QuickBooks BigQuery Connector**
- Google has native QBO → BigQuery integration
- Google Cloud Console → Data Transfer Service → QuickBooks Online
- Cost: Free (part of BigQuery)
- Limitation: May not have all reports you need

**Option 3: Manual Export (Interim)**
- QBO → Reports → Export to Excel
- Upload to BigQuery manually
- Repeat monthly

**Option 4: Third-Party ETL**
- Fivetran (has QBO connector)
- Stitch Data
- More robust than manual, less work than custom API

---

### Recommended Automation Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  DATA SOURCES                           │
├─────────────────────────────────────────────────────────┤
│  Bill.com          QuickBooks Online      Bank CSVs     │
│  (Payments)        (GL, COA, Invoices)    (Statements)  │
└──────────┬─────────────────┬──────────────────┬─────────┘
           │                 │                  │
           │   API calls     │   API calls      │  Manual
           │   (scheduled)   │   (scheduled)    │  upload
           │                 │                  │
           ▼                 ▼                  ▼
      ┌────────────────────────────────────────────┐
      │         Cloud Function / Cloud Run         │
      │      (Python ETL scripts, scheduled)       │
      └───────────────────┬────────────────────────┘
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
              │  - bank_balances        │
              └───────────┬─────────────┘
                          │
                          │ QUERY
                          │
                          ▼
              ┌─────────────────────────┐
              │  Hex Notebooks          │
              │  (Analysis, Reporting)  │
              └─────────────────────────┘
```

---

## 🎯 Priority Order

**Phase 1 (Do This Week)**:
1. ✅ Get all loan schedules (equipment, balloon, unsecured)
2. ✅ Export Bill.com payment history (12 months)
3. ✅ Export QBO Chart of Accounts
4. ✅ Download bank statements (checking, credit cards) - last 12 months

**Phase 2 (Do This Month)**:
5. Export QBO General Ledger (12 months)
6. List all recurring expenses not in Bill.com
7. List all committed future expenses (contracts, orders)
8. Document tax payment schedules

**Phase 3 (Do Next Month)**:
9. Build Bill.com API connector
10. Build QBO API connector
11. Automate bank statement import

---

## 📝 Next Steps

1. Review this checklist
2. Start gathering Phase 1 data
3. Once you have loan schedules, I'll build a universal debt scheduler
4. Once you have Bill.com payments, I'll build ETL for actual payments
5. Once you have QBO GL, I'll refine expense categorization

Let me know which data sources you want to tackle first!

---

**Date**: 2026-02-25
**Status**: Data requirements documented
**Owner**: Dalton (data gathering), Claude (ETL development)
