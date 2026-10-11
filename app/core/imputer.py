import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer


def apply_strategies(df: pd.DataFrame, strategies: dict, is_train: bool = True, fitted: dict | None = None):
    df = df.copy()
    fitted = fitted or {}

    for col, spec in strategies.items():
        if col not in df.columns:
            continue
        method = spec.get("method", "none")
        if method == "none":
            continue

        try:
            if method == "mean":
                fill = fitted.get(col) if not is_train else _safe_stat(df[col], "mean")
                if fill is not None:
                    df[col] = df[col].fillna(fill)
                fitted[col] = fill

            elif method == "median":
                fill = fitted.get(col) if not is_train else _safe_stat(df[col], "median")
                if fill is not None:
                    df[col] = df[col].fillna(fill)
                fitted[col] = fill

            elif method == "mode":
                fill = fitted.get(col) if not is_train else _mode(df[col])
                if fill is not None:
                    df[col] = df[col].fillna(fill)
                fitted[col] = fill

            elif method == "constant":
                fill = spec.get("value", 0)
                df[col] = df[col].fillna(fill)
                fitted[col] = fill

            elif method == "ffill":
                df[col] = df[col].ffill().bfill()

            elif method == "bfill":
                df[col] = df[col].bfill().ffill()

            elif method == "knn":
                df, fitted[col] = _knn_impute(df, col, fitted.get(col), is_train)

            elif method == "mice":
                df, fitted[col] = _mice_impute(df, col, fitted.get(col), is_train)

            elif method == "drop":
                df = df.dropna(subset=[col]).reset_index(drop=True)

        except Exception:
            # Fallback: never let one column kill the whole batch
            fallback = _safe_fallback(df[col])
            if fallback is not None:
                df[col] = df[col].fillna(fallback)

    return df, fitted


def _safe_stat(s, kind):
    num = pd.to_numeric(s, errors="coerce")
    if num.dropna().empty:
        return None
    v = num.mean() if kind == "mean" else num.median()
    return None if pd.isna(v) or np.isinf(v) else float(v)


def _mode(s):
    m = s.dropna().mode()
    return m.iloc[0] if not m.empty else None


def _safe_fallback(s):
    non_null = s.dropna()
    if non_null.empty:
        return None
    if pd.api.types.is_numeric_dtype(s):
        v = non_null.median()
        return None if pd.isna(v) else float(v)
    return non_null.iloc[0]


def _knn_impute(df, col, model, is_train):
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    # Need at least 2 numeric columns and the target column present
    if col not in numeric or len(numeric) < 2:
        fill = _safe_fallback(df[col])
        if fill is not None:
            df[col] = df[col].fillna(fill)
        return df, fill

    sub = df[numeric].copy()
    # Drop columns that are entirely NaN
    sub = sub.loc[:, sub.notna().any()]
    if sub.shape[1] < 2 or len(sub) < 2:
        fill = _safe_fallback(df[col])
        if fill is not None:
            df[col] = df[col].fillna(fill)
        return df, fill

    # Safety: ensure all sub columns are float
    sub = sub.astype(float)

    if is_train or model is None:
        n_neighbors = min(5, max(1, len(sub) - 1))
        model = KNNImputer(n_neighbors=n_neighbors, weights="uniform")
        model.fit(sub)

    imputed = model.transform(sub)
    df[sub.columns] = imputed
    return df, model


def _mice_impute(df, col, model, is_train):
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    if col not in numeric or len(numeric) < 2:
        fill = _safe_fallback(df[col])
        if fill is not None:
            df[col] = df[col].fillna(fill)
        return df, fill

    sub = df[numeric].copy()
    sub = sub.loc[:, sub.notna().any()]
    if sub.shape[1] < 2 or len(sub.dropna(how="all")) < 2:
        fill = _safe_fallback(df[col])
        if fill is not None:
            df[col] = df[col].fillna(fill)
        return df, fill

    sub = sub.astype(float)

    if is_train or model is None:
        model = IterativeImputer(max_iter=10, random_state=42, sample_posterior=False)
        model.fit(sub)

    imputed = model.transform(sub)
    df[sub.columns] = imputed
    return df, model