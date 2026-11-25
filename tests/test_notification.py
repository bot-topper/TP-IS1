"""Pruebas unitarias para Notification.

Colocar en: tests/test_notification.py
"""

import pytest
from myapp.models.notification import Notification

from myapp.extensions import db
from myapp.models.user import AdminUser, NormalUser


def test_notification_creacion_persistencia_y_mark_as_read(app) -> None:
    student = NormalUser(email="ana@unrc.edu.ar", passwordHash="secret123")
    admin = AdminUser(email="admin@unrc.edu.ar", passwordHash="secret456")
    db.session.add_all([student, admin])
    db.session.flush()

    notif = Notification(message="  Nueva respuesta en tu pregunta  ", user=student)
    notif_admin = Notification(message="Nuevo reporte", user=admin)
    db.session.add_all([notif, notif_admin])
    db.session.commit()

    assert notif.id is not None
    assert notif.message == "Nueva respuesta en tu pregunta"
    assert notif.isRead is False
    assert notif.createdAt is not None
    assert notif.user is student
    assert notif.user_type == "NormalUser"
    assert notif.user_id == student.id

    notif.markAsRead()
    db.session.commit()

    reloaded = db.session.get(Notification, notif.id)
    assert reloaded is not None
    assert reloaded.isRead is True


def test_notification_valida_mensaje_y_usuario() -> None:
    user = NormalUser(email="ana@unrc.edu.ar", passwordHash="secret123")

    with pytest.raises(ValueError, match="User"):
        Notification(message="Hola", user=None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="User"):
        Notification(message="Hola", user=object())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="vacío"):
        Notification(message="   ", user=user)
