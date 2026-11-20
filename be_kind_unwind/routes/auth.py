from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
import jwt
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from be_kind_unwind.extensions import db
from be_kind_unwind.models import User

auth_bp = Blueprint("auth", __name__)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Missing or invalid token",
                    }
                ),
                401,
            )

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Missing or invalid token",
                    }
                ),
                401,
            )

        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
            )
            g.current_user_id = int(payload["sub"])
            g.current_role = payload.get("role", "user")
        except jwt.ExpiredSignatureError:
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Token has expired",
                    }
                ),
                401,
            )
        except (jwt.PyJWTError, KeyError, ValueError, TypeError):
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Missing or invalid token",
                    }
                ),
                401,
            )

        return f(*args, **kwargs)

    return decorated


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not data:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Request body must be valid JSON",
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
        or not password.strip()
    ):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        "username, email, and password are required non-empty"
                        " strings"
                    ),
                }
            ),
            400,
        )

    clean_username = username.strip()
    clean_email = email.strip()

    user = User(
        username=clean_username,
        email=clean_email,
        password_hash=generate_password_hash(password),
        role="user",
        created_at=datetime.now(timezone.utc),
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": (
                        "A user with that username or email already exists"
                    ),
                }
            ),
            409,
        )

    return (
        jsonify(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Request body must be valid JSON",
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
        or not password.strip()
    ):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        "username and password are required non-empty strings"
                    ),
                }
            ),
            400,
        )

    user = User.query.filter_by(username=username.strip()).first()

    if user is None or not check_password_hash(user.password_hash, password):
        return (
            jsonify(
                {"error": "Unauthorized", "message": "Invalid credentials"}
            ),
            401,
        )

    expires_minutes = current_app.config.get(
        "JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 60
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }

    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

    return jsonify({"token": token}), 200


@auth_bp.route("/me", methods=["GET"])
@token_required
def me():
    user = db.session.get(User, g.current_user_id)
    if user is None:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "User not found",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            }
        ),
        200,
    )


@auth_bp.route("/me", methods=["PATCH"])
@token_required
def update_me():
    user = db.session.get(User, g.current_user_id)
    if user is None:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": "User not found",
                }
            ),
            404,
        )

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Request body must be a non-empty JSON object",
                }
            ),
            400,
        )

    restricted_fields = {"role", "password_hash", "id", "created_at"}
    if any(field in data for field in restricted_fields):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Cannot modify restricted fields",
                }
            ),
            400,
        )

    allowed_fields = {"username", "email"}
    unknown_fields = set(data.keys()) - allowed_fields
    if unknown_fields:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Only username and email can be updated",
                }
            ),
            400,
        )

    if "username" in data:
        username = data["username"]
        if not isinstance(username, str) or not username.strip():
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "message": "username must be a non-empty string",
                    }
                ),
                400,
            )
        user.username = username.strip()

    if "email" in data:
        email = data["email"]
        if not isinstance(email, str) or not email.strip():
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "message": "email must be a non-empty string",
                    }
                ),
                400,
            )
        user.email = email.strip()

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": (
                        "A user with that username or email already exists"
                    ),
                }
            ),
            409,
        )

    return (
        jsonify(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            }
        ),
        200,
    )


@auth_bp.route("/admin/users", methods=["GET"])
@token_required
def list_users():
    if g.current_role != "admin":
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "Admin access required",
                }
            ),
            403,
        )

    users = db.session.execute(db.select(User).order_by(User.id)).scalars().all()
    return (
        jsonify(
            [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat(),
                }
                for user in users
            ]
        ),
        200,
    )