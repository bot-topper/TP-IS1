from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from myapp.models.user import IAuthor

if TYPE_CHECKING:
    from myapp.models.post import Post

#Clase abstracta del Factory
class PostCreatorAbs(ABC):
    @abstractmethod
    def createPost(self, data: dict, author: IAuthor) -> Post:
        ...
