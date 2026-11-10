
import mysql.connector
from flask import Blueprint, jsonify, request
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
budget_bp = Blueprint("budgets", __name__)


# Create a new budget
@budget_bp.route("/api/budgets", methods=["POST"])
@jwt_required()
def create_budget():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Please provide budget details as JSON"
        }), 400

    required_fields = [
        "category_id",
        "amount",
        "month",
        "year"
    ]

    for field in required_fields:
        if field not in data:
            return jsonify({
                "status": "error",
                "message": f"Missing required field: {field}"
            }), 400

    try:
        user_id = int(get_jwt_identity())
        category_id = int(data["category_id"])
        month = int(data["month"])
        year = int(data["year"])

        if isinstance(data["amount"], bool):
            raise ValueError

        amount = float(data["amount"])

        if user_id <= 0 or category_id <= 0:
            raise ValueError

        if amount <= 0 or amount == float("inf") or amount != amount:
            raise ValueError

        if month < 1 or month > 12:
            raise ValueError

        if year < 2000 or year > 2100:
            raise ValueError

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "status": "error",
            "message": "Provide valid IDs, a positive amount, month 1-12, and year 2000-2100"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Check that the category belongs to this user
        # and is an expense category
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_id = %s
              AND user_id = %s
              AND category_type = 'expense'
            """,
            (category_id, user_id)
        )

        if cursor.fetchone() is None:
            return jsonify({
                "status": "error",
                "message": "Expense category not found for this user"
            }), 400

        # Avoid creating a duplicate budget for the same
        # user, category, month, and year
        cursor.execute(
            """
            SELECT budget_id
            FROM budgets
            WHERE user_id = %s
              AND category_id = %s
              AND month = %s
              AND year = %s
            """,
            (user_id, category_id, month, year)
        )

        if cursor.fetchone() is not None:
            return jsonify({
                "status": "error",
                "message": "A budget already exists for this category and month"
            }), 409

        cursor.execute(
            """
            INSERT INTO budgets (
                user_id, category_id, amount, month, year
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, category_id, amount, month, year)
        )

        connection.commit()
        new_budget_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Budget created successfully",
            "budget_id": new_budget_id
        }), 201

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Could not create budget"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# Get all budgets for a user
# Get all budgets for a user
@budget_bp.route("/api/budgets/<int:user_id>", methods=["GET"])
@jwt_required()
def get_budgets(user_id):
    user_id = int(get_jwt_identity())

    if user_id <= 0:
        return jsonify({
            "status": "error",
            "message": "user_id must be positive"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                b.budget_id,
                b.user_id,
                b.category_id,
                c.category_name,
                b.amount,
                b.month,
                b.year
            FROM budgets b
            JOIN categories c
                ON b.category_id = c.category_id
            WHERE b.user_id = %s
            ORDER BY b.year DESC, b.month DESC, c.category_name
            """,
            (user_id,)
        )

        budgets = cursor.fetchall()

        for budget in budgets:
            budget["amount"] = float(budget["amount"])

        return jsonify({
            "status": "success",
            "count": len(budgets),
            "budgets": budgets
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not retrieve budgets"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
