"""Pruebas de API JSON e integración extremo a extremo (Sub-issue 7.3)."""

from myapp.extensions import db
from myapp.models.moderation_log import ModerationLog
from myapp.models.notification import Notification
from myapp.models.question import Question, QuestionStatus


def _register(client, email: str, password: str, role: str = "normal") -> None:
    client.post(
        "/auth/register",
        data={"email": email, "password": password, "role": role},
        follow_redirects=True,
    )


def test_api_questions_requires_auth_and_validates_payloads(app, client) -> None:
    # Sin sesión retorna 401
    unauth = client.post(
        "/api/questions",
        json={"title": "Hola", "body": "Cuerpo", "category": "Python"},
    )
    assert unauth.status_code == 401

    assert client.get("/api/questions/9999").status_code == 404

    _register(client, "apiuser@unrc.edu.ar", "secret123", "normal")

    bad_payload = client.post("/api/questions", json={"title": "Sin categoría", "body": "x"})
    assert bad_payload.status_code == 400

    bad_tags = client.post(
        "/api/questions",
        json={"title": "T", "body": "B", "category": "Python", "tags": "no-es-lista"},
    )
    assert bad_tags.status_code == 400

    missing_q_answer = client.post("/api/questions/9999/answers", json={"body": "Hola"})
    assert missing_q_answer.status_code == 404


def test_api_questions_crud_and_filters(app, client) -> None:
    _register(client, "dev@unrc.edu.ar", "secret123", "normal")

    create_resp = client.post(
        "/api/questions",
        json={
            "title": "¿Cómo usar Factory Method?",
            "body": "Ejemplo en Python con Flask.",
            "category": "Patrones",
            "tags": ["factory", "python"],
        },
    )
    assert create_resp.status_code == 201
    data = create_resp.get_json()
    assert data["title"] == "¿Cómo usar Factory Method?"
    assert data["status"] == "OPEN"
    assert data["category"]["slug"] == "patrones"
    assert data["tags"] == ["factory", "python"]
    q_id = data["id"]

    # Listado y filtros
    list_all = client.get("/api/questions").get_json()["questions"]
    assert len(list_all) == 1

    list_match = client.get("/api/questions?category=patrones&tag=factory").get_json()["questions"]
    assert len(list_match) == 1

    list_empty = client.get("/api/questions?tag=inexistente").get_json()["questions"]
    assert list_empty == []

    # Detalle JSON
    detail_resp = client.get(f"/api/questions/{q_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["answers"] == []


def test_end_to_end_integration_flow_api_ia_notifications_and_moderation(app, client) -> None:
    # 1. Autor crea pregunta con #ia-help vía API (dispara QuestionCreator + TagQuestionManager)
    _register(client, "autor@unrc.edu.ar", "secret123", "normal")
    q_resp = client.post(
        "/api/questions",
        json={
            "title": "Duda sobre Proxy y Strategy",
            "body": "¿Cómo se conectan ambos patrones?",
            "category": "Arquitectura",
            "tags": ["#ia-help", "patrones"],
        },
    )
    assert q_resp.status_code == 201
    q_data = q_resp.get_json()
    q_id = q_data["id"]
    assert q_data["answersCount"] == 1
    assert q_data["answers"][0]["isAIGenerated"] is True
    assert q_data["answers"][0]["triggerType"] == "TAG"

    # 2. Segundo usuario responde vía API (AnswerCreator + QANotificationMediator) y vota
    client.post("/auth/logout")
    _register(client, "colaborador@unrc.edu.ar", "secret123", "normal")

    ans_resp = client.post(
        f"/api/questions/{q_id}/answers",
        json={"body": "Proxy envuelve a Strategy implementando la misma interfaz AnswerIA."},
    )
    assert ans_resp.status_code == 201
    ans_id = ans_resp.get_json()["id"]

    client.post(f"/posts/{ans_id}/vote", data={"value": "1"})

    # 3. Autor acepta respuesta (Question -> ANSWERED + notificación al colaborador)
    client.post("/auth/logout")
    client.post("/auth/login", data={"email": "autor@unrc.edu.ar", "password": "secret123"})
    accept_resp = client.post(f"/answers/{ans_id}/accept", follow_redirects=True)
    assert accept_resp.status_code == 200

    # 4. AdminUser modera cerrando la pregunta (CloseQuestionCommand + ModerationLog)
    client.post("/auth/logout")
    _register(client, "admin@unrc.edu.ar", "admin456", "admin")
    mod_resp = client.post(
        f"/questions/{q_id}/moderate-close",
        data={"reason": "Resuelta y archivada"},
        follow_redirects=True,
    )
    assert mod_resp.status_code == 200

    with app.app_context():
        question = db.session.get(Question, q_id)
        assert question is not None
        assert question.status == QuestionStatus.CLOSED
        assert len(question.answers) == 2

        notifications = db.session.scalars(db.select(Notification)).all()
        assert len(notifications) >= 2

        logs = db.session.scalars(db.select(ModerationLog)).all()
        assert len(logs) == 1
        assert logs[0].reason == "Resuelta y archivada"
