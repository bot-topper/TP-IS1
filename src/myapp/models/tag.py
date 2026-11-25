from myapp.extensions import db

class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False, unique = True)

    def __init__(self, name: str):
        if name is None or name.strip() == "":
            raise ValueError("El nombre de una Tag no puede ser nulo ni vacio.")
        super().__init__()

        self.name = name.strip().lower()