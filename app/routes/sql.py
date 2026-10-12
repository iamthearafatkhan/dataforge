import io
import csv
from flask import Blueprint, jsonify, request, send_file
from app.core import storage, sql_engine
from app.core import storage, sql_engine, exporter

sql_bp = Blueprint("sql", __name__)


@sql_bp.get("/schema")
def schema():
    try:
        df = storage.load_working()
        return jsonify({
            "ok": True,
            "schema": sql_engine.describe(df),
            "suggestions": sql_engine.suggest_queries(df),
        })
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "Session expired. Please re-upload."}), 410
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@sql_bp.post("/run")
def run():
    try:
        body = request.get_json(silent=True) or {}
        sql = body.get("sql", "")
        if not sql.strip():
            return jsonify({"ok": False, "error": "Empty query."}), 400

        df = storage.load_working()
        result = sql_engine.run_query(df, sql)
        return jsonify({"ok": True, "result": result})

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "Session expired. Please re-upload."}), 410
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Query failed: {e}"}), 500


@sql_bp.post("/export")
def export():
    """Re-run the query and stream the full result as CSV or JSON."""
    try:
        body = request.get_json(silent=True) or {}
        sql = body.get("sql", "")
        fmt = (request.args.get("fmt") or "csv").lower()
        if not sql.strip():
            return jsonify({"ok": False, "error": "Empty query."}), 400

        df = storage.load_working()
        result = sql_engine.run_query(df, sql, max_rows=100_000)

        if fmt == "csv":
            import csv
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(result["columns"])
            w.writerows(result["rows"])
            data = buf.getvalue().encode("utf-8")
            return send_file(
                io.BytesIO(data),
                mimetype="text/csv",
                as_attachment=True,
                download_name=exporter.build_output_filename("csv", suffix="query"),
            )

        if fmt == "json":
            import json
            payload = {
                "columns": result["columns"],
                "rows": result["rows"],
                "row_count": result["row_count"],
            }
            data = json.dumps(payload, indent=2, default=str).encode("utf-8")
            return send_file(
                io.BytesIO(data),
                mimetype="application/json",
                as_attachment=True,
                download_name=exporter.build_output_filename("json", suffix="query"),
            )

        return jsonify({"ok": False, "error": "Unsupported format."}), 400

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500