import pandas as pd

def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates().reset_index(drop=True)

def fix_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to coerce object columns to numeric/datetime where safe."""
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        # try numeric
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().sum() >= 0.9 * df[col].notna().sum():
            df[col] = coerced
            continue
        # try datetime
        try:
            coerced_dt = pd.to_datetime(df[col], errors="coerce")
            if coerced_dt.notna().sum() >= 0.9 * df[col].notna().sum():
                df[col] = coerced_dt
        except Exception:
            pass
    return df

def strip_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip().replace({"nan": None})
    return df

def iqr_outliers(df: pd.DataFrame, cols: list[str], action: str = "cap") -> pd.DataFrame:
    """Cap or drop outliers via IQR rule on numeric columns."""
    df = df.copy()
    for col in cols:
        if col not in df.columns: continue
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        if action == "cap":
            df[col] = df[col].clip(lo, hi)
        elif action == "drop":
            df = df[(df[col] >= lo) & (df[col] <= hi)]
    return df.reset_index(drop=True)