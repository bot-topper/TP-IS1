from myapp.extensions import db

class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False, unique=True)
    slug = db.Column(db.String(100), nullable = False, unique=True)

    def __init__(self, name: str, slug: str):
        if name is None or name.strip() == "":
            raise ValueError("El nombre de una Categoria no puede ser nulo ni vacio.")

        if slug is None or slug.strip() == "":
            raise ValueError("El slug no puede ser nulo ni vacio.")
        
        self.name = name.strip()
        self.slug = slug.strip().lower()