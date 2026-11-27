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


def get_owned_session(session_id):
    session = db.session.get(MoodCheckSession, session_id)
    if session is None or session.user_id != g.current_user_id:
        return None
    return session


def validate_session_payload(data, partial=False):
    if not isinstance(data, dict):
        return {"_schema": "Request body must be valid JSON"}

    errors = {}

    if "user_id" in data:
        errors["user_id"] = "user_id cannot be supplied in the request body"

    unknown_fields = sorted(set(data.keys()) - UPDATABLE_SESSION_FIELDS - {"user_id"})
    if unknown_fields:
        errors["_schema"] = (
            f"Cannot modify restricted or unknown fields: {', '.join(unknown_fields)}"
        )

    if partial and not data:
        errors["_schema"] = "At least one updatable field must be provided"

    for field in ("mood", "attention_span", "recommendation"):
        if not partial or field in data:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                if partial:
                    errors[field] = f"{field} must be a non-empty string"
                else:
                    errors[field] = f"{field} is required and must be a non-empty string"

    if not partial or "time_commitment" in data:
        time_commitment = data.get("time_commitment")
        if (
            isinstance(time_commitment, bool)
            or not isinstance(time_commitment, int)
            or time_commitment <= 0
        ):
            if partial:
                errors["time_commitment"] = "time_commitment must be a positive integer"
            else:
                errors["time_commitment"] = (
                    "time_commitment is required and must be a positive integer"
                )

    if "notes" in data:
        notes = data.get("notes")
        if notes is not None and not isinstance(notes, str):
            errors["notes"] = "notes must be a string or null"

    return errors or None


@sessions_bp.route("", methods=["GET"])
@token_required
def list_sessions():
    raw_page = request.args.get("page", "1")
    raw_per_page = request.args.get("per_page", "10")

    try:
        page = int(raw_page)
        per_page = int(raw_per_page)
    except (TypeError, ValueError):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "page and per_page must be positive integers",
                }
            ),
            400,
        )

    if page < 1 or per_page < 1:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "page and per_page must be positive integers",
                }
            ),
            400,
        )

    if per_page > 50:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "per_page cannot exceed 50",
                }
            ),
            400,
        )

    base_query = db.select(MoodCheckSession).where(
        MoodCheckSession.user_id == g.current_user_id
    )

    total = db.session.scalar(
        db.select(db.func.count()).select_from(base_query.subquery())
    )
    pages = (total + per_page - 1) // per_page if total > 0 else 0

    offset = (page - 1) * per_page
    sessions = (
        db.session.execute(
            base_query.order_by(MoodCheckSession.id.asc())
            .limit(per_page)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    return (
        jsonify(
            {
                "items": [session_to_dict(s) for s in sessions],
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
            }
        ),
        200,
    )


@sessions_bp.route("", methods=["POST"])
@token_required
def create_session():
    data = request.get_json(silent=True)
    errors = validate_session_payload(data, partial=False)
    if errors:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Validation failed",
                    "details": errors,
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
    session = get_owned_session(session_id)
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
    errors = validate_session_payload(data, partial=True)
    if errors:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Validation failed",
                    "details": errors,
                }
            ),
            400,
        )

    session = get_owned_session(session_id)
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
    session = get_owned_session(session_id)
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