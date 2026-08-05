"""Controller registry for all Flask Blueprints."""
from .admin import admin_bp
from .applicants import applicants_bp
from .auth import auth_bp
from .hr import hr_bp
from .interview import interview_bp
from .schedule import schedule_bp
from .summary import summary_bp


def register_controllers(app):
    """Register every controller Blueprint exactly once."""
    for blueprint in (
        auth_bp,
        applicants_bp,
        hr_bp,
        interview_bp,
        schedule_bp,
        summary_bp,
        admin_bp,
    ):
        app.register_blueprint(blueprint)
