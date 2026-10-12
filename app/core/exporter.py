import io
import os
import pandas as pd
from flask import session


def build_output_filename(ext: str, suffix: str = "") -> str:
    """Build a filename like dataforge_titanic.csv from the uploaded filename."""
    original = session.get("original_filename", "")
    base = "dataset"

    if original:
        # Strip path and extension
        raw = os.path.splitext(os.path.basename(original))[0]
        # Keep only safe characters
        cleaned = "".join(
            c if (c.isalnum() or c in "-_") else "_"
            for c in raw
        ).strip("_")
        if cleaned:
            base = cleaned[:60]   # cap length

    parts = ["dataforge", base]
    if suffix:
        parts.append(suffix)

    return f"{'_'.join(parts)}.{ext}"


def to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_json(df: pd.DataFrame) -> bytes:
    return df.to_json(orient="records", indent=2).encode("utf-8")


def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="cleaned")
    return buf.getvalue()


def to_xml(df: pd.DataFrame, root: str = "rows", row: str = "row") -> bytes:
    def esc(v):
        s = "" if pd.isna(v) else str(v)
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))

    parts = [f'<?xml version="1.0" encoding="UTF-8"?>', f"<{root}>"]
    for _, r in df.iterrows():
        parts.append(f"  <{row}>")
        for c in df.columns:
            tag = str(c).replace(" ", "_")
            parts.append(f"    <{tag}>{esc(r[c])}</{tag}>")
        parts.append(f"  </{row}>")
    parts.append(f"</{root}>")
    return "\n".join(parts).encode("utf-8")


EXPORTERS = {
    "csv":  (to_csv,   "text/csv",  "csv"),
    "json": (to_json,  "application/json", "json"),
    "xml":  (to_xml,   "application/xml",  "xml"),
    "xlsx": (to_excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
}