import io
from flask import Blueprint, jsonify, request, session, send_file, flash, redirect, url_for
import pandas as pd
from app.core import storage, pipeline

pipeline_bp = Blueprint("pipeline", __name__)


@pipeline_bp.get("/export")
def export_pipeline():
    """Download the current preprocessing recipe as YAML."""
    try:
        recipe = session.get("last_recipe")
        if not recipe:
            return jsonify({"error": "Run preprocessing first — no recipe to export."}), 400

        yml = pipeline.to_yaml(recipe)

        # Build dataforge_<original>.yaml
        from app.core import exporter
        filename = exporter.build_output_filename("yaml")

        return send_file(
            io.BytesIO(yml.encode("utf-8")),
            mimetype="application/x-yaml",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pipeline_bp.post("/preview")
def preview():
    """Preview the recipe that would be exported."""
    recipe = session.get("last_recipe")
    if not recipe:
        return jsonify({"recipe": None})
    return jsonify({"recipe": recipe, "yaml": pipeline.to_yaml(recipe)})


@pipeline_bp.post("/apply")
def apply_pipeline():
    """Upload a new CSV + a YAML recipe; return the transformed data summary."""
    try:
        file = request.files.get("file")
        yaml_file = request.files.get("pipeline")
        if not file or not yaml_file:
            return jsonify({"ok": False, "error": "Both a data file and a pipeline file are required."}), 400

        name = file.filename.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(file)
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        elif name.endswith(".json"):
            df = pd.read_json(file)
        else:
            return jsonify({"ok": False, "error": "Unsupported data file type."}), 400

        recipe = pipeline.from_yaml(yaml_file.read().decode("utf-8"))
        df_out, fitted = pipeline.apply_pipeline_to_df(df, recipe, fitted=None)
        pipeline.save_fitted_state(fitted)

        storage.save_raw(df_out)
        session["last_recipe"] = recipe

        return jsonify({
            "ok": True,
            "shape": {"rows": len(df_out), "cols": len(df_out.columns)},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500