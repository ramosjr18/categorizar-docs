import os
from datetime import timedelta
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_session import Session
from .config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, supports_credentials=True, origins=["http://localhost:8000"])

Session(app)

# Definir carpeta uploads con ruta relativa segura
basedir = os.path.abspath(os.path.dirname(__file__))
upload_folder = os.path.join(basedir, '..', 'uploads')
app.config['UPLOAD_FOLDER'] = upload_folder
app.config.setdefault("MAX_CONTENT_LENGTH", 25 * 1024 * 1024)
os.makedirs(upload_folder, exist_ok=True)

db = SQLAlchemy(app)

# Importar modelos y rutas después de crear db para evitar ciclos
from . import models
from .auth_routes import auth_bp
app.register_blueprint(auth_bp)
from . import routes

with app.app_context():
    db.create_all()

logger.info("Aplicación Flask inicializada correctamente")
