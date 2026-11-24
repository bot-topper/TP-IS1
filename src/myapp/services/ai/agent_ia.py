"""Clase AgentIA que implementa IAutor y delega la generación de respuestas en una estrategia AnswerIA.
"""

from typing import Protocol

from myapp.models.user import IAuthor

class _AnswerIAStrategy(Protocol):
    """Contrato de Strategy"""

    def answer(self, question: object) -> str: ...


class _QuestionLike(Protocol):
    """Contrato de una pregunta para extraer contexto."""

    title: str
    body: str


class AgentIA(IAuthor):
    """Agente de IA como autor válido."""

    def __init__(self, agentName: String, strategy_ia: _AnswerIAStrategy):
        if not agentName or not agentName.strip():
            raise ValueError("El nombre del agente no puede estar vacío.")
        if strategy_ia is None:
            raise ValueError("AgentIA requiere una estrategia AnswerIA activa.")

        self.agentName = agentName.strip()
        self.strategyIA = strategy_ia

    def getName(self) -> str:
        """Retorna el nombre identificador del agente IA (contrato IAutor)."""
        return self.agentName

    def readQuestion(self, question: _QuestionLike) -> str:
        """Extrae el título y cuerpo de la pregunta como contexto legible."""
        return f"Título: {question.title}\nContenido: {question.body}"

    def answer(self, question: _QuestionLike) -> str:
        """Delega la generación de la respuesta a la estrategia AnswerIA configurada."""
        return self.strategyIA.answer(question)
