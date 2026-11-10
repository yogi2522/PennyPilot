
import mysql.connector
from datetime import date
from flask import Blueprint, jsonify, request
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

transaction_bp = Blueprint("transactions", __name__)



# Get transactions for a specific user
@transaction_bp.route("/api/transactions", methods=["GET"])
@jwt_required()
def get_transactions():
    user_id = int(get_jwt_identity())

    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Please provide a user_id"
        }), 400

    try:
        user_id = int(user_id)

        if user_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "user_id must be a positive integer"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                transaction_id,
                user_id,
                category_id,
                transaction_type,
                amount,
                description,
                transaction_date,
                created_at
            FROM transactions
            WHERE user_id = %s
            ORDER BY transaction_date DESC
        """

        cursor.execute(query, (user_id,))
        transactions = cursor.fetchall()

        for transaction in transactions:
            if transaction["amount"] is not None:
                transaction["amount"] = float(transaction["amount"])

            if transaction["transaction_date"] is not None:
                transaction["transaction_date"] = (
                    transaction["transaction_date"].isoformat()
                )

            if transaction["created_at"] is not None:
                transaction["created_at"] = (
                    transaction["created_at"].isoformat()
                )

        return jsonify({
            "status": "success",
            "count": len(transactions),
            "transactions": transactions
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not retrieve transactions"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

        



# Add a new income or expense transaction

@transaction_bp.route("/api/transactions", methods=["POST"])
@jwt_required()
def add_transaction():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Please provide transaction details as JSON"
        }), 400



    required_fields = [
        "category_id",
        "transaction_type",
        "amount",
        "transaction_date"
    ]   

    for field in required_fields:
        if field not in data:
            return jsonify({
                "status": "error",
                "message": f"Missing required field: {field}"
            }), 400

    transaction_type = data["transaction_type"]

    if transaction_type not in ("income", "expense"):
        return jsonify({
            "status": "error",
            "message": "Transaction type must be income or expense"
        }), 400

    try:
        user_id = int(get_jwt_identity())
        category_id = int(data["category_id"])

        if isinstance(data["amount"], bool):
            raise ValueError

        amount = float(data["amount"])

        if user_id <= 0 or category_id <= 0:
            raise ValueError

        if amount <= 0 or amount == float("inf") or amount != amount:
            raise ValueError

        if isinstance(data["transaction_date"], date):
            raise ValueError

        transaction_date = date.fromisoformat(
            data["transaction_date"]
        )

        description = data.get("description")

        if description is not None and not isinstance(description, str):
            raise ValueError

        if description is not None and len(description) > 255:
            return jsonify({
                "status": "error",
                "message": "Description cannot exceed 255 characters"
            }), 400

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "status": "error",
            "message": (
                "Provide valid positive IDs, a positive amount, "
                "a description of at most 255 characters, and a date "
                "in YYYY-MM-DD format"
            )
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check that the category belongs to this user
        cursor.execute(
            """
            SELECT category_type
            FROM categories
            WHERE category_id = %s AND user_id = %s
            """,
            (category_id, user_id)
        )

        category = cursor.fetchone()

        if category is None:
            return jsonify({
                "status": "error",
                "message": "Category not found for this user"
            }), 400

        # Ensure the transaction type matches the category
        if category["category_type"] != transaction_type:
            return jsonify({
                "status": "error",
                "message": "Transaction type must match the category type"
            }), 400

        cursor.execute(
            """
            INSERT INTO transactions (
                user_id,
                category_id,
                transaction_type,
                amount,
                description,
                transaction_date
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                category_id,
                transaction_type,
                amount,
                description,
                transaction_date
            )
        )

        connection.commit()
        new_transaction_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Transaction added successfully",
            "transaction_id": new_transaction_id
        }), 201

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Could not add transaction"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# Update an existing transaction
@transaction_bp.route(
    "/api/transactions/<int:transaction_id>",
    methods=["PUT"]
)
@jwt_required()
def update_transaction(transaction_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Please provide transaction details as JSON"
        }), 400

    required_fields = [
    "category_id",
    "transaction_type",
    "amount",
    "transaction_date"
]

    for field in required_fields:
        if field not in data:
            return jsonify({
                "status": "error",
                "message": f"Missing required field: {field}"
            }), 400

    if data["transaction_type"] not in ("income", "expense"):
        return jsonify({
            "status": "error",
            "message": "Transaction type must be income or expense"
        }), 400

    try:
        user_id = int(get_jwt_identity())
        category_id = int(data["category_id"])

        if isinstance(data["category_id"], bool):
            raise ValueError

        if user_id <= 0 or category_id <= 0 or transaction_id <= 0:
            raise ValueError

        if isinstance(data["amount"], bool):
            raise ValueError

        amount = float(data["amount"])

        if amount <= 0 or amount == float("inf") or amount != amount:
            raise ValueError

        if not isinstance(data["transaction_date"], str):
            raise ValueError

        transaction_date = date.fromisoformat(data["transaction_date"])

        description = data.get("description")

        if description is not None and not isinstance(description, str):
            raise ValueError

        if description is not None and len(description) > 255:
            return jsonify({
                "status": "error",
                "message": "Description cannot exceed 255 characters"
            }), 400

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "status": "error",
            "message": "Please provide valid transaction details"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check that this transaction belongs to the specified user
        cursor.execute(
            """
            SELECT transaction_id
            FROM transactions
            WHERE transaction_id = %s AND user_id = %s
            """,
            (transaction_id, user_id)
        )

        transaction = cursor.fetchone()

        if transaction is None:
            return jsonify({
                "status": "error",
                "message": "Transaction not found for this user"
            }), 404

        # Check that the category belongs to this user
        cursor.execute(
            """
            SELECT category_type
            FROM categories
            WHERE category_id = %s AND user_id = %s
            """,
            (category_id, user_id)
        )

        category = cursor.fetchone()

        if category is None:
            return jsonify({
                "status": "error",
                "message": "Category not found for this user"
            }), 400

        # Check that the category matches the transaction type
        if category["category_type"] != data["transaction_type"]:
            return jsonify({
                "status": "error",
                "message": "Transaction type must match the category type"
            }), 400

        cursor.execute(
            """
            UPDATE transactions
            SET category_id = %s,
                transaction_type = %s,
                amount = %s,
                description = %s,
                transaction_date = %s
            WHERE transaction_id = %s AND user_id = %s
            """,
            (
                category_id,
                data["transaction_type"],
                amount,
                description,
                transaction_date,
                transaction_id,
                user_id
            )
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Transaction updated successfully",
            "transaction_id": transaction_id
        }), 200

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Could not update transaction"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# Delete an existing transaction
@transaction_bp.route(
    "/api/transactions/<int:transaction_id>",
    methods=["DELETE"]
)
@jwt_required()
def delete_transaction(transaction_id):
    user_id = int(get_jwt_identity())

    try:
        user_id = int(user_id)

        if user_id <= 0 or transaction_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "IDs must be positive integers"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM transactions
            WHERE transaction_id = %s AND user_id = %s
            """,
            (transaction_id, user_id)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Transaction not found for this user"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Transaction deleted successfully",
            "transaction_id": transaction_id
        }), 200

    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Could not delete transaction"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
