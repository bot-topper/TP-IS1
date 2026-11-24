from datetime import datetime, timezone
from sqlalchemy.orm import Mapped
from myapp.extensions import db
from sqlalchemy.orm import Mapped, relationship

from myapp.models.vote import Vote

class Post(db.Model):

    __tablename__ = "post"
    
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable = False)

    publication_Date = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        default=lambda: datetime.now(timezone.utc))

    # Columna para saber que tipo de Post es: Question y Answer
    type = db.Column(db.String(50), nullable=False, default="post")

    #atributo para saber que tipo de autor lo hizo
    author_type = db.Column(db.String(50), nullable = False)
    author_id = db.Column(db.Integer, nullable = True)

    isHidden = db.Column(db.Boolean, nullable = False, default = False)

    #Relación de composición (1 a 0..*) entre Post y Vote:
    # - backref="post": crea automáticamente el atributo .post en la clase Vote,
    #   permitiendo asignar `self.post = post` al crear un voto y sincronizar `post_id`.
    # - cascade="all, delete-orphan": implementa la composición del UML; si se elimina
    #   el Post o se quita un voto de `self.votes`, se elimina automáticamente de la BD.
    # - lazy=True: carga los votos desde la BD recién cuando se accede a `post.votes`.
    votes : Mapped[list["Vote"]] = relationship("Vote", backref = "post", cascade = "all, delete-orphan", lazy = True)

    def __init__(self, body: str, author_type: str, author_id: int | None = None, **kwargs):
        if (type(self) == Post):
            raise TypeError("Post es una clase abstracta y no puede instanciarse directamente.")
        
        if(author_type == None or author_type.strip() == ""):
            raise ValueError("El Post debe tener un autor obligatorio.")

        if(body == None or body.strip() == ""):
            raise ValueError("El contenido del Post no puede ser nulo ni vacio.")

        super().__init__()

        self.body = body
        self.author_id = author_id
        self.author_type = author_type

    def calculateScore(self) -> int:
        raise NotImplementedError("Las subclases deben implementar calculateScore().")

    #funcion para votar y se decide que hacer si el usuario ya votó
    def vote(self, user, value: int):
        if user is None:
            raise ValueError("El usuario debe existir.")

        if value !=1 and value !=-1:
            raise ValueError("Valor no permitido.")

        #buscar entre la lista de votos
        existing_vote = None
        for v in self.votes:
            #compara las instancias de python || objetos ya persistentes en la bdd.
            if v.user == user or (v.user_id is not None and v.user_id == user.id):
                existing_vote = v
                break

        #si no exite un voto
        if existing_vote is None:
            v = Vote(value, user, self)
        #si ya hay un voto, y tiene el mismo valor entonces está quitando el voto
        elif existing_vote.value == value:
            self.votes.remove(existing_vote)
        #si ya hay un voto pero tiene el valor opuesto, hay que modificarlo
        else:
            existing_vote.value = value
