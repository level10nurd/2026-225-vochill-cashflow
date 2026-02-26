# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VoChill Cash Flow Forecasting and Reporting System - An automated cash reporting and forecasting tool for VoChill's multi-source financial operations.

**Execution Environment:** [Hex](https://hex.tech) - Jupyter notebook-like environment for Python data analysis and visualization.

**Goal:** Robust, automated cash flow reporting and 13-week rolling forecasts integrating data from multiple banking and ecommerce platforms.

## Package Management

**CRITICAL:** Always use `uv` instead of `pip` for all Python package operations.

```bash
# Install dependencies
uv pip install <package>

# Sync dependencies from pyproject.toml
uv pip sync

# Add dependency to project
uv add <package>
```

## Development Environment

- Python 3.13+ (see `.python-version`)
- Dependencies managed via `pyproject.toml`
- Code runs in Hex's Jupyter-like notebook environment

## Architecture Overview

### Data Sources Integration

The system integrates cash flow data from multiple sources:

**Banking:**
- Frost Bank (primary bank and line of credit)
- American Express
- Chase Inc
- Southwest Card
- Bill.com
- Shopify Card

**Ecommerce Platforms:**
- Amazon.com
- Shopify.com

**Critical Design Consideration:** Ecommerce platform deposit timing is highly variable and critical for accurate forecasting. The system must model payout schedules and delays for Amazon and Shopify separately.

### Reference Model

`examples/13-week Cash Flow Model.xlsx` - Current working Excel model serving as inspiration for:
- Cash flow calculation logic
- Forecasting methodology
- Report structure and flow
- Multi-week rolling forecast approach

Use as a guide for logic patterns, not as strict specification. Incorporate proven concepts while building a more robust automated system.

## Key Design Requirements

1. **Multi-source reconciliation:** Aggregate and deduplicate transactions across banking and payment sources
2. **Forecast timing accuracy:** Model platform-specific payout schedules (Amazon vs Shopify have different cycles)
3. **13-week rolling horizon:** Maintain forward-looking cash position projections
4. **Hex compatibility:** Structure code to work in Hex's notebook execution model (cell-based, stateful environment)
