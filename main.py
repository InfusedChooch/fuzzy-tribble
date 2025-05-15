from src import create_app
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


def cleanup_inactive_rooms(interval: int = 60, timeout: int = 120):
    heartbeat_path = "data/station_heartbeat.json"
    active_path    = "data/active_rooms.json"

    while True:
        now = datetime.now(timezone.utc)

        try:
            with open(heartbeat_path, "r") as fh:
                beats = json.load(fh)
        except Exception:
            beats = {}

        try:
            with open(active_path, "r") as fh:
                active = set(json.load(fh))
        except Exception:
            active = set()

        expired = set()
        for station, stamp in beats.items():
            try:
                last_seen = datetime.fromisoformat(stamp)
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                if (now - last_seen).total_seconds() > timeout:
                    expired.add(station)
            except Exception:
                continue

        if expired:
            with open(active_path, "w") as fh:
                json.dump(sorted(active - expired), fh)

        time.sleep(interval)


if __name__ == "__main__":
    app = get_app()

    Thread(target=cleanup_inactive_rooms, daemon=True).start()

    debug_enabled = os.getenv("DEBUG", "").lower() in {"1", "true", "yes"}

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug_enabled,
        use_reloader=False,   # ← keeps a single process the GUI can stop
    )
