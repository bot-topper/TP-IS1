"""Pruebas unitarias para NotificationMediator y QANotificationMediator

Colocar en: tests/
"""

from dataclasses import dataclass, field

import pytest

from myapp.extensions import db
from myapp.models.user import AdminUser, NormalUser
from myapp.services.ai.agent_ia import AgentIA
from myapp.services.ai.strategies import AnswerIA
from myapp.services.notifications.mediator import (
    NotificationMediator,
    QANotificationMediator,
)


class _DummyStrategy(AnswerIA):
    def answer(self, question) -> str:
        return "Respuesta automática"


@dataclass
class _FakeQuestion:
    title: str
    body: str
    author: object
    subscribers: list[object] = field(default_factory=list)


@dataclass
class _FakeAnswer:
    body: str
    author: object
    question: _FakeQuestion


def test_notification_mediator_es_interfaz_abstracta() -> None:
    with pytest.raises(TypeError):
        NotificationMediator()  # type: ignore[abstract]


def test_new_answer_notifica_autor_y_suscriptores_sin_duplicar_ni_notificar_actor(app) -> None:
    author = NormalUser(email="autor@unrc.edu.ar", passwordHash="secret123")
    sub1 = NormalUser(email="sub1@unrc.edu.ar", passwordHash="secret123")
    sub2 = AdminUser(email="sub2@unrc.edu.ar", passwordHash="secret456")
    db.session.add_all([author, sub1, sub2])
    db.session.flush()

    question = _FakeQuestion(
        title="¿Cómo usar Mediator?",
        body="Ejemplo en Python",
        author=author,
        subscribers=[author, sub1, sub2],
    )
    mediator = QANotificationMediator()

    created = mediator.notify(QANotificationMediator.EVENT_NEW_ANSWER, question, actor=sub2)

    assert len(created) == 2
    assert {n.user for n in created} == {author, sub1}
    assert all("sub2@unrc.edu.ar" in n.message for n in created)


def test_new_comment_y_answer_accepted_notifican_al_autor_correcto() -> None:
    q_author = NormalUser(email="q@unrc.edu.ar", passwordHash="secret123")
    a_author = NormalUser(email="a@unrc.edu.ar", passwordHash="secret123")
    question = _FakeQuestion(title="Duda", body="Detalle", author=q_author)
    answer = _FakeAnswer(body="Solución", author=a_author, question=question)

    mediator = QANotificationMediator()

    accepted_notifs = mediator.notify(
        QANotificationMediator.EVENT_ANSWER_ACCEPTED, answer, actor=q_author
    )
    assert len(accepted_notifs) == 1
    assert accepted_notifs[0].user is a_author

    self_comment_notifs = mediator.notify(
        QANotificationMediator.EVENT_NEW_COMMENT, answer, actor=a_author
    )
    assert self_comment_notifs == []


def test_agent_ia_puede_ser_actor_sin_notificarse_a_si_mismo() -> None:
    author = NormalUser(email="autor@unrc.edu.ar", passwordHash="secret123")
    question = _FakeQuestion(title="¿Qué es Strategy?", body="Ayuda", author=author)
    bot = AgentIA(agentName="Bot-UNRC", strategy_ia=_DummyStrategy())

    mediator = QANotificationMediator()
    notifs = mediator.notify(QANotificationMediator.EVENT_NEW_ANSWER, question, actor=bot)

    assert len(notifs) == 1
    assert notifs[0].user is author
    assert "Bot-UNRC" in notifs[0].message
