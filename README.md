# VoChill Cash Flow Forecasting System

**Purpose-built financial data model and forecasting engine for VoChill's cash flow management**

---

## 🎯 Project Goals

1. **Automated cash reporting** - Daily/weekly cash position tracking
2. **13-week rolling forecast** - Forward-looking liquidity planning
3. **Multi-scenario planning** - Base/best/worst case modeling
4. **Payment timing precision** - Accurate cash dates for Amazon, Shopify, vendors
5. **BigQuery-native** - Leverage existing data warehouse infrastructure

---

## 🏗️ Architecture

### Data Model
```
┌─────────────────────────────────────────┐
│   EXISTING TABLES (Sales & Operations)  │
│   • deposits, orders, fees, refunds     │
│   • items, vendors, po, invoices        │
│   • forecast (SKU-level)                │
└────────────┬────────────────────────────┘
             │ ETL Transform
             ▼
┌─────────────────────────────────────────┐
│   NEW FINANCIAL TABLES                  │
│   • cash_transactions (all cash in/out) │
│   • cash_balances (daily position)      │
│   • debt_schedule (SBA loan)            │
│   • cash_forecast (13-week rolling)     │
│   • bank_accounts, chart_of_accounts    │
│   • recurring_transactions, capex_plan  │
└────────────┬────────────────────────────┘
             │ Query & Report
             ▼
┌─────────────────────────────────────────┐
│   OUTPUTS                               │
│   • Hex app (dashboard, runway, scenarios)│
│   • JSON/CSV exports                    │
└─────────────────────────────────────────┘
```

### Key Features
- ✅ **13 new BigQuery tables** for financial data
- ✅ **Comprehensive CoA mapping** (200+ accounts → cash flow categories)
- ✅ **Payment timing rules** (Amazon bi-weekly, Shopify daily, vendor Net 30)
- ✅ **SBA loan scheduler** ($500k revolving LOC, Prime + 2.25%)
- ✅ **Scenario planning** (base/best/worst cases built-in)
- ✅ **Hex-compatible** Python modules

---

## 📁 Project Structure

```
vochill-cashflow/
├── data/
│   ├── config/
│   │   ├── cash_flow_categories.yaml  # CoA → CF mapping
│   │   └── payment_timing.yaml        # Payment timing rules
│   ├── raw/                           # Original data exports
│   └── processed/                     # Transformed data
│
├── src/
│   ├── config.py                      # Configuration mgmt
│   ├── data/
│   │   └── bigquery_connector.py      # BQ client & helpers
│   ├── forecast/                      # Forecasting engine (TODO)
│   ├── reports/                       # Report generators (TODO)
│   └── queries/
│       ├── revenue_by_channel.sql
│       ├── vendor_payments.sql
│       └── consolidated_cash_flow.sql
│
├── database/
│   ├── create_financial_tables.sql    # BigQuery DDL
│   ├── financial_schema_design.md     # Schema documentation
│   └── bigquery_entity_map.csv        # Existing tables reference
│
├── docs/
│   ├── ARCHITECTURE.md                # System architecture
│   ├── BIGQUERY_SCHEMA_SUMMARY.md     # Implementation guide
│   └── INITIAL.md                     # Original project notes
│
├── notebooks/
│   └── bigquery_example.py            # Example queries
│
├── outputs/                           # Generated reports
├── pyproject.toml                     # Python dependencies
└── .env                               # Environment config
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
uv pip install -e .
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your GCP credentials
```

### 3. Create BigQuery Tables
```bash
# Execute in BigQuery Console or via bq CLI
bq query --use_legacy_sql=false < database/create_financial_tables.sql
```

### 4. Test Connection
```python
python notebooks/bigquery_example.py
```

---

## 📊 New BigQuery Tables

### Core Tables
| Table | Records | Purpose |
|-------|---------|---------|
| `cash_transactions` | ~50k/year | All cash inflows/outflows |
| `cash_balances` | 365/year | Daily cash position by account |
| `debt_schedule` | 84 payments | SBA loan payment schedule |
| `cash_forecast` | 13 weeks × 3 scenarios | Rolling 13-week forecast |

### Supporting Tables
- `bank_accounts` - Master list of accounts & LOCs
- `chart_of_accounts` - CoA with CF category mapping
- `gl_transactions` - QuickBooks GL export
- `payment_terms` - Timing rules (Amazon, Shopify, vendors)
- `recurring_transactions` - Known recurring items
- `capex_plan` - Planned capital expenditures
- `budget` - Annual/monthly budgets
- `scenarios` - Forecast scenario definitions
- `forecast_assumptions` - Detailed forecast assumptions

### Analytical Views
- `v_daily_cash_flow` - Daily cash flow statement
- `v_weekly_cash_flow` - 13-week rolling view
- `v_cash_position` - Current cash + liquidity

---

## 💰 Cash Flow Categories

### Operating Inflows
- Revenue by channel: Amazon, Shopify, TikTok, Wholesale, Whiskey
- Shipping income
- Other income

### Operating Outflows
- **COGS**: Platform fees, fulfillment, materials, shipping, direct labor
- **Marketing**: Facebook, Google, Amazon PPC, TikTok, Agency fees
- **Payroll**: Wages, taxes, benefits, contractors
- **SG&A**: Rent, utilities, insurance, software, office supplies
- **Professional Services**: Legal, accounting, consulting

### Investing
- CapEx: Equipment, technology, IP

### Financing
- **Inflows**: LOC draws, equity contributions
- **Outflows**: Loan payments (principal + interest), owner draws

---

## ⏰ Payment Timing

| Source | Timing | Example |
|--------|--------|---------|
| **Amazon** | Bi-weekly + 2 days | Order Feb 1 → Settlement Feb 1-14 → Deposit Feb 16 |
| **Shopify** | Daily + 2-3 days | Order Mon → Payout Wed |
| **Credit Cards** | ~30 days | Charge Feb 1 → Payment ~Mar 1 |
| **Vendors Net 30** | Invoice + 32 days | Invoice Feb 1 → Payment Mar 4 |
| **SBA Loan** | Monthly on day 30 | Interest payment on 30th of month |

---

## 📈 13-Week Forecast

The forecast engine generates weekly projections for:
- Operating cash flow (revenue - expenses)
- CapEx & investing activities
- Debt service
- Beginning cash → Ending cash
- LOC availability
- Total liquidity (cash + available LOC)
- **Runway** (weeks until cash depletion)

Supports 3 scenarios:
- **Base Case**: Conservative revenue, realistic expenses
- **Best Case**: +20% revenue upside
- **Worst Case**: -15% revenue decline

---

## 🔧 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Data Warehouse** | Google Cloud BigQuery |
| **Language** | Python 3.13+ |
| **Data Processing** | pandas, numpy |
| **Database Client** | google-cloud-bigquery |
| **Reporting** | Hex (dashboard) |
| **Configuration** | PyYAML, python-dotenv |
| **Execution** | Hex (Jupyter-like notebooks) |
| **Package Mgmt** | uv (not pip!) |

---

## 📝 Next Steps

**Next step:** Build the Cash Flow Hex app. See **[docs/hex_app/READY_TO_BUILD.md](docs/hex_app/READY_TO_BUILD.md)** to start.

### Phase 1: ✅ Foundation (COMPLETE)
- [x] Data architecture design
- [x] BigQuery schema (13 tables + 3 views)
- [x] Chart of accounts mapping (200+ accounts)
- [x] Payment timing reference
- [x] BigQuery connector module
- [x] SQL query templates

### Phase 2: ✅ Data Access (COMPLETE)
- [x] BigQuery tables created and populated (bank_accounts, debt_schedule, recurring_transactions, etc.)
- [x] ETL: deposits and invoices → cash_transactions
- [x] 13-week forecast script ([scripts/build_forecast.py](scripts/build_forecast.py)) writes to cash_transactions

### Phase 3: External (vochill-forecasting)
- Demand/revenue forecasting lives in a separate Hex project (vochill-forecasting repo). This repo’s 13-week cash forecast is generated by `build_forecast.py`; revenue inputs will connect when both Hex apps are live.

### Phase 4: 🔜 Reporting — Hex App
- [ ] Hex app: cash position, runway, 13-week cash flow, scenario comparison
- [ ] Build in Hex using [docs/hex_app/](docs/hex_app/) (strategy, cell guide, checklist)

---

## 📚 Documentation

- **[docs/projectdocs/ARCHITECTURE.md](docs/projectdocs/ARCHITECTURE.md)** - System architecture and phase status
- **[docs/hex_app/READY_TO_BUILD.md](docs/hex_app/READY_TO_BUILD.md)** - Next step: build the Hex cash flow app
- **[docs/hex_app/](docs/hex_app/)** - Hex app strategy, cell-by-cell guide, implementation checklist
- **[BIGQUERY_SCHEMA_SUMMARY.md](docs/projectdocs/BIGQUERY_SCHEMA_SUMMARY.md)** - BigQuery implementation guide
- **[financial_schema_design.md](database/financial_schema_design.md)** - Complete schema design with rationale

---

## 🎓 Usage Examples

### Query Recent Revenue
```python
from src.data import BigQueryConnector

bq = BigQueryConnector()

# Get last 30 days of Amazon revenue
revenue = bq.get_deposits(
    start_date='2026-02-01',
    end_date='2026-02-28',
    platform='Amazon'
)

print(f"Total Amazon revenue: ${revenue['total'].sum():,.2f}")
```

### Get Current Cash Position
```sql
SELECT * FROM vochill.revrec.v_cash_position;
```

### Get 13-Week Forecast
```sql
SELECT
  period_date,
  ending_cash,
  total_liquidity,
  weeks_of_runway
FROM vochill.revrec.cash_forecast
WHERE forecast_id = (SELECT MAX(forecast_id) FROM vochill.revrec.cash_forecast)
  AND scenario_id = 'base'
ORDER BY week_number;
```

---

## 🤝 Contributing

This is a VoChill internal project. For questions or issues:
- **Technical**: Review docs in `docs/` directory
- **Data**: Check `database/` schema files
- **Configuration**: See `data/config/` YAML files

---

## 📄 License

Internal VoChill project - All rights reserved

---

**Built with Claude Code** 🤖
