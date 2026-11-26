from flask import Blueprint, abort, render_template

from myapp.extensions import db
from myapp.models.user import User

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.get("/")
def index():
    users = []
    for subcls in User.__subclasses__():
        if not getattr(subcls, "__abstract__", False):
            users.extend(db.session.scalars(db.select(subcls)).all())
    return render_template("users/index.html", users=users)


@users_bp.get("/<int:user_id>")
def detail(user_id):
    user = None
    for subcls in User.__subclasses__():
        if not getattr(subcls, "__abstract__", False):
            user = db.session.get(subcls, user_id)
            if user is not None:
                break
    if user is None:
        abort(404)
    return render_template("users/detail.html", user=user)
