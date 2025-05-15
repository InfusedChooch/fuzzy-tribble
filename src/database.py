from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from src.models import db
import os

def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, '..', 'templates')
    app = Flask(__name__, template_folder=template_dir)

    app.secret_key = 'Duck_Goon_Slap00'
    db_path = os.path.join(base_dir, '..', 'data', 'hallpass.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if not all(tbl in tables for tbl in ['students', 'passes', 'audit_log', 'pass_log']):
            db.create_all()

    return app
