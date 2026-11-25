from enum import Enum
from typing import ClassVar

from sqlalchemy import ForeignKey

from myapp.extensions import db
from myapp.models.category import Category
from myapp.models.post import Post
from myapp.models.tag import Tag
from myapp.models.user import NormalUser


class QuestionStatus(str, Enum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    CLOSED = "CLOSED"


question_tag = db.Table(
    "question_tag",
    db.Column("question_id", db.Integer, ForeignKey("question.id"), primary_key=True),
    db.Column("tag_id", db.Integer, ForeignKey("tag.id"), primary_key=True),
)

question_subscription = db.Table(
    "question_subscription",
    db.Column("question_id", db.Integer, ForeignKey("question.id"), primary_key=True),
    db.Column("user_id", db.Integer, ForeignKey("normaluser.id"), primary_key=True),
)


class Question(Post):
    __tablename__ = "question"
    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "question",
    }

    id = db.Column(db.Integer, ForeignKey("post.id"), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(
        db.Enum(QuestionStatus, native_enum=False),
        nullable=False,
        default=QuestionStatus.OPEN,
    )

    # Asociación obligatoria: 1 Question -> exactamente 1 Category
    category_id = db.Column(db.Integer, ForeignKey("category.id"), nullable=False)
    category = db.relationship(
        "Category",
        backref=db.backref("questions", lazy=True),
        lazy=True,
    )

    # Asociacion obligatoria: 1 Question -> muchas Answer
    answers = db.relationship(
        "Answer", #lista de objetos de tipo Answer
        backref = "question", #crea el atributo .question dentro de Answer
        foreign_keys = "Answer.question_id", #sqlAlchemy va a saber por donde unir
        cascade="all, delete-orphan",
        lazy = True
    )

    # Asociación muchos a muchos (0..* a 0..*) con Tag
    tags = db.relationship(
        "Tag",
        secondary=question_tag,
        backref=db.backref("questions", lazy=True),
        lazy=True,
    )

    # Suscripción (0..* a 0..*) entre NormalUser y Question
    subscribers = db.relationship(
        "NormalUser",
        secondary=question_subscription,
        backref=db.backref("subscribed_questions", lazy=True),
        lazy=True,
    )

    def __init__(
        self,
        title: str,
        body: str,
        category: Category,
        author: object | None = None,
        tags: list[Tag] | None = None,
        **kwargs,
    ) -> None:
        if title is None or not isinstance(title, str) or title.strip() == "":
            raise ValueError("El título de la pregunta no puede ser nulo ni vacío.")

        if category is None or not isinstance(category, Category):
            raise ValueError("La pregunta debe tener exactamente una Category válida.")

        super().__init__(body=body, author=author, **kwargs)

        self.title = title.strip()
        self.status = QuestionStatus.OPEN
        self.category = category

        if tags:
            for tag in tags:
                self.add_tag(tag)

    def add_tag(self, tag: Tag) -> None:
        if tag is None or not isinstance(tag, Tag):
            raise ValueError("Se requiere una instancia válida de Tag.")
        if any(existing is tag or existing.name == tag.name for existing in self.tags):
            return
        self.tags.append(tag)

    def subscribe(self, user: NormalUser) -> None:
        if user is None or not isinstance(user, NormalUser):
            raise ValueError("Solo un NormalUser válido puede suscribirse a una pregunta.")
        if user not in self.subscribers:
            self.subscribers.append(user)

    def unsubscribe(self, user: NormalUser) -> None:
        if user in self.subscribers:
            self.subscribers.remove(user)

    def calculateScore(self) -> int:
        return sum(v.value for v in self.votes)

    def markAsAnswered(self) -> None:
        if self.status == QuestionStatus.CLOSED:
            raise ValueError("No se puede marcar como respondida una pregunta cerrada.")
        self.status = QuestionStatus.ANSWERED

    def close(self) -> None:
        self.status = QuestionStatus.CLOSED

    def reopen(self) -> None:
        self.status = QuestionStatus.OPEN
