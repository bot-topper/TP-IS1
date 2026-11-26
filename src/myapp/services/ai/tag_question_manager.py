"""TagQuestionManager

Colocar en: src/myapp/services/ai/
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from myapp.extensions import db
from myapp.services.ai.agent_ia import AgentIA


class _TagLike(Protocol):
    name: str


class _AnswerLike(Protocol):
    isAIGenerated: bool
    triggerType: str | None


class _QuestionLike(Protocol):
    id: int | None
    title: str
    body: str
    publicationDate: datetime
    tags: Iterable[_TagLike]
    answers: list[_AnswerLike]


class _AnswerCreatorLike(Protocol):
    def createPost(self, data: dict[str, Any], autor: AgentIA) -> Any: ...


class TagQuestionManager:
    """Orquestador de respuestas automáticas por etiqueta (#ia-help) o timeout."""

    IA_HELP_TAG = "ia-help"

    def __init__(
        self,
        agent_ia: AgentIA,
        answer_creator: _AnswerCreatorLike,
        questions_provider: Callable[[], Iterable[_QuestionLike]] | None = None,
        persist_answer: Callable[[Any], None] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if agent_ia is None or not isinstance(agent_ia, AgentIA):
            raise ValueError("TagQuestionManager requiere una instancia de AgentIA.")
        if answer_creator is None or not callable(getattr(answer_creator, "createPost", None)):
            raise ValueError("TagQuestionManager requiere un AnswerCreator válido.")

        self.agent_ia = agent_ia
        self.answer_creator = answer_creator
        self._questions_provider = questions_provider or list
        self._persist_answer = persist_answer or self._default_persist
        self._clock = clock or (lambda: datetime.now(UTC))

    @staticmethod
    def _default_persist(answer: Any) -> None:
        db.session.add(answer)
        db.session.commit()

    @staticmethod
    def _has_ai_answer(question: _QuestionLike) -> bool:
        return any(getattr(ans, "isAIGenerated", False) for ans in getattr(question, "answers", []))

    @classmethod
    def _has_ia_help_tag(cls, question: _QuestionLike) -> bool:
        for tag in getattr(question, "tags", []):
            normalized = tag.name.strip().lstrip("#").lower()
            if normalized == cls.IA_HELP_TAG:
                return True
        return False

    def _generate_and_persist(self, question: _QuestionLike, trigger_type: str) -> Any:
        body = self.agent_ia.answer(question)
        strategy = getattr(self.agent_ia, "strategyIA", None)
        model_used = getattr(
            strategy,
            "model",
            type(strategy).__name__ if strategy is not None else "unknown",
        )

        answer_data = {
            "body": body,
            "question": question,
            "isAIGenerated": True,
            "modelUsed": model_used,
            "triggerType": trigger_type,
        }
        answer = self.answer_creator.createPost(answer_data, self.agent_ia)
        if hasattr(question, "answers") and isinstance(question.answers, list):
            question.answers.append(answer)
        self._persist_answer(answer)
        return answer

    def checkLabelQuestion(self, question: _QuestionLike) -> Any | None:
        """Dispara AgentIA si la pregunta tiene #ia-help y aún no tiene respuesta de IA."""
        if question is None:
            raise ValueError("La pregunta no puede ser nula.")
        if self._has_ai_answer(question):
            return None
        if not self._has_ia_help_tag(question):
            return None

        return self._generate_and_persist(question, trigger_type="TAG")

    def checkUnansweredQuestions(self, timeoutHours: int) -> list[Any]:
        """Detecta preguntas sin respuestas que superaron timeoutHours y las responde."""
        if isinstance(timeoutHours, bool) or not isinstance(timeoutHours, int):
            raise TypeError("timeoutHours debe ser un entero.")
        if timeoutHours <= 0:
            raise ValueError("timeoutHours debe ser mayor que cero.")

        cutoff = self._clock() - timedelta(hours=timeoutHours)
        generated: list[Any] = []

        for question in self._questions_provider():
            if getattr(question, "answers", []) or self._has_ai_answer(question):
                continue
            status = getattr(question, "status", None)
            if str(status).upper().endswith("CLOSED"):
                continue
            if question.publicationDate <= cutoff:
                generated.append(self._generate_and_persist(question, trigger_type="TIMEOUT"))

        return generated
