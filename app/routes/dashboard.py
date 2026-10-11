from flask import Blueprint, jsonify, request
from app.core import storage, dashboard

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/templates")
def templates():
    return jsonify({
        "ok": True,
        "templates": [
            {"key": k, "name": v["name"], "description": v["description"]}
            for k, v in dashboard.TEMPLATES.items()
        ],
    })


@dashboard_bp.get("/render/<key>")
def render(key):
    try:
        df = storage.load_working()
        result = dashboard.generate(key, df)
        return jsonify({"ok": True, "dashboard": result})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500