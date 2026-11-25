"""Interfaz ModerationCommand y comandos concretos (Sub-issue 6.1).

Destino en el proyecto: src/myapp/services/moderation/commands.py
(Crear __init__.py vacio en esa carpeta)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class _QuestionLike(Protocol):
    status: Any

    def close(self) -> None: ...


class _PostLike(Protocol):
    isHidden: bool


class ModerationCommand(ABC):
    """Interfaz Command para acciones de moderacion reversibles."""

    def __init__(self, reason: str = "Acción de moderación") -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("El motivo de moderación no puede estar vacío.")
        self.reason = reason.strip()

    @property
    def actionName(self) -> str:
        return type(self).__name__

    @abstractmethod
    def execute(self) -> None:
        """Ejecuta la acción de moderación."""

    @abstractmethod
    def undo(self) -> None:
        """Revierte la acción de moderación."""


class CloseQuestionCommand(ModerationCommand):
    """Cierra una Pregunta y guarda su estado previo para poder revertirlo."""

    def __init__(
        self,
        targetQuestion: _QuestionLike,
        reason: str = "Pregunta cerrada por moderación",
    ) -> None:
        
        if targetQuestion is None or not callable(getattr(targetQuestion, "close", None)):
            raise ValueError("Se requiere una Question válida.")
        
        super().__init__(reason=reason)

        self.targetQuestion = targetQuestion
        self.previousStatus: Any = None
        self._executed = False

    def execute(self) -> None:
        #guarda el estado previo solo si todavía no se ejecutó
        if not self._executed: 
            self.previousStatus = self.targetQuestion.status 
        self.targetQuestion.close()
        self._executed = True

    def undo(self) -> None:
        if not self._executed:
            raise RuntimeError("No se puede deshacer un comando que no fue ejecutado.")
        self.targetQuestion.status = self.previousStatus
        self._executed = False


class HidePostCommand(ModerationCommand):
    """Alterna isHidden sobre un Post y permite revertir el cambio."""

    def __init__(
        self,
        targetPost: _PostLike,
        reason: str = "Visibilidad de publicación modificada por moderación",
    ) -> None:
        
        if targetPost is None or not hasattr(targetPost, "isHidden"):
            raise ValueError("Se requiere un Post válido.")

        super().__init__(reason=reason)

        self.targetPost = targetPost
        self._previous_hidden: bool | None = None

    def execute(self) -> None:
        if self._previous_hidden is None:
            self._previous_hidden = bool(self.targetPost.isHidden)
        self.targetPost.isHidden = not self._previous_hidden

    def undo(self) -> None:
        if self._previous_hidden is None:
            raise RuntimeError("No se puede deshacer un comando que no fue ejecutado.")
        self.targetPost.isHidden = self._previous_hidden
        self._previous_hidden = None
