"""Pruebas unitarias para Comment y su composición con Post (Issue #23)."""

from typing import ClassVar

import pytest

from myapp.extensions import db
from myapp.models.comment import MAX_COMMENT_LENGTH, Comment
from myapp.models.post import Post
from myapp.models.user import AdminUser, NormalUser


class _DummyQuestion(Post):
    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "dummy_question"
    }

    def calculateScore(self) -> int:
        return sum(v.value for v in self.votes)


class _DummyAnswer(Post):
    __mapper_args__: ClassVar[dict[str, str]] = {"polymorphic_identity": "dummy_answer"}

    def calculateScore(self) -> int:
        return sum(v.value for v in self.votes)


def test_comment_valida_usuario_post_y_longitud_de_cuerpo() -> None:
    user = NormalUser(email="ana@unrc.edu.ar", passwordHash="secret123")
    post = _DummyQuestion(body="Pregunta de prueba", author=user)

    with pytest.raises(ValueError, match="User"):
        Comment(body="Hola", user=None, post=post)

    with pytest.raises(ValueError, match="User"):
        Comment(body="Hola", user=object(), post=post)

    with pytest.raises(ValueError, match="Post"):
        Comment(body="Hola", user=user, post=None)

    with pytest.raises(ValueError, match="caracteres"):
        Comment(body="   ", user=user, post=post)

    with pytest.raises(ValueError, match="caracteres"):
        Comment(body="a" * (MAX_COMMENT_LENGTH + 1), user=user, post=post)


def test_comment_persiste_en_question_y_answer_y_respeta_composicion(app) -> None:
    student = NormalUser(email="juan@unrc.edu.ar", passwordHash="secret123")
    admin = AdminUser(email="admin@unrc.edu.ar", passwordHash="secret456")
    db.session.add_all([student, admin])
    db.session.flush()

    question = _DummyQuestion(body="¿Cómo funciona Alembic?", author=student)
    answer = _DummyAnswer(body="Usando upgrade head.", author=admin)
    db.session.add_all([question, answer])
    db.session.commit()

    c1 = Comment(body="  ¿Podrías dar un ejemplo?  ", user=student, post=question)
    c2 = Comment(body="Claro, revisa alembic.ini.", user=admin, post=answer)
    db.session.commit()

    assert c1.body == "¿Podrías dar un ejemplo?"
    assert c1.user is student
    assert c1.user_type == "NormalUser"
    assert c1.post is question
    assert len(question.comments) == 1

    assert c2.user is admin
    assert c2.user_type == "AdminUser"
    assert len(answer.comments) == 1

    # Al eliminar el Post, se eliminan sus Comment asociados
    db.session.delete(question)
    db.session.commit()
    assert db.session.scalars(db.select(Comment)).all() == [c2]
