
import mysql.connector
from flask import Flask, jsonify
from db import get_db_connection
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
app = Flask(__name__)
# Load environment variables from .env
load_dotenv()

jwt_secret = os.getenv("JWT_SECRET_KEY")

if not jwt_secret:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing. Check your .env file."
    )

# JWT configuration
app.config["JWT_SECRET_KEY"] = jwt_secret
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)

# Initialize JWT
jwt = JWTManager(app)

# Check whether the backend is running
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "project": "PennyPilot",
        "message": "PennyPilot backend is running!",
        "status": "success"
    })


# Check whether the database connection works
@app.route("/api/health", methods=["GET"])
def health_check():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]

        return jsonify({
            "status": "success",
            "message": "Database connection successful",
            "database": database_name
        }), 200

    except mysql.connector.Error:
        return jsonify({
            "status": "error",
            "message": "Database connection failed"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# Register transaction API routes
from transaction_routes import transaction_bp
app.register_blueprint(transaction_bp)

# Register category API routes
from category_routes import category_bp
app.register_blueprint(category_bp)

# Register dashboard API routes
from dashboard_routes import dashboard_bp
app.register_blueprint(dashboard_bp)

# Register monthly report API routes
from monthly_report_routes import monthly_report_bp
app.register_blueprint(monthly_report_bp)

# Register budget API routes
from budget_routes import budget_bp
app.register_blueprint(budget_bp)

from budget_progress_routes import budget_progress_bp
app.register_blueprint(budget_progress_bp)

from savings_goal_routes import savings_goal_bp
app.register_blueprint(savings_goal_bp)

# Register Smart Spending Insights API
from spending_insights_routes import spending_insights_bp
app.register_blueprint(spending_insights_bp)


# Register authentication API routes
from auth_routes import auth_bp
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True)



