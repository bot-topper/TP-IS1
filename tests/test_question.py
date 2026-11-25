"""Pruebas unitarias para Category, Tag, QuestionStatus y Question (Issue #24)."""

import pytest

from myapp.extensions import db
from myapp.models.category import Category
from myapp.models.post import Post
from myapp.models.question import Question, QuestionStatus
from myapp.models.tag import Tag
from myapp.models.user import AdminUser, NormalUser


def test_question_status_enum_values() -> None:
    assert QuestionStatus.OPEN.value == "OPEN"
    assert QuestionStatus.ANSWERED.value == "ANSWERED"
    assert QuestionStatus.CLOSED.value == "CLOSED"


def test_category_and_tag_validations_and_normalization(app) -> None:
    cat = Category(name="  Arquitectura  ", slug="  ARQUITECTURA-SW ")
    tag = Tag(name="  Python  ")
    db.session.add_all([cat, tag])
    db.session.commit()

    assert cat.id is not None
    assert cat.name == "Arquitectura"
    assert cat.slug == "arquitectura-sw"
    assert tag.id is not None
    assert tag.name == "python"

    with pytest.raises(ValueError):
        Category(name="   ", slug="valid")
    with pytest.raises(ValueError):
        Category(name="Valid", slug="  ")
    with pytest.raises(ValueError):
        Tag(name="  ")


def test_question_inherits_post_validates_fields_and_deduplicates_tags(app) -> None:
    author = NormalUser(email="autor@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="Patrones", slug="patrones")
    t1 = Tag(name="Strategy")
    t3 = Tag(name="python")
    db.session.add_all([author, cat, t1, t3])
    db.session.flush()

    question = Question(
        title="¿Cómo usar Strategy?",
        body="Necesito intercambiar modelos de IA.",
        category=cat,
        author=author,
        tags=[t1, t1, t3],
    )
    db.session.add(question)
    db.session.commit()

    assert isinstance(question, Post)
    assert question.title == "¿Cómo usar Strategy?"
    assert question.status == QuestionStatus.OPEN
    assert question.category is cat
    assert [t.name for t in question.tags] == ["strategy", "python"]

    # Agregar tag repetido (por instancia o mismo nombre normalizado) no lo duplica
    question.add_tag(t1)
    question.add_tag(Tag(name="  STRATEGY "))
    assert len(question.tags) == 2

    with pytest.raises(ValueError):
        Question(title="  ", body="Cuerpo", category=cat, author=author)
    with pytest.raises(ValueError):
        Question(title="Título", body="Cuerpo", category=None, author=author)  # type: ignore[arg-type]


def test_question_subscriptions_between_normal_user_and_question(app) -> None:
    author = NormalUser(email="autor@unrc.edu.ar", passwordHash="secret123")
    sub1 = NormalUser(email="sub1@unrc.edu.ar", passwordHash="secret123")
    sub2 = NormalUser(email="sub2@unrc.edu.ar", passwordHash="secret123")
    admin = AdminUser(email="admin@unrc.edu.ar", passwordHash="secret456")
    cat = Category(name="Bases de Datos", slug="bd")
    db.session.add_all([author, sub1, sub2, admin, cat])
    db.session.flush()

    q1 = Question(title="SQLite", body="Duda con FK", category=cat, author=author)
    q2 = Question(title="Alembic", body="Duda con upgrade", category=cat, author=author)
    db.session.add_all([q1, q2])
    db.session.commit()

    q1.subscribe(sub1)
    q1.subscribe(sub1)  # sin duplicados
    q1.subscribe(sub2)
    q2.subscribe(sub1)
    db.session.commit()

    assert set(q1.subscribers) == {sub1, sub2}
    assert set(sub1.subscribed_questions) == {q1, q2}

    q1.unsubscribe(sub2)
    db.session.commit()
    assert q1.subscribers == [sub1]

    with pytest.raises(ValueError, match="NormalUser"):
        q1.subscribe(admin)  # type: ignore[arg-type]


def test_question_calculate_score_and_status_transitions(app) -> None:
    author = NormalUser(email="autor@unrc.edu.ar", passwordHash="secret123")
    voter1 = NormalUser(email="v1@unrc.edu.ar", passwordHash="secret123")
    voter2 = NormalUser(email="v2@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="Testing", slug="testing")
    db.session.add_all([author, voter1, voter2, cat])
    db.session.flush()

    question = Question(title="Pytest", body="¿Cómo usar fixtures?", category=cat, author=author)
    db.session.add(question)
    db.session.commit()

    question.vote(voter1, 1)
    question.vote(voter2, 1)
    assert question.calculateScore() == 2

    question.markAsAnswered()
    assert question.status == QuestionStatus.ANSWERED

    question.close()
    assert question.status == QuestionStatus.CLOSED

    with pytest.raises(ValueError, match="cerrada"):
        question.markAsAnswered()

    question.reopen()
    assert question.status == QuestionStatus.OPEN
