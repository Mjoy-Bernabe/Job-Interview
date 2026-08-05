"""Flask application factory for the MVC application."""
from flask import Flask, current_app

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
        """Verify that the configured MySQL server and schema are reachable."""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT DATABASE(), 1")
            database_name, result = cursor.fetchone()
            cursor.close()
            return {
                "status": "ok",
                "database": database_name,
                "connection_source": current_app.config.get(
                    "MYSQL_CONNECTION_SOURCE"
                ),
                "query_result": result,
            }, 200
        except Exception as exc:
            logger.exception("Database health check failed")
            return {
                "status": "error",
                "message": str(exc),
                "host": current_app.config.get("MYSQL_HOST"),
                "port": current_app.config.get("MYSQL_PORT"),
                "database": current_app.config.get("MYSQL_DB"),
                "connection_source": current_app.config.get(
                    "MYSQL_CONNECTION_SOURCE"
                ),
            }, 503

    @app.get("/debug-routes")
    def debug_routes():
        return "<br>".join(
            f"{rule.endpoint} -> {rule}" for rule in app.url_map.iter_rules()
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

    logger.info("Application created using the MVC package structure.")
    return app
