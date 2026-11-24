from myapp.extensions import db
from datetime import datetime, timezone
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Comment(db.Model):
    __tablename__ = "comment"

    id = db.Column(db.Integer, primary_key = True)
    body = db.Column(db.Text, nullable = False)
    createdAt = db.Column(db.DateTime(timezone = True), nullable = False, 
                          default=lambda: datetime.now(timezone.utc))

    #claves foraneas
    #referencia a Post (y a sus hijos que tienen este atributo)
    post_id = db.Column(db.Integer, ForeignKey("post.id"), nullable = False)

    #referencia a User
    user_id = db.Column(db.Integer, ForeignKey("user.id"), nullable = False)

    #relacion a nivel objetos.
    #para poder acceder al objeto autor mediante comentario.user sin tener que tocar user.py
    user = relationship("User", lazy = True)

    def __init__(self, body: str, user, post):
        if user is None : 
            raise ValueError("El voto debe provenir de un User")
        
        if post is None :
            raise ValueError("El voto debe ir a un Post")

        if(body is None or body.strip() == "" or len(body.strip()) > 300):
            raise ValueError("El contenido del Post no puede ser nulo, vacio ni superar el máximo de 300 caracteres.")
    
        super().__init__()

        self.body = body
        self.user = user
        self.post = post

