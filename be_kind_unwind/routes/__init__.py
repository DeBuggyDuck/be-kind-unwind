from flask import Blueprint, g, jsonify, request

from be_kind_unwind.extensions import db
from be_kind_unwind.models import MoodCheckSession
from be_kind_unwind.routes.auth import token_required

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")


def session_to_dict(session):
    return {
        "id": session.id,
        "user_id": session.user_id,
        "mood": session.mood,
        "attention_span": session.attention_span,
        "time_commitment": session.time_commitment,
        "recommendation": session.recommendation,
        "notes": session.notes,
        "created_at": session.created_at.isoformat(),
    }


def validate_session_payload(data):
    if not isinstance(data, dict):
        return "Request body must be valid JSON"

    if "user_id" in data:
        return "user_id cannot be supplied in the request body"

    for field in ("mood", "attention_span", "recommendation"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"{field} is required and must be a non-empty string"

    time_commitment = data.get("time_commitment")
    if (
        isinstance(time_commitment, bool)
        or not isinstance(time_commitment, int)
        or time_commitment <= 0
    ):
        return "time_commitment is required and must be a positive integer"

    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        return "notes must be a string or null"

    return None


@sessions_bp.route("", methods=["GET"])
@token_required
def list_sessions():
    sessions = (
        db.session.execute(
            db.select(MoodCheckSession)
            .where(MoodCheckSession.user_id == g.current_user_id)
            .order_by(MoodCheckSession.id.asc())
        )
        .scalars()
        .all()
    )
    return jsonify([session_to_dict(s) for s in sessions]), 200


@sessions_bp.route("", methods=["POST"])
@token_required
def create_session():
    data = request.get_json(silent=True)
    error_message = validate_session_payload(data)
    if error_message:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": error_message,
                }
            ),
            400,
        )

    notes = data.get("notes")
    clean_notes = notes.strip() if isinstance(notes, str) and notes.strip() else None

    new_session = MoodCheckSession(
        user_id=g.current_user_id,
        mood=data["mood"].strip(),
        attention_span=data["attention_span"].strip(),
        time_commitment=data["time_commitment"],
        recommendation=data["recommendation"].strip(),
        notes=clean_notes,
    )

    db.session.add(new_session)
    db.session.commit()

    return jsonify(session_to_dict(new_session)), 201