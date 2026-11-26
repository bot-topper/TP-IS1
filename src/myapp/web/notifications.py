from flask import Blueprint, abort, flash, g, redirect, render_template, url_for

from myapp.extensions import db
from myapp.models.notification import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.get("/")
def index():
    user = getattr(g, "current_user", None)
    if user is None:
        flash("Debes iniciar sesión para ver tus notificaciones.")
        return redirect(url_for("auth.login"))

    notifications = db.session.scalars(
        db.select(Notification)
        .where(
            Notification.user_type == type(user).__name__,
            Notification.user_id == user.id,
        )
        .order_by(Notification.createdAt.desc(), Notification.id.desc())
    ).all()

    return render_template("notifications/index.html", notifications=notifications)


@notifications_bp.post("/<int:notification_id>/read")
def mark_read(notification_id: int):
    user = getattr(g, "current_user", None)
    if user is None:
        return redirect(url_for("auth.login"))

    notification = db.session.get(Notification, notification_id)
    if notification is None:
        abort(404)

    if (
        notification.user_type != type(user).__name__
        or notification.user_id != user.id
    ):
        abort(403)

    notification.markAsRead()
    db.session.commit()
    return redirect(url_for("notifications.index"))
