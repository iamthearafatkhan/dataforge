import os
import uuid
import yaml
import joblib
import pandas as pd
from datetime import datetime
from flask import current_app, session
from app.core import imputer

PIPELINE_VERSION = "1.0"


def build_pipeline(cleaning_ops: list, strategies: dict, dataset_meta: dict) -> dict:
    """Create a portable, human-readable recipe."""
    return {
        "version": PIPELINE_VERSION,
        "created": datetime.utcnow().isoformat() + "Z",
        "tool": "DataForge",
        "dataset": {
            "rows": dataset_meta.get("rows"),
            "columns": dataset_meta.get("columns", []),
        },
        "cleaning": cleaning_ops,
        "imputation": strategies,
    }


def to_yaml(pipeline: dict) -> str:
    return yaml.safe_dump(pipeline, sort_keys=False, default_flow_style=False)


def from_yaml(text: str) -> dict:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("Pipeline file is not a valid YAML mapping.")
    if data.get("tool") != "DataForge":
        raise ValueError("Not a DataForge pipeline file.")
    if data.get("version", "0") > PIPELINE_VERSION:
        raise ValueError("Pipeline was created with a newer version of DataForge.")
    return data


def save_fitted_state(fitted: dict) -> str:
    """Persist fitted models to disk; return a token for later retrieval."""
    token = session.get("fitted_token") or uuid.uuid4().hex
    session["fitted_token"] = token
    path = _fitted_path(token)
    joblib.dump(fitted, path)
    return token


def load_fitted_state(token: str) -> dict:
    path = _fitted_path(token)
    if not os.path.exists(path):
        return {}
    return joblib.load(path)


def _fitted_path(token: str) -> str:
    uid = session.get("uid", "shared")
    folder = os.path.join(current_app.config["STORAGE_DIR"], uid)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"fitted_{token}.joblib")


def apply_pipeline_to_df(df: pd.DataFrame, pipeline: dict, fitted: dict | None = None):
    """Run the recipe on a new DataFrame using previously fitted state (if any)."""
    from app.core import cleaner

    cleaning = pipeline.get("cleaning", [])
    if "strip_whitespace" in cleaning:
        df = cleaner.strip_whitespace(df)
    if "fix_dtypes" in cleaning:
        df = cleaner.fix_dtypes(df)
    if "drop_duplicates" in cleaning:
        df = cleaner.drop_duplicates(df)

    strategies = pipeline.get("imputation", {})
    # Only impute columns that exist in the new df
    applicable = {k: v for k, v in strategies.items() if k in df.columns}

    df, new_fitted = imputer.apply_strategies(
        df, applicable, is_train=(fitted is None), fitted=fitted
    )
    return df, new_fitted