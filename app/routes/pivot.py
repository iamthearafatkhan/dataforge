from flask import Blueprint, jsonify, request, send_file
import io
import csv
from app.core import storage, pivot
from app.core import storage, pivot, exporter

pivot_bp = Blueprint("pivot", __name__)


@pivot_bp.get("/suggest")
def suggest():
    try:
        df = storage.load_working()
        return jsonify({
            "ok": True,
            "suggested": pivot.suggest_pivot(df),
            "columns": list(df.columns),
            "aggfuncs": list(pivot.AGG_FUNCS.keys()),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@pivot_bp.post("/run")
def run():
    try:
        body = request.get_json(silent=True) or {}
        df = storage.load_working()
        result = pivot.run_pivot(
            df,
            rows=body.get("rows", []),
            cols=body.get("cols", []),
            values=body.get("values", []),
            aggfuncs=body.get("aggfuncs", ["mean"]),
            fill_value=body.get("fill_value"),
            margins=bool(body.get("margins", False)),
        )
        return jsonify({"ok": True, "result": result})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@pivot_bp.post("/export")
def export():
    try:
        body = request.get_json(silent=True) or {}
        df = storage.load_working()
        result = pivot.run_pivot(
            df,
            rows=body.get("rows", []),
            cols=body.get("cols", []),
            values=body.get("values", []),
            aggfuncs=body.get("aggfuncs", ["mean"]),
            fill_value=body.get("fill_value"),
            margins=bool(body.get("margins", False)),
        )
        import io, csv
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(result["columns"])
        w.writerows(result["rows"])
        return send_file(
            io.BytesIO(buf.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=exporter.build_output_filename("csv", suffix="pivot"),
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500