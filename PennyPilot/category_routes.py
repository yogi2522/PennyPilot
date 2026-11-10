
import mysql.connector
from flask import Blueprint, jsonify
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
category_bp = Blueprint("categories", __name__)


# Retrieve all categories for a user
@category_bp.route("/api/categories/<int:user_id>", methods=["GET"])
@jwt_required()
def get_categories(user_id):
    user_id = int(get_jwt_identity())
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                category_id,
                user_id,
                category_name,
                category_type
            FROM categories
            WHERE user_id = %s
            ORDER BY category_type, category_name
        """

        cursor.execute(query, (user_id,))
        categories = cursor.fetchall()

        return jsonify({
            "status": "success",
            "count": len(categories),
            "categories": categories
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not retrieve categories"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
