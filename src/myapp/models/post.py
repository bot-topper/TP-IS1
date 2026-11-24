from datetime import datetime, timezone
from myapp.extensions import db

class Post(db.Model):

    __tablename__ = "post"
    
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable = False)

    publication_Date = db.Column(
        db.DateTime(timezone = True),
        nullable = False,
        default=lambda: datetime.now(timezone.utc))
    #"datetime.now(timezone.utc) genera la hora y la fecha actual en formato universal utc.
    # El lambda hace que python calcule la hora cada vez que se cree un Post"
    isHidden = db.Column(db.Boolean, nullable = False, default = False)

    # Columna para saber que tipo de Post es: Question y Answer
    type = db.Column(db.String(50), nullable=False, default="post"))

    #atributo para saber que tipo de autor lo hizo
    author_type = db.Column(db.String(50), nullable = False)
    author_id = db.Column(db.Integer, nullable = True)

    def __init__(self, body: str, author_type: str, author_id: int | None = None, **kwargs):
        if (type(self) == Post):
            raise TypeError("Post es una clase abstracta y no puede instanciarse directamente.")
        
        if(author_type == None ):
            raise ValueError("El Post debe tener un autor obligatorio.")

        if(body == None or body.strip() == ""):
            raise ValueError("El contenido del Post no puede ser nulo ni vacio.")

        super().__init__()

        self.body = body
        self.isHidden = isHidden

    @property
    def calculateScore(self) -> int:
        raise NotImplementedError("Las subclases deben implementar calculateScore().")


