"""Pruebas unitarias para CachedAIProxy verificando caché y control de cuota."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from myapp.services.ai.cached_ai_proxy import CachedAIProxy, QuotaExceededError
from myapp.services.ai.strategies import AnswerIA, LocalModelAnswer, QuestionLike


@dataclass
class _FakeUser:
    id: int
    email: str

    def getName(self) -> str:
        return self.email


@dataclass
class _FakeQuestion:
    title: str
    body: str
    author: _FakeUser | None = None


class _SpyStrategy(AnswerIA):
    """Estrategia que cuenta cuántas veces fue invocada."""

    def __init__(self, prefix: str = "IA") -> None:
        self.prefix = prefix
        self.calls: int = 0

    def answer(self, question: QuestionLike) -> str:
        self.calls += 1
        return f"{self.prefix} #{self.calls}: {question.title}"


class _FakeClock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **kwargs: int) -> None:
        self.current += timedelta(**kwargs)


def test_cached_ai_proxy_implements_answer_ia() -> None:
    strategy = _SpyStrategy()
    proxy = CachedAIProxy(realStrategy=strategy, maxRequestsPerHour=5)

    assert isinstance(proxy, AnswerIA)
    assert proxy.realStrategy is strategy
    assert proxy.maxRequestsPerHour == 5
    assert proxy.cache == {}


def test_cached_ai_proxy_validates_constructor_args() -> None:
    strategy = _SpyStrategy()

    with pytest.raises(TypeError):
        CachedAIProxy(realStrategy=None)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        CachedAIProxy(realStrategy=strategy, maxRequestsPerHour=True)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        CachedAIProxy(realStrategy=strategy, maxRequestsPerHour=0)


def test_cache_hit_avoids_calling_real_strategy_for_identical_and_equivalent_questions() -> (
    None
):
    strategy = _SpyStrategy()
    proxy = CachedAIProxy(realStrategy=strategy, maxRequestsPerHour=5)
    user = _FakeUser(id=1, email="ana@unrc.edu.ar")

    q1 = _FakeQuestion(
        title="¿Qué es Proxy?", body="Explica el patrón Proxy en Python."
    )
    q2 = _FakeQuestion(
        title="¿qué es proxy? ",
        body="explica el patrón proxy en python.  ",
    )

    first_answer = proxy.answer(q1, user=user)
    second_answer = proxy.answer(q1, user=user)
    third_answer = proxy.answer(q2, user=user)

    assert first_answer == "IA #1: ¿Qué es Proxy?"
    assert second_answer == first_answer
    assert third_answer == first_answer
    assert strategy.calls == 1
    assert len(proxy.cache) == 1


def test_quota_blocks_user_when_exceeding_max_requests_per_hour() -> None:
    strategy = _SpyStrategy()
    clock = _FakeClock(datetime(2026, 11, 24, 10, 0, tzinfo=UTC))
    proxy = CachedAIProxy(realStrategy=strategy, maxRequestsPerHour=2, clock=clock)
    user = _FakeUser(id=7, email="juan@unrc.edu.ar")

    q1 = _FakeQuestion(title="Pregunta 1", body="Cuerpo 1", author=user)
    q2 = _FakeQuestion(title="Pregunta 2", body="Cuerpo 2", author=user)
    q3 = _FakeQuestion(title="Pregunta 3", body="Cuerpo 3", author=user)

    assert proxy._checkQuota(user) is True
    proxy.answer(q1)
    assert proxy._checkQuota(user) is True
    proxy.answer(q2)
    assert proxy._checkQuota(user) is False

    with pytest.raises(QuotaExceededError):
        proxy.answer(q3)

    assert strategy.calls == 2

    # Un cache hit sigue respondiendo aunque la cuota esté agotada (no consulta al proveedor)
    assert proxy.answer(q1) == "IA #1: Pregunta 1"
    assert strategy.calls == 2


def test_quota_is_isolated_per_user_and_resets_after_one_hour() -> None:
    strategy = _SpyStrategy()
    clock = _FakeClock(datetime(2026, 11, 24, 10, 0, tzinfo=UTC))
    proxy = CachedAIProxy(realStrategy=strategy, maxRequestsPerHour=1, clock=clock)
    user_a = _FakeUser(id=1, email="a@unrc.edu.ar")
    user_b = _FakeUser(id=2, email="b@unrc.edu.ar")

    proxy.answer(_FakeQuestion(title="Q-A1", body="Body A1"), user=user_a)
    with pytest.raises(QuotaExceededError):
        proxy.answer(_FakeQuestion(title="Q-A2", body="Body A2"), user=user_a)

    # Otro usuario mantiene su propia cuota independiente
    assert (
        proxy.answer(_FakeQuestion(title="Q-B1", body="Body B1"), user=user_b)
        == "IA #2: Q-B1"
    )

    # Al pasar más de una hora, la cuota de user_a se renueva
    clock.advance(minutes=61)
    assert proxy._checkQuota(user_a) is True
    assert (
        proxy.answer(_FakeQuestion(title="Q-A2", body="Body A2"), user=user_a)
        == "IA #3: Q-A2"
    )


def test_proxy_delegates_to_concrete_strategy() -> None:
    calls = 0

    def fake_transport(url, payload, headers, timeout):
        nonlocal calls
        calls += 1
        return {"response": "Respuesta desde modelo local"}

    real_strategy = LocalModelAnswer(transport=fake_transport)
    proxy = CachedAIProxy(realStrategy=real_strategy, maxRequestsPerHour=3)
    question = _FakeQuestion(title="Docker", body="¿Cómo levantar el contenedor?")

    assert proxy.answer(question) == "Respuesta desde modelo local"
    assert proxy.answer(question) == "Respuesta desde modelo local"
    assert calls == 1
