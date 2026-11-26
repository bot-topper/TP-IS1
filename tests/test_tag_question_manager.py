"""Pruebas unitarias para TagQuestionManager

Colocar en: tests/
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from myapp.services.ai.tag_question_manager import TagQuestionManager

from myapp.services.ai.agent_ia import AgentIA
from myapp.services.ai.strategies import AnswerIA


@dataclass
class _FakeTag:
    name: str


@dataclass
class _FakeAnswer:
    body: str
    isAIGenerated: bool = False
    modelUsed: str | None = None
    triggerType: str | None = None


@dataclass
class _FakeQuestion:
    id: int
    title: str
    body: str
    publicationDate: datetime
    tags: list[_FakeTag] = field(default_factory=list)
    answers: list[_FakeAnswer] = field(default_factory=list)
    status: str = "OPEN"


class _SpyStrategy(AnswerIA):
    model = "gemini-2.5-flash"

    def __init__(self) -> None:
        self.calls = 0

    def answer(self, question) -> str:
        self.calls += 1
        return f"Respuesta automática para: {question.title}"


class _FakeAnswerCreator:
    def createPost(self, data: dict, autor: AgentIA) -> _FakeAnswer:
        return _FakeAnswer(
            body=data["body"],
            isAIGenerated=data["isAIGenerated"],
            modelUsed=data["modelUsed"],
            triggerType=data["triggerType"],
        )


def test_check_label_question_triggers_on_ia_help_and_avoids_duplicates() -> None:
    strategy = _SpyStrategy()
    agent = AgentIA(agentName="Asistente-IA", strategy_ia=strategy)
    persisted: list[_FakeAnswer] = []
    manager = TagQuestionManager(
        agent_ia=agent,
        answer_creator=_FakeAnswerCreator(),
        persist_answer=persisted.append,
    )

    question = _FakeQuestion(
        id=1,
        title="Duda con Factory",
        body="¿Cómo implemento AnswerCreator?",
        publicationDate=datetime(2026, 11, 24, 10, 0, tzinfo=UTC),
        tags=[_FakeTag(name="#ia-help")],
    )

    first = manager.checkLabelQuestion(question)
    second = manager.checkLabelQuestion(question)

    assert first is not None
    assert first.isAIGenerated is True
    assert first.triggerType == "TAG"
    assert first.modelUsed == "gemini-2.5-flash"
    assert second is None
    assert strategy.calls == 1
    assert len(persisted) == 1


def test_check_unanswered_questions_triggers_after_timeout_only_once() -> None:
    now = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)
    strategy = _SpyStrategy()
    agent = AgentIA(agentName="Asistente-IA", strategy_ia=strategy)

    expired_question = _FakeQuestion(
        id=10,
        title="Pregunta vencida",
        body="Nadie respondió aún.",
        publicationDate=now - timedelta(hours=25),
    )
    recent_question = _FakeQuestion(
        id=11,
        title="Pregunta reciente",
        body="Recién publicada.",
        publicationDate=now - timedelta(hours=2),
    )
    already_answered = _FakeQuestion(
        id=12,
        title="Pregunta respondida",
        body="Ya tiene respuesta humana.",
        publicationDate=now - timedelta(hours=30),
        answers=[_FakeAnswer(body="Respuesta humana", isAIGenerated=False)],
    )

    manager = TagQuestionManager(
        agent_ia=agent,
        answer_creator=_FakeAnswerCreator(),
        questions_provider=lambda: [expired_question, recent_question, already_answered],
        persist_answer=lambda _ans: None,
        clock=lambda: now,
    )

    first_run = manager.checkUnansweredQuestions(timeoutHours=24)
    second_run = manager.checkUnansweredQuestions(timeoutHours=24)

    assert len(first_run) == 1
    assert first_run[0].triggerType == "TIMEOUT"
    assert second_run == []
    assert strategy.calls == 1


def test_check_unanswered_questions_validates_timeout_hours() -> None:
    agent = AgentIA(agentName="Asistente-IA", strategy_ia=_SpyStrategy())
    manager = TagQuestionManager(
        agent_ia=agent,
        answer_creator=_FakeAnswerCreator(),
        persist_answer=lambda _ans: None,
    )

    with pytest.raises(ValueError):
        manager.checkUnansweredQuestions(timeoutHours=0)
