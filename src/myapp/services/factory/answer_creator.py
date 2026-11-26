from __future__ import annotations

from typing import Any

from myapp.models.answer import Answer
from myapp.models.user import User
from myapp.services.ai.agent_ia import AgentIA
from myapp.services.factory.post_creator_abs import PostCreatorAbs


class AnswerCreator(PostCreatorAbs):
    def createPost(self, data: dict[str, Any], autor: object) -> Answer:
        if autor is None or not isinstance(autor, (User, AgentIA)):
            raise ValueError("El autor de una respuesta debe ser un User o un AgentIA.")

        if not isinstance(data, dict):
            raise TypeError(
                "Los datos de la respuesta deben enviarse en un diccionario."
            )

        missing = [field for field in ("body", "question") if field not in data]
        if missing:
            raise ValueError(
                f"Faltan campos obligatorios para crear la respuesta: {', '.join(missing)}."
            )

        if isinstance(autor, AgentIA):
            strategy = getattr(autor, "strategyIA", None)
            default_model = getattr(
                strategy,
                "model",
                type(strategy).__name__ if strategy is not None else None,
            )
            is_ai = True
            model_used = data.get("modelUsed") or default_model
            trigger_type = data.get("triggerType") or "TAG"
        else:
            is_ai = bool(data.get("isAIGenerated", False))
            model_used = data.get("modelUsed")
            trigger_type = data.get("triggerType")

        return Answer(
            body=data["body"],
            question=data["question"],
            author=autor,
            isAIGenerated=is_ai,
            modelUsed=model_used,
            triggerType=trigger_type,
        )
