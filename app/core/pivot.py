import pandas as pd
import math


AGG_FUNCS = {
    "sum": "sum",
    "mean": "mean",
    "median": "median",
    "count": "count",
    "min": "min",
    "max": "max",
    "std": "std",
    "nunique": "nunique",
}


def run_pivot(df: pd.DataFrame, rows: list, cols: list, values: list,
              aggfuncs: list, fill_value=None, margins: bool = False) -> dict:
    """Build a pivot table. Supports multiple value columns and multiple aggregations."""
    rows = [c for c in (rows or []) if c in df.columns]
    cols = [c for c in (cols or []) if c in df.columns]
    values = [c for c in (values or []) if c in df.columns]
    aggfuncs = [a for a in (aggfuncs or ["mean"]) if a in AGG_FUNCS]

    if not rows and not cols:
        raise ValueError("Pick at least one row or column field.")
    if not values:
        raise ValueError("Pick at least one value field.")
    if not aggfuncs:
        raise ValueError("Pick at least one aggregation.")

    if len(values) == 1 and len(aggfuncs) == 1:
        agg_arg = aggfuncs[0]
    else:
        # Cross product: apply every aggregation to every value
        agg_arg = {v: aggfuncs for v in values}

    try:
        pivot = df.pivot_table(
            index=rows if rows else None,
            columns=cols if cols else None,
            values=values,
            aggfunc=agg_arg,
            fill_value=fill_value,
            margins=margins,
            observed=False,
            dropna=False,
        )
    except Exception as e:
        raise ValueError(f"Could not build pivot table: {e}")

    pivot = pivot.reset_index()

    # Flatten MultiIndex columns into readable strings
    if isinstance(pivot.columns, pd.MultiIndex):
        flat = []
        for tup in pivot.columns:
            parts = [str(p) for p in tup if p not in (None, "")]
            flat.append(" · ".join(parts) if parts else "value")
        pivot.columns = flat
    else:
        pivot.columns = [str(c) for c in pivot.columns]

    return {
        "columns": list(pivot.columns),
        "rows": _serialize(pivot),
        "row_count": len(pivot),
        "shape": [len(pivot), len(pivot.columns)],
    }


def _serialize(df: pd.DataFrame) -> list[list]:
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
            elif hasattr(v, "item"):
                safe.append(v.item())
            else:
                safe.append(v)
        records.append(safe)
    return records


def suggest_pivot(df: pd.DataFrame) -> dict:
    """Guess reasonable defaults from column types."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    return {
        "rows": categorical[:1],
        "cols": categorical[1:2] if len(categorical) > 1 else [],
        "values": numeric[:1],
        "aggfuncs": ["mean"],
    }