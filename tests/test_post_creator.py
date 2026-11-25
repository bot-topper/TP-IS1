"""Pruebas unitarias para PostCreatorAbs"""

from typing import ClassVar

import pytest

from myapp.models.post import Post
from myapp.services.factory.post_creator_abs import PostCreatorAbs


class _DummyPost(Post):
    __mapper_args__: ClassVar[dict[str, str]] = {
        "polymorphic_identity": "dummy_creator_post"
    }
    def calculateScore(self) -> int:
        return 0


class _DummyCreator(PostCreatorAbs):
    def createPost(self, data: dict, autor: object) -> Post:
        return _DummyPost(body=data["body"], author=autor)


class _DummyAuthor:
    def getName(self) -> str:
        return "autor"


def test_post_creator_abs_es_abstracta_y_soporta_iauthor() -> None:
    with pytest.raises(TypeError):
        PostCreatorAbs()  # type: ignore[abstract]

    creator = _DummyCreator()
    post = creator.createPost({"body": "Contenido"}, autor=_DummyAuthor())
    assert isinstance(post, Post)
    assert post.author is not None
    assert post.author.getName() == "autor"