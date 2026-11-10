
import mysql.connector
from flask import Blueprint, jsonify, request
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
budget_progress_bp = Blueprint("budget_progress", __name__)


# Compare actual expenses with the monthly budget
@budget_progress_bp.route(
    "/api/budget-progress/<int:user_id>",
    methods=["GET"]
)
@jwt_required()
def get_budget_progress(user_id):
    user_id = int(get_jwt_identity())

    month = request.args.get("month")
    year = request.args.get("year")
    if month is None or year is None:
        return jsonify({
            "status": "error",
            "message": "Please provide month and year"
        }), 400

    try:
        month = int(month)
        year = int(year)

        if user_id <= 0 or month < 1 or month > 12:
            raise ValueError

        if year < 2000 or year > 2100:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Provide a valid user_id, month, and year"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                b.budget_id,
                b.category_id,
                c.category_name,
                b.amount AS budget_amount,

                COALESCE(SUM(t.amount), 0) AS spent_amount

            FROM budgets b

            JOIN categories c
                ON b.category_id = c.category_id

            LEFT JOIN transactions t
                ON t.category_id = b.category_id
                AND t.user_id = b.user_id
                AND t.transaction_type = 'expense'
                AND YEAR(t.transaction_date) = b.year
                AND MONTH(t.transaction_date) = b.month

            WHERE b.user_id = %s
              AND b.month = %s
              AND b.year = %s

            GROUP BY
                b.budget_id,
                b.category_id,
                c.category_name,
                b.amount

            ORDER BY c.category_name
        """

        cursor.execute(query, (user_id, month, year))
        results = cursor.fetchall()

        progress = []

        for item in results:
            budget_amount = float(item["budget_amount"])
            spent_amount = float(item["spent_amount"])
            remaining_amount = round(
                budget_amount - spent_amount, 2
            )

            percentage_used = round(
                (spent_amount / budget_amount) * 100, 2
            )

            if spent_amount > budget_amount:
                budget_status = "over_budget"
            else:
                budget_status = "within_budget"

            progress.append({
                "budget_id": item["budget_id"],
                "category_id": item["category_id"],
                "category_name": item["category_name"],
                "budget_amount": budget_amount,
                "spent_amount": spent_amount,
                "remaining_amount": remaining_amount,
                "percentage_used": percentage_used,
                "status": budget_status
            })

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "month": month,
            "year": year,
            "count": len(progress),
            "budget_progress": progress
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not calculate budget progress"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
