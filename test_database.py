"""Test the active local or hosted MySQL configuration."""
from app import create_app
from app.extensions import mysql

app = create_app()

print("Connection source:", app.config.get("MYSQL_CONNECTION_SOURCE"))
print("Host:", app.config.get("MYSQL_HOST"))
print("Port:", app.config.get("MYSQL_PORT"))
print("Database:", app.config.get("MYSQL_DB"))
print("User:", app.config.get("MYSQL_USER"))

with app.app_context():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database_name, server_version = cursor.fetchone()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()

        print("MySQL connection successful.")
        print(f"Connected database: {database_name}")
        print(f"Server version: {server_version}")
        print(f"Tables found: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
    except Exception as exc:
        print("MySQL connection failed.")
        print(f"Reason: {exc}")
        print(
            "Use MYSQL_PUBLIC_URL for Railway public access, or set "
            "MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DB."
        )
        raise SystemExit(1)
