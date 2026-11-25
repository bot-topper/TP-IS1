from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from myapp.models.user import IAuthor

if TYPE_CHECKING:
    from myapp.models.post import Post
#
class postCreator(ABC):
    @abstractmethod
    def createPost(self, data: dict, author: IAuthor) -> Post:
        ...
        