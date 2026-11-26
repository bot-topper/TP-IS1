"""Entidad Notification y asociación con User.

en el proyecto: src/myapp/models/
(Crear __init__.py vacio en esa carpeta)
"""

from datetime import UTC, datetime

from myapp.extensions import db
from myapp.models.user import User


class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    isRead = db.Column(db.Boolean, nullable=False, default=False)
    createdAt = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Identificación de cualquier subclase de User (NormalUser / AdminUser)
    user_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, nullable=True)

    def __init__(self, message: str, user: User) -> None:
        if user is None or not isinstance(user, User):
            raise ValueError("La notificación debe estar asociada a un User válido.")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("El mensaje de la notificación no puede estar vacío.")

        super().__init__()

        self.message = message.strip()
        self.isRead = False
        self.user_type = type(user).__name__
        self.user_id = getattr(user, "id", None)
        self._user = user

    @property
    def user(self) -> User | None:
        return getattr(self, "_user", None)

    def markAsRead(self) -> None:
        """Marca la notificación como leída."""
        self.isRead = True
