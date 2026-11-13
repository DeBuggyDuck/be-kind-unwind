from flask import Blueprint

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")


@sessions_bp.route("", methods=["GET"])
def list_sessions():
    return "sessions endpoint placeholder"
