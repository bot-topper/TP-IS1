from flask import Flask, g

from myapp.config import Config
from myapp.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)

    from myapp.api.health import health_bp
    from myapp.web.auth import auth_bp, get_current_user
    from myapp.web.users import users_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(auth_bp)

    @app.before_request
    def load_logged_in_user():
        g.current_user, g.current_user_role = get_current_user()

    @app.context_processor
    def inject_current_user():
        return {
            "current_user": getattr(g, "current_user", None),
            "current_user_role": getattr(g, "current_user_role", None),
        }

    return app
