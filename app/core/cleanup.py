import os
import time
from flask import current_app

def purge_expired_sessions():
    """Delete session folders older than SESSION_TTL_HOURS."""
    root = current_app.config["STORAGE_DIR"]
    ttl = current_app.config["SESSION_TTL_HOURS"] * 3600
    now = time.time()
    if not os.path.isdir(root):
        return
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        try:
            newest = max(
                (os.path.getmtime(os.path.join(path, f)) for f in os.listdir(path)),
                default=os.path.getmtime(path),
            )
            if now - newest > ttl:
                for f in os.listdir(path):
                    os.remove(os.path.join(path, f))
                os.rmdir(path)
        except OSError:
            pass