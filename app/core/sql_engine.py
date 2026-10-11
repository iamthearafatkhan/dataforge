import math
import re
import time
from datetime import datetime, date
import duckdb
import pandas as pd

MAX_ROWS = 10_000

# Statements that could mutate or escape the sandbox
_FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|TRUNCATE|REPLACE|GRANT|REVOKE"
    r"|ATTACH|DETACH|COPY|EXPORT|IMPORT|PRAGMA|INSTALL|LOAD|CALL|SET)\b",
    re.IGNORECASE,
)


def _strip_comments(sql: str) -> str:
    # Remove -- line comments and /* block comments */
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", "", sql)
    return sql


def validate(sql: str) -> str:
    """Return cleaned SQL or raise ValueError with a helpful message."""
    sql = _strip_comments(sql).strip().rstrip(";").strip()
    if not sql:
        raise ValueError("Query is empty.")
    if ";" in sql:
        raise ValueError("Only a single statement is allowed.")
    if _FORBIDDEN.search(sql):
        raise ValueError("Only SELECT and WITH queries are allowed here.")
    first = sql.split(None, 1)[0].upper()
    if first not in ("SELECT", "WITH"):
        raise ValueError("Query must start with SELECT or WITH.")
    return sql


def run_query(df: pd.DataFrame, sql: str, max_rows: int = MAX_ROWS) -> dict:
    """Execute a read-only query against the in-memory dataframe."""
    sql = validate(sql)

    con = duckdb.connect(database=":memory:")
    try:
        con.register("df", df)
        # Disable external file access as a defensive measure
        con.execute("SET enable_external_access=false;")
    except Exception:
        pass

    t0 = time.perf_counter()
    cursor = con.execute(sql)
    result = cursor.fetchdf()
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    total = len(result)
    truncated = total > max_rows
    if truncated:
        result = result.head(max_rows)

    return {
        "columns": list(result.columns),
        "rows": _serialize(result),
        "row_count": len(result),
        "total_rows": total,
        "truncated": truncated,
        "elapsed_ms": elapsed_ms,
    }


def _serialize(df: pd.DataFrame) -> list[list]:
    """Convert a DataFrame into JSON-safe rows (lists, not dicts, to keep key order)."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    records = []
    for row in out.itertuples(index=False, name=None):
        safe = []
        for v in row:
            if v is None:
                safe.append(None)
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                safe.append(None)
            elif isinstance(v, (datetime, date, pd.Timestamp)):
                safe.append(str(v))
            elif hasattr(v, "item"):
                # numpy scalar → python scalar
                safe.append(v.item())
            else:
                safe.append(v)
        records.append(safe)
    return records


def describe(df: pd.DataFrame) -> dict:
    """Column types and a small preview for the sidebar."""
    cols = [{"name": c, "type": str(df[c].dtype)} for c in df.columns]
    preview = df.head(5)
    return {
        "columns": cols,
        "row_count": len(df),
        "preview": {
            "columns": list(preview.columns),
            "rows": _serialize(preview),
        },
    }


def suggest_queries(df: pd.DataFrame) -> list[dict]:
    """Return starter queries tuned to the actual columns."""
    q = [
        {"label": "First 20 rows", "sql": "SELECT * FROM df LIMIT 20"},
        {"label": "Row count", "sql": "SELECT COUNT(*) AS total_rows FROM df"},
    ]

    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if numeric:
        n = numeric[0]
        q.append({
            "label": f"Summary of {n}",
            "sql": f'SELECT MIN("{n}") AS min, AVG("{n}") AS avg, MAX("{n}") AS max FROM df',
        })

    if categorical and numeric:
        c, n = categorical[0], numeric[0]
        q.append({
            "label": f"Avg {n} by {c}",
            "sql": f'SELECT "{c}", AVG("{n}") AS avg_{n}, COUNT(*) AS n '
                   f'FROM df GROUP BY "{c}" ORDER BY avg_{n} DESC',
        })

    if categorical:
        c = categorical[0]
        q.append({
            "label": f"Counts by {c}",
            "sql": f'SELECT "{c}", COUNT(*) AS n FROM df '
                   f'GROUP BY "{c}" ORDER BY n DESC',
        })

    return q[:6]