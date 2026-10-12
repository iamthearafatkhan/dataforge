from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import pandas as pd
from app.core import storage

main_bp = Blueprint("main", __name__)


def _expire_guard():
    try:
        if not storage.has_dataset():
            return redirect(url_for("main.index"))
        storage.load_working()
    except FileNotFoundError:
        flash("Your session expired. Please re-upload your file.", "error")
        return redirect(url_for("main.index"))
    return None


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or f.filename == "":
        flash("Please choose a file.", "error")
        return redirect(url_for("main.index"))

    original_name = f.filename
    name = original_name.lower()

    try:
        if name.endswith(".csv"):
            df = pd.read_csv(f)
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(f)
        elif name.endswith(".json"):
            df = pd.read_json(f)
        else:
            flash("Unsupported file type.", "error")
            return redirect(url_for("main.index"))
    except Exception as e:
        flash(f"Could not read file: {e}", "error")
        return redirect(url_for("main.index"))

    if df.empty:
        flash("File is empty.", "error")
        return redirect(url_for("main.index"))

    # Remember the original filename for future downloads
    session["original_filename"] = original_name
    session.pop("fitted", None)

    storage.save_raw(df)
    flash(f"Loaded {len(df):,} rows × {len(df.columns)} columns.", "success")
    return redirect(url_for("main.profile_page"))


@main_bp.route("/profile")
def profile_page():
    g = _expire_guard()
    return g or render_template("profile.html")


@main_bp.route("/preprocess")
def preprocess_page():
    g = _expire_guard()
    return g or render_template("preprocess.html")


@main_bp.route("/visualize")
def visualize_page():
    g = _expire_guard()
    return g or render_template("visualize.html")


@main_bp.route("/sql")
def sql_page():
    g = _expire_guard()
    return g or render_template("sql.html")


@main_bp.route("/pivot")
def pivot_page():
    g = _expire_guard()
    return g or render_template("pivot.html")


@main_bp.route("/formula")
def formula_page():
    g = _expire_guard()
    return g or render_template("formula.html")


@main_bp.route("/dashboard")
def dashboard_page():
    g = _expire_guard()
    return g or render_template("dashboard.html")


@main_bp.route("/stats")
def stats_page():
    g = _expire_guard()
    return g or render_template("stats.html")


@main_bp.route("/ml")
def ml_page():
    g = _expire_guard()
    return g or render_template("ml.html")


@main_bp.route("/export")
def export_page():
    g = _expire_guard()
    return g or render_template("export.html")


@main_bp.route("/reset", methods=["POST"])
def reset():
    storage.reset_working()
    session.pop("fitted", None)
    flash("Reset to original dataset.", "success")
    return redirect(url_for("main.profile_page"))