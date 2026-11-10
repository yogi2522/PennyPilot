
import mysql.connector
from flask import Blueprint, jsonify
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

dashboard_bp = Blueprint("dashboard", __name__)


# Get the financial summary for a user
@dashboard_bp.route("/api/dashboard/<int:user_id>", methods=["GET"])
@jwt_required()
def get_dashboard_summary(user_id):
    user_id = int(get_jwt_identity())

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                COALESCE(
                    SUM(CASE
                        WHEN transaction_type = 'income'
                        THEN amount ELSE 0
                    END), 0
                ) AS total_income,

                COALESCE(
                    SUM(CASE
                        WHEN transaction_type = 'expense'
                        THEN amount ELSE 0
                    END), 0
                ) AS total_expenses

            FROM transactions
            WHERE user_id = %s
        """

        cursor.execute(query, (user_id,))
        summary = cursor.fetchone()

        total_income = float(summary["total_income"])
        total_expenses = float(summary["total_expenses"])
        balance = total_income - total_expenses

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": round(balance, 2)
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not retrieve dashboard summary"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
