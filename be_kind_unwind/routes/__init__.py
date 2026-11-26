from flask import Blueprint, g, jsonify

from be_kind_unwind.routes.auth import token_required

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")

@sessions_bp.route("", methods=["GET"])
@token_required
def list_sessions():
    return (
        jsonify(
            {
                "user_id": g.current_user_id,
                "sessions": [],
            }
        ),
        200,
    )