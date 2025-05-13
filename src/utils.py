import json
import os

ACTIVE_ROOMS_FILE = os.path.join('data', 'active_rooms.json')

def get_active_rooms():
    try:
        with open(ACTIVE_ROOMS_FILE) as f:
            return set(json.load(f))
    except:
        return set()

def activate_room(room):
    rooms = get_active_rooms()
    rooms.add(room)
    with open(ACTIVE_ROOMS_FILE, 'w') as f:
        json.dump(sorted(rooms), f)

def deactivate_room(room):
    rooms = get_active_rooms()
    rooms.discard(room)
    with open(ACTIVE_ROOMS_FILE, 'w') as f:
        json.dump(sorted(rooms), f)
