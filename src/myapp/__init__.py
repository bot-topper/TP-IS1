from pathlib import Path

from flask import Flask, g

from myapp.config import Config
from myapp.extensions import db

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_app(config_class=Config):
    app = Flask(__name__, instance_path=str(_PROJECT_ROOT))
    app.config.from_object(config_class)
    db.init_app(app)

    from myapp.api.health import health_bp
    from myapp.api.questions import api_questions_bp
    from myapp.models.notification import Notification
    from myapp.web.auth import auth_bp, get_current_user
    from myapp.web.notifications import notifications_bp
    from myapp.web.questions import questions_bp
    from myapp.web.users import users_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(api_questions_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(notifications_bp)

    @app.before_request
    def load_logged_in_user():
        g.current_user, g.current_user_role = get_current_user()

    @app.context_processor
    def inject_current_user():
        user = getattr(g, "current_user", None)
        unread_count = 0
        if user is not None and getattr(user, "id", None) is not None:
            unread_count = db.session.query(Notification).filter_by(
                user_type=type(user).__name__,
                user_id=user.id,
                isRead=False,
            ).count()
        return {
            "current_user": user,
            "current_user_role": getattr(g, "current_user_role", None),
            "unread_notifications_count": unread_count,
        }

    return app
