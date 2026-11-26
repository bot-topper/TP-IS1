from myapp.models.category import Category
from myapp.models.question import Question
from myapp.models.user import IAuthor, User
from myapp.services.factory.post_creator_abs import PostCreatorAbs

REQUIRED_FIELDS = ("title", "body", "category")


class QuestionCreator(PostCreatorAbs):
    def createPost(self, data: dict, autor: IAuthor) -> Question:
        if not isinstance(autor, User):
            raise TypeError("El autor de una pregunta debe ser una instancia de User.")

        if not isinstance(data, dict):
            raise TypeError(
                "Los datos de la pregunta deben enviarse en un diccionario."
            )

        missing = []
        for field in REQUIRED_FIELDS:
            if data.get(field) is None:
                missing.append(field)

        # Como python evalua las listas que contienen elementos como True, hago un join (tomar todos los elementos
        # y los mete en una sola string separandolos por ,)
        if missing:
            raise ValueError(f"Faltan campos obligatorios: {', '.join(missing)}.")

        title = data["title"]
        body = data["body"]
        category = data["category"]

        if not isinstance(title, str) or not title.strip():
            raise ValueError("El campo 'title' debe ser un texto no vacío.")

        if not isinstance(body, str) or not body.strip():
            raise ValueError("El campo 'body' debe ser un texto no vacío.")

        if not isinstance(category, Category):
            raise TypeError(
                "El campo 'category' debe ser una instancia válida de Category."
            )

        return Question(
            title=title.strip(),
            body=body.strip(),
            category=category,
            author=autor,
            tags=data.get("tags"),
        )
