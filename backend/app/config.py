from datetime import timedelta
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', '4f3c2a5d6b7e9f1234567890abcdef1234567890abcdef1234567890abcdef12')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///documentos.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de sesión para cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  
    SESSION_COOKIE_SECURE = False  
    SESSION_COOKIE_HTTPONLY = True
    SESSION_TYPE = 'filesystem'




