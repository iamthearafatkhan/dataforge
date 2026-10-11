import re
import pandas as pd
import numpy as np

# Excel-style function map → pandas/NumPy equivalents
# Each entry: (regex pattern, python replacement using lambda-friendly syntax)
_FUNCS = [
    (r"\bIF\s*\(",      "where_("),
    (r"\bABS\s*\(",     "abs_("),
    (r"\bROUND\s*\(",   "round_("),
    (r"\bSQRT\s*\(",    "sqrt_("),
    (r"\bLOG\s*\(",     "log_("),
    (r"\bEXP\s*\(",     "exp_("),
    (r"\bUPPER\s*\(",   "upper_("),
    (r"\bLOWER\s*\(",   "lower_("),
    (r"\bTRIM\s*\(",    "trim_("),
    (r"\bLEN\s*\(",     "len_("),
    (r"\bCONCAT\s*\(",  "concat_("),
    (r"\bCOALESCE\s*\(", "coalesce_("),
    (r"\bLEFT\s*\(",    "left_("),
    (r"\bRIGHT\s*\(",   "right_("),
    (r"\bREPLACE\s*\(", "replace_("),
    (r"\bYEAR\s*\(",    "year_("),
    (r"\bMONTH\s*\(",   "month_("),
    (r"\bDAY\s*\(",     "day_("),
    (r"\bISBLANK\s*\(", "isblank_("),
    (r"\bTODAY\s*\(\s*\)", "today_()"),
    (r"\bNOW\s*\(\s*\)",   "now_()"),
]

_FORBIDDEN = re.compile(
    r"(__|\bimport\b|\bexec\b|\beval\b|\bopen\b|\bcompile\b|"
    r"\bos\b|\bsys\b|\bsubprocess\b|\bglobals\b|\blocals\b|\bgetattr\b|"
    r"\bsetattr\b|\bdelattr\b|\bclass\b|\blambda\b|\byield\b|\bawait\b|"
    r"\[|\]|\{|\})",
    re.IGNORECASE,
)


def _build_namespace(df: pd.DataFrame) -> dict:
    ns = {}
    # Columns become plain identifiers
    for col in df.columns:
        if isinstance(col, str) and col.isidentifier():
            ns[col] = df[col]
        # also add a sanitized version for columns with spaces / special chars
        if isinstance(col, str):
            safe = re.sub(r"\W|^(?=\d)", "_", col)
            if safe.isidentifier() and safe != col:
                ns[safe] = df[col]

    ns["where_"]    = lambda cond, a, b: np.where(cond, a, b)
    ns["abs_"]      = np.abs
    ns["round_"]    = np.round
    ns["sqrt_"]     = np.sqrt
    ns["log_"]      = np.log
    ns["exp_"]      = np.exp
    ns["upper_"]    = lambda s: s.astype(str).str.upper()
    ns["lower_"]    = lambda s: s.astype(str).str.lower()
    ns["trim_"]     = lambda s: s.astype(str).str.strip()
    ns["len_"]      = lambda s: s.astype(str).str.len()
    ns["concat_"]   = lambda *args: pd.concat([_as_series(a) for a in args], axis=1)\
                                    .astype(str).agg("".join, axis=1)
    ns["coalesce_"] = lambda *args: _as_series(args[0]).where(
        _as_series(args[0]).notna(),
        _coalesce_rest(args[1:]),
    )
    ns["left_"]     = lambda s, n: s.astype(str).str[:int(n)]
    ns["right_"]    = lambda s, n: s.astype(str).str[-int(n):]
    ns["replace_"]  = lambda s, old, new: s.astype(str).str.replace(str(old), str(new), regex=False)
    ns["year_"]     = lambda s: pd.to_datetime(s, errors="coerce").dt.year
    ns["month_"]    = lambda s: pd.to_datetime(s, errors="coerce").dt.month
    ns["day_"]      = lambda s: pd.to_datetime(s, errors="coerce").dt.day
    ns["isblank_"]  = lambda s: s.isna()
    ns["today_"]    = lambda: pd.Timestamp.today().normalize()
    ns["now_"]      = lambda: pd.Timestamp.now()

    # Safe builtins
    ns["True"]  = True
    ns["False"] = False
    ns["None"]  = None

    # NumPy helpers used by operators
    ns["np"] = np
    return ns


def _as_series(x):
    if isinstance(x, pd.Series):
        return x
    return pd.Series([x])


def _coalesce_rest(args):
    if not args:
        return None
    first = _as_series(args[0])
    return first.where(first.notna(), _coalesce_rest(args[1:]))


def _preprocess(expr: str) -> str:
    expr = expr.strip()
    if expr.startswith("="):
        expr = expr[1:]
    if not expr:
        raise ValueError("Formula is empty.")

    if _FORBIDDEN.search(expr):
        raise ValueError("Formula contains characters that are not allowed.")

    # Boolean keywords → operators that work with pandas
    expr = re.sub(r"\bAND\b", "&", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b",  "|", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "~", expr, flags=re.IGNORECASE)

    # Replace Excel function names with internal equivalents
    for pattern, repl in _FUNCS:
        expr = re.sub(pattern, repl, expr, flags=re.IGNORECASE)

    return expr


def apply_formula(df: pd.DataFrame, expr: str, target: str | None = None) -> dict:
    """
    Evaluate an Excel-style formula against the DataFrame.
    If `target` is provided, adds the result as a new column of that name.
    Returns a dict with preview rows and (optionally) the new column name.
    """
    processed = _preprocess(expr)
    namespace = _build_namespace(df)

    try:
        result = eval(processed, {"__builtins__": {}}, namespace)
    except NameError as e:
        missing = str(e).split("'")[1] if "'" in str(e) else str(e)
        raise ValueError(f"Unknown column or function: {missing}")
    except Exception as e:
        raise ValueError(f"Could not evaluate formula: {e}")

    if not isinstance(result, pd.Series):
        # scalar result → broadcast to all rows
        result = pd.Series([result] * len(df))

    result = result.reset_index(drop=True)

    preview_df = pd.DataFrame({
        "row": range(1, min(len(df), 20) + 1),
        "result": result.head(20).tolist(),
    })

    out = {
        "preview": _serialize(preview_df),
        "preview_columns": ["row", "result"],
        "dtype": str(result.dtype),
        "non_null": int(result.notna().sum()),
        "null": int(result.isna().sum()),
        "total": len(result),
    }

    if target:
        target = target.strip()
        if not target.isidentifier():
            raise ValueError("New column name must be a valid identifier.")
        if target in df.columns:
            raise ValueError(f"A column named '{target}' already exists.")
        out["column"] = target
        out["values"] = _serialize(pd.DataFrame({"v": result}))[0] if False else None

    return out, result


def apply_and_store(df: pd.DataFrame, expr: str, target: str):
    """Returns (df_with_new_column, info)."""
    info, series = apply_formula(df, expr, target=None)
    df = df.copy()
    df[target] = series.values
    info["column"] = target
    info["shape"] = {"rows": len(df), "cols": len(df.columns)}
    return df, info


def _serialize(df: pd.DataFrame) -> list[list]:
    import math
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
                try:
                    safe.append(v.item())
                except Exception:
                    safe.append(str(v))
            else:
                safe.append(v)
        records.append(safe)
    return records


EXAMPLES = [
    {"label": "Price × Quantity", "formula": "=price * quantity", "target": "total"},
    {"label": "Discount 10%", "formula": "=price * 0.9", "target": "price_after_discount"},
    {"label": "High / Low tag", "formula": '=IF(price > 100, "high", "low")', "target": "price_tier"},
    {"label": "Upper-case name", "formula": "=UPPER(name)", "target": "name_upper"},
    {"label": "Full name", "formula": '=CONCAT(first_name, " ", last_name)', "target": "full_name"},
    {"label": "Year from date", "formula": "=YEAR(order_date)", "target": "order_year"},
    {"label": "Missing→0", "formula": "=COALESCE(discount, 0)", "target": "discount_filled"},
]