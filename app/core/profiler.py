import pandas as pd
import numpy as np

def profile_columns(df: pd.DataFrame) -> list[dict]:
    """Return per-column diagnostics used to recommend imputation strategy."""
    n = len(df)
    profiles = []
    for col in df.columns:
        s = df[col]
        missing = int(s.isna().sum())
        missing_pct = round(missing / n * 100, 2) if n else 0
        nunique = int(s.nunique(dropna=True))

        if pd.api.types.is_numeric_dtype(s):
            kind = "numeric"
            skew = float(s.skew()) if s.notna().sum() > 2 else 0.0
            stats = {
                "mean": _safe(s.mean()),
                "median": _safe(s.median()),
                "std": _safe(s.std()),
                "min": _safe(s.min()),
                "max": _safe(s.max()),
                "skew": round(skew, 3),
            }
        elif pd.api.types.is_datetime64_any_dtype(s):
            kind = "datetime"
            stats = {"min": str(s.min()), "max": str(s.max())}
        else:
            kind = "categorical" if nunique <= 50 else "text"
            top = s.value_counts(dropna=True).head(5).to_dict()
            stats = {"top_values": {str(k): int(v) for k, v in top.items()}}

        profiles.append({
            "name": col,
            "dtype": str(s.dtype),
            "kind": kind,
            "missing": missing,
            "missing_pct": missing_pct,
            "unique": nunique,
            "stats": stats,
            "recommendation": _recommend(kind, missing_pct, nunique, stats),
        })
    return profiles

def _safe(v):
    try:
        f = float(v)
        return None if np.isnan(f) or np.isinf(f) else round(f, 4)
    except Exception:
        return None

def _recommend(kind, missing_pct, nunique, stats):
    """Rule-based recommendation with human-readable reason."""
    if missing_pct == 0:
        return {"method": "none", "reason": "No missing values."}
    if kind == "numeric":
        if abs(stats.get("skew", 0)) > 1.0:
            return {"method": "median", "reason": "Skewed distribution — median is robust to outliers."}
        if nunique > 10:
            return {"method": "knn", "reason": "Continuous numeric — KNN can exploit correlations."}
        return {"method": "mean", "reason": "Roughly symmetric numeric distribution."}
    if kind in ("categorical", "text"):
        return {"method": "mode", "reason": "Categorical — mode preserves the dominant class."}
    if kind == "datetime":
        return {"method": "ffill", "reason": "Time series — forward fill preserves ordering."}
    return {"method": "drop", "reason": "Fallback: drop rows with missing values."}