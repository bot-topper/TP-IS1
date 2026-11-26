from datetime import UTC, datetime

from sqlalchemy import ForeignKey

from myapp.extensions import db
from myapp.models.user import AdminUser


class ModerationLog(db.Model):
    __tablename__ = "moderation_log"

    id = db.Column(db.Integer, primary_key=True)
    actionName = db.Column(db.String(120), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    executedAt = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Clave foranea de AdminUser
    admin_id = db.Column(db.Integer, ForeignKey("adminuser.id"), nullable=False)

    # Asociación 1 AdminUser -> 0..* ModerationLog
    admin = db.relationship(
        "AdminUser",
        backref=db.backref("moderation_logs", lazy=True),
        lazy=True,
    )

    def __init__(self,
                actionName: str,
                reason: str,
                admin: AdminUser
                ) -> None:
        
        if admin is None or not isinstance(admin, AdminUser):
            raise ValueError("El registro de auditoría debe pertenecer a un AdminUser.")
        
        if actionName is None or not isinstance(actionName, str) or not actionName.strip():
            raise ValueError("actionName no puede se nulo ni vacío.")
        
        if reason is None or not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason no puede ser nulo ni vacío.")

        super().__init__()

        self.actionName = actionName.strip()
        self.reason = reason.strip()
        self.admin = admin
