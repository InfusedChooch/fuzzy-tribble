# server_entry.py
from waitress import serve
from main import get_app
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="5000")
args = parser.parse_args()

serve(get_app(), host="0.0.0.0", port=int(args.port))
