"""Flask application factory for the MVC application."""
from flask import Flask, current_app, render_template, request

from app.config import Config
from app.controllers import register_controllers
from app.extensions import limiter, logger, mail, mysql
from app.session_utils import PortalSessionInterface


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="static",
    )
    app.config.from_object(config_class)
    app.session_interface = PortalSessionInterface()

    mysql.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    register_controllers(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.get("/health/db")
    def database_health():
        """Verify the Aiven/local connection and required login schema."""
        cursor = None
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT DATABASE(), VERSION(), 1")
            database_name, server_version, result = cursor.fetchone()

            cursor.execute("SHOW TABLES LIKE 'users'")
            users_table_exists = cursor.fetchone() is not None

            required_columns = {
                "user_id", "email", "password_hash", "user_type"
            }
            missing_columns = []
            if users_table_exists:
                cursor.execute("SHOW COLUMNS FROM users")
                available_columns = {row[0] for row in cursor.fetchall()}
                missing_columns = sorted(required_columns - available_columns)

            healthy = users_table_exists and not missing_columns
            return {
                "status": "ok" if healthy else "schema_error",
                "database": database_name,
                "server_version": server_version,
                "connection_source": current_app.config.get(
                    "MYSQL_CONNECTION_SOURCE"
                ),
                "ssl_mode": current_app.config.get("MYSQL_CUSTOM_OPTIONS", {}).get(
                    "ssl_mode", "DISABLED"
                ),
                "users_table_exists": users_table_exists,
                "missing_login_columns": missing_columns,
                "query_result": result,
            }, 200 if healthy else 503
        except Exception as exc:
            logger.exception("Database health check failed")
            return {
                "status": "error",
                "error_type": type(exc).__name__,
                "message": str(exc),
                "host": current_app.config.get("MYSQL_HOST"),
                "port": current_app.config.get("MYSQL_PORT"),
                "database": current_app.config.get("MYSQL_DB"),
                "connection_source": current_app.config.get(
                    "MYSQL_CONNECTION_SOURCE"
                ),
                "ssl_mode": current_app.config.get("MYSQL_CUSTOM_OPTIONS", {}).get(
                    "ssl_mode", "DISABLED"
                ),
            }, 503
        finally:
            if cursor is not None:
                cursor.close()

    @app.get("/debug-routes")
    def debug_routes():
        return "<br>".join(
            f"{rule.endpoint} -> {rule}" for rule in app.url_map.iter_rules()
        )

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.exception(
            "Unhandled server error on %s %s",
            request.method,
            request.path,
            exc_info=error,
        )
        # Use the existing 500 template when available; otherwise return a
        # clear response without exposing credentials or a traceback.
        try:
            return render_template("500.html"), 500
        except Exception:
            return (
                "The application encountered an internal error. "
                "Check the Render logs and /health/db endpoint.",
                500,
            )

    @app.after_request
    def add_security_headers(response):
        if "text/html" in response.content_type:
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    logger.info(
        "Application created. MySQL target=%s:%s/%s source=%s ssl=%s",
        app.config.get("MYSQL_HOST"),
        app.config.get("MYSQL_PORT"),
        app.config.get("MYSQL_DB"),
        app.config.get("MYSQL_CONNECTION_SOURCE"),
        app.config.get("MYSQL_CUSTOM_OPTIONS", {}).get("ssl_mode", "DISABLED"),
    )
    return app
