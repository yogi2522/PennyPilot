
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
import mysql.connector
from db import get_db_connection


auth_bp = Blueprint("auth", __name__)


# =========================
# SIGNUP API
# =========================
@auth_bp.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Please provide signup details as JSON"
        }), 400

    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (full_name, email, password)
    ):
        return jsonify({
            "status": "error",
            "message": "Name, email, and password are required"
        }), 400

    full_name = full_name.strip()
    email = email.strip().lower()

    if len(full_name) > 100:
        return jsonify({
            "status": "error",
            "message": "Name cannot exceed 100 characters"
        }), 400

    if len(email) > 255 or "@" not in email:
        return jsonify({
            "status": "error",
            "message": "Please provide a valid email address"
        }), 400

    if len(password) < 8:
        return jsonify({
            "status": "error",
            "message": "Password must contain at least 8 characters"
        }), 400

    if len(password) > 1024:
        return jsonify({
            "status": "error",
            "message": "Password is too long"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,)
        )

        if cursor.fetchone() is not None:
            return jsonify({
                "status": "error",
                "message": "An account with this email already exists"
            }), 409

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (full_name, email, password_hash)
        )

        user_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Account created successfully",
            "user": {
                "user_id": user_id,
                "full_name": full_name,
                "email": email
            }
        }), 201

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Could not create account"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# =========================
# LOGIN API
# =========================
@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Please provide login details as JSON"
        }), 400

    email = data.get("email")
    password = data.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    email = email.strip().lower()

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT user_id, full_name, email, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid email or password"
            }), 401

        # Generate JWT after successful authentication
        access_token = create_access_token(
            identity=str(user["user_id"])
        )

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "access_token": access_token,
            "user": {
                "user_id": user["user_id"],
                "full_name": user["full_name"],
                "email": user["email"]
            }
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not process login"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
