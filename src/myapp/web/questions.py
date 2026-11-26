import os

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from myapp.extensions import db
from myapp.models.answer import Answer
from myapp.models.category import Category
from myapp.models.comment import Comment
from myapp.models.post import Post
from myapp.models.question import Question
from myapp.models.tag import Tag
from myapp.models.user import AdminUser, NormalUser, User
from myapp.services.ai.agent_ia import AgentIA
from myapp.services.ai.cached_ai_proxy import CachedAIProxy, QuotaExceededError
from myapp.services.ai.strategies import AnswerGemini, AnswerIA, AnswerOpenAI
from myapp.services.ai.tag_question_manager import TagQuestionManager
from myapp.services.factory.answer_creator import AnswerCreator
from myapp.services.factory.question_creator import QuestionCreator
from myapp.services.moderation.commands import CloseQuestionCommand, HidePostCommand
from myapp.services.notifications.mediator import QANotificationMediator

questions_bp = Blueprint("questions", __name__)

_USER_MODELS = {
    "NormalUser": NormalUser,
    "AdminUser": AdminUser,
}


class _LocalBoardFallbackStrategy(AnswerIA):
    """Estrategia local de respaldo cuando no hay credenciales LLM configuradas."""

    model = "board-assistant-local"

    def answer(self, question) -> str:
        return (
            f"> {question.title}\n"
            "Sugerencia automática del asistente: revisa el planteo paso a paso "
            "y verifica los modelos/tests asociados en el repositorio."
        )


def _build_ai_agent() -> AgentIA:
    custom_factory = current_app.config.get("AI_STRATEGY_FACTORY")
    if callable(custom_factory):
        strategy = custom_factory()
    elif os.getenv("GEMINI_API_KEY"):
        strategy = AnswerGemini()
    elif os.getenv("OPENAI_API_KEY"):
        strategy = AnswerOpenAI()
    else:
        strategy = _LocalBoardFallbackStrategy()

    proxy = CachedAIProxy(realStrategy=strategy, maxRequestsPerHour=20)
    return AgentIA(agentName="Bot-UNRC", strategy_ia=proxy)


def _resolve_author(post: Post) -> object | None:
    if post.author is not None:
        return post.author
    if post.author_type == "AgentIA":
        return None
    model_cls = _USER_MODELS.get(post.author_type)
    if model_cls is not None and post.author_id is not None:
        return db.session.get(model_cls, post.author_id)
    return None


def _author_label(post: Post) -> str:
    if post.author_type == "AgentIA":
        return "Bot-UNRC [IA]"
    resolved = _resolve_author(post)
    if resolved is not None and callable(getattr(resolved, "getName", None)):
        return resolved.getName()
    return post.author_type


def _is_question_author(question: Question, user: User | None) -> bool:
    if user is None:
        return False
    return (
        question.author_type == type(user).__name__
        and question.author_id == getattr(user, "id", None)
    )


def _slugify(value: str) -> str:
    cleaned = "-".join(value.strip().lower().split())
    return cleaned or "general"


def _get_or_create_category(name: str) -> Category:
    normalized_name = name.strip()
    slug = _slugify(normalized_name)
    existing = db.session.scalars(
        db.select(Category).where(Category.slug == slug)
    ).first()
    if existing is not None:
        return existing
    category = Category(name=normalized_name, slug=slug)
    db.session.add(category)
    db.session.flush()
    return category


def _parse_tags(raw_tags: str) -> list[Tag]:
    tags: list[Tag] = []
    seen: set[str] = set()
    for part in raw_tags.split(","):
        normalized = part.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        existing = db.session.scalars(
            db.select(Tag).where(Tag.name == normalized)
        ).first()
        if existing is None:
            existing = Tag(name=normalized)
            db.session.add(existing)
            db.session.flush()
        tags.append(existing)
    return tags


def _require_user() -> User | None:
    user = getattr(g, "current_user", None)
    if user is None:
        flash("Debes iniciar sesión para realizar esta acción.")
        return None
    return user


def _notify_and_persist(event: str, post: object, actor: object) -> None:
    if hasattr(post, "author") and post.author is None and isinstance(post, Post):
        resolved = _resolve_author(post)
        if resolved is not None:
            post._author = resolved
    if hasattr(post, "question") and post.question is not None:
        q = post.question
        if q.author is None:
            q_author = _resolve_author(q)
            if q_author is not None:
                q._author = q_author

    mediator = QANotificationMediator()
    notifs = mediator.notify(event, post, actor)
    if notifs:
        db.session.add_all(notifs)


@questions_bp.get("/")
def home():
    return redirect(url_for("questions.index"))


@questions_bp.get("/questions/")
def index():
    category_slug = request.args.get("category", "").strip().lower()
    tag_name = request.args.get("tag", "").strip().lower()

    stmt = db.select(Question).order_by(Question.publicationDate.desc(), Question.id.desc())
    questions = list(db.session.scalars(stmt).all())

    if category_slug:
        questions = [q for q in questions if q.category.slug == category_slug]
    if tag_name:
        questions = [q for q in questions if any(t.name == tag_name for t in q.tags)]

    categories = db.session.scalars(db.select(Category).order_by(Category.name)).all()
    tags = db.session.scalars(db.select(Tag).order_by(Tag.name)).all()

    return render_template(
        "questions/index.html",
        questions=questions,
        categories=categories,
        tags=tags,
        selected_category=category_slug,
        selected_tag=tag_name,
        author_label=_author_label,
    )


@questions_bp.route("/questions/new", methods=["GET", "POST"])
def create():
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    categories = db.session.scalars(db.select(Category).order_by(Category.name)).all()

    if request.method == "POST":
        title = request.form.get("title", "")
        body = request.form.get("body", "")
        category_id = request.form.get("category_id", "").strip()
        new_category = request.form.get("new_category", "").strip()
        raw_tags = request.form.get("tags", "")

        try:
            if new_category:
                category = _get_or_create_category(new_category)
            elif category_id.isdigit():
                category = db.session.get(Category, int(category_id))
            else:
                category = None

            if category is None:
                raise ValueError("Debes seleccionar o crear una categoría.")

            tags = _parse_tags(raw_tags)
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

            # Disparo automático si incluye #ia-help
            manager = TagQuestionManager(
                agent_ia=_build_ai_agent(),
                answer_creator=AnswerCreator(),
            )
            try:
                manager.checkLabelQuestion(question)
            except RuntimeError as exc:
                flash(f"Hilo publicado, pero falló la respuesta automática IA: {exc}")
                return redirect(url_for("questions.detail", question_id=question.id))

            flash("Hilo publicado correctamente.")
            return redirect(url_for("questions.detail", question_id=question.id))
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            return (
                render_template(
                    "questions/new.html",
                    categories=categories,
                    error=str(exc),
                ),
                400,
            )

    return render_template("questions/new.html", categories=categories)


@questions_bp.get("/questions/<int:question_id>")
def detail(question_id: int):
    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    current_user = getattr(g, "current_user", None)
    is_author = _is_question_author(question, current_user)
    is_subscribed = (
        isinstance(current_user, NormalUser) and current_user in question.subscribers
    )

    return render_template(
        "questions/detail.html",
        question=question,
        is_author=is_author,
        is_subscribed=is_subscribed,
        author_label=_author_label,
    )


@questions_bp.post("/questions/<int:question_id>/answers")
def add_answer(question_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    body = request.form.get("body", "")
    try:
        answer = AnswerCreator().createPost(
            data={"body": body, "question": question},
            autor=user,
        )
        db.session.add(answer)
        _notify_and_persist(QANotificationMediator.EVENT_NEW_ANSWER, answer, user)
        db.session.commit()
        flash("Respuesta publicada.")
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        flash(str(exc))

    return redirect(url_for("questions.detail", question_id=question.id))


@questions_bp.post("/answers/<int:answer_id>/accept")
def accept_answer(answer_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    answer = db.session.get(Answer, answer_id)
    if answer is None:
        abort(404)

    if not _is_question_author(answer.question, user):
        abort(403)

    try:
        answer.accept()
        _notify_and_persist(QANotificationMediator.EVENT_ANSWER_ACCEPTED, answer, user)
        db.session.commit()
        flash("Respuesta marcada como aceptada.")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc))

    return redirect(url_for("questions.detail", question_id=answer.question_id))


@questions_bp.post("/posts/<int:post_id>/vote")
def vote_post(post_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)

    raw_value = request.form.get("value", "")
    try:
        value = int(raw_value)
        post.vote(user, value)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc))

    question_id = post.question_id if isinstance(post, Answer) else post.id
    return redirect(url_for("questions.detail", question_id=question_id))


@questions_bp.post("/posts/<int:post_id>/comments")
def add_comment(post_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)

    body = request.form.get("body", "")
    try:
        comment = Comment(body=body, user=user, post=post)
        db.session.add(comment)
        _notify_and_persist(QANotificationMediator.EVENT_NEW_COMMENT, post, user)
        db.session.commit()
        flash("Comentario agregado.")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc))

    question_id = post.question_id if isinstance(post, Answer) else post.id
    return redirect(url_for("questions.detail", question_id=question_id))


@questions_bp.post("/questions/<int:question_id>/subscribe")
def toggle_subscribe(question_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    if not isinstance(user, NormalUser):
        flash("Solo los usuarios normales pueden suscribirse a preguntas.")
        return redirect(url_for("questions.detail", question_id=question_id))

    if user in question.subscribers:
        question.unsubscribe(user)
        flash("Suscripción cancelada.")
    else:
        question.subscribe(user)
        flash("Suscripto al hilo.")
    db.session.commit()
    return redirect(url_for("questions.detail", question_id=question_id))


@questions_bp.post("/questions/<int:question_id>/ai-answer")
def generate_ai_answer(question_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    try:
        agent = _build_ai_agent()
        body = agent.strategyIA.answer(question, user=user)
        strategy = getattr(agent.strategyIA, "realStrategy", agent.strategyIA)
        model_used = getattr(strategy, "model", type(strategy).__name__)
        answer = AnswerCreator().createPost(
            data={
                "body": body,
                "question": question,
                "isAIGenerated": True,
                "modelUsed": model_used,
                "triggerType": "MANUAL",
            },
            autor=agent,
        )
        db.session.add(answer)
        _notify_and_persist(QANotificationMediator.EVENT_NEW_ANSWER, answer, agent)
        db.session.commit()
        flash("Respuesta generada por el agente IA.")
    except QuotaExceededError as exc:
        db.session.rollback()
        flash(str(exc))
    except (RuntimeError, ValueError) as exc:
        db.session.rollback()
        flash(f"No se pudo generar respuesta IA: {exc}")

    return redirect(url_for("questions.detail", question_id=question_id))


@questions_bp.post("/questions/<int:question_id>/moderate-close")
def moderate_close(question_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))
    if not isinstance(user, AdminUser):
        abort(403)

    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    reason = request.form.get("reason", "Cerrada por moderación")
    cmd = CloseQuestionCommand(targetQuestion=question, reason=reason)
    user.executeModeration(cmd, reason=reason)
    db.session.commit()
    flash("Pregunta cerrada por moderación.")
    return redirect(url_for("questions.detail", question_id=question_id))


@questions_bp.post("/posts/<int:post_id>/moderate-hide")
def moderate_hide(post_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))
    if not isinstance(user, AdminUser):
        abort(403)

    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)

    reason = request.form.get("reason", "Visibilidad alternada por moderación")
    cmd = HidePostCommand(targetPost=post, reason=reason)
    user.executeModeration(cmd, reason=reason)
    db.session.commit()
    flash("Visibilidad del post actualizada.")
    question_id = post.question_id if isinstance(post, Answer) else post.id
    return redirect(url_for("questions.detail", question_id=question_id))


def _can_manage_question(question: Question, user: User | None) -> bool:
    return _is_question_author(question, user) or isinstance(user, AdminUser)


@questions_bp.route("/questions/<int:question_id>/edit", methods=["GET", "POST"])
def edit(question_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    if not _can_manage_question(question, user):
        abort(403)

    categories = db.session.scalars(db.select(Category).order_by(Category.name)).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        category_id = request.form.get("category_id", "").strip()
        raw_tags = request.form.get("tags")

        if not title:
            return (
                render_template(
                    "questions/edit.html",
                    question=question,
                    categories=categories,
                    error="El título de la pregunta no puede estar vacío.",
                ),
                400,
            )
        if not body:
            return (
                render_template(
                    "questions/edit.html",
                    question=question,
                    categories=categories,
                    error="El cuerpo de la pregunta no puede estar vacío.",
                ),
                400,
            )

        if category_id.isdigit():
            category = db.session.get(Category, int(category_id))
            if category is not None:
                question.category = category

        question.title = title
        question.body = body
        if raw_tags is not None:
            question.tags.clear()
            for tag in _parse_tags(raw_tags):
                question.add_tag(tag)

        db.session.commit()
        flash("Hilo actualizado.")
        return redirect(url_for("questions.detail", question_id=question.id))

    return render_template("questions/edit.html", question=question, categories=categories)


@questions_bp.post("/questions/<int:question_id>/delete")
def delete(question_id: int):
    user = _require_user()
    if user is None:
        return redirect(url_for("auth.login"))

    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    if not _can_manage_question(question, user):
        abort(403)

    db.session.delete(question)
    db.session.commit()
    flash("Hilo eliminado.")
    return redirect(url_for("questions.index"))
