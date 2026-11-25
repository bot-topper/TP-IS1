from datetime import UTC, datetime

from sqlalchemy import ForeignKey, UniqueConstraint

from myapp.extensions import db


class Vote(db.Model):
    __tablename__ = "vote"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_vote_user_post"),
    )

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable = False)
    createdAt = db.Column(
        db.DateTime(timezone=True),
        nullable = False,
        default=lambda: datetime.now(UTC),
    )

    # Clave foranea para User
    user_id = db.Column(db.Integer, ForeignKey("user.id"), nullable=False)

    # Clave foranea para Post
    post_id = db.Column(db.Integer, ForeignKey("post.id"), nullable=False)

    user = db.relationship("User", lazy = True)

    def __init__(self, value: int, user, post):
        if user == None : 
            raise ValueError("El voto debe provenir de un User")

        if post == None :
            raise ValueError("El voto debe ir a un Post")

        if value not in (1, -1):
            raise ValueError("El valor del voto solo debe ser +1 o -1")

        super().__init__()

        self.value = value
        self.user = user
        post.votes.append(self)
