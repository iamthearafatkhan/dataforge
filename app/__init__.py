import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, flash, redirect, url_for, session
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["STORAGE_DIR"], exist_ok=True)

    @app.before_request
    def make_session_permanent():
        session.permanent = True
        session.modified = True

    with app.app_context():
        from app.core.cleanup import purge_expired_sessions
        purge_expired_sessions()
        from app.core.db import init_schema
        init_schema()

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.preprocess import preprocess_bp
    from app.routes.visualize import visualize_bp
    from app.routes.export import export_bp
    from app.routes.pipeline import pipeline_bp
    from app.routes.sql import sql_bp
    from app.routes.pivot import pivot_bp
    from app.routes.formula import formula_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.stats import stats_bp
    from app.routes.ml import ml_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(preprocess_bp, url_prefix="/api/preprocess")
    app.register_blueprint(visualize_bp, url_prefix="/api/visualize")
    app.register_blueprint(export_bp, url_prefix="/api/export")
    app.register_blueprint(pipeline_bp, url_prefix="/api/pipeline")
    app.register_blueprint(sql_bp, url_prefix="/api/sql")
    app.register_blueprint(pivot_bp, url_prefix="/api/pivot")
    app.register_blueprint(formula_bp, url_prefix="/api/formula")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(stats_bp, url_prefix="/api/stats")
    app.register_blueprint(ml_bp, url_prefix="/api/ml")

    @app.errorhandler(413)
    def too_large(_e):
        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        msg = f"File exceeds the {limit_mb} MB limit."
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": msg}), 413
        flash(msg, "error")
        return redirect(url_for("main.index"))

    @app.context_processor
    def inject_globals():
        from app.core import storage
        try:
            has_data = storage.has_dataset()
        except Exception:
            has_data = False
        return {
            "has_data": has_data,
            "brand": {
                "name": "DataForge",
                "tagline": "Clean · Understand · Export",
                "github": "https://github.com/iamthearafatkhan",
                "linkedin": "https://www.linkedin.com/in/iamthearafatkhan",
                "website": "https://arafatkhan.vercel.app",
                "author": "Arafat Khan",
                "ttl_hours": app.config["SESSION_TTL_HOURS"],
            },
        }

    return app