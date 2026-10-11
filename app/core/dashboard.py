import pandas as pd
from app.core import visualizer


TEMPLATES = {
    "sales": {
        "name": "Sales Dashboard",
        "description": "Revenue trends, top products, regional performance.",
        "roles": {
            "revenue": "numeric",
            "quantity": "numeric",
            "product": "categorical",
            "region": "categorical",
            "date": "datetime_or_categorical",
        },
    },
    "hr": {
        "name": "HR Analytics",
        "description": "Headcount, salary distribution, department breakdown.",
        "roles": {
            "salary": "numeric",
            "department": "categorical",
            "role": "categorical",
            "date": "datetime_or_categorical",
        },
    },
    "finance": {
        "name": "Finance Overview",
        "description": "Income, expenses, and category-wise totals.",
        "roles": {
            "amount": "numeric",
            "category": "categorical",
            "date": "datetime_or_categorical",
        },
    },
    "marketing": {
        "name": "Marketing Performance",
        "description": "Campaign metrics, conversion, channel performance.",
        "roles": {
            "spend": "numeric",
            "conversions": "numeric",
            "channel": "categorical",
            "campaign": "categorical",
        },
    },
    "quality": {
        "name": "Quality & Operations",
        "description": "Defects, yield, and process variation.",
        "roles": {
            "defects": "numeric",
            "units": "numeric",
            "line": "categorical",
            "shift": "categorical",
        },
    },
}


def _pick_columns(df: pd.DataFrame) -> dict:
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

    # Categories with reasonable cardinality
    low_card_cat = [c for c in categorical if 2 <= df[c].nunique(dropna=True) <= 30]

    return {
        "numeric": numeric,
        "categorical": categorical,
        "datetime": datetime_cols,
        "low_card_cat": low_card_cat,
    }


def generate(template_key: str, df: pd.DataFrame) -> dict:
    if template_key not in TEMPLATES:
        raise ValueError("Unknown dashboard template.")

    spec = TEMPLATES[template_key]
    picks = _pick_columns(df)

    charts = []

    if template_key == "sales":
        charts = _sales(df, picks)
    elif template_key == "hr":
        charts = _hr(df, picks)
    elif template_key == "finance":
        charts = _finance(df, picks)
    elif template_key == "marketing":
        charts = _marketing(df, picks)
    elif template_key == "quality":
        charts = _quality(df, picks)

    charts = [c for c in charts if c is not None]

    return {
        "template": template_key,
        "name": spec["name"],
        "description": spec["description"],
        "charts": charts,
        "available": {
            "numeric": picks["numeric"],
            "categorical": picks["categorical"],
            "datetime": picks["datetime"],
        },
    }


# ---------- Templates ----------

def _sales(df, p):
    out = []
    revenue = p["numeric"][0] if p["numeric"] else None
    qty = p["numeric"][1] if len(p["numeric"]) > 1 else None
    product = p["low_card_cat"][0] if p["low_card_cat"] else None
    region = p["low_card_cat"][1] if len(p["low_card_cat"]) > 1 else None
    date_col = p["datetime"][0] if p["datetime"] else None

    if revenue:
        out.append(_wrap("Revenue distribution", visualizer.histogram(df, revenue)))
    if product and revenue:
        out.append(_wrap(f"Avg {revenue} by {product}",
                         visualizer.category_heatmap(df, product, None, revenue) or
                         visualizer.value_counts_bar(df, product)))
    if region and revenue:
        out.append(_wrap(f"{revenue} by {region}",
                         visualizer.box_by_category(df, revenue, region)))
    if date_col and revenue:
        ts = visualizer.time_series(df, date_col, revenue, "M")
        if ts:
            out.append(_wrap(f"{revenue} over time", ts))
    if qty and product:
        out.append(_wrap(f"Total {qty} by {product}",
                         visualizer.value_counts_bar(df, product)))
    return out


def _hr(df, p):
    out = []
    salary = p["numeric"][0] if p["numeric"] else None
    dept = p["low_card_cat"][0] if p["low_card_cat"] else None
    role = p["low_card_cat"][1] if len(p["low_card_cat"]) > 1 else None

    if salary:
        out.append(_wrap("Salary distribution", visualizer.histogram(df, salary)))
    if dept:
        out.append(_wrap(f"Headcount by {dept}", visualizer.value_counts_bar(df, dept)))
    if dept and salary:
        out.append(_wrap(f"Salary by {dept}", visualizer.box_by_category(df, salary, dept)))
    if role:
        out.append(_wrap(f"Roles", visualizer.value_counts_bar(df, role)))
    return out


def _finance(df, p):
    out = []
    amount = p["numeric"][0] if p["numeric"] else None
    category = p["low_card_cat"][0] if p["low_card_cat"] else None
    date_col = p["datetime"][0] if p["datetime"] else None

    if amount:
        out.append(_wrap("Amount distribution", visualizer.histogram(df, amount)))
    if category and amount:
        out.append(_wrap(f"Total by {category}",
                         visualizer.box_by_category(df, amount, category)))
    if date_col and amount:
        ts = visualizer.time_series(df, date_col, amount, "M")
        if ts:
            out.append(_wrap("Trend over time", ts))
    if category:
        out.append(_wrap(f"Count by {category}", visualizer.value_counts_bar(df, category)))
    return out


def _marketing(df, p):
    out = []
    spend = p["numeric"][0] if p["numeric"] else None
    conv = p["numeric"][1] if len(p["numeric"]) > 1 else None
    channel = p["low_card_cat"][0] if p["low_card_cat"] else None
    campaign = p["low_card_cat"][1] if len(p["low_card_cat"]) > 1 else None

    if spend:
        out.append(_wrap("Spend distribution", visualizer.histogram(df, spend)))
    if channel:
        out.append(_wrap(f"Volume by {channel}", visualizer.value_counts_bar(df, channel)))
    if channel and spend:
        out.append(_wrap(f"Spend by {channel}", visualizer.box_by_category(df, spend, channel)))
    if spend and conv:
        out.append(_wrap(f"{conv} vs {spend}", visualizer.scatter(df, spend, conv)))
    if campaign:
        out.append(_wrap("Campaign volumes", visualizer.value_counts_bar(df, campaign)))
    return out


def _quality(df, p):
    out = []
    defects = p["numeric"][0] if p["numeric"] else None
    units = p["numeric"][1] if len(p["numeric"]) > 1 else None
    line = p["low_card_cat"][0] if p["low_card_cat"] else None
    shift = p["low_card_cat"][1] if len(p["low_card_cat"]) > 1 else None

    if defects:
        out.append(_wrap("Defects distribution", visualizer.histogram(df, defects)))
    if line:
        out.append(_wrap(f"Volume by {line}", visualizer.value_counts_bar(df, line)))
    if line and defects:
        out.append(_wrap(f"Defects by {line}", visualizer.box_by_category(df, defects, line)))
    if units and defects:
        out.append(_wrap(f"Defects vs Units", visualizer.scatter(df, units, defects)))
    if shift:
        out.append(_wrap("Shift split", visualizer.value_counts_bar(df, shift)))
    return out


def _wrap(title, fig):
    if fig is None:
        return None
    return {"title": title, "figure": fig}