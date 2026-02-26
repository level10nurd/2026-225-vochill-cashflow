# VoChill Cash Flow Model - Architecture

## Overview

VoChill's cash flow forecasting system is built on a **BigQuery-first architecture**, leveraging pre-transformed ecommerce and operational data already in the `vochill.revrec` dataset.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Amazon   │  │ Shopify  │  │ Vendors  │  │ QB/Xero  │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘   │
└────────┼─────────────┼─────────────┼─────────────┼─────────┘
         │             │             │             │
         └──────┬──────┴──────┬──────┴──────┬──────┘
                │             │             │
         ┌──────▼─────────────▼─────────────▼──────┐
         │      GOOGLE CLOUD BIGQUERY               │
         │      Project: vochill                    │
         │      Dataset: revrec                     │
         │                                          │
         │  Tables:                                 │
         │  • deposits (Amazon/Shopify payouts)     │
         │  • orders (order-level detail)           │
         │  • fees (platform fees)                  │
         │  • refunds (returns)                     │
         │  • item (SKU master)                     │
         │  • vendors (payment terms)               │
         │  • po / po_line_item (commitments)       │
         │  • invoices / invoiceItems (AP)          │
         │  • forecast (existing SKU forecasts)     │
         └──────────────┬───────────────────────────┘
                        │
         ┌──────────────▼───────────────────────────┐
         │   CASH FLOW FORECAST ENGINE (Python)     │
         │                                          │
         │  Components:                             │
         │  • BigQuery Connector                    │
         │  • Cash Flow Aggregator                  │
         │  • Payment Timing Engine                 │
         │  • Forecast Calculator                   │
         │  • Scenario Analyzer                     │
         └──────────────┬───────────────────────────┘
                        │
         ┌──────────────▼───────────────────────────┐
         │         OUTPUT GENERATORS                │
         │                                          │
         │  • Excel Workbook (formatted reports)    │
         │  • Hex Notebook (interactive analysis)   │
         │  • JSON/CSV (data exports)               │
         └──────────────────────────────────────────┘
```

## Directory Structure

```
vochill-cashflow/
├── data/
│   ├── config/                    # Configuration files
│   │   ├── cash_flow_categories.yaml  # CoA → CF category mapping
│   │   └── payment_timing.yaml        # Payment timing rules
│   ├── raw/                       # Original data exports (if needed)
│   └── processed/                 # Intermediate processed data
│
├── src/
│   ├── __init__.py
│   ├── config.py                  # Configuration management
│   │
│   ├── data/                      # Data access layer
│   │   ├── __init__.py
│   │   └── bigquery_connector.py  # BigQuery client & queries
│   │
│   ├── forecast/                  # Forecasting engine
│   │   ├── __init__.py
│   │   ├── cash_flow_aggregator.py  # Aggregate BQ → CF categories
│   │   ├── payment_timing.py        # Apply payment timing rules
│   │   ├── forecast_engine.py       # 13-week rolling forecast
│   │   └── scenarios.py             # Base/best/worst scenarios
│   │
│   ├── reports/                   # Report generators
│   │   ├── __init__.py
│   │   ├── excel_generator.py     # Excel workbook creation
│   │   └── metrics.py             # Cash flow metrics (runway, etc.)
│   │
│   ├── queries/                   # SQL query templates
│   │   ├── revenue.sql
│   │   ├── cogs.sql
│   │   ├── opex.sql
│   │   └── financing.sql
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       └── dates.py               # Date handling utilities
│
├── notebooks/                     # Hex notebook development
│   └── cashflow_analysis.ipynb
│
├── outputs/                       # Generated reports
│   └── (Excel files, CSVs, etc.)
│
├── database/                      # Database schema reference
│   └── bigquery_entity_map.csv
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # This file
│   └── INITIAL.md                 # Initial project notes
│
├── .env                           # Environment configuration
├── pyproject.toml                 # Python dependencies
└── README.md
```

## Data Flow

### 1. **Data Ingestion** (Already Complete)
- Ecommerce data (Amazon, Shopify) → BigQuery `deposits`, `orders`, `fees`, `refunds` tables
- Operational data (vendors, SKUs, POs, invoices) → BigQuery reference tables
- **No additional parsing needed** — data is pre-transformed

### 2. **Cash Flow Aggregation**
```python
BigQuery Tables → SQL Aggregation → Cash Flow Categories

Example:
  deposits table (Amazon/Shopify)
  + Apply settlement/payout dates
  + Map to "Operating Inflows - Revenue by Channel"
  = Revenue cash flow by date
```

### 3. **Payment Timing Application**
```python
Transaction Date → Payment Timing Rules → Cash Date

Examples:
  • Amazon order on Feb 1 → Settlement Feb 1-14 → Deposit Feb 16
  • Shopify order on Mon → Payout on Wed (2 days later)
  • Credit card expense on Feb 1 → Payment ~Mar 1 (30 days later)
  • Vendor invoice Net 30 → Payment 32 days after invoice
```

### 4. **Forecasting**
```python
Historical Actuals (3-6 months)
+ Revenue forecast (from BQ forecast table)
+ Expense trends (3-month average)
+ Known commitments (POs, CapEx)
+ Debt service schedule (SBA loan)
= 13-week rolling cash forecast
```

### 5. **Scenario Analysis**
- **Base Case**: Conservative revenue, realistic expenses
- **Best Case**: Upside revenue scenarios
- **Worst Case**: Revenue decline, expense overruns

### 6. **Output Generation**
- Excel workbook with formatted tabs (Dashboard, Forecast, Scenarios, etc.)
- Hex notebook for interactive analysis
- JSON/CSV exports for further analysis

## Key Design Principles

### 1. **Cash Timing Precision**
Revenue ≠ Cash. The system models the exact timing lag between:
- When a sale occurs (transaction date)
- When cash is received (settlement/payout date)

This is **critical** for accurate weekly cash projections.

### 2. **Platform Fee Treatment**
Amazon and Shopify fees are deducted **before payout**. The system uses:
- **Net proceeds** (what actually hits the bank)
- Not gross revenue minus fees

### 3. **BigQuery as Source of Truth**
All data comes from BigQuery. No local file parsing needed.
- Queries return DataFrames ready for analysis
- Single source of truth for historical data
- Forecast table provides baseline revenue projections

### 4. **Configuration-Driven**
- Chart of Accounts mapping: `cash_flow_categories.yaml`
- Payment timing rules: `payment_timing.yaml`
- Easy to update without code changes

### 5. **Hex-Compatible**
- Code designed to run in Hex notebook environment
- Modular functions that work in cells
- Interactive visualization support

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Data Warehouse** | Google Cloud BigQuery |
| **Language** | Python 3.13+ |
| **Data Processing** | pandas, numpy |
| **Database Client** | google-cloud-bigquery |
| **Excel Generation** | openpyxl, xlsxwriter |
| **Configuration** | PyYAML, python-dotenv |
| **Execution Environment** | Hex (Jupyter-like notebooks) |
| **Package Management** | uv (not pip!) |

## Cash Flow Categories

See `data/config/cash_flow_categories.yaml` for complete mapping.

### High-Level Categories:
1. **Operating Inflows**
   - Revenue by channel (Amazon, Shopify, TikTok, Wholesale, Whiskey)
   - Shipping income
   - Less: Refunds and discounts

2. **Cost of Goods Sold**
   - Platform fees (Amazon referral, FBA fees, Shopify transaction fees)
   - Fulfillment costs
   - Product materials
   - Freight
   - Direct labor

3. **Operating Expenses**
   - Marketing & Advertising (by channel: FB, Google, Amazon PPC, TikTok)
   - Payroll (wages, taxes, benefits)
   - SG&A (rent, utilities, insurance, software, etc.)
   - Professional services (legal, accounting)

4. **Investing**
   - Capital expenditures (equipment, IP, manufacturing tools)

5. **Financing**
   - Inflows: LOC draws, equity contributions
   - Outflows: Loan payments (principal + interest), owner draws

## Payment Timing Rules

See `data/config/payment_timing.yaml` for complete timing reference.

### Key Timing Patterns:
- **Amazon**: Bi-weekly settlements + 2 days
- **Shopify**: Daily payouts (weekdays) + 2-3 days
- **Credit Cards**: ~30 days after transaction
- **Vendor Net 30**: ~32 days after invoice
- **Payroll**: Bi-weekly (TBD exact schedule)
- **SBA Loan**: Monthly interest (I/O period through May 2026)

## Next Steps

See `/tasks` for current build status.

### Phase 1: Foundation ✅
- [x] Data architecture design
- [x] Chart of accounts mapping
- [x] Payment timing reference
- [x] BigQuery schema documentation

### Phase 2: Data Access (In Progress)
- [ ] BigQuery connector module
- [ ] Cash flow SQL queries
- [ ] Data aggregation functions

### Phase 3: Forecasting
- [ ] 13-week forecast engine
- [ ] Payment timing application
- [ ] Scenario generator
- [ ] SBA loan payment scheduler
- [ ] CapEx commitment tracker

### Phase 4: Reporting
- [ ] Excel workbook generator
- [ ] Dashboard metrics
- [ ] Variance analysis
- [ ] Scenario comparison

### Phase 5: Deployment
- [ ] Hex notebook integration
- [ ] Automated refresh schedule
- [ ] Documentation
