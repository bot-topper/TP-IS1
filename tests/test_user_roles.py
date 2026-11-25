"""Pruebas unitarias para NormalUser y AdminUser"""

import pytest

from myapp.extensions import db
from myapp.models.user import AdminUser, NormalUser, User


class _FakeModerationCommand:
    def __init__(self) -> None:
        self.executed = False

    def execute(self) -> None:
        self.executed = True


def test_normal_and_admin_inherit_user_and_fulfill_iauthor(app) -> None:
    normal = NormalUser(email="student@unrc.edu.ar", passwordHash="secret123")
    admin = AdminUser(email="admin@unrc.edu.ar", passwordHash="secret456")

    db.session.add_all([normal, admin])
    db.session.commit()

    assert isinstance(normal, User)
    assert isinstance(admin, User)
    assert callable(getattr(normal, "getName", None))
    assert callable(getattr(admin, "getName", None))
    assert normal.getName() == "student@unrc.edu.ar"
    assert admin.getName() == "admin@unrc.edu.ar"


def test_normal_user_permissions_by_reputation(app) -> None:
    user = NormalUser(email="rep@unrc.edu.ar", passwordHash="secret123")

    assert user.canDownvote() is False
    assert user.canCreateTags() is False

    db.session.add(user)
    db.session.commit()

    assert user.reputation == 0
    assert user.canDownvote() is False
    assert user.canCreateTags() is False

    user.updateReputation(50)
    assert user.canDownvote() is True
    assert user.canCreateTags() is False

    user.updateReputation(50)
    assert user.canDownvote() is True
    assert user.canCreateTags() is True


def test_admin_user_executes_moderation_command() -> None:
    admin = AdminUser(email="mod@unrc.edu.ar", passwordHash="secret123")
    cmd = _FakeModerationCommand()

    admin.executeModeration(cmd)
    assert cmd.executed is True

    with pytest.raises(ValueError):
        admin.executeModeration(None)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        admin.executeModeration(object())  # type: ignore[arg-type]
