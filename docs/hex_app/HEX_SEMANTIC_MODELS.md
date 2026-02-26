# Hex Semantic Models (YAML)

This doc references Hex’s **semantic model** YAML spec and how it could be used for VoChill cash flow. Semantic models are **separate** from [project import/export](IMPORT_EXPORT.md): they define **data models** (tables, dimensions, measures, views) for Hex’s semantic layer and Data Browser, not the structure of a notebook/app project.

**Spec (authoritative):** [YAML specification \| Hex](https://learn.hex.tech/docs/connect-to-data/semantic-models/semantic-authoring/modeling-specification)  
**Status:** Semantic authoring in Hex is in **beta**; the format may change.

---

## What the spec covers

- **Resources:** Each YAML document is one semantic resource.
- **Models** — Reusable definition for a table:
  - `id`, `type: model`
  - `base_sql_table` or `base_sql_query` (data source)
  - `dimensions` (filter/group fields; at least one with `unique: true`)
  - `measures` (aggregations: count, sum, avg, or `func_sql` / `func_calc`)
  - `relations` (joins to other models: many_to_one, one_to_many, one_to_one)
  - Optional: `name`, `description`, `visibility` (public / internal / private)
- **Views** — Optional; declare on top of models to expose a subset of dimensions/measures for self-serve analysis. Have `type: view`, `base` (model id), and `contents` (groups of dimensions/measures).
- **IDs:** Lowercase letters, underscores, numbers; 2–128 chars; reserved: `this`, `self`, `dataset`, `model`, `view`, `metric`, `env`, `_hex*`.
- **Data types:** `number`, `string`, `date`, `timestamp_tz`, `timestamp_naive`, `boolean`, `other`.
- **SQL interpolation:** In SQL fields, use `${dimension_id}`, `${measure_id}`, `${relation_id}.field` to reference other resources.
- **Files:** Any `.yaml` / `.yml`; multi-document YAML supported (separate with `---`).

---

## Optional: VoChill cash flow semantic model

If you use a **Hex semantic project** (or Modeling Workbench) and connect it to BigQuery `vochill.revrec`, you can define models and views over cash flow tables. Example below uses existing BQ objects; table names assume dataset is exposed (e.g. as `revrec` or your connection’s schema).

**Example: model over weekly cash flow (actuals)**

Uses the existing view `v_weekly_cash_flow` (actuals only, last 13 weeks). One unique dimension is required; here `week_start` is used as the grain.

```yaml
id: weekly_cash_flow
type: model
base_sql_table: revrec.v_weekly_cash_flow
name: Weekly cash flow
description: Weekly rollup of cash flow by section and category (actuals only).

dimensions:
  - id: row_key
    type: string
    unique: true
    expr_sql: CONCAT(CAST(week_start AS STRING), '_', COALESCE(cash_flow_section, ''), '_', COALESCE(cash_flow_category, ''))
    visibility: internal
  - id: week_start
    type: date
  - id: week_end
    type: date
  - id: cash_flow_section
    type: string
  - id: cash_flow_category
    type: string
  - id: net_cash_flow
    type: number
  - id: transaction_count
    type: number

measures:
  - id: total_net_cash_flow
    func: sum
    of: net_cash_flow
    name: Net cash flow
  - id: total_transaction_count
    func: sum
    of: transaction_count
    name: Transaction count
```

**Example: model over cash position (single-row view)**

`v_cash_position` returns one row (total_cash, total_loc_available, total_liquidity). A semantic model can expose it for metrics; at least one unique dimension is required, so a synthetic key is used.

```yaml
id: cash_position
type: model
base_sql_table: revrec.v_cash_position
name: Cash position
description: Current cash and liquidity from v_cash_position.

dimensions:
  - id: row_key
    type: string
    unique: true
    expr_sql: 'current'
    visibility: internal

measures:
  - id: total_cash
    func_sql: SUM(total_cash)
  - id: total_liquidity
    func_sql: SUM(total_liquidity)
  - id: total_loc_available
    func_sql: SUM(total_loc_available)
```

**Note:** Exact `base_sql_table` values depend on how your Hex BigQuery connection exposes the dataset (e.g. `vochill.revrec.v_weekly_cash_flow` vs `revrec.v_weekly_cash_flow`). Adjust to match your connection’s schema.

---

## When to use this

- You want **self-serve exploration** of cash flow data in Hex’s Data Browser or in semantic-aware cells.
- You are already using or evaluating **Hex semantic projects** / Modeling Workbench.
- You do **not** need this for the basic VoChill Cash Flow app (notebook + SQL cells + charts); that app reads directly from BigQuery via SQL cells or the starter notebook.

For **project**-level import/export (not semantic models), see [IMPORT_EXPORT.md](IMPORT_EXPORT.md).
