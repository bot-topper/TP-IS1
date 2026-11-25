"""Pruebas unitarias para Post y Vote (Issue #22)."""

from typing import ClassVar

import pytest

from myapp.extensions import db
from myapp.models.post import Post
from myapp.models.user import AdminUser, NormalUser
from myapp.models.vote import Vote


class _DummyPost(Post):
    """Subclase mínima para probar Post sin instanciar la clase abstracta."""

    __mapper_args__: ClassVar[dict[str, str]] = {"polymorphic_identity": "dummy_post"}

    def calculateScore(self) -> int:
        return sum(v.value for v in self.votes)


class _DummyAuthor:
    id = 99

    def getName(self) -> str:
        return "autor-ejemplo"


def test_post_es_abstracto_y_valida_campos() -> None:
    author = _DummyAuthor()

    with pytest.raises(TypeError, match="abstracta"):
        Post(body="Contenido", author=author)

    with pytest.raises(ValueError, match="nulo ni vacío"):
        _DummyPost(body="   ", author=author)

    with pytest.raises(ValueError, match="autor obligatorio"):
        _DummyPost(body="Contenido válido")

    with pytest.raises(TypeError, match="IAuthor"):
        _DummyPost(body="Contenido válido", author=object())


def test_post_asocia_autor_y_declara_calculate_score_abstracto() -> None:
    author = _DummyAuthor()
    post = _DummyPost(body="Pregunta de prueba", author=author)

    assert post.author is author
    assert post.author_type == "_DummyAuthor"
    assert post.author_id == 99
    assert post.isHidden is False

    with pytest.raises(NotImplementedError):
        Post.calculateScore(post)


def test_vote_valida_argumentos() -> None:
    author = _DummyAuthor()
    post = _DummyPost(body="Post", author=author)
    user = NormalUser(email="ana@unrc.edu.ar", passwordHash="secret123")

    with pytest.raises(ValueError, match="User"):
        Vote(value=1, user=None, post=post)

    with pytest.raises(ValueError, match="Post"):
        Vote(value=1, user=user, post=None)

    with pytest.raises(ValueError, match=r"\+1 o -1"):
        Vote(value=5, user=user, post=post)


def test_post_vote_crea_modifica_y_revierte_voto_en_bd(app) -> None:
    student = NormalUser(email="juan@unrc.edu.ar", passwordHash="secret123")
    admin = AdminUser(email="admin@unrc.edu.ar", passwordHash="secret456")
    db.session.add_all([student, admin])
    db.session.flush()

    post = _DummyPost(body="¿Cómo funciona Strategy?", author=student)
    db.session.add(post)
    db.session.commit()

    # 1. Voto positivo inicial
    post.vote(student, 1)
    db.session.commit()
    assert len(post.votes) == 1
    assert post.votes[0].value == 1
    assert post.calculateScore() == 1

    # 2. Cambio de voto (+1 -> -1) sin duplicar registro
    post.vote(student, -1)
    db.session.commit()
    assert len(post.votes) == 1
    assert post.votes[0].value == -1
    assert post.calculateScore() == -1

    # 3. Otro usuario (AdminUser) también puede votar sin colisionar
    post.vote(admin, 1)
    db.session.commit()
    assert len(post.votes) == 2
    assert post.calculateScore() == 0

    # 4. Repetir mismo voto (-1) lo elimina (toggle)
    post.vote(student, -1)
    db.session.commit()
    assert len(post.votes) == 1
    assert post.calculateScore() == 1
