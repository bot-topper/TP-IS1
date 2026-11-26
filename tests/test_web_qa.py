"""Pruebas funcionales de las vistas Web Q&A, IA, notificaciones y moderación (Sub-issue 7.2)."""

from myapp.extensions import db
from myapp.models.answer import Answer
from myapp.models.moderation_log import ModerationLog
from myapp.models.notification import Notification
from myapp.models.question import Question, QuestionStatus


def _register_and_login(client, email: str, password: str, role: str = "normal") -> None:
    client.post(
        "/auth/register",
        data={"email": email, "password": password, "role": role},
        follow_redirects=True,
    )


def test_home_redirects_and_filters_questions_by_category_and_tag(app, client) -> None:
    home_resp = client.get("/")
    assert home_resp.status_code == 302
    assert "/questions/" in home_resp.headers["Location"]

    _register_and_login(client, "autor@unrc.edu.ar", "secret123", "normal")

    client.post(
        "/questions/new",
        data={
            "title": "Duda Python",
            "new_category": "Python",
            "tags": "python, flask",
            "body": "¿Cómo usar Blueprints?",
        },
        follow_redirects=True,
    )
    client.post(
        "/questions/new",
        data={
            "title": "Duda SQL",
            "new_category": "Bases de Datos",
            "tags": "sqlite",
            "body": "¿Cómo definir FK?",
        },
        follow_redirects=True,
    )

    by_cat = client.get("/questions/?category=python")
    assert by_cat.status_code == 200
    assert b"Duda Python" in by_cat.data
    assert b"Duda SQL" not in by_cat.data

    by_tag = client.get("/questions/?tag=sqlite")
    assert by_tag.status_code == 200
    assert b"Duda SQL" in by_tag.data
    assert b"Duda Python" not in by_tag.data


def test_create_question_with_ia_help_triggers_tag_question_manager(app, client) -> None:
    _register_and_login(client, "estudiante@unrc.edu.ar", "secret123", "normal")

    resp = client.post(
        "/questions/new",
        data={
            "title": "¿Qué es Strategy?",
            "new_category": "Patrones",
            "tags": "#ia-help, patrones",
            "body": "Necesito ayuda con el patrón Strategy.",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Bot-UNRC [IA]" in resp.data
    assert b"TAG" in resp.data

    with app.app_context():
        question = db.session.scalars(db.select(Question)).first()
        assert question is not None
        assert len(question.answers) == 1
        assert question.answers[0].isAIGenerated is True
        assert question.answers[0].triggerType == "TAG"


def test_answer_accept_vote_comment_subscribe_and_notifications(app, client) -> None:
    _register_and_login(client, "autor@unrc.edu.ar", "secret123", "normal")
    client.post(
        "/questions/new",
        data={
            "title": "Hilo de prueba",
            "new_category": "General",
            "tags": "duda",
            "body": "Cuerpo del hilo.",
        },
    )

    with app.app_context():
        question = db.session.scalars(db.select(Question)).first()
        assert question is not None
        q_id = question.id

    # Segundo usuario responde, vota y comenta
    client.post("/auth/logout")
    _register_and_login(client, "helper@unrc.edu.ar", "secret123", "normal")

    ans_resp = client.post(
        f"/questions/{q_id}/answers",
        data={"body": "Esta es la solución."},
        follow_redirects=True,
    )
    assert ans_resp.status_code == 200
    assert b"Esta es la soluci" in ans_resp.data

    with app.app_context():
        ans = db.session.scalars(db.select(Answer)).first()
        assert ans is not None
        ans_id = ans.id

    # Votar pregunta y respuesta (+1)
    client.post(f"/posts/{q_id}/vote", data={"value": "1"})
    client.post(f"/posts/{ans_id}/vote", data={"value": "1"})

    # Comentar en respuesta y suscribirse
    client.post(f"/posts/{ans_id}/comments", data={"body": "Buen aporte"})
    client.post(f"/questions/{q_id}/subscribe")

    # Autor acepta respuesta y revisa sus notificaciones
    client.post("/auth/logout")
    client.post(
        "/auth/login",
        data={"email": "autor@unrc.edu.ar", "password": "secret123"},
    )
    accept_resp = client.post(f"/answers/{ans_id}/accept", follow_redirects=True)
    assert accept_resp.status_code == 200
    assert b"ACEPTADA" in accept_resp.data
    assert b"ANSWERED" in accept_resp.data

    notif_resp = client.get("/notifications/")
    assert notif_resp.status_code == 200
    assert b"helper@unrc.edu.ar" in notif_resp.data

    with app.app_context():
        notif = db.session.scalars(db.select(Notification)).first()
        assert notif is not None
        notif_id = notif.id

    read_resp = client.post(f"/notifications/{notif_id}/read", follow_redirects=True)
    assert read_resp.status_code == 200
    with app.app_context():
        refreshed = db.session.get(Notification, notif_id)
        assert refreshed is not None
        assert refreshed.isRead is True


def test_admin_moderation_commands_and_normal_user_forbidden(app, client) -> None:
    _register_and_login(client, "user@unrc.edu.ar", "secret123", "normal")
    client.post(
        "/questions/new",
        data={
            "title": "Hilo moderable",
            "new_category": "General",
            "tags": "test",
            "body": "Contenido.",
        },
    )

    with app.app_context():
        q_id = db.session.scalars(db.select(Question)).first().id

    # Usuario normal no puede moderar
    forbidden = client.post(f"/questions/{q_id}/moderate-close")
    assert forbidden.status_code == 403

    # AdminUser cierra y oculta el hilo generando ModerationLog
    client.post("/auth/logout")
    _register_and_login(client, "admin@unrc.edu.ar", "admin456", "admin")

    close_resp = client.post(
        f"/questions/{q_id}/moderate-close",
        data={"reason": "Duplicada"},
        follow_redirects=True,
    )
    assert close_resp.status_code == 200
    assert b"CLOSED" in close_resp.data

    hide_resp = client.post(
        f"/posts/{q_id}/moderate-hide",
        data={"reason": "Spam"},
        follow_redirects=True,
    )
    assert hide_resp.status_code == 200
    assert b"OCULTO" in hide_resp.data

    with app.app_context():
        question = db.session.get(Question, q_id)
        assert question is not None
        assert question.status == QuestionStatus.CLOSED
        assert question.isHidden is True
        logs = db.session.scalars(db.select(ModerationLog)).all()
        assert len(logs) == 2


def test_create_question_with_failing_ai_key_does_not_crash(app, client) -> None:
    from myapp.services.ai.strategies import AnswerIA

    class _FailingStrategy(AnswerIA):
        def answer(self, question) -> str:
            raise RuntimeError("Error HTTP 401: API key inválida")

    app.config["AI_STRATEGY_FACTORY"] = _FailingStrategy
    _register_and_login(client, "user@unrc.edu.ar", "secret123", "normal")

    resp = client.post(
        "/questions/new",
        data={
            "title": "Pregunta con key inválida",
            "new_category": "General",
            "tags": "#ia-help",
            "body": "El hilo debe publicarse igual.",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Pregunta con key" in resp.data
    assert b"Error HTTP 401" in resp.data
