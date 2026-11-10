
import mysql.connector
from datetime import date
from flask import Blueprint, jsonify, request
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

savings_goal_bp = Blueprint("savings_goals", __name__)


# Create a new savings goal
@savings_goal_bp.route("/api/savings-goals", methods=["POST"])
@jwt_required()
def create_savings_goal():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Please provide savings goal details as JSON"
        }), 400

    required_fields = ["goal_name", "target_amount"]

    for field in required_fields:
        if field not in data:
            return jsonify({
                "status": "error",
                "message": f"Missing required field: {field}"
            }), 400

    try:
        user_id = int(get_jwt_identity())
        goal_name = data["goal_name"]
        target_amount = data["target_amount"]
        current_amount = data.get("current_amount", 0)
        target_date = data.get("target_date")

        if not isinstance(goal_name, str):
            raise ValueError

        goal_name = goal_name.strip()

        if not goal_name or len(goal_name) > 100:
            raise ValueError

        if isinstance(target_amount, bool) or isinstance(current_amount, bool):
            raise ValueError

        target_amount = float(target_amount)
        current_amount = float(current_amount)

        if user_id <= 0:
            raise ValueError

        if (
            target_amount <= 0
            or not float("-inf") < target_amount < float("inf")
        ):
            raise ValueError

        if (
            current_amount < 0
            or not float("-inf") < current_amount < float("inf")
            or current_amount > target_amount
        ):
            raise ValueError

        if target_date is not None:
            if not isinstance(target_date, str):
                raise ValueError
            target_date = date.fromisoformat(target_date)

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "status": "error",
            "message": (
                "Provide a valid goal_name, target_amount, "
                "current_amount, and optional target_date (YYYY-MM-DD)"
            )
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        status = (
            "completed"
            if current_amount == target_amount
            else "in_progress"
        )

        cursor.execute(
            """
            INSERT INTO savings_goals (
                user_id,
                goal_name,
                target_amount,
                current_amount,
                target_date,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                goal_name,
                target_amount,
                current_amount,
                target_date,
                status
            )
        )

        connection.commit()
        goal_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Savings goal created successfully",
            "goal_id": goal_id
        }), 201

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Could not create savings goal"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# Retrieve savings goals for the authenticated user
@savings_goal_bp.route(
    "/api/savings-goals/<int:user_id>",
    methods=["GET"]
)
@jwt_required()
def get_savings_goals(user_id):
    user_id = int(get_jwt_identity())

    if user_id <= 0:
        return jsonify({
            "status": "error",
            "message": "Invalid user"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                goal_id,
                user_id,
                goal_name,
                target_amount,
                current_amount,
                target_date,
                status,
                created_at
            FROM savings_goals
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        goals = cursor.fetchall()

        for goal in goals:
            target = float(goal["target_amount"])
            saved = float(goal["current_amount"])

            goal["target_amount"] = target
            goal["current_amount"] = saved
            goal["remaining_amount"] = round(target - saved, 2)
            goal["percentage_completed"] = round(
                (saved / target) * 100, 2
            ) if target > 0 else 0

            if goal["target_date"] is not None:
                goal["target_date"] = goal["target_date"].isoformat()

            if goal["created_at"] is not None:
                goal["created_at"] = goal["created_at"].isoformat()

        return jsonify({
            "status": "success",
            "count": len(goals),
            "savings_goals": goals
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not retrieve savings goals"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# Update the amount saved toward a goal owned by the authenticated user
@savings_goal_bp.route(
    "/api/savings-goals/<int:goal_id>",
    methods=["PATCH"]
)
@jwt_required()
def update_savings_goal(goal_id):
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or "current_amount" not in data:
        return jsonify({
            "status": "error",
            "message": "Please provide current_amount as JSON"
        }), 400

    try:
        if isinstance(data["current_amount"], bool):
            raise ValueError

        current_amount = float(data["current_amount"])

        if (
            current_amount < 0
            or not float("-inf") < current_amount < float("inf")
        ):
            raise ValueError

        if goal_id <= 0 or user_id <= 0:
            raise ValueError

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "status": "error",
            "message": "Provide a valid goal_id and non-negative current_amount"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Find the goal only if it belongs to the authenticated user
        cursor.execute(
            """
            SELECT target_amount
            FROM savings_goals
            WHERE goal_id = %s AND user_id = %s
            """,
            (goal_id, user_id)
        )

        goal = cursor.fetchone()

        if goal is None:
            return jsonify({
                "status": "error",
                "message": "Savings goal not found"
            }), 404

        target_amount = float(goal["target_amount"])

        if current_amount > target_amount:
            return jsonify({
                "status": "error",
                "message": "Saved amount cannot exceed the target amount"
            }), 400

        status = (
            "completed"
            if current_amount == target_amount
            else "in_progress"
        )

        # Update only the authenticated user's goal
        cursor.execute(
            """
            UPDATE savings_goals
            SET current_amount = %s,
                status = %s
            WHERE goal_id = %s AND user_id = %s
            """,
            (current_amount, status, goal_id, user_id)
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Savings progress updated successfully",
            "goal_id": goal_id,
            "current_amount": current_amount,
            "remaining_amount": round(
                target_amount - current_amount, 2
            ),
            "percentage_completed": round(
                (current_amount / target_amount) * 100, 2
            ),
            "goal_status": status
        }), 200

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Could not update savings progress"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
