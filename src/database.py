from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from src.models import db
import os

def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, '..', 'templates')
    app = Flask(__name__, template_folder=template_dir)

    app.secret_key = 'Duck_Goon_Slap00'  # or any secure random string

    # Configure SQLite database path
    db_path = os.path.join(base_dir, '..', 'data', 'hallpass.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize SQLAlchemy
    db.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    return app