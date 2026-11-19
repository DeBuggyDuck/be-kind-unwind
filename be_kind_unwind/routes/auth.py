from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
import jwt
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "username, email, and password are required non-empty strings",
                }
            ),
            400,
        )

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(email, str)
        or not email.strip()
        or not isinstance(password, str)
        or len(password) == 0
    ):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "username, email, and password are required non-empty strings",
                }
            ),
            400,
        )

    clean_username = username.strip()
    clean_email = email.strip()

    existing_user = User.query.filter(
        or_(User.username == clean_username, User.email == clean_email)
    ).first()
    if existing_user is not None:
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": "A user with that username or email already exists",
                }
            ),
            409,
        )

    user = User(
        username=clean_username,
        email=clean_email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    created_at = user.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return (
        jsonify(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": created_at.isoformat(),
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "username and password are required non-empty strings",
                }
            ),
            400,
        )

    username = data.get("username")
    password = data.get("password")

    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(password, str)
        or len(password) == 0
    ):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "username and password are required non-empty strings",
                }
            ),
            400,
        )

    user = User.query.filter_by(username=username.strip()).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "message": "Invalid credentials",
                }
            ),
            401,
        )

    expires_minutes = current_app.config["JWT_ACCESS_TOKEN_EXPIRES_MINUTES"]
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

    return jsonify({"token": token}), 200