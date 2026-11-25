"""Pruebas unitarias para ModerationLog y auditoría en AdminUser
"""

import pytest
from myapp.services.moderation.commands import CloseQuestionCommand

from myapp.extensions import db
from myapp.models.moderation_log import ModerationLog
from myapp.models.user import AdminUser, NormalUser


class _FakeQuestion:
    def __init__(self) -> None:
        self.status = "OPEN"

    def close(self) -> None:
        self.status = "CLOSED"


def test_moderation_log_valida_campos_y_persiste(app) -> None:
    admin = AdminUser(email="admin@unrc.edu.ar", passwordHash="secret456")
    normal = NormalUser(email="user@unrc.edu.ar", passwordHash="secret123")
    db.session.add_all([admin, normal])
    db.session.flush()

    log = ModerationLog(
        actionName="CloseQuestionCommand",
        reason="Fuera de tema",
        admin=admin,
    )
    db.session.add(log)
    db.session.commit()

    assert log.id is not None
    assert log.actionName == "CloseQuestionCommand"
    assert log.reason == "Fuera de tema"
    assert log.executedAt is not None
    assert admin.moderation_logs == [log]

    with pytest.raises(ValueError, match="AdminUser"):
        ModerationLog(actionName="HidePostCommand", reason="Spam", admin=normal)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="actionName"):
        ModerationLog(actionName="  ", reason="Spam", admin=admin)

    with pytest.raises(ValueError, match="reason"):
        ModerationLog(actionName="HidePostCommand", reason="  ", admin=admin)


def test_admin_user_execute_moderation_registra_log(app) -> None:
    admin = AdminUser(email="mod@unrc.edu.ar", passwordHash="secret456")
    db.session.add(admin)
    db.session.flush()

    question = _FakeQuestion()
    cmd = CloseQuestionCommand(targetQuestion=question, reason="Pregunta duplicada")

    admin.executeModeration(cmd)
    db.session.commit()

    assert question.status == "CLOSED"
    assert len(admin.moderation_logs) == 1
    assert admin.moderation_logs[0].actionName == "CloseQuestionCommand"
    assert admin.moderation_logs[0].reason == "Pregunta duplicada"
