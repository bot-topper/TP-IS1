"""Pruebas unitarias para la clase abstracta User y las rutas de usuarios."""

import pytest
from werkzeug.security import check_password_hash

from myapp.extensions import db
from myapp.models.user import User


class _DummyUser(User):
    """Subclase concreta mínima para probar el comportamiento base de User."""

    __tablename__ = "dummy_user"


def test_user_is_abstract():
    assert User.__abstract__ is True
    assert not hasattr(User, "__table__")


def test_user_persists_normalizes_email_and_hashes_password(app):
    with app.app_context():
        user = _DummyUser(email="  ADA@Example.com ", passwordHash="secret123")
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.email == "ada@example.com"
        assert user.getName() == "ada@example.com"
        assert user.passwordHash != "secret123"
        assert check_password_hash(user.passwordHash, "secret123") is True


def test_invalid_email_raises_value_error(app):
    with app.app_context():
        user = _DummyUser(email="correo-invalido", passwordHash="secret123")
        db.session.add(user)
        with pytest.raises(ValueError, match="email"):
            db.session.commit()
        db.session.rollback()


def test_empty_password_raises_value_error(app):
    with app.app_context():
        user = _DummyUser(email="ada@example.com", passwordHash="")
        db.session.add(user)
        with pytest.raises(ValueError, match="contraseña"):
            db.session.commit()
        db.session.rollback()


def test_reputation_starts_at_zero_and_updates(app):
    with app.app_context():
        user = _DummyUser(email="rep@example.com", passwordHash="secret123")
        db.session.add(user)
        db.session.commit()

        assert user.reputation == 0

        user.updateReputation(10)
        assert user.reputation == 10

        user.updateReputation(-3)
        assert user.reputation == 7


def test_users_detail_returns_404_when_missing(client):
    response = client.get("/users/999")
    assert response.status_code == 404
