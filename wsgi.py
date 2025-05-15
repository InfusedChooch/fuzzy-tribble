# wsgi.py
from src import create_app

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
