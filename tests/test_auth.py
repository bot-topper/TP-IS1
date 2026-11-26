"""Pruebas funcionales de registro, login y logout"""

from myapp.extensions import db
from myapp.models.user import AdminUser, NormalUser


def test_register_normal_and_admin_user_hashes_password_and_sets_session(app, client) -> None:
    response = client.post(
        "/auth/register",
        data={
            "email": "Estudiante@unrc.edu.ar",
            "password": "MilanesaNapo",
            "role": "normal",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"estudiante@unrc.edu.ar (NormalUser)" in response.data

    with app.app_context():
        user = db.session.scalars(
            db.select(NormalUser).where(NormalUser.email == "estudiante@unrc.edu.ar")
        ).first()
        assert user is not None
        assert user.passwordHash != "MilanesaNapo"
        assert user.checkPassword("MilanesaNapo") is True
        assert user.checkPassword("otra") is False

    admin_response = client.post(
        "/auth/register",
        data={
            "email": "admin@unrc.edu.ar",
            "password": "AdminPass456",
            "role": "admin",
        },
        follow_redirects=True,
    )
    assert admin_response.status_code == 200
    assert b"admin@unrc.edu.ar (AdminUser)" in admin_response.data

    with app.app_context():
        admin = db.session.scalars(
            db.select(AdminUser).where(AdminUser.email == "admin@unrc.edu.ar")
        ).first()
        assert admin is not None
        assert admin.checkPassword("AdminPass456") is True


def test_register_rejects_duplicate_email_and_invalid_inputs(app, client) -> None:
    with app.app_context():
        db.session.add(NormalUser(email="repetido@unrc.edu.ar", passwordHash="secret123"))
        db.session.commit()

    # No permite duplicar el mismo email ni siquiera con otro rol
    dup_resp = client.post(
        "/auth/register",
        data={
            "email": "REPETIDO@unrc.edu.ar",
            "password": "otraPassword",
            "role": "admin",
        },
    )
    assert dup_resp.status_code == 400
    assert b"registrado" in dup_resp.data

    bad_email_resp = client.post(
        "/auth/register",
        data={"email": "no-es-email", "password": "secret123", "role": "normal"},
    )
    assert bad_email_resp.status_code == 400

    empty_pass_resp = client.post(
        "/auth/register",
        data={"email": "nuevo@unrc.edu.ar", "password": "", "role": "normal"},
    )
    assert empty_pass_resp.status_code == 400


def test_login_and_logout_for_normal_and_admin_users(app, client) -> None:
    with app.app_context():
        db.session.add_all(
            [
                NormalUser(email="juan@unrc.edu.ar", passwordHash="secret123"),
                AdminUser(email="mod@unrc.edu.ar", passwordHash="modpass456"),
            ]
        )
        db.session.commit()

    bad_login = client.post(
        "/auth/login",
        data={"email": "juan@unrc.edu.ar", "password": "wrong"},
    )
    assert bad_login.status_code == 401
    assert b"inv" in bad_login.data

    ok_normal = client.post(
        "/auth/login",
        data={"email": "juan@unrc.edu.ar", "password": "secret123"},
        follow_redirects=True,
    )
    assert ok_normal.status_code == 200
    assert b"juan@unrc.edu.ar (NormalUser)" in ok_normal.data

    logout_resp = client.post("/auth/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"Iniciar sesi" in logout_resp.data
    assert b"juan@unrc.edu.ar (NormalUser)" not in logout_resp.data

    ok_admin = client.post(
        "/auth/login",
        data={"email": "mod@unrc.edu.ar", "password": "modpass456"},
        follow_redirects=True,
    )
    assert ok_admin.status_code == 200
    assert b"mod@unrc.edu.ar (AdminUser)" in ok_admin.data
