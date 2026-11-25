from datetime import UTC, datetime

from sqlalchemy import ForeignKey

from myapp.extensions import db
from myapp.models.user import User

MAX_COMMENT_LENGTH = 300


class Comment(db.Model):
    __tablename__ = "comment"

    id = db.Column(db.Integer, primary_key = True)
    body = db.Column(db.Text, nullable = False)
    createdAt = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        default=lambda: datetime.now(UTC),
    )

    #claves foraneas
    #referencia a Post (y a sus hijos que tienen este atributo)
    post_id = db.Column(db.Integer, ForeignKey("post.id"), nullable = False)

    # Identificación a cualquier subclase concreta de User (NormalUser / AdminUser)
    user_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, nullable = True)

    def __init__(self, body: str, user, post):
        if user is None or not isinstance(user, User):
            raise ValueError("El Comment debe provenir de un User valido.")
        if post is None:
            raise ValueError("El Comment debe ir a un Post valido.")

        if body is None or not isinstance(body, str):
            raise ValueError(
                f"El contenido del Comment no puede ser nulo, vacío ni superar {MAX_COMMENT_LENGTH} caracteres."
            )
        
        normalized_body = body.strip()
        if not normalized_body or len(normalized_body) > MAX_COMMENT_LENGTH:
            raise ValueError(
                f"El contenido del Comment no puede ser nulo, vacío ni superar {MAX_COMMENT_LENGTH} caracteres."
            )

        super().__init__()

        self.body = normalized_body
        self.user_type = type(user).__name__
        self.user_id = getattr(user, "id", None)
        self._user = user
        post.comments.append(self)

    @property
    def user(self) -> User | None:
        return getattr(self, "_user", None)
