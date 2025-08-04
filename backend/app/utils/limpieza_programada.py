import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import Config
from app.models import db, Documento

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../uploads'))

def limpiar_archivos_no_registrados():
    archivos_en_carpeta = set(os.listdir(UPLOAD_FOLDER))
    archivos_en_db = set(doc.nombre for doc in Documento.query.all())
    archivos_a_eliminar = archivos_en_carpeta - archivos_en_db

    for archivo in archivos_a_eliminar:
        ruta = os.path.join(UPLOAD_FOLDER, archivo)
        try:
            os.remove(ruta)
            print(f"Archivo eliminado: {archivo}")
        except Exception as e:
            print(f"No se pudo eliminar {archivo}: {e}")

def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: limpiar_archivos_no_registrados(), trigger="interval", days=7)
    scheduler.start()
    return scheduler


if __name__ == '__main__':
    with app.app_context():
        
        limpiar_archivos_no_registrados()

        scheduler = iniciar_scheduler()
        print("Scheduler iniciado. Ejecutando limpieza cada 7 días.")
        try:
            while True:
                pass  
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()

