from . import db
from werkzeug.security import generate_password_hash, check_password_hash

class Documento(db.Model):
    """
    Modelo para representar un documento cargado por el usuario.
    Soporta control de versiones, categorización y almacenamiento de hash para evitar duplicados.
    """
    __tablename__ = 'documentos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, comment="Nombre del archivo original")
    tipo = db.Column(db.String(20), nullable=False, comment="Extensión del archivo")
    contenido = db.Column(db.Text, nullable=True, comment="Texto extraído del documento")
    categoria = db.Column(db.String(50), nullable=False, comment="Categoría asignada")
    fecha_subida = db.Column(db.String(20), nullable=False, comment="Fecha de subida (ISO)")
    
    version = db.Column(db.Integer, nullable=False, default=1, comment="Número de versión del archivo")
    grupo = db.Column(db.String(120), nullable=False, comment="Grupo base para agrupar versiones")
    hash_contenido = db.Column(db.String(64), nullable=True, comment="Hash SHA-256 del contenido")

    def __repr__(self):
        return f"<Documento {self.nombre} v{self.version} ({self.categoria})>"


class Usuario(db.Model):
    """
    Modelo de usuario para autenticación básica por email y contraseña.
    """
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, comment="Correo electrónico único")
    password_hash = db.Column(db.String(128), nullable=False, comment="Contraseña en hash")

    def set_password(self, password: str):
        """Cifra y guarda la contraseña del usuario."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verifica si la contraseña ingresada es válida."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.email}>"
