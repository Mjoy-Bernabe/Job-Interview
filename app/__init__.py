"""Flask application factory for the MVC application."""
from flask import Flask

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
