import math
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, KFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, mean_squared_error, mean_absolute_error, r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


CLASSIFIERS = {
    "logistic_regression": lambda: LogisticRegression(max_iter=1000, random_state=42),
    "decision_tree":       lambda: DecisionTreeClassifier(random_state=42),
    "random_forest":       lambda: RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    "gradient_boosting":   lambda: GradientBoostingClassifier(random_state=42),
}

REGRESSORS = {
    "linear_regression": lambda: LinearRegression(),
    "ridge":             lambda: Ridge(random_state=42),
    "decision_tree":     lambda: DecisionTreeRegressor(random_state=42),
    "random_forest":     lambda: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
}


def _safe(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if hasattr(v, "item"):
        try: return v.item()
        except Exception: pass
    return v


def detect_task(df, target_col):
    """Return 'classification' or 'regression' based on the target."""
    s = df[target_col].dropna()
    if not pd.api.types.is_numeric_dtype(s):
        return "classification"
    if s.nunique() <= 20 and s.nunique() / max(len(s), 1) < 0.05:
        return "classification"
    return "regression"


def _prepare(df, target_col, feature_cols):
    """Build a numeric feature matrix; encode categoricals; drop all-null cols."""
    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # Drop rows where target is missing
    mask = y.notna()
    X = X[mask]
    y = y[mask].reset_index(drop=True)
    X = X.reset_index(drop=True)

    # Encode categoricals
    encoders = {}
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            encoders[col] = le

    # Drop columns that are all-NaN after encoding
    X = X.loc[:, X.notna().any()]

    # Encode target if classification
    target_encoder = None
    if not pd.api.types.is_numeric_dtype(y):
        target_encoder = LabelEncoder()
        y = pd.Series(target_encoder.fit_transform(y.astype(str)))

    return X, y, encoders, target_encoder


def train_model(df, target_col, feature_cols, model_key, test_size=0.2):
    task = detect_task(df, target_col)
    if not feature_cols:
        raise ValueError("Pick at least one feature column.")
    if target_col in feature_cols:
        raise ValueError("Target cannot also be a feature.")

    X, y, encoders, target_encoder = _prepare(df, target_col, feature_cols)

    if len(X) < 10:
        raise ValueError("Need at least 10 rows after cleaning.")

    # Split
    stratify = y if task == "classification" and y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )

    # Build pipeline: impute → scale (for linear models) → estimator
    models = CLASSIFIERS if task == "classification" else REGRESSORS
    if model_key not in models:
        raise ValueError(f"Unknown model: {model_key}")

    estimator = models[model_key]()

    needs_scaling = model_key in ("logistic_regression", "linear_regression", "ridge")
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if needs_scaling:
        steps.append(("scaler", StandardScaler()))
    steps.append(("model", estimator))

    pipe = Pipeline(steps)
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    metrics = {}
    extras = {}

    if task == "classification":
        metrics["accuracy"]  = _safe(accuracy_score(y_test, y_pred))
        metrics["precision"] = _safe(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        metrics["recall"]    = _safe(recall_score(y_test, y_pred, average="weighted", zero_division=0))
        metrics["f1"]        = _safe(f1_score(y_test, y_pred, average="weighted", zero_division=0))

        try:
            if hasattr(pipe, "predict_proba") and y.nunique() == 2:
                y_proba = pipe.predict_proba(X_test)[:, 1]
                metrics["roc_auc"] = _safe(roc_auc_score(y_test, y_proba))
        except Exception:
            pass

        cm = confusion_matrix(y_test, y_pred)
        extras["confusion_matrix"] = cm.tolist()
        extras["classes"] = (
            [str(c) for c in target_encoder.classes_]
            if target_encoder else sorted(y.unique().tolist(), key=str)
        )

        cv = StratifiedKFold(n_splits=min(5, len(X)), shuffle=True, random_state=42)
    else:
        metrics["rmse"] = _safe(math.sqrt(mean_squared_error(y_test, y_pred)))
        metrics["mae"]  = _safe(mean_absolute_error(y_test, y_pred))
        metrics["r2"]   = _safe(r2_score(y_test, y_pred))
        cv = KFold(n_splits=min(5, len(X)), shuffle=True, random_state=42)

    # Cross-validation score
    try:
        scoring = "accuracy" if task == "classification" else "r2"
        cv_scores = cross_val_score(pipe, X, y, cv=cv, scoring=scoring)
        extras["cv_mean"] = _safe(cv_scores.mean())
        extras["cv_std"]  = _safe(cv_scores.std())
        extras["cv_scores"] = [_safe(s) for s in cv_scores.tolist()]
    except Exception:
        pass

    # Feature importances
    try:
        model_step = pipe.named_steps["model"]
        if hasattr(model_step, "feature_importances_"):
            imp = model_step.feature_importances_
        elif hasattr(model_step, "coef_"):
            coef = model_step.coef_
            imp = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)
        else:
            imp = None
        if imp is not None:
            pairs = sorted(zip(X.columns, imp.tolist()), key=lambda p: p[1], reverse=True)
            extras["feature_importance"] = [{"feature": f, "importance": _safe(v)} for f, v in pairs[:20]]
    except Exception:
        pass

    return {
        "task": task,
        "model": model_key,
        "target": target_col,
        "features": list(X.columns),
        "train_rows": len(X_train),
        "test_rows":  len(X_test),
        "metrics": metrics,
        "extras": extras,
    }


def suggest_ml(df):
    """Return sensible defaults based on column types."""
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    # Usable categoricals for features: low-cardinality only
    usable_cat = [c for c in categorical if 2 <= df[c].nunique(dropna=True) <= 30]

    # Guess target: first categorical with 2-10 unique values, else last numeric
    target = None
    for c in categorical:
        n = df[c].nunique(dropna=True)
        if 2 <= n <= 10:
            target = c
            break
    if target is None and numeric:
        target = numeric[-1]

    # Suggested features: numeric + low-cardinality categoricals, target excluded
    features = [c for c in (numeric + usable_cat) if c != target][:15]

    return {
        "target_guess": target,
        "features_guess": features,
        "numeric": numeric,
        "categorical": categorical,
        "usable_categorical": usable_cat,
        "classifiers": list(CLASSIFIERS.keys()),
        "regressors": list(REGRESSORS.keys()),
    }