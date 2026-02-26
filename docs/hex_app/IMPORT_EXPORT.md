# Hex Project Import and Export

This doc summarizes [Hex’s import/export options](https://learn.hex.tech/docs/explore-data/projects/import-export) and how they fit the VoChill Cash Flow app.

**Two different YAML uses in Hex:** (1) **Project** import/export — full project (cells, app layout) as `.yaml`; schema is defined by Hex when you export. (2) **Semantic models** — YAML for data models (tables, dimensions, measures, views) in Hex’s semantic layer; see [HEX_SEMANTIC_MODELS.md](HEX_SEMANTIC_MODELS.md) and the [Hex YAML specification](https://learn.hex.tech/docs/connect-to-data/semantic-models/semantic-authoring/modeling-specification).

---

## Hex’s two project file formats

Hex supports two file formats for moving **projects** in and out of Hex:

| Format | Extension | Use case | Limitation |
|--------|-----------|----------|------------|
| **Hex file format** | `.yaml` | Round-trip export/import; versioning; code review | Best choice when exporting from Hex. Schema is defined by Hex (export produces it). |
| **Jupyter Notebook** | `.ipynb` | Import existing notebooks into Hex | SQL cells and Input parameters are **not** preserved when exporting Hex → .ipynb; when importing .ipynb → Hex you get code/markdown only, and add SQL/Inputs in Hex. |

**Recommendation from Hex:** Prefer the **Hex .yaml format** where possible (round-trip, no loss of SQL/Inputs, human-readable).

---

## Import (create project from a file)

1. In Hex, open the **Projects** home.
2. Click **Import**.
3. Upload a **`.yaml`** (Hex format) or **`.ipynb`** (Jupyter) file.
4. Hex creates a **new project** from that file.

**Import as a new version of an existing project (Hex .yaml only):**

- Open the project → **History & Versions** → **+ Version** → **Import a version**.
- Upload a `.yaml` file; Hex applies it as a new version of the current project.

---

## Export (save project to a file)

1. Open the project in Hex.
2. Use the **dropdown in the project title**.
3. Choose **Export**.
4. Pick **Hex file format (.yaml)** or **Jupyter Notebook (.ipynb)**.

- **.yaml:** Full project logic and app layout; no outputs; round-trip safe; good for Git and code review.
- **.ipynb:** Code and markdown only; SQL cells and Input parameters do **not** export correctly.

---

## Git export (Team / Enterprise)

On [Team and Enterprise plans](https://hex.tech/pricing), you can [export projects to a Git repo](https://learn.hex.tech/docs/explore-data/projects/git-export). Each publish can write the project to a repo as a YAML file (same format as manual export). One-way: Hex → Git; pulling external Git changes into Hex is not supported.

---

## For VoChill Cash Flow

- **Starter notebook:** Use [vochill_cash_flow_starter.ipynb](vochill_cash_flow_starter.ipynb) to **import** into Hex as a new project. It contains markdown and Python (data fetch via BigQuery client, metrics, charts). After import you can:
  - Add **Hex Input** cells for `scenario_id`, `lookback_weeks`, `starting_balance_override`.
  - Optionally replace the data-fetch Python with **Hex SQL** cells wired to **VoChill BigQuery**.
- **After you build the app in Hex:** Use **Export → Hex file format (.yaml)** to save the project into this repo (e.g. under `docs/hex_app/` or a dedicated path). That gives you a versionable, importable project file; re-import via **Import** (new project) or **Import a version** (existing project).
