# main.py
from src import create_app
from threading import Thread
from datetime import datetime, timezone
import json, os, time

_app = None

def get_app():
    global _app
    if _app is None:
        _app = create_app()
    return _app

def cleanup_inactive_rooms(interval=60, timeout=120):
    heartbeat_path = 'data/station_heartbeat.json'
    active_path = 'data/active_rooms.json'

    while True:
        now = datetime.now(timezone.utc)
        try:
            with open(heartbeat_path, 'r') as f:
                beats = json.load(f)
        except:
            beats = {}

        try:
            with open(active_path, 'r') as f:
                active = set(json.load(f))
        except:
            active = set()

        to_remove = set()
        for station, stamp in beats.items():
            try:
                last_seen = datetime.fromisoformat(stamp)
                if (now - last_seen).total_seconds() > timeout:
                    to_remove.add(station)
            except:
                continue

        if to_remove:
            updated = active - to_remove
            with open(active_path, 'w') as f:
                json.dump(sorted(updated), f)

        time.sleep(interval)

if __name__ == '__main__':
    app = get_app()
    Thread(target=cleanup_inactive_rooms, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
