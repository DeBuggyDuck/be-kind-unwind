from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import config_by_name
from .extensions import db, migrate


def register_error_handlers(app):
    @app.errorhandler(400)
    def handle_bad_request(err):
        message = (
            err.description
            if isinstance(err, HTTPException) and err.description
            else "Bad request"
        )
        return jsonify({"error": "Bad Request", "message": message}), 400

    @app.errorhandler(401)
    def handle_unauthorized(err):
        message = (
            err.description
            if isinstance(err, HTTPException) and err.description
            else "Authentication required"
        )
        return jsonify({"error": "Unauthorized", "message": message}), 401

    @app.errorhandler(403)
    def handle_forbidden(err):
        message = (
            err.description
            if isinstance(err, HTTPException) and err.description
            else "Forbidden"
        )
        return jsonify({"error": "Forbidden", "message": message}), 403

    @app.errorhandler(404)
    def handle_not_found(err):
        message = (
            err.description
            if isinstance(err, HTTPException) and err.description
            else "The requested URL was not found on the server."
        )
        return jsonify({"error": "Not Found", "message": message}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(err):
        message = (
            err.description
            if isinstance(err, HTTPException) and err.description
            else "The method is not allowed for the requested URL."
        )
        return jsonify({"error": "Method Not Allowed", "message": message}), 405

    @app.errorhandler(500)
    def handle_internal_server_error(err):
        return (
            jsonify(
                {
                    "error": "Internal Server Error",
                    "message": "An unexpected internal server error occurred.",
                }
            ),
            500,
        )


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

    register_error_handlers(app)

    return app