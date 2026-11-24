from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from myapp.extensions import db

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable = False)
    createAt = db.Column(db.DateTime, nullable = False, default=lambda: datetime.now(timezone.utc))

    id_User = db.Column(db.Integer, ForeignKey("user.id"), nullable = False)