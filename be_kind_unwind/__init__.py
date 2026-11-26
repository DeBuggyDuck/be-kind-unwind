from flask import Flask

from .config import config_by_name

from .extensions import db, migrate

from .models import MoodCheckSession, User  # noqa: F401

def create_app(config_name=None):
    if config_name is None:
        config_name = "development"

    if config_name not in config_by_name:
        raise ValueError(
            f"Unknown config '{config_name}'. Must be one of {list(config_by_name.keys())}"
        )

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    from .models import User  # noqa: F401
    from .routes import sessions_bp
    from .routes.auth import auth_bp
    from .routes.health import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(health_bp)

    return app