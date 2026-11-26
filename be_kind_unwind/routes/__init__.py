from flask import Blueprint, g, jsonify, request

from be_kind_unwind.extensions import db
from be_kind_unwind.models import MoodCheckSession
from be_kind_unwind.routes.auth import token_required

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")

UPDATABLE_SESSION_FIELDS = {
    "mood",
    "attention_span",
    "time_commitment",
    "recommendation",
    "notes",
}


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


def validate_session_payload(data, partial=False):
    if not isinstance(data, dict):
        return "Request body must be valid JSON"

    if "user_id" in data:
        return "user_id cannot be supplied in the request body"

    unknown_fields = set(data.keys()) - UPDATABLE_SESSION_FIELDS
    if unknown_fields:
        return "Cannot modify restricted or unknown fields"

    if partial and not data:
        return "At least one updatable field must be provided"

    for field in ("mood", "attention_span", "recommendation"):
        if not partial or field in data:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                if partial:
                    return f"{field} must be a non-empty string"
                return f"{field} is required and must be a non-empty string"

    if not partial or "time_commitment" in data:
        time_commitment = data.get("time_commitment")
        if (
            isinstance(time_commitment, bool)
            or not isinstance(time_commitment, int)
            or time_commitment <= 0
        ):
            if partial:
                return "time_commitment must be a positive integer"
            return "time_commitment is required and must be a positive integer"

    if "notes" in data:
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
    error_message = validate_session_payload(data, partial=False)
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
    clean_notes = (
        notes.strip() if isinstance(notes, str) and notes.strip() else None
    )

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


@sessions_bp.route("/<int:session_id>", methods=["GET"])
@token_required
def get_session(session_id):
    session = db.session.get(MoodCheckSession, session_id)
    if session is None:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "Session not found",
                }
            ),
            404,
        )

    return jsonify(session_to_dict(session)), 200


@sessions_bp.route("/<int:session_id>", methods=["PATCH"])
@token_required
def update_session(session_id):
    data = request.get_json(silent=True)
    error_message = validate_session_payload(data, partial=True)
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

    session = db.session.get(MoodCheckSession, session_id)
    if session is None:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "Session not found",
                }
            ),
            404,
        )

    if "mood" in data:
        session.mood = data["mood"].strip()
    if "attention_span" in data:
        session.attention_span = data["attention_span"].strip()
    if "time_commitment" in data:
        session.time_commitment = data["time_commitment"]
    if "recommendation" in data:
        session.recommendation = data["recommendation"].strip()
    if "notes" in data:
        notes = data["notes"]
        session.notes = (
            notes.strip() if isinstance(notes, str) and notes.strip() else None
        )

    db.session.commit()

    return jsonify(session_to_dict(session)), 200


@sessions_bp.route("/<int:session_id>", methods=["DELETE"])
@token_required
def delete_session(session_id):
    session = db.session.get(MoodCheckSession, session_id)
    if session is None:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "Session not found",
                }
            ),
            404,
        )

    db.session.delete(session)
    db.session.commit()

    return "", 204