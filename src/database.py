"""
Application factory + table-exist check
──────────────────────────────────────
• Uses the newer schema (users, student_periods, passes, pass_events, audit_log)
• Registers every blueprint that was previously in src/__init__.py
• Only creates the tables if one of the required ones is missing
"""

import os
from flask import Flask
from sqlalchemy import inspect
from .models import db

# ─────────────────────────── blueprint imports ──────────────────────────
from .routes.admin    import admin_bp
from .routes.auth     import auth_bp
from .routes.students import students_bp
from .routes.report   import report_bp
from .routes.passlog  import passlog_bp
from .routes.core     import core_bp, ping_bp


def create_app() -> Flask:
    base_dir    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_dir = os.path.join(base_dir, "templates")
    static_dir   = os.path.join(base_dir, "static")
    data_dir     = os.path.join(base_dir, "data")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )

    # ───── configuration ─────
    app.secret_key = os.environ.get("SECRET_KEY", "Duck_Goon_Slap00")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(data_dir, 'hallpass.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # ───── blueprints ─────
    app.register_blueprint(ping_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(passlog_bp)

    # ───── create tables only if needed ─────
    with app.app_context():
        inspector = inspect(db.engine)
        existing  = set(inspector.get_table_names())
        required  = {
            "users",
            "student_periods",
            "passes",
            "pass_events",
            "audit_log",
        }
        if not required.issubset(existing):
            db.create_all()

    return app
