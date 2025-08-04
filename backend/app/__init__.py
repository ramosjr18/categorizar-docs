from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from .config import Config
import os
from datetime import timedelta

app = Flask(__name__)
app.config.from_object(Config)

app.config['SECRET_KEY'] = 'tu_secreto_super_seguro_aqui'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

CORS(app, supports_credentials=True)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)  # Definir db aquí primero

# Importar modelos y rutas después de crear db para evitar ciclos
from . import models
from .auth_routes import auth_bp
app.register_blueprint(auth_bp)
from . import routes

with app.app_context():
    db.create_all()
