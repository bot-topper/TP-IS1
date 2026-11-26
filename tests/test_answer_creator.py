"""Pruebas unitarias para AnswerCreator"""

import pytest
from myapp.models.answer import Answer
from myapp.services.factory.answer_creator import AnswerCreator

from myapp.models.category import Category
from myapp.models.question import Question
from myapp.models.user import NormalUser
from myapp.services.ai.agent_ia import AgentIA
from myapp.services.ai.strategies import AnswerIA


class _DummyStrategy(AnswerIA):
    model = "gpt-4o-mini"

    def answer(self, question) -> str:
        return "Respuesta generada"


def test_answer_creator_crea_respuesta_humana_y_de_ia() -> None:
    creator = AnswerCreator()
    student = NormalUser(email="student@unrc.edu.ar", passwordHash="secret123")
    helper = NormalUser(email="helper@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="Bases de Datos", slug="bdd")
    question = Question(title="Duda", body="¿Como se aprueba Bases de Datos?", category=cat, author=student)

    human_answer = creator.createPost(
        data={"body": "Estudiando.", "question": question},
        autor=helper,
    )
    assert isinstance(human_answer, Answer)
    assert human_answer.isAIGenerated is False
    assert human_answer.modelUsed is None
    assert human_answer.triggerType is None
    assert human_answer.author is helper

    bot = AgentIA(agentName="Ceci-Cecex", strategy_ia=_DummyStrategy())
    ai_answer = creator.createPost(
        data={
            "body": "Estudiando mucho mucho.",
            "question": question,
            "triggerType": "TIMEOUT",
        },
        autor=bot,
    )
    assert isinstance(ai_answer, Answer)
    assert ai_answer.isAIGenerated is True
    assert ai_answer.modelUsed == "gpt-4o-mini"
    assert ai_answer.triggerType == "TIMEOUT"
    assert ai_answer.author is bot


def test_answer_creator_rechaza_autor_o_datos_invalidos() -> None:
    creator = AnswerCreator()
    student = NormalUser(email="student@unrc.edu.ar", passwordHash="secret123")
    cat = Category(name="IA", slug="ia")
    question = Question(title="Duda", body="Detalle", category=cat, author=student)

    with pytest.raises(ValueError, match="User o un AgentIA"):
        creator.createPost(data={"body": "Hola", "question": question}, autor=object())

    with pytest.raises(ValueError, match="Faltan campos obligatorios"):
        creator.createPost(data={"body": "Sin pregunta"}, autor=student)
