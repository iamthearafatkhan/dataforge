# DataForge

**Clean · Understand · Query · Export**

A web-based data workbench for analysts, data scientists, and anyone who works with tabular data. Upload a CSV, Excel, or JSON file and go from raw and messy to clean and queryable — without writing a line of code.

**Live demo:** https://dataforge-studio.onrender.com

---

## Why this exists

Data professionals spend 60–80% of their time on data preparation. Existing tools force a choice: use a Python library and write code, or use a GUI and give up control. DataForge is the middle path — a browser tool with per-column control, statistical imputation methods normally reserved for code, SQL querying, pivot tables, formulas, and one-click export.

Built as a portfolio project, engineered for real use.

---

## Features

### Intelligent profiling
Every column is analyzed on upload: data type, missingness percentage, cardinality, distribution skew, and correlation with other columns. Each column gets a recommended imputation strategy with a plain-English explanation — no black boxes.

### Per-feature imputation
Unlike tools that apply one global strategy, DataForge lets you pick the method **per column**:

| Method | When to use |
|---|---|
| `mean` / `median` | Numeric columns — symmetric (mean) or skewed (median) |
| `mode` | Categorical columns |
| `KNN` | Numeric with correlated features — uses nearest neighbors |
| `MICE` | Strongest statistical imputation — iterative modelling |
| `ffill` / `bfill` | Time series or ordered data |
| `constant` | Custom fill value |
| `drop` | Drop rows with missing values |

Recommendations are pre-selected but every choice is overridable.

### Cleaning operations
- Strip whitespace from text columns
- Auto-fix data types (coerce numeric strings, parse dates)
- Drop duplicate rows

### Interactive visualization
Built on Plotly — every chart is fully interactive and downloadable as PNG.

- Histogram, box plot, violin plot
- Box / violin by category
- Scatter, line, time series (daily / weekly / monthly / quarterly / yearly)
- Scatter matrix
- Category heatmap
- Value counts
- Missingness bar chart and missingness matrix
- Correlation heatmap

### SQL Studio
Write SQL directly against your uploaded dataset. The table is named `df`. Powered by [DuckDB](https://duckdb.org/), the modern in-process analytical database.

```sql
SELECT Sex, AVG(Age) AS avg_age, COUNT(*) AS n
FROM df
GROUP BY Sex
ORDER BY avg_age DESC;
```
- Supports SELECT, WITH, JOIN, GROUP BY, window functions, CTEs
- Read-only enforcement — DROP, DELETE, COPY, ATTACH are blocked
- External file access disabled at the database level
- Result export to CSV or JSON
- Adaptive starter queries based on your actual columns

### Pivot table builder
* Build pivot tables like in Excel:
* Row fields, column fields, value fields, aggregations
* Click-to-toggle chip pickers — no awkward multi-select boxes
* Multiple aggregations produce cross-aggregated columns
* Optional totals (margins)
* Export the pivot result as CSV

### Formula builder
Compute new columns with Excel-style formulas. Type =, reference columns by name, use familiar functions:
=price * quantity
=IF(price > 100, "high", "low")
=UPPER(name)
=CONCAT(first_name, " ", last_name)
=YEAR(order_date)
=ROUND(price * 0.9, 2)
=COALESCE(discount, 0)

* Supported functions: IF, ABS, ROUND, SQRT, LOG, EXP, UPPER, LOWER, TRIM, LEN, CONCAT, COALESCE, LEFT, RIGHT, REPLACE, YEAR, MONTH, DAY, ISBLANK, TODAY, NOW.
- Examples adapt to your actual columns — no hardcoded references.

### Dashboard templates
* One-click dashboards for common industries. Columns are auto-detected.
* Sales — revenue distribution, top products, regional performance
* HR — headcount, salary distribution, department breakdown
* Finance — income, expenses, category-wise totals
* Marketing — campaign metrics, conversion, channel performance
* Quality — defects, yield, process variation
* Each chart is downloadable as PNG.

---
Pipeline export & replay
Save your entire preprocessing recipe as a YAML file. On new data, upload the YAML plus a fresh CSV — DataForge re-applies the exact same transformations using the fitted parameters from the original run, not re-fitted values. This is how production ML pipelines maintain train/test consistency and avoid data leakage
```
version: "1.0"
tool: DataForge
cleaning:
  - strip_whitespace
  - fix_dtypes
imputation:
  Age:
    method: knn
  Cabin:
    method: mode
  Embarked:
    method: mode
```

### Multi-format export
CSV — universal
Excel (.xlsx) — for stakeholders and BI tools
JSON — for APIs and web apps
XML — for legacy integrations

### Product polish
Dark and light themes (persisted across reloads)
Animated landing page with typewriter effect
Global loading indicator
24-hour session retention with automatic cleanup
Per-session file isolation — never shared between users
FAQ section with self-serve answers


## Tech Stack

| 

| **Layer** | **Technology** | 
| **Web framework** | Flask 3.1 | 
| **Data manipulation** | pandas 2.2 | 
| **Machine learning** | scikit-learn 1.6 (KNN, Iterative / MICE) | 
| **SQL engine** | DuckDB 1.1 | 
| **Visualization** | Plotly 5.24 | 
| **Storage format** | Apache Parquet (via pyarrow) | 
| **Configuration** | PyYAML, joblib | 
| **Production server** | Gunicorn | 
| **Deployment** | Render (Python runtime) | 

> *All dependencies are open source. No paid services, no proprietary APIs.*

## Project Structure

```
dataforge/
├── app/
│   ├── __init__.py             # App factory, blueprint registration
│   ├── core/
│   │   ├── storage.py          # Per-session Parquet persistence
│   │   ├── profiler.py         # Column profiling + recommendations
│   │   ├── imputer.py          # Per-feature imputation engine
│   │   ├── cleaner.py          # Whitespace, dtype, dedup operations
│   │   ├── visualizer.py       # Plotly chart builders
│   │   ├── exporter.py         # CSV / Excel / JSON / XML writers
│   │   ├── sql_engine.py       # DuckDB wrapper + query sandboxing
│   │   ├── pivot.py            # Pivot table builder
│   │   ├── formula.py          # Excel-style formula evaluator
│   │   ├── dashboard.py        # Industry dashboard templates
│   │   ├── pipeline.py         # YAML pipeline serialization
│   │   └── cleanup.py          # Expired session purging
│   ├── routes/
│   │   ├── main.py             # Page routes
│   │   ├── preprocess.py       # Profiling + imputation API
│   │   ├── visualize.py        # Chart API
│   │   ├── sql.py              # SQL query API
│   │   ├── pivot.py            # Pivot API
│   │   ├── formula.py          # Formula API
│   │   ├── dashboard.py        # Dashboard template API
│   │   ├── pipeline.py         # Pipeline export / apply API
│   │   └── export.py           # Download routes
│   ├── templates/              # Jinja2 templates
│   └── static/                 # CSS, JS, SVG assets
├── storage/                    # Per-session Parquet files (gitignored)
├── config.py                   # Environment-aware configuration
├── requirements.txt
└── run.py                      # Gunicorn entry point (run:app)

```

## Getting Started Locally

### Prerequisites

* Python 3.13

* Git

### Installation

```
git clone https://github.com/iamthearafatkhan/dataforge.git
cd dataforge

python -m venv venv
source venv/Scripts/activate        # Windows Git Bash
# source venv/bin/activate          # macOS / Linux

pip install -r requirements.txt

```

### Run

```
python run.py

```

Open <http://localhost:5000> in your browser.

## Deployment

Deployed on Render (free tier, Python runtime) with a cron-job.org keep-alive ping every 10 minutes to prevent idle spin-down.

| **Setting** | **Value** | 
| **Runtime** | Python 3 | 
| **Build command** | `pip install -r requirements.txt` | 
| **Start command** | `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120` | 
| **Live URL** | <https://dataforge-studio.onrender.com> | 

## Security & Privacy

* **Read-only SQL:** Only `SELECT` and `WITH` statements are permitted. DDL and DML statements are rejected by a validator before execution.

* **No external file access:** DuckDB's `enable_external_access` is disabled at connection time.

* **Formula sandbox:** Excel-style formulas are evaluated with an empty `__builtins__` namespace. Attribute access, imports, and subscript operators are rejected before evaluation.

* **Per-session isolation:** Each browser session gets a unique storage directory. No cross-session access is possible.

* **Automatic expiry:** Sessions are purged 24 hours after last activity. Files are never sent to external services and never used for training.

* **Upload cap:** Configurable via `MAX_UPLOAD_MB` environment variable (Default: `100 MB`).

## Author

**Arafat Khan**

* GitHub: [@iamthearafatkhan](https://github.com/iamthearafatkhan)

* LinkedIn: [iamthearafatkhan](https://linkedin.com/in/iamthearafatkhan)

* Website: [arafatkhan.vercel.app](https://arafatkhan.vercel.app)

## License

MIT — free to use, modify, and distribute.
