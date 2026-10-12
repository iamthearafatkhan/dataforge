from flask import Blueprint, jsonify, request
from app.core import storage, ml_engine

ml_bp = Blueprint("ml", __name__)


@ml_bp.get("/suggest")
def suggest():
    try:
        df = storage.load_working()
        return jsonify({"ok": True, **ml_engine.suggest_ml(df)})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@ml_bp.post("/train")
def train():
    try:
        body = request.get_json(silent=True) or {}
        target = body.get("target", "")
        features = body.get("features", [])
        model_key = body.get("model", "random_forest")
        test_size = float(body.get("test_size", 0.2))

        if not target:
            return jsonify({"ok": False, "error": "Pick a target column."}), 400
        if not features:
            return jsonify({"ok": False, "error": "Pick at least one feature."}), 400

        df = storage.load_working()
        result = ml_engine.train_model(df, target, features, model_key, test_size)
        return jsonify({"ok": True, "result": result})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500