import os
import time
import uuid
import pandas as pd
from flask import current_app, session


def _user_dir():
    if "uid" not in session:
        session["uid"] = uuid.uuid4().hex
    path = os.path.join(current_app.config["STORAGE_DIR"], session["uid"])
    os.makedirs(path, exist_ok=True)
    return path


def _is_expired(path: str) -> bool:
    ttl = current_app.config["SESSION_TTL_HOURS"] * 3600
    if not os.path.exists(path):
        return False
    return time.time() - os.path.getmtime(path) > ttl


def _raw_path():
    return os.path.join(_user_dir(), "raw.parquet")


def _work_path():
    return os.path.join(_user_dir(), "working.parquet")


def _sanitize_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        types = non_null.map(type).unique()
        if len(types) > 1:
            df[col] = df[col].where(df[col].isna(), df[col].astype(str))
    return df


def save_raw(df: pd.DataFrame):
    df = _sanitize_for_parquet(df)
    df.to_parquet(_raw_path(), index=False)
    df.to_parquet(_work_path(), index=False)


def load_raw() -> pd.DataFrame:
    return pd.read_parquet(_raw_path())


def load_working() -> pd.DataFrame:
    p = _work_path()
    if _is_expired(p):
        raise FileNotFoundError("Session expired")
    return pd.read_parquet(p)


def save_working(df: pd.DataFrame):
    df = _sanitize_for_parquet(df)
    df.to_parquet(_work_path(), index=False)


def reset_working():
    load_raw().to_parquet(_work_path(), index=False)


def has_dataset() -> bool:
    return os.path.exists(_raw_path())