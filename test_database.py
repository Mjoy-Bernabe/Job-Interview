"""Test the MySQL connection configured in the project's .env file."""
from app import create_app
from app.extensions import mysql

app = create_app()

with app.app_context():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database_name, server_version = cursor.fetchone()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()

        print("MySQL connection successful.")
        print(f"Database: {database_name}")
        print(f"Server version: {server_version}")
        print(f"Tables found: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
    except Exception as exc:
        print("MySQL connection failed.")
        print(f"Reason: {exc}")
        print("Check MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DB in .env.")
        raise SystemExit(1)
