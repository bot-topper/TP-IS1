from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from myapp.extensions import db

class Vote(db.Model):
    __tablename__ = "vote"

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable = False)
    createdAt = db.Column(db.DateTime, nullable = False, default=lambda: datetime.now(timezone.utc))
    #clave foranea para User
    user_id = db.Column(db.Integer, ForeignKey("user.id"), nullable = False)

    #clave foranea para Post
    post_id = db.Column(db.Integer, ForeignKey("post.id"), nullable = False)

    #relationship relaciona dos clases entre si a nivel objetos
    user = db.relationship("User", lazy = True)

    def __init__(self, value: int, user, post):
        if user == None : 
            raise ValueError("El voto debe provenir de un User")

        if post == None :
            raise ValueError("El voto debe ir a un Post")

        if value != 1 and value != -1 :
            raise ValueError("El valor del voto solo debe ser +1 o -1")
        
        super().__init__()

        self.value = value
        self.post = post
        self.user = user

