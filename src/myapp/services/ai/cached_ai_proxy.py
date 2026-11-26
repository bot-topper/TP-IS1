"""Proxy de caché y control de cuota horaria para estrategias AnswerIA."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from myapp.services.ai.strategies import AnswerIA, QuestionLike


class QuotaExceededError(RuntimeError):
    """Se lanza cuando un usuario supera su límite horario de consultas a la IA."""


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _build_cache_key(question: QuestionLike) -> str:
    """Construye una clave normalizada para detectar preguntas idénticas o equivalentes."""
    if question is None:
        raise ValueError("La pregunta no puede ser nula.")

    title = getattr(question, "title", None)
    if not isinstance(title, str) or not title.strip():
        raise ValueError("La pregunta debe tener un título no vacío.")
    body = getattr(question, "body", None)
    if not isinstance(body, str) or not body.strip():
        raise ValueError("La pregunta debe tener un cuerpo no vacío.")

    return f"{_normalize_text(title)}|{_normalize_text(body)}"


def _resolve_user_key(user: object) -> str:
    """Obtiene un identificador estable para llevar el registro de cuota por usuario."""
    user_id = getattr(user, "id", None)
    if user_id is not None:
        return f"id:{user_id}"

    get_name = getattr(user, "getName", None)
    if callable(get_name):
        name = get_name()
        if isinstance(name, str) and name.strip():
            return f"name:{name.strip().lower()}"

    email = getattr(user, "email", None)
    if isinstance(email, str) and email.strip():
        return f"email:{email.strip().lower()}"

    return f"obj:{id(user)}"


class CachedAIProxy(AnswerIA):
    """Proxy que agrega caché de respuestas y límite horario por usuario sobre AnswerIA."""

    def __init__(
        self,
        realStrategy: AnswerIA,
        maxRequestsPerHour: int = 10,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(realStrategy, AnswerIA):
            raise TypeError("realStrategy debe implementar la interfaz AnswerIA.")
        if isinstance(maxRequestsPerHour, bool) or not isinstance(
            maxRequestsPerHour, int
        ):
            raise TypeError("maxRequestsPerHour debe ser un entero.")
        if maxRequestsPerHour <= 0:
            raise ValueError("maxRequestsPerHour debe ser mayor que cero.")

        self.realStrategy = realStrategy
        self.maxRequestsPerHour = maxRequestsPerHour
        self.cache: dict[str, str] = {}
        self._clock = clock or (lambda: datetime.now(UTC))
        self._request_timestamps: dict[str, list[datetime]] = {}

    def _prune_expired_requests(self, user_key: str, now: datetime) -> list[datetime]:
        cutoff = now - timedelta(hours=1)
        active = [
            ts for ts in self._request_timestamps.get(user_key, []) if ts > cutoff
        ]
        self._request_timestamps[user_key] = active
        return active

    def _checkQuota(self, user: object) -> bool:
        """Verifica si el usuario aún tiene cuota disponible en la última hora."""
        if user is None:
            raise ValueError("El usuario no puede ser nulo al verificar la cuota.")

        now = self._clock()
        user_key = _resolve_user_key(user)
        active_requests = self._prune_expired_requests(user_key, now)
        return len(active_requests) < self.maxRequestsPerHour

    def _record_request(self, user: object) -> None:
        now = self._clock()
        user_key = _resolve_user_key(user)
        active_requests = self._prune_expired_requests(user_key, now)
        active_requests.append(now)

    def answer(self, question: QuestionLike, user: object | None = None) -> str:
        """Retorna una respuesta desde caché o delega en realStrategy respetando la cuota."""
        cache_key = _build_cache_key(question)
        if cache_key in self.cache:
            return self.cache[cache_key]

        target_user = user if user is not None else getattr(question, "author", None)
        if target_user is not None and not self._checkQuota(target_user):
            raise QuotaExceededError(
                f"El usuario superó el límite de {self.maxRequestsPerHour} consultas por hora."
            )

        response = self.realStrategy.answer(question)
        if target_user is not None:
            self._record_request(target_user)
        self.cache[cache_key] = response
        return response
