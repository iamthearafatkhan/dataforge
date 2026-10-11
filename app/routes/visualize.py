from flask import Blueprint, jsonify, request
from app.core import storage, visualizer

visualize_bp = Blueprint("visualize", __name__)


@visualize_bp.get("/overview")
def overview():
    df = storage.load_working()
    charts = {
        "missingness": visualizer.missingness_bar(df),
        "correlation": visualizer.correlation_heatmap(df),
    }
    return jsonify({"charts": charts, "columns": list(df.columns)})


@visualize_bp.get("/missingness_matrix")
def missingness_matrix():
    try:
        df = storage.load_working()
        fig = visualizer.missingness_matrix(df)
        return jsonify({"chart": fig})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@visualize_bp.post("/chart")
def chart():
    df = storage.load_working()
    body = request.get_json(silent=True) or {}
    kind = body.get("kind")

    try:
        if kind == "histogram":
            fig = visualizer.histogram(df, body["col"])
        elif kind == "box":
            fig = visualizer.boxplot(df, body["col"])
        elif kind == "box_category":
            fig = visualizer.box_by_category(df, body["y"], body["x"])
        elif kind == "violin_category":
            fig = visualizer.violin_by_category(df, body["y"], body["x"])
        elif kind == "value_counts":
            fig = visualizer.value_counts_bar(df, body["col"])
        elif kind == "scatter":
            fig = visualizer.scatter(df, body["x"], body["y"], body.get("color"))
        elif kind == "line":
            fig = visualizer.line(df, body["x"], body["y"])
        elif kind == "scatter_matrix":
            fig = visualizer.scatter_matrix(df, body.get("cols", []), body.get("color"))
        elif kind == "time_series":
            fig = visualizer.time_series(df, body["x"], body["y"], body.get("freq", "D"))
        elif kind == "category_heatmap":
            fig = visualizer.category_heatmap(df, body["row"], body["col"], body["value"], body.get("agg", "mean"))
        else:
            return jsonify({"error": "Unknown chart kind"}), 400

        if fig is None:
            return jsonify({"error": "Not enough data or columns for this chart."}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

    return jsonify({"chart": fig})