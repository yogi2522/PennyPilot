
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "Yogi@2006"),
        database=os.getenv("DB_NAME", "pennypilot")
    )
    return connection

try:
    connection = get_db_connection()

    if connection.is_connected():
        print("PennyPilot database connected successfully!")

        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")

        print("\nTables in PennyPilot:")

        for table in cursor.fetchall():
            print(table[0])

        cursor.close()
        connection.close()

except mysql.connector.Error as error:
    print("Database connection failed.")
    print("Error:", error)
