from typing import ClassVar

from sqlalchemy import ForeignKey

from myapp.extensions import db
from myapp.models.post import Post
from myapp.models.question import Question


class Answer(Post):
    __tablename__ = "answer"
    __mapper_args__: ClassVar[dict[str, str]] = {
            "polymorphic_identity": "answer",
        }

    id = db.Column(db.Integer, ForeignKey("post.id"), primary_key = True)
    acceptedAnswer = db.Column(db.Boolean, nullable = False, default = False)
    isAIGenerated = db.Column(db.Boolean, nullable = False, default = False)
    modelUsed = db.Column(db.String(100), nullable = True)
    triggerType = db.Column(db.String(100), nullable = True)

    #Clave foranea de Question
    question_id = db.Column(db.Integer, ForeignKey("question.id"), nullable = False)


    def __init__(self,
                 body: str,
                 question: Question,
                 author: object | None = None,
                 isAIGenerated: bool = False,
                 modelUsed: str | None = None,
                 triggerType: str | None = None,
                 **kwargs,
                 ) -> None:

        if question is None or not isinstance(question, Question):
            raise ValueError("La respuesta debe pertenecer a una Question válida.")

        if not isinstance(isAIGenerated, bool):
            raise TypeError("isAIGenerated debe ser un valor booleano")

        # si es generado con IA
        if isAIGenerated:
            #si modelUsed es None O modelUsed no es un str O modelUser es vacio
            if modelUsed is None or not isinstance(modelUsed, str) or modelUsed.strip() == "":
                raise ValueError("Una respuesta generada por IA debe indicar el modelUsed.")

            #si triggerType es None O triggerType no es un str O triggerType es vacio
            if triggerType is None or not isinstance(triggerType, str) or triggerType.strip() == "":
                raise ValueError("Una respuesta generada por IA debe indicar el triggerType.")

        super().__init__(
            body = body,
            author = author,
            **kwargs
        )

        #llena automaticamente el tributo question_id
        self.question = question
        self.acceptedAnswer = False
        self.isAIGenerated = isAIGenerated
        self.modelUsed = modelUsed.strip() if isinstance(modelUsed, str) and modelUsed.strip() else None
        self.triggerType = triggerType.strip().upper() if isinstance(triggerType, str) and triggerType.strip() else None


    def calculateScore(self) -> int:
        return sum(v.value for v in self.votes)

    def accept(self) -> None:
        if self.question is None:
            raise ValueError("La respuesta debe estar asociada a una pregunta para ser aceptada.")

        #marcar la pregunta como respondida ya que tiene una respuesta aceptada
        self.question.markAsAnswered()

        #buscamos si habia otra respuesta aceptada y la desmarcamos
        for answer in self.question.answers:
            if answer is not self and answer.acceptedAnswer:
                answer.acceptedAnswer = False

        #marcamos la respuesta nueva
        self.acceptedAnswer = True