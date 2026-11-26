"""Interfaz NotificationMediator y mediator QANotificationMediator

Colocar en: src/myapp/services/notifications/
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from myapp.models.notification import Notification
from myapp.models.user import User


class _AuthorLike(Protocol):
    def getName(self) -> str: ...


class _PostLike(Protocol):
    author: object | None


class NotificationMediator(ABC):
    """Interfaz Mediator para centralizar el envío de notificaciones del foro."""

    @abstractmethod
    def notify(self, event: str, post: _PostLike, actor: _AuthorLike) -> list[Notification]:
        """Notifica a los destinatarios correspondientes ante un evento sobre un Post."""


class QANotificationMediator(NotificationMediator):
    """Mediador concreto coordina notificaciones de preguntas, respuestas y comentarios."""

    EVENT_NEW_ANSWER = "NEW_ANSWER"
    EVENT_NEW_COMMENT = "NEW_COMMENT"
    EVENT_ANSWER_ACCEPTED = "ANSWER_ACCEPTED"

    @staticmethod
    def _is_same_actor(recipient: object, actor: object) -> bool:
        if recipient is actor:
            return True
        rec_id = getattr(recipient, "id", None)
        act_id = getattr(actor, "id", None)
        return (
            rec_id is not None
            and act_id is not None
            and type(recipient) is type(actor)
            and rec_id == act_id
        )

    def _collect_recipients(self, event: str, post: object, actor: object) -> list[User]:
        candidates: list[object] = []

        if event == self.EVENT_NEW_ANSWER:
            question = getattr(post, "question", post)
            if getattr(question, "author", None) is not None:
                candidates.append(question.author)
            candidates.extend(getattr(question, "subscribers", []))
        elif event in (self.EVENT_NEW_COMMENT, self.EVENT_ANSWER_ACCEPTED):
            if getattr(post, "author", None) is not None:
                candidates.append(post.author)
            question = getattr(post, "question", None)
            if event == self.EVENT_NEW_COMMENT and question is not None:
                candidates.extend(getattr(question, "subscribers", []))

        # Deduplica destinatarios y excluye al actor que origino el evento
        unique: list[User] = []
        for candidate in candidates:
            if not isinstance(candidate, User):
                continue
            if self._is_same_actor(candidate, actor):
                continue
            if not any(self._is_same_actor(candidate, existing) for existing in unique):
                unique.append(candidate)
        return unique

    @staticmethod
    def _build_message(event: str, post: object, actor: _AuthorLike) -> str:
        actor_name = actor.getName()
        if event == QANotificationMediator.EVENT_NEW_ANSWER:
            title = getattr(post, "title", "tu pregunta")
            return f"{actor_name} publicó una nueva respuesta en '{title}'."
        if event == QANotificationMediator.EVENT_NEW_COMMENT:
            return f"{actor_name} dejó un nuevo comentario en tu publicación."
        if event == QANotificationMediator.EVENT_ANSWER_ACCEPTED:
            return f"{actor_name} marcó tu respuesta como aceptada."
        raise ValueError(f"Evento de notificación no soportado: {event}")

    def notify(self, event: str, post: _PostLike, actor: _AuthorLike) -> list[Notification]:
        if post is None:
            raise ValueError("El post no puede ser nulo.")
        if actor is None or not callable(getattr(actor, "getName", None)):
            raise ValueError("El actor debe implementar IAuthor (getName).")

        message = self._build_message(event, post, actor)
        recipients = self._collect_recipients(event, post, actor)
        return [Notification(message=message, user=recipient) for recipient in recipients]
