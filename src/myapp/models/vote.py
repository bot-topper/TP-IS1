from datetime import UTC, datetime

from sqlalchemy import ForeignKey, UniqueConstraint

from myapp.extensions import db
from myapp.models.user import User


class Vote(db.Model):
    __tablename__ = "vote"
    __table_args__ = (
        UniqueConstraint("user_type", "user_id", "post_id", name="uq_vote_user_post"),
    )

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    createdAt = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Identificación polimórfica de cualquier subclase concreta de User (NormalUser / AdminUser)
    user_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, nullable=True)

    # Clave foránea para Post
    post_id = db.Column(db.Integer, ForeignKey("post.id"), nullable=False)

    def __init__(self, value: int, user, post):
        if user is None or not isinstance(user, User):
            raise ValueError("El voto debe provenir de un User")

        if post is None:
            raise ValueError("El voto debe ir a un Post")

        if value not in (1, -1):
            raise ValueError("El valor del voto solo debe ser +1 o -1")

        super().__init__()

        self.value = value
        self.user_type = type(user).__name__
        self.user_id = getattr(user, "id", None)
        self._user = user
        post.votes.append(self)

    @property
    def user(self) -> User | None:
        return getattr(self, "_user", None)
