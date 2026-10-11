import pandas as pd
import plotly.express as px
import plotly.io as pio
import json


def _fig_to_json(fig):
    return json.loads(pio.to_json(fig))

def missingness_bar(df: pd.DataFrame):
    miss = df.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    if miss.empty:
        return None
    fig = px.bar(x=miss.index, y=miss.values,
                 labels={"x": "Column", "y": "Missing count"},
                 title="Missing values per column")
    return _fig_to_json(fig)

def histogram(df: pd.DataFrame, col: str):
    fig = px.histogram(df, x=col, nbins=40, title=f"Distribution of {col}")
    return _fig_to_json(fig)

def boxplot(df: pd.DataFrame, col: str):
    fig = px.box(df, y=col, title=f"Box plot — {col}")
    return _fig_to_json(fig)

def correlation_heatmap(df: pd.DataFrame):
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return None
    corr = numeric.corr().round(3)
    fig = px.imshow(corr, text_auto=True, aspect="auto",
                    color_continuous_scale="RdBu_r", title="Correlation heatmap")
    return _fig_to_json(fig)

def value_counts_bar(df: pd.DataFrame, col: str, top: int = 15):
    vc = df[col].value_counts().head(top)
    fig = px.bar(x=vc.index.astype(str), y=vc.values,
                 labels={"x": col, "y": "Count"},
                 title=f"Top {top} values — {col}")
    return _fig_to_json(fig)

def scatter(df: pd.DataFrame, x: str, y: str, color: str | None = None):
    fig = px.scatter(df, x=x, y=y, color=color, title=f"{y} vs {x}")
    return _fig_to_json(fig)

def line(df: pd.DataFrame, x: str, y: str):
    fig = px.line(df, x=x, y=y, title=f"{y} over {x}")
    return _fig_to_json(fig)

def box_by_category(df, numeric_col, category_col):
    fig = px.box(df, x=category_col, y=numeric_col,
                 title=f"{numeric_col} by {category_col}")
    return _fig_to_json(fig)


def violin_by_category(df, numeric_col, category_col):
    fig = px.violin(df, x=category_col, y=numeric_col, box=True, points="outliers",
                    title=f"{numeric_col} distribution by {category_col}")
    return _fig_to_json(fig)


def scatter_matrix(df, cols, color=None):
    cols = [c for c in cols if c in df.columns][:6]
    if len(cols) < 2:
        return None
    fig = px.scatter_matrix(df, dimensions=cols, color=color,
                            title="Scatter matrix", height=700)
    fig.update_traces(diagonal_visible=False, showupperhalf=False)
    return _fig_to_json(fig)


def time_series(df, date_col, value_col, freq="D"):
    d = df[[date_col, value_col]].dropna().copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col]).set_index(date_col).sort_index()
    if d.empty:
        return None
    agg = d[value_col].resample(freq).mean()
    fig = px.line(x=agg.index, y=agg.values,
                  labels={"x": date_col, "y": value_col},
                  title=f"{value_col} over time ({freq})")
    return _fig_to_json(fig)


def missingness_matrix(df, max_rows=300):
    """Visual heatmap of where missing values sit (sampled for large data)."""
    import numpy as np
    sample = df.head(max_rows)
    z = sample.isna().astype(int).values.T
    fig = px.imshow(
        z,
        aspect="auto",
        color_continuous_scale=[[0, "#101216"], [1, "#f87171"]],
        labels={"x": "Row (sampled)", "y": "Column", "color": "Missing"},
        title=f"Missingness map (first {min(max_rows, len(df))} rows)",
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(range(len(df.columns))),
        ticktext=list(df.columns),
    )
    return _fig_to_json(fig)


def category_heatmap(df, row_col, col_col, value_col, agg="mean"):
    try:
        pivot = df.pivot_table(index=row_col, columns=col_col, values=value_col, aggfunc=agg)
    except Exception:
        return None
    if pivot.empty:
        return None
    fig = px.imshow(pivot, aspect="auto", text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    title=f"{value_col} by {row_col} × {col_col} ({agg})")
    return _fig_to_json(fig)