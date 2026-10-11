from flask import Blueprint, jsonify, request
from app.core import storage, formula

formula_bp = Blueprint("formula", __name__)


@formula_bp.get("/examples")
def examples():
    try:
        df = storage.load_working()
        return jsonify({"ok": True, "examples": formula.generate_examples(df)})
    except FileNotFoundError:
        return jsonify({"ok": True, "examples": []})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": True, "examples": [], "warning": str(e)})


@formula_bp.post("/preview")
def preview():
    try:
        body = request.get_json(silent=True) or {}
        expr = body.get("formula", "")
        if not expr.strip():
            return jsonify({"ok": False, "error": "Formula is empty."}), 400

        df = storage.load_working()
        info, _ = formula.apply_formula(df, expr)
        return jsonify({"ok": True, "result": info})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@formula_bp.post("/apply")
def apply():
    try:
        body = request.get_json(silent=True) or {}
        expr = body.get("formula", "")
        target = body.get("target", "").strip()

        if not expr.strip():
            return jsonify({"ok": False, "error": "Formula is empty."}), 400
        if not target:
            return jsonify({"ok": False, "error": "New column name is required."}), 400

        df = storage.load_working()
        df, info = formula.apply_and_store(df, expr, target)
        storage.save_working(df)
        return jsonify({"ok": True, "result": info, "shape": info["shape"]})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500