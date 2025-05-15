# src/__init__.py

from flask import Flask
from .models import db
import os

def create_app():
    # Resolve base directory for template and static paths
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static')
    )

    # Secret key and database config
    app.secret_key = os.environ.get("SECRET_KEY", "Duck_Goon_Slap00")
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(base_dir, 'data', 'hallpass.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Register route blueprints
    from .routes.admin import admin_bp
    from .routes.auth import auth_bp
    from .routes.students import students_bp
    from .routes.report import report_bp
    from .routes.passlog import passlog_bp
    from .routes.core import core_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(passlog_bp)

    with app.app_context():
        db.create_all()

    return app
