from src.database import create_app
from threading import Thread
from datetime import datetime, timezone
import json, os, time, sys

_app = None
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vendor"))

def get_app():
    global _app
    if _app is None:
        _app = create_app()
    return _app


if __name__ == "__main__":
    app = get_app()


    debug_enabled = os.getenv("DEBUG", "").lower() in {"1", "true", "yes"}

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug_enabled,
        use_reloader=False,   # ← keeps a single process the GUI can stop
    )
