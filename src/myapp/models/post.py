from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy.orm import Mapped, relationship

from myapp.extensions import db
from myapp.models.comment import Comment
from myapp.models.vote import Vote


class Post(db.Model):
    __tablename__ = "post"
    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "post",
        "polymorphic_on": "type",
    }

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)

    publicationDate = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Columna para saber que tipo de Post es: Question y Answer
    type = db.Column(db.String(50), nullable=False, default="post")

    # Atributo para saber que tipo de autor (User o AgentIA)
    author_type = db.Column(db.String(50), nullable=False)
    author_id = db.Column(db.Integer, nullable=True)

    isHidden = db.Column(db.Boolean, nullable=False, default=False)

    # Relacion de composicion (1 a 0..*) entre Post y Vote
    votes: Mapped[list["Vote"]] = relationship(
        "Vote",
        backref="post",  # crea automáticamente el atributo .post en la clase Vote
        cascade="all, delete-orphan",  # si se elimina el Post o se quita un voto de `self.votes`, se elimina automáticamente de la BD
        lazy=True,  # carga los votos desde la BD recién cuando se accede a `post.votes`.
    )

    # Relacion de composicion (1 a 0..*) entre Post y Comment
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        backref="post",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __init__(
        self,
        body: str,
        author: object | None = None,
        author_type: str | None = None,
        author_id: int | None = None,
        **kwargs,
    ):
        if type(self) is Post:
            raise TypeError(
                "Post es una clase abstracta y no puede instanciarse directamente."
            )

        if body is None or not isinstance(body, str) or body.strip() == "":
            raise ValueError("El contenido del Post no puede ser nulo ni vacío.")

        if author is not None:
            if not callable(getattr(author, "getName", None)):
                raise TypeError(
                    "El autor debe implementar la interfaz IAuthor (getName)."
                )
            resolved_type = author_type or type(author).__name__
            resolved_id = (
                author_id if author_id is not None else getattr(author, "id", None)
            )
        elif author_type is not None and author_type.strip() != "":
            resolved_type = author_type.strip()
            resolved_id = author_id
        else:
            raise ValueError("El Post debe tener un autor obligatorio.")

        super().__init__(**kwargs)

        self.body = body
        self.author_type = resolved_type
        self.author_id = resolved_id
        self.isHidden = bool(kwargs.get("isHidden", False))
        self._author = author

    @property
    def author(self) -> object | None:
        return getattr(self, "_author", None)

    def calculateScore(self) -> int:
        raise NotImplementedError("Las subclases deben implementar calculateScore().")

    # funcion para votar y se decide que hacer si el usuario ya votó
    def vote(self, user, value: int):
        if user is None:
            raise ValueError("El usuario debe existir.")

        if value not in (1, -1):
            raise ValueError("Valor no permitido.")
        # buscar entre la lista de votos
        existing_vote = None
        for v in self.votes:
            # Compara instancias en memoria o registros persistidos por tipo e id de usuario.
            if v.user == user or (
                v.user_id is not None
                and v.user_type == type(user).__name__
                and getattr(user, "id", None) == v.user_id
            ):
                existing_vote = v
                break

        # si no exite un voto
        if existing_vote is None:
            v = Vote(value, user, self)
        # si ya hay un voto, y tiene el mismo valor entonces está quitando el voto
        elif existing_vote.value == value:
            self.votes.remove(existing_vote)
        # si ya hay un voto pero tiene el valor opuesto, hay que modificarlo
        else:
            existing_vote.value = value
