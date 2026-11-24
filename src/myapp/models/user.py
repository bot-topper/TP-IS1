import re

from sqlalchemy import event
from werkzeug.security import generate_password_hash

from myapp.extensions import db

EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


# Interfaz
class IAuthor:
    def getName(self) -> str: ...


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)

<<<<<<< HEAD
    def __repr__(self):
        return f"<User {self.email}>"
=======
    id = db.Column(db.Integer, primary_key=True)
    passwordHash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    reputation = db.Column(db.Integer, nullable=False, default=0)

    @staticmethod
    def validate_user_fields(mapper, connection, target) -> None:
        if not target._email or not EMAIL_RE.match(target._email.strip()):
            raise ValueError("El email no es válido")
        target._email = target._email.strip().lower()

        if not target._passwordHash:
            raise ValueError("La contraseña no puede estar vacía")
        if not target._passwordHash.startswith(("scrypt:", "pbkdf2:")):
            target._passwordHash = generate_password_hash(target._passwordHash)

    def getName(self) -> str:
        return self._email

    def updateReputation(self, points: int) -> None:
        self._reputation += points


event.listen(User, "before_insert", User.validate_user_fields, propagate=True)
event.listen(User, "before_update", User.validate_user_fields, propagate=True)
>>>>>>> 026197e (Fix de la Issue (#19))
