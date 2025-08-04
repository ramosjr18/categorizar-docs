from datetime import timedelta
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tu_secreto_por_defecto')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///documentos.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False



