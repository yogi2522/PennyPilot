
import mysql.connector
from flask import Blueprint, jsonify, request
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
spending_insights_bp = Blueprint(
    "spending_insights",
    __name__
)


# Get smart spending insights for a user
@spending_insights_bp.route(
    "/api/insights/spending/<int:user_id>",
    methods=["GET"]
)
@jwt_required()
def get_spending_insights(user_id):
    user_id = int(get_jwt_identity())
    
    month_value = request.args.get("month")
    year_value = request.args.get("year")

    try:
        month = int(month_value) if month_value is not None else None
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "month must be a number between 1 and 12"
        }), 400

    try:
        year = int(year_value) if year_value is not None else None
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "year must be a valid number"
        }), 400


    if user_id <= 0:
        return jsonify({
            "status": "error",
            "message": "user_id must be positive"
        }), 400

    if (month is None) != (year is None):
        return jsonify({
            "status": "error",
            "message": "Please provide both month and year"
        }), 400

    if month is not None and not (1 <= month <= 12):
        return jsonify({
            "status": "error",
            "message": "month must be between 1 and 12"
        }), 400

    if year is not None and not (2000 <= year <= 2100):
        return jsonify({
            "status": "error",
            "message": "year must be between 2000 and 2100"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        
        # Get total expenses
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_expenses
            FROM transactions
            WHERE user_id = %s
              AND transaction_type = 'expense'
              AND (%s IS NULL OR MONTH(transaction_date) = %s)
              AND (%s IS NULL OR YEAR(transaction_date) = %s)
            """,
            (user_id, month, month, year, year)
        )

        total_result = cursor.fetchone()
        total_expenses = float(total_result["total_expenses"])

        
        # Compare spending with the previous month
        previous_month_expenses = None
        spending_change_percentage = None
        spending_trend = "not_available"

        if month is not None and year is not None:
            if month == 1:
                previous_month = 12
                previous_year = year - 1
            else:
                previous_month = month - 1
                previous_year = year

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total_expenses
                FROM transactions
                WHERE user_id = %s
                  AND transaction_type = 'expense'
                  AND MONTH(transaction_date) = %s
                  AND YEAR(transaction_date) = %s
                """,
                (user_id, previous_month, previous_year)
            )

            previous_result = cursor.fetchone()
            previous_month_expenses = float(
                previous_result["total_expenses"]
            )

            if previous_month_expenses > 0:
                spending_change_percentage = round(
                    (
                        (total_expenses - previous_month_expenses)
                        / previous_month_expenses
                    ) * 100,
                    2
                )

                if total_expenses > previous_month_expenses:
                    spending_trend = "increased"
                elif total_expenses < previous_month_expenses:
                    spending_trend = "decreased"
                else:
                    spending_trend = "unchanged"
            elif total_expenses > 0:
                spending_trend = "increased"



        
        # Find spending category totals
        cursor.execute(
            """
            SELECT
                c.category_id,
                c.category_name,
                SUM(t.amount) AS amount_spent,
                COUNT(t.transaction_id) AS transaction_count
            FROM transactions t
            JOIN categories c
                ON t.category_id = c.category_id
            WHERE t.user_id = %s
              AND t.transaction_type = 'expense'
              AND (%s IS NULL OR MONTH(t.transaction_date) = %s)
              AND (%s IS NULL OR YEAR(t.transaction_date) = %s)
            GROUP BY c.category_id, c.category_name
            ORDER BY amount_spent DESC
            """,
            (user_id, month, month, year, year)
        )

        categories = cursor.fetchall()


        # Convert MySQL decimal amounts to JSON-friendly numbers
        for category in categories:
            category["amount_spent"] = float(
                category["amount_spent"]
            )
            category["transaction_count"] = int(
                category["transaction_count"]
            )

            category["percentage_of_expenses"] = round(
                (category["amount_spent"] / total_expenses) * 100,
                2
            ) if total_expenses > 0 else 0

        
        # Get budget and spending details for the selected period
        cursor.execute(
            """
            SELECT
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
                AND MONTH(t.transaction_date) = b.month
                AND YEAR(t.transaction_date) = b.year
            WHERE b.user_id = %s
              AND (%s IS NULL OR b.month = %s)
              AND (%s IS NULL OR b.year = %s)
            GROUP BY
                b.category_id,
                c.category_name,
                b.amount
            """,
            (user_id, month, month, year, year)
        )

        budget_details = cursor.fetchall()

        for budget in budget_details:
            budget["budget_amount"] = float(budget["budget_amount"])
            budget["spent_amount"] = float(budget["spent_amount"])
            budget["remaining_amount"] = round(
                budget["budget_amount"] - budget["spent_amount"], 2
            )
            budget["percentage_used"] = round(
                (budget["spent_amount"] / budget["budget_amount"]) * 100,
                2
            ) if budget["budget_amount"] > 0 else 0
        
        # Calculate a rule-based spending management score
        spending_health_score = None

        if budget_details:
            spending_health_score = 100

            for budget in budget_details:
                if budget["percentage_used"] >= 100:
                    spending_health_score -= 25
                elif budget["percentage_used"] >= 80:
                    spending_health_score -= 10

            spending_health_score = max(
                0, spending_health_score
            )
        # Explain the spending health score
        if spending_health_score is None:
            spending_health_label = "Not available"
        elif spending_health_score >= 90:
            spending_health_label = "Excellent budget control"
        elif spending_health_score >= 70:
            spending_health_label = "Good budget control"
        elif spending_health_score >= 40:
            spending_health_label = "Needs attention"
        else:
            spending_health_label = "Review your budgets"
 

        # Find the highest-spending category
        highest_category = categories[0] if categories else None
        
        # Generate spending observations
        spending_observations = []


        if total_expenses == 0:
            spending_observations.append(
                "No expenses were recorded for this period."
            )
        elif highest_category is not None:
            spending_observations.append(
                f"{highest_category['category_name']} is your "
                f"highest-spending category, with "
                f"{highest_category['percentage_of_expenses']}% "
                f"of recorded expenses."
            )

            if len(categories) == 1:
                spending_observations.append(
                    "Only one expense category has recorded "
                    "spending in this period."
                )
        
        # Generate month-over-month observations
        if previous_month_expenses is not None:
            if previous_month_expenses == 0 and total_expenses > 0:
                spending_observations.append(
                    "You recorded expenses this month, while the "
                    "previous month had no recorded expenses."
                )
            elif spending_trend == "increased":
                spending_observations.append(
                    f"Your spending increased by "
                    f"{spending_change_percentage}% compared with "
                    f"the previous month."
                )
            elif spending_trend == "decreased":
                spending_observations.append(
                    f"Your spending decreased by "
                    f"{abs(spending_change_percentage)}% compared "
                    f"with the previous month."
                )
            elif spending_trend == "unchanged":
                spending_observations.append(
                    "Your spending remained unchanged compared "
                    "with the previous month."
                )

            
        # Generate budget-aware observations
        for budget in budget_details:
            if budget["percentage_used"] >= 100:
                spending_observations.append(
                    f"You have exceeded or fully used your "
                    f"{budget['category_name']} budget."
                )
            elif budget["percentage_used"] >= 80:
                spending_observations.append(
                    f"Warning: You have used "
                    f"{budget['percentage_used']}% of your "
                    f"{budget['category_name']} budget."
                )



        # Build the response
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "month": month,
            "year": year,
            "total_expenses": total_expenses,
            "previous_month_expenses": previous_month_expenses,
            "spending_change_percentage": spending_change_percentage,
            "spending_trend": spending_trend,
            "spending_health_score": spending_health_score,
            "spending_health_label": spending_health_label,
            "highest_spending_category": highest_category,
            "category_breakdown": categories,
            "spending_observations": spending_observations,
            "budget_details": budget_details
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Could not generate spending insights"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
