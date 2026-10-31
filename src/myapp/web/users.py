from flask import Blueprint, render_template, abort
from myapp.extensions import db
from myapp.models.user import User

users_bp = Blueprint("users", __name__, url_prefix="/users")

@users_bp.get("/")
def index():
    users = db.session.scalars(db.select(User)).all()
    return render_template("users/index.html", users=users)

@users_bp.get("/<int:user_id>")
def detail(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    return render_template("users/detail.html", user=user)