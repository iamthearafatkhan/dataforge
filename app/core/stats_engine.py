import math
import numpy as np
import pandas as pd
from scipy import stats


def _safe(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return round(float(v), 6)


def _interpret_p(p):
    if p is None:
        return "unknown"
    if p < 0.001:
        return "very strong evidence against the null hypothesis"
    if p < 0.01:
        return "strong evidence against the null hypothesis"
    if p < 0.05:
        return "moderate evidence against the null hypothesis"
    if p < 0.10:
        return "weak evidence against the null hypothesis"
    return "insufficient evidence to reject the null hypothesis"


def correlate(df, col_a, col_b, method="pearson"):
    """Correlation between two numeric columns."""
    d = df[[col_a, col_b]].dropna()
    if len(d) < 3:
        raise ValueError("Need at least 3 non-null rows to correlate.")

    if method == "pearson":
        r, p = stats.pearsonr(d[col_a], d[col_b])
    elif method == "spearman":
        r, p = stats.spearmanr(d[col_a], d[col_b])
    elif method == "kendall":
        r, p = stats.kendalltau(d[col_a], d[col_b])
    else:
        raise ValueError("Unknown correlation method.")

    return {
        "test": f"{method.capitalize()} correlation",
        "statistic": _safe(r),
        "p_value": _safe(p),
        "n": len(d),
        "interpretation": _interpret_p(p),
        "detail": f"r = {r:.4f}, p = {p:.6f}",
    }


def t_test(df, numeric_col, group_col):
    """Compare means of a numeric column across exactly 2 groups."""
    d = df[[numeric_col, group_col]].dropna()
    groups = d[group_col].unique()
    if len(groups) != 2:
        raise ValueError(f"t-test needs exactly 2 groups; found {len(groups)}.")
    a = d[d[group_col] == groups[0]][numeric_col]
    b = d[d[group_col] == groups[1]][numeric_col]
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Need at least 2 rows per group.")

    stat, p = stats.ttest_ind(a, b, equal_var=False)  # Welch's t-test

    # effect size (Cohen's d)
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    d_val = (a.mean() - b.mean()) / pooled if pooled > 0 else 0

    return {
        "test": f"Welch's t-test: {numeric_col} by {group_col}",
        "statistic": _safe(stat),
        "p_value": _safe(p),
        "n": len(d),
        "groups": [str(g) for g in groups],
        "means": [_safe(a.mean()), _safe(b.mean())],
        "cohens_d": _safe(d_val),
        "interpretation": _interpret_p(p),
        "detail": f"t = {stat:.4f}, p = {p:.6f}, d = {d_val:.4f}",
    }


def anova(df, numeric_col, group_col):
    """Compare means of a numeric column across 3+ groups."""
    d = df[[numeric_col, group_col]].dropna()
    groups = d[group_col].unique()
    if len(groups) < 3:
        raise ValueError(f"ANOVA needs 3+ groups; found {len(groups)}.")
    samples = [d[d[group_col] == g][numeric_col].values for g in groups]
    samples = [s for s in samples if len(s) >= 2]
    if len(samples) < 3:
        raise ValueError("Not enough valid groups for ANOVA.")

    stat, p = stats.f_oneway(*samples)

    # eta squared (effect size)
    grand_mean = d[numeric_col].mean()
    ss_between = sum(len(s) * (s.mean() - grand_mean) ** 2 for s in samples)
    ss_total = ((d[numeric_col] - grand_mean) ** 2).sum()
    eta_sq = ss_between / ss_total if ss_total > 0 else 0

    return {
        "test": f"One-way ANOVA: {numeric_col} by {group_col}",
        "statistic": _safe(stat),
        "p_value": _safe(p),
        "n": len(d),
        "groups": [str(g) for g in groups],
        "eta_squared": _safe(eta_sq),
        "interpretation": _interpret_p(p),
        "detail": f"F = {stat:.4f}, p = {p:.6f}, η² = {eta_sq:.4f}",
    }


def chi_square(df, col_a, col_b):
    """Test independence between two categorical columns."""
    d = df[[col_a, col_b]].dropna()
    if d.empty:
        raise ValueError("No non-null rows for these columns.")
    table = pd.crosstab(d[col_a], d[col_b])
    if table.size < 4:
        raise ValueError("Need at least a 2x2 contingency table.")

    chi2, p, dof, expected = stats.chi2_contingency(table)

    # Cramér's V (effect size)
    n = table.values.sum()
    min_dim = min(table.shape) - 1
    cramers_v = math.sqrt(chi2 / (n * min_dim)) if n * min_dim > 0 else 0

    return {
        "test": f"Chi-square test: {col_a} × {col_b}",
        "statistic": _safe(chi2),
        "p_value": _safe(p),
        "n": int(n),
        "dof": int(dof),
        "cramers_v": _safe(cramers_v),
        "interpretation": _interpret_p(p),
        "detail": f"χ² = {chi2:.4f}, p = {p:.6f}, V = {cramers_v:.4f}",
    }


def normality(df, col):
    """Shapiro-Wilk test for normality (sample ≤ 5000 rows)."""
    d = df[col].dropna()
    if len(d) < 3:
        raise ValueError("Need at least 3 rows.")
    sample = d.sample(min(len(d), 5000), random_state=42) if len(d) > 5000 else d
    stat, p = stats.shapiro(sample)

    return {
        "test": f"Shapiro-Wilk normality test: {col}",
        "statistic": _safe(stat),
        "p_value": _safe(p),
        "n": len(sample),
        "interpretation": (
            "Data appears to be normally distributed" if p > 0.05
            else "Data deviates significantly from normality"
        ),
        "detail": f"W = {stat:.4f}, p = {p:.6f}",
    }


def _looks_like_id(df, col):
    """Detect ID-like columns: unique integer values, or name contains 'id'."""
    if not pd.api.types.is_numeric_dtype(df[col]):
        return False
    # Every value unique AND name contains id
    if "id" in col.lower():
        return True
    # Sequential integers with no gaps
    try:
        v = df[col].dropna()
        if len(v) == v.nunique() and v.dtype.kind in "iu":
            return True
    except Exception:
        pass
    return False


def suggest_tests(df):
    """Generate a list of suggested tests based on column types."""
    numeric = [c for c in df.select_dtypes(include="number").columns
               if not _looks_like_id(df, c)]
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    low_card_cat = [c for c in categorical if 2 <= df[c].nunique(dropna=True) <= 15]

    suggestions = []

    if len(numeric) >= 2:
        for i in range(min(3, len(numeric) - 1)):
            suggestions.append({
                "kind": "correlate",
                "label": f"Correlation: {numeric[i]} vs {numeric[i+1]}",
                "params": {"col_a": numeric[i], "col_b": numeric[i+1], "method": "pearson"},
            })

    two_val_cat = [c for c in low_card_cat if df[c].nunique(dropna=True) == 2]
    if numeric and two_val_cat:
        suggestions.append({
            "kind": "t_test",
            "label": f"t-test: {numeric[0]} by {two_val_cat[0]}",
            "params": {"numeric_col": numeric[0], "group_col": two_val_cat[0]},
        })

    multi_cat = [c for c in low_card_cat if df[c].nunique(dropna=True) >= 3]
    if numeric and multi_cat:
        suggestions.append({
            "kind": "anova",
            "label": f"ANOVA: {numeric[0]} by {multi_cat[0]}",
            "params": {"numeric_col": numeric[0], "group_col": multi_cat[0]},
        })

    if len(low_card_cat) >= 2:
        suggestions.append({
            "kind": "chi_square",
            "label": f"Chi-square: {low_card_cat[0]} × {low_card_cat[1]}",
            "params": {"col_a": low_card_cat[0], "col_b": low_card_cat[1]},
        })

    if numeric:
        suggestions.append({
            "kind": "normality",
            "label": f"Normality test: {numeric[0]}",
            "params": {"col": numeric[0]},
        })

    return {
        "suggestions": suggestions,
        "numeric": numeric,
        "categorical": categorical,
    }


def run_test(df, kind, params):
    """Dispatch a test by kind."""
    if kind == "correlate":
        return correlate(df, params["col_a"], params["col_b"], params.get("method", "pearson"))
    if kind == "t_test":
        return t_test(df, params["numeric_col"], params["group_col"])
    if kind == "anova":
        return anova(df, params["numeric_col"], params["group_col"])
    if kind == "chi_square":
        return chi_square(df, params["col_a"], params["col_b"])
    if kind == "normality":
        return normality(df, params["col"])
    raise ValueError(f"Unknown test: {kind}")