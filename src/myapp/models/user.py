import re
from typing import Protocol

from sqlalchemy import event
from werkzeug.security import generate_password_hash

from myapp.extensions import db

EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


# Interfaz
class IAuthor():
    def getName(self) -> str: ...


class User(db.Model):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    passwordHash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    reputation = db.Column(db.Integer, nullable=False, default=0)

    @staticmethod
    def validate_user_fields(mapper, connection, target) -> None:
        if not target.email or not EMAIL_RE.match(target.email.strip()):
            raise ValueError("El email no es válido")
        target.email = target.email.strip().lower()

        if not target.passwordHash:
            raise ValueError("La contraseña no puede estar vacía")
        if not target.passwordHash.startswith(("scrypt:", "pbkdf2:")):
            target.passwordHash = generate_password_hash(target.passwordHash)

    def getName(self) -> str:
        return self.email

    def updateReputation(self, points: int) -> None:
        self.reputation += points


event.listen(User, "before_insert", User.validate_user_fields, propagate=True)
event.listen(User, "before_update", User.validate_user_fields, propagate=True)

class _ModerationCommandLike(Protocol):
    def execute(self) -> None: ...


class NormalUser(User):
    __tablename__ = "normaluser"

    def canDownvote(self) -> bool:
        return (self.reputation or 0) >= 50

    def canCreateTags(self) -> bool:
        return (self.reputation or 0) >= 100


class AdminUser(User):
    __tablename__ = "adminuser"

    def executeModeration(self, cmd: _ModerationCommandLike) -> None:
        if cmd is None or not callable(getattr(cmd, "execute", None)):
            raise ValueError("Se requiere un ModerationCommand válido.")
        cmd.execute()