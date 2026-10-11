from flask import Blueprint, jsonify, request, session
from app.core import storage, profiler, imputer, cleaner
from app.core import pipeline

preprocess_bp = Blueprint("preprocess", __name__)

@preprocess_bp.get("/profile")
def profile():
    df = storage.load_working()
    return jsonify({
        "shape": {"rows": len(df), "cols": len(df.columns)},
        "columns": profiler.profile_columns(df),
    })

@preprocess_bp.post("/clean")
def clean():
    try:
        df = storage.load_working()
        body = request.get_json(silent=True) or {}
        ops = body.get("operations", [])
        session["cleaning_ops"] = ops   # remember which were applied

        if "strip_whitespace" in ops:
            df = cleaner.strip_whitespace(df)
        if "fix_dtypes" in ops:
            df = cleaner.fix_dtypes(df)
        if "drop_duplicates" in ops:
            df = cleaner.drop_duplicates(df)

        storage.save_working(df)
        return jsonify({"ok": True, "shape": {"rows": len(df), "cols": len(df.columns)}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@preprocess_bp.post("/impute")
def impute():
    try:
        df = storage.load_working()
        body = request.get_json(silent=True) or {}
        strategies = body.get("strategies", {})
        is_train = body.get("is_train", True)

        fitted = session.get("fitted") if not is_train else None
        df2, new_fitted = imputer.apply_strategies(
            df, strategies, is_train=is_train, fitted=fitted
        )
        recipe = pipeline.build_pipeline(
            cleaning_ops=session.get("cleaning_ops", []),
            strategies=strategies,
            dataset_meta={"rows": len(df2), "columns": list(df2.columns)},
        )
        session["last_recipe"] = recipe

        if is_train:
            session["fitted"] = _json_safe(new_fitted)

        storage.save_working(df2)
        return jsonify({
            "ok": True,
            "shape": {"rows": len(df2), "cols": len(df2.columns)},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()   # prints to terminal for your debugging
        return jsonify({"ok": False, "error": str(e)}), 500

def _json_safe(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, (int, float, str, type(None))):
            out[k] = v
        else:
            out[k] = None  # sklearn model not JSON-serialisable; store on disk in prod
    return out