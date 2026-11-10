
import mysql.connector
from flask import Blueprint, jsonify, request
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
monthly_report_bp = Blueprint("monthly_report", __name__)


# Get a user's monthly financial report
@monthly_report_bp.route(
    "/api/reports/monthly/<int:user_id>",
    methods=["GET"]
)
@jwt_required()
def get_monthly_report(user_id):
    user_id = int(get_jwt_identity())

    year = request.args.get("year")
    month = request.args.get("month")

    if year is None or month is None:
        return jsonify({
            "status": "error",
            "message": "Please provide year and month"
        }), 400

    try:
        year = int(year)
        month = int(month)

        if year < 2000 or year > 2100:
            raise ValueError

        if month < 1 or month > 12:
            raise ValueError

        if user_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Provide a valid user_id, year, and month"
        }), 400

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
                ) AS total_expenses,

                COUNT(*) AS transaction_count

            FROM transactions
            WHERE user_id = %s
              AND YEAR(transaction_date) = %s
              AND MONTH(transaction_date) = %s
        """

        cursor.execute(query, (user_id, year, month))
        report = cursor.fetchone()

        total_income = float(report["total_income"])
        total_expenses = float(report["total_expenses"])
        balance = total_income - total_expenses

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "year": year,
            "month": month,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": round(balance, 2),
            "transaction_count": report["transaction_count"]
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not generate monthly report"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
