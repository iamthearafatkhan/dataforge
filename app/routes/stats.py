from flask import Blueprint, jsonify, request
from app.core import storage, stats_engine

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/suggest")
def suggest():
    try:
        df = storage.load_working()
        return jsonify({"ok": True, **stats_engine.suggest_tests(df)})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@stats_bp.post("/run")
def run():
    try:
        body = request.get_json(silent=True) or {}
        kind = body.get("kind", "")
        params = body.get("params", {})
        df = storage.load_working()
        result = stats_engine.run_test(df, kind, params)
        return jsonify({"ok": True, "result": result})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500