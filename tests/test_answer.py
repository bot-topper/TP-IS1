"""Pruebas unitarias para Answer y logica de respuesta aceptada"""

import pytest

from myapp.extensions import db
from myapp.models.answer import Answer
from myapp.models.category import Category
from myapp.models.post import Post
from myapp.models.question import Question, QuestionStatus
from myapp.models.user import NormalUser


def test_answer_hereda_post_y_valida_question(app) -> None:
    author = NormalUser(email="autor@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="Python", slug="python")
    db.session.add_all([author, cat])
    db.session.flush()

    question = Question(title="Duda", body="¿Cómo usar el abaco?", category=cat, author=author)
    db.session.add(question)
    db.session.flush()

    answer = Answer(
        body="Usando una calculadora.",
        question=question,
        author=author,
        isAIGenerated=True,
        modelUsed="gemini-2.5-flash",
        triggerType="tag",
    )
    db.session.add(answer)
    db.session.commit()

    assert isinstance(answer, Post)
    assert answer.acceptedAnswer is False
    assert answer.isAIGenerated is True
    assert answer.modelUsed == "gemini-2.5-flash"
    assert answer.triggerType == "TAG"
    assert question.answers == [answer]

    with pytest.raises(ValueError, match="Question"):
        Answer(body="Sin pregunta", question=None, author=author)  # type: ignore[arg-type]


def test_answer_calculate_score_y_accept_unica_por_pregunta(app) -> None:
    q_author = NormalUser(email="q@unrc.edu.ar", passwordHash="secret123")
    u1 = NormalUser(email="u1@unrc.edu.ar", passwordHash="secret123")
    u2 = NormalUser(email="u2@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="Patrones", slug="patrones")
    db.session.add_all([q_author, u1, u2, cat])
    db.session.flush()

    question = Question(title="Factory", body="¿Cómo aplicarlo?", category=cat, author=q_author)
    a1 = Answer(body="Primera respuesta", question=question, author=u1)
    a2 = Answer(body="Segunda respuesta", question=question, author=u2)
    db.session.add_all([question, a1, a2])
    db.session.commit()

    a1.vote(q_author, 1)
    a1.vote(u2, 1)
    assert a1.calculateScore() == 2

    a1.accept()
    assert a1.acceptedAnswer is True
    assert a2.acceptedAnswer is False
    assert question.status == QuestionStatus.ANSWERED

    # Aceptar a2 desmarca a1 automáticamente (única aceptada por pregunta)
    a2.accept()
    assert a1.acceptedAnswer is False
    assert a2.acceptedAnswer is True
    assert question.status == QuestionStatus.ANSWERED
