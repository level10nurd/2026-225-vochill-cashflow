# VoChill Cash Flow Hex App — Ready to Build

**Import the whole project:** Use one of the two files below. Hex → **Projects** → **Import** → upload the file.

| File | Use |
|------|-----|
| **[vochill_cash_flow_starter.ipynb](vochill_cash_flow_starter.ipynb)** | **Recommended.** Full project as Jupyter Notebook. Import this; set BigQuery connection (project `vochill`, dataset `revrec`); Run All. |
| **[vochill_cash_flow_project.yaml](vochill_cash_flow_project.yaml)** | Same project as YAML. Hex’s project import schema is not public — if import fails, use the .ipynb above. |

After import: configure your BigQuery connection so the data cells run. Optionally replace the inputs cell with Hex **Input** cells and the data-fetch code with **SQL** cells wired to **VoChill BigQuery** (see [HEX_CELL_BY_CELL_GUIDE.md](HEX_CELL_BY_CELL_GUIDE.md)).

See **[IMPORT_EXPORT.md](IMPORT_EXPORT.md)** for Hex import/export options.

---

## Build from scratch (no import)

1. **Open your Hex workspace** and create a new project named **"VoChill Cash Flow"**.
2. **Confirm the BigQuery connection** (e.g. "VoChill BigQuery", project: `vochill`, dataset: `revrec`).
3. **Follow [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** step by step, starting with **Phase 4A** (project skeleton).
4. **Copy-paste code** from [HEX_CELL_BY_CELL_GUIDE.md](HEX_CELL_BY_CELL_GUIDE.md) into each cell as you go.

---

## Docs in This Folder

| When you need… | Use this file |
|----------------|----------------|
| **Import whole project** | [vochill_cash_flow_starter.ipynb](vochill_cash_flow_starter.ipynb) (recommended) or [vochill_cash_flow_project.yaml](vochill_cash_flow_project.yaml) |
| **Import/export options** | [IMPORT_EXPORT.md](IMPORT_EXPORT.md) |
| **Semantic models (YAML)** | [HEX_SEMANTIC_MODELS.md](HEX_SEMANTIC_MODELS.md) — data models per [Hex spec](https://learn.hex.tech/docs/connect-to-data/semantic-models/semantic-authoring/modeling-specification) |
| **What to build and why** | [HEX_PROJECT_STRATEGY.md](HEX_PROJECT_STRATEGY.md) |
| **Exact code for each cell** | [HEX_CELL_BY_CELL_GUIDE.md](HEX_CELL_BY_CELL_GUIDE.md) |
| **Step-by-step tasks** | [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) |

---

## Phase 4A First Tasks (≈1 hour)

- Create Hex project "VoChill Cash Flow".
- Add Section 1 inputs (scenario, lookback weeks, starting balance override).
- Add Cell 2.1 (SQL: Get Cash Transactions) and verify it returns data.
- Once 2.1 works, continue with 4B → 4C → 4D → 4E (optional) → 4F.

---

## After the Hex Project Is Built

- Record the Hex project URL in this file or in the repo README.
- Run `scripts/build_forecast.py` when you want to refresh the 13-week forecast in BigQuery; the Hex app will show the latest data on next run.
