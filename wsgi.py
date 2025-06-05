# wsgi.py
from src.database import create_app
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vendor"))
_app = None

def get_app():
    global _app
    if _app is None:
        _app = create_app()
    return _app

# Optional: enable standalone run
if __name__ == "__main__":
    app = get_app()
    app.run()

