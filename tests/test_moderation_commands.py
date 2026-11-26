"""Pruebas unitarias para ModerationCommand y comandos concretos

Colocar en: tests/
"""

from dataclasses import dataclass

import pytest

from myapp.services.moderation.commands import (
    CloseQuestionCommand,
    HidePostCommand,
    ModerationCommand,
)


@dataclass
class _FakeQuestion:
    status: str = "OPEN"

    def close(self) -> None:
        self.status = "CLOSED"


@dataclass
class _FakePost:
    isHidden: bool = False


def test_moderation_command_es_abstracta() -> None:
    with pytest.raises(TypeError):
        ModerationCommand()  # type: ignore[abstract]


def test_close_question_command_execute_y_undo() -> None:
    question = _FakeQuestion(status="ANSWERED")
    cmd = CloseQuestionCommand(targetQuestion=question, reason="Contenido duplicado")

    assert cmd.actionName == "CloseQuestionCommand"
    assert cmd.reason == "Contenido duplicado"

    cmd.execute()
    assert cmd.previousStatus == "ANSWERED"
    assert question.status == "CLOSED"

    cmd.undo()
    assert question.status == "ANSWERED"


def test_hide_post_command_execute_y_undo() -> None:
    post = _FakePost(isHidden=False)
    cmd = HidePostCommand(targetPost=post, reason="Spam")

    cmd.execute()
    assert post.isHidden is True

    cmd.undo()
    assert post.isHidden is False

    # Tambien funciona si el post ya estaba oculto (alterna a False y revierte a True)
    post.isHidden = True
    cmd.execute()
    assert post.isHidden is False
    cmd.undo()
    assert post.isHidden is True


def test_moderation_commands_validan_objetivos_y_orden_de_undo() -> None:
    with pytest.raises(ValueError, match="Question"):
        CloseQuestionCommand(targetQuestion=None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Post"):
        HidePostCommand(targetPost=None)  # type: ignore[arg-type]

    q_cmd = CloseQuestionCommand(targetQuestion=_FakeQuestion())
    with pytest.raises(RuntimeError, match="no fue ejecutado"):
        q_cmd.undo()

    p_cmd = HidePostCommand(targetPost=_FakePost())
    with pytest.raises(RuntimeError, match="no fue ejecutado"):
        p_cmd.undo()
