"""Pruebas unitarias para QuestionCreator"""

import pytest

from myapp.models.category import Category
from myapp.models.question import Question, QuestionStatus
from myapp.models.tag import Tag
from myapp.models.user import NormalUser
from myapp.services.ai.agent_ia import AgentIA
from myapp.services.ai.strategies import AnswerIA
from myapp.services.factory.question_creator import QuestionCreator


class _DummyStrategy(AnswerIA):
    def answer(self, question) -> str:
        return "ok"


def test_question_creator_crea_pregunta_valida() -> None:
    creator = QuestionCreator()
    author = NormalUser(email="student@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="Filosofia", slug="filo")
    tag = Tag(name="filosofia")

    question = creator.createPost(
        data={
            "title": "¿Quien es Socrates?",
            "body": "¿Porque me cuestiona todo lo que digo?.",
            "category": cat,
            "tags": [tag],
        },
        autor=author,
    )

    assert isinstance(question, Question)
    assert question.title == "¿Quien es Socrates?"
    assert question.status == QuestionStatus.OPEN
    assert question.category is cat
    assert question.tags == [tag]
    assert question.author is author


def test_question_creator_rechaza_agent_ia_y_datos_incompletos() -> None:
    creator = QuestionCreator()
    author = NormalUser(email="student@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="Arquitectura", slug="arquitectura")
    bot = AgentIA(agentName="Ceci-Cecex", strategy_ia=_DummyStrategy())

    with pytest.raises(TypeError, match="User"):
        creator.createPost(
            data={"title": "Título", "body": "Cuerpo", "category": cat},
            autor=bot,
        )

    with pytest.raises(ValueError, match="Faltan campos obligatorios"):
        creator.createPost(
            data={"title": "Solo título", "body": "Sin categoría"},
            autor=author,
        )
