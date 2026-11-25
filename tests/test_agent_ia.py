"""Pruebas unitarias para AgentIA verificando autoría y delegación en Strategy."""

import pytest

from myapp.models.user import IAuthor
from myapp.services.ai.agent_ia import AgentIA


class _FakeQuestion:
    "Post (Question) falso"
    def __init__(self, title: str, body: str):
        self.title = title
        self.body = body


class _FakeStrategy:
    "Strategy falso"
    def answer(self, question: _FakeQuestion) -> str:
        return f"Respuesta automática sobre: {question.title}"


def test_agent_ia_implements_iautor():
    agent = AgentIA(agentName="Asistente-UNRC", strategy_ia=_FakeStrategy())
    assert isinstance(agent, IAuthor)
    assert agent.getName() == "Asistente-UNRC"


def test_agent_ia_validates_name_and_strategy():
    with pytest.raises(ValueError):
        AgentIA(agentName="   ", strategy_ia=_FakeStrategy())
    with pytest.raises(ValueError):
        AgentIA(agentName="Bot", strategy_ia=None)  # type: ignore[arg-type]


def test_agent_ia_reads_question_and_delegates_answer():
    agent = AgentIA(agentName="Ceci-UNRC", strategy_ia=_FakeStrategy())
    question = _FakeQuestion(
        title="¿Cómo usar Strategy?",
        body="Necesito intercambiar proveedores de LLM.",
    )

    context = agent.readQuestion(question)
    assert "¿Cómo usar Strategy?" in context
    assert "proveedores de LLM" in context

    response = agent.answer(question)
    assert response == "Respuesta automática sobre: ¿Cómo usar Strategy?"
