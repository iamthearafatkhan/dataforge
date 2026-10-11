from flask import Blueprint, send_file, abort, current_app
import io
from app.core import storage, exporter

export_bp = Blueprint("export", __name__)

@export_bp.get("/<fmt>")
def download(fmt: str):
    if fmt not in exporter.EXPORTERS:
        abort(400)
    df = storage.load_working()
    fn, mimetype, ext = exporter.EXPORTERS[fmt]
    data = fn(df)
    return send_file(
        io.BytesIO(data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"dataforge_cleaned.{ext}",
    )