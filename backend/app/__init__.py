# app/__init__.py
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_session import Session
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Expone db y app a nivel de módulo para que routes.py pueda: from . import app, db
db = SQLAlchemy()
app = None  # se asignará dentro de create_app()

def create_app():
    global app
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS
    CORS(app, supports_credentials=True, origins=["http://localhost:8000"])

    # Sessions
    Session(app)

    # uploads/
    basedir = os.path.abspath(os.path.dirname(__file__))
    upload_folder = os.path.join(basedir, '..', 'uploads')
    app.config['UPLOAD_FOLDER'] = upload_folder
    app.config.setdefault("MAX_CONTENT_LENGTH", 25 * 1024 * 1024)
    os.makedirs(upload_folder, exist_ok=True)

    # DB
    db.init_app(app)

    # Importa modelos / blueprints / rutas DESPUÉS de crear app
    from . import models  # noqa: F401
    from .auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    # Importa routes: aquí se ejecutan los @app.route y el handler 404
    from . import routes  # noqa: F401

    with app.app_context():
        db.create_all()

    logger.info("Aplicación Flask inicializada correctamente")
    return app
