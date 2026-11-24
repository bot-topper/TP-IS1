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

    def __repr__(self):
        return f"<User {self.email}>"
