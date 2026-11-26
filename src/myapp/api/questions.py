from flask import Blueprint, g, request

from myapp.extensions import db
from myapp.models.answer import Answer
from myapp.models.question import Question
from myapp.services.ai.tag_question_manager import TagQuestionManager
from myapp.services.factory.answer_creator import AnswerCreator
from myapp.services.factory.question_creator import QuestionCreator
from myapp.services.notifications.mediator import QANotificationMediator
from myapp.web.questions import (
    _author_label,
    _build_ai_agent,
    _can_manage_question,
    _get_or_create_category,
    _notify_and_persist,
    _parse_tags,
)

api_questions_bp = Blueprint("api_questions", __name__, url_prefix="/api/questions")


def _serialize_answer(answer: Answer) -> dict:
    return {
        "id": answer.id,
        "body": answer.body,
        "author": _author_label(answer),
        "acceptedAnswer": answer.acceptedAnswer,
        "isAIGenerated": answer.isAIGenerated,
        "modelUsed": answer.modelUsed,
        "triggerType": answer.triggerType,
        "score": answer.calculateScore(),
        "isHidden": answer.isHidden,
        "publicationDate": answer.publicationDate.isoformat(),
    }


def _serialize_question(question: Question, include_answers: bool = False) -> dict:
    payload = {
        "id": question.id,
        "title": question.title,
        "body": question.body,
        "author": _author_label(question),
        "status": question.status.value,
        "category": {
            "id": question.category.id,
            "name": question.category.name,
            "slug": question.category.slug,
        },
        "tags": [tag.name for tag in question.tags],
        "score": question.calculateScore(),
        "answersCount": len(question.answers),
        "isHidden": question.isHidden,
        "publicationDate": question.publicationDate.isoformat(),
    }
    if include_answers:
        payload["answers"] = [_serialize_answer(ans) for ans in question.answers]
    return payload


@api_questions_bp.get("")
def list_questions():
    category_slug = request.args.get("category", "").strip().lower()
    tag_name = request.args.get("tag", "").strip().lower()

    stmt = db.select(Question).order_by(Question.publicationDate.desc(), Question.id.desc())
    questions = list(db.session.scalars(stmt).all())

    if category_slug:
        questions = [q for q in questions if q.category.slug == category_slug]
    if tag_name:
        questions = [q for q in questions if any(t.name == tag_name for t in q.tags)]

    return {"questions": [_serialize_question(q) for q in questions]}


@api_questions_bp.get("/<int:question_id>")
def get_question(question_id: int):
    question = db.session.get(Question, question_id)
    if question is None:
        return {"error": "Pregunta no encontrada."}, 404
    return _serialize_question(question, include_answers=True)


@api_questions_bp.post("")
def create_question():
    user = getattr(g, "current_user", None)
    if user is None:
        return {"error": "Autenticación requerida."}, 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "Se requiere un cuerpo JSON válido."}, 400

    title = payload.get("title", "")
    body = payload.get("body", "")
    category_name = payload.get("category", "")
    raw_tags = payload.get("tags", [])

    if not isinstance(category_name, str) or not category_name.strip():
        return {"error": "El campo 'category' es obligatorio."}, 400
    if not isinstance(raw_tags, list) or not all(isinstance(t, str) for t in raw_tags):
        return {"error": "El campo 'tags' debe ser una lista de strings."}, 400

    try:
        category = _get_or_create_category(category_name)
        tags = _parse_tags(",".join(raw_tags))
        question = QuestionCreator().createPost(
            data={
                "title": title,
                "body": body,
                "category": category,
                "tags": tags,
            },
            autor=user,
        )
        db.session.add(question)
        db.session.commit()

        manager = TagQuestionManager(
            agent_ia=_build_ai_agent(),
            answer_creator=AnswerCreator(),
        )
        manager.checkLabelQuestion(question)
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return {"error": str(exc)}, 400

    return _serialize_question(question, include_answers=True), 201


@api_questions_bp.post("/<int:question_id>/answers")
def create_answer(question_id: int):
    user = getattr(g, "current_user", None)
    if user is None:
        return {"error": "Autenticación requerida."}, 401

    question = db.session.get(Question, question_id)
    if question is None:
        return {"error": "Pregunta no encontrada."}, 404

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "Se requiere un cuerpo JSON válido."}, 400

    body = payload.get("body", "")
    try:
        answer = AnswerCreator().createPost(
            data={"body": body, "question": question},
            autor=user,
        )
        db.session.add(answer)
        _notify_and_persist(QANotificationMediator.EVENT_NEW_ANSWER, answer, user)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return {"error": str(exc)}, 400

    return _serialize_answer(answer), 201


@api_questions_bp.patch("/<int:question_id>")
def update_question(question_id: int):
    user = getattr(g, "current_user", None)
    if user is None:
        return {"error": "Autenticación requerida."}, 401

    question = db.session.get(Question, question_id)
    if question is None:
        return {"error": "Pregunta no encontrada."}, 404

    if not _can_manage_question(question, user):
        return {"error": "No tienes permisos para editar esta pregunta."}, 403

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "Se requiere un cuerpo JSON válido."}, 400

    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip():
            return {"error": "El título no puede estar vacío."}, 400
        question.title = title.strip()

    if "body" in payload:
        body = payload["body"]
        if not isinstance(body, str) or not body.strip():
            return {"error": "El cuerpo no puede estar vacío."}, 400
        question.body = body.strip()

    db.session.commit()
    return _serialize_question(question, include_answers=True)


@api_questions_bp.delete("/<int:question_id>")
def delete_question(question_id: int):
    user = getattr(g, "current_user", None)
    if user is None:
        return {"error": "Autenticación requerida."}, 401

    question = db.session.get(Question, question_id)
    if question is None:
        return {"error": "Pregunta no encontrada."}, 404

    if not _can_manage_question(question, user):
        return {"error": "No tienes permisos para eliminar esta pregunta."}, 403

    db.session.delete(question)
    db.session.commit()
    return {"deleted": True, "id": question_id}
