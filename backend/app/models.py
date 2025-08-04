from . import db
from werkzeug.security import generate_password_hash, check_password_hash

class Documento(db.Model):
    __tablename__ = 'documentos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False) 
    tipo = db.Column(db.String(20), nullable=False)  
    contenido = db.Column(db.Text, nullable=True)        
    categoria = db.Column(db.String(50), nullable=False)
    fecha_subida = db.Column(db.String(20), nullable=False)

    version = db.Column(db.Integer, nullable=False, default=1)
    grupo = db.Column(db.String(120), nullable=False)
    hash_contenido = db.Column(db.String(64), nullable=True) 

    def __repr__(self):
        return f"<Documento {self.nombre} v{self.version} ({self.categoria})>"


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.email}>"
