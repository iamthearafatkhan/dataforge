import re
import math
import pandas as pd
import numpy as np


_FUNCS = [
    (r"\bIF\s*\(",       "where_("),
    (r"\bABS\s*\(",      "abs_("),
    (r"\bROUND\s*\(",    "round_("),
    (r"\bSQRT\s*\(",     "sqrt_("),
    (r"\bLOG\s*\(",      "log_("),
    (r"\bEXP\s*\(",      "exp_("),
    (r"\bUPPER\s*\(",    "upper_("),
    (r"\bLOWER\s*\(",    "lower_("),
    (r"\bTRIM\s*\(",     "trim_("),
    (r"\bLEN\s*\(",      "len_("),
    (r"\bCONCAT\s*\(",   "concat_("),
    (r"\bCOALESCE\s*\(", "coalesce_("),
    (r"\bLEFT\s*\(",     "left_("),
    (r"\bRIGHT\s*\(",    "right_("),
    (r"\bREPLACE\s*\(",  "replace_("),
    (r"\bYEAR\s*\(",     "year_("),
    (r"\bMONTH\s*\(",    "month_("),
    (r"\bDAY\s*\(",      "day_("),
    (r"\bISBLANK\s*\(",  "isblank_("),
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
    for col in df.columns:
        if isinstance(col, str) and col.isidentifier():
            ns[col] = df[col]
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
    ns["concat_"]   = lambda *args: pd.concat(
        [_as_series(a) for a in args], axis=1
    ).astype(str).agg("".join, axis=1)
    ns["coalesce_"] = lambda *args: _as_series(args[0]).where(
        _as_series(args[0]).notna(),
        _coalesce_rest(args[1:]),
    )
    ns["left_"]     = lambda s, n: s.astype(str).str[: int(n)]
    ns["right_"]    = lambda s, n: s.astype(str).str[-int(n):]
    ns["replace_"]  = lambda s, old, new: s.astype(str).str.replace(
        str(old), str(new), regex=False
    )
    ns["year_"]     = lambda s: pd.to_datetime(s, errors="coerce").dt.year
    ns["month_"]    = lambda s: pd.to_datetime(s, errors="coerce").dt.month
    ns["day_"]      = lambda s: pd.to_datetime(s, errors="coerce").dt.day
    ns["isblank_"]  = lambda s: s.isna()
    ns["today_"]    = lambda: pd.Timestamp.today().normalize()
    ns["now_"]      = lambda: pd.Timestamp.now()

    ns["True"]  = True
    ns["False"] = False
    ns["None"]  = None
    ns["np"]    = np
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

    expr = re.sub(r"\bAND\b", "&", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b",  "|", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "~", expr, flags=re.IGNORECASE)

    for pattern, repl in _FUNCS:
        expr = re.sub(pattern, repl, expr, flags=re.IGNORECASE)

    return expr


def apply_formula(df: pd.DataFrame, expr: str, target: str | None = None):
    """Evaluate a formula. Returns (info, result_series)."""
    processed = _preprocess(expr)
    namespace = _build_namespace(df)

    try:
        result = eval(processed, {"__builtins__": {}}, namespace)
    except NameError as e:
        missing = str(e).split("'")[1] if "'" in str(e) else str(e)
        valid = [c for c in df.columns if isinstance(c, str) and c.isidentifier()][:10]
        hint = f" Available columns: {', '.join(valid)}" if valid else ""
        raise ValueError(f"Unknown column or function: {missing}.{hint}")
    except SyntaxError:
        raise ValueError("Formula has a syntax error. Check parentheses and operators.")
    except Exception as e:
        raise ValueError(f"Could not evaluate formula: {e}")

    if not isinstance(result, pd.Series):
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

    return out, result


def apply_and_store(df: pd.DataFrame, expr: str, target: str):
    """Returns (df_with_new_column, info)."""
    info, series = apply_formula(df, expr, target=None)
    df = df.copy()
    df[target] = series.values
    info["column"] = target
    info["shape"] = {"rows": len(df), "cols": len(df.columns)}
    return df, info


def _serialize(df: pd.DataFrame) -> list:
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


def generate_examples(df: pd.DataFrame) -> list:
    """Create formula examples based on actual columns."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

    examples = []

    if len(numeric) >= 2:
        a, b = numeric[0], numeric[1]
        examples.append({"label": f"{a} × {b}", "formula": f"={a} * {b}", "target": f"{a}_x_{b}"})
        examples.append({"label": f"{a} + {b}", "formula": f"={a} + {b}", "target": f"{a}_plus_{b}"})

    if numeric:
        a = numeric[0]
        examples.append({"label": f"Double {a}", "formula": f"={a} * 2", "target": f"{a}_x2"})
        examples.append({"label": f"Round {a}", "formula": f"=ROUND({a}, 2)", "target": f"{a}_rounded"})

    if numeric and categorical:
        n, c = numeric[0], categorical[0]
        examples.append({"label": f"Upper-case {c}", "formula": f"=UPPER({c})", "target": f"{c}_upper"})

    if numeric:
        n = numeric[0]
        examples.append({
            "label": f"Flag if {n} > 0",
            "formula": f'=IF({n} > 0, "positive", "zero")',
            "target": f"{n}_flag",
        })

    if len(categorical) >= 2:
        a, b = categorical[0], categorical[1]
        examples.append({
            "label": f"Combine {a} + {b}",
            "formula": f'=CONCAT({a}, " | ", {b})',
            "target": f"{a}_{b}_combined",
        })

    if datetime_cols:
        d = datetime_cols[0]
        examples.append({"label": f"Year from {d}", "formula": f"=YEAR({d})", "target": f"{d}_year"})

    if not examples:
        first_col = df.columns[0] if len(df.columns) else "col"
        examples.append({"label": "Identity copy", "formula": f"={first_col} * 1", "target": "copy"})

    return examples[:8]