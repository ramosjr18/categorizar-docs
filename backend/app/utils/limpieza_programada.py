import os
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import Config
from app.models import db, Documento

# --- Configuración de Flask y SQLAlchemy ---
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# --- Ruta absoluta de la carpeta de uploads ---
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../uploads'))

def limpiar_archivos_no_registrados():
    """
    Elimina archivos del directorio UPLOAD_FOLDER que no están registrados en la base de datos.
    """
    try:
        archivos_en_carpeta = set(os.listdir(UPLOAD_FOLDER))
        archivos_en_db = set(doc.nombre for doc in Documento.query.all())
        archivos_a_eliminar = archivos_en_carpeta - archivos_en_db

        for archivo in archivos_a_eliminar:
            ruta = os.path.join(UPLOAD_FOLDER, archivo)
            try:
                os.remove(ruta)
                print(f"[✓] Archivo eliminado: {archivo}")
            except Exception as e:
                print(f"[✗] Error eliminando {archivo}: {e}")
    except Exception as general_error:
        print(f"[!] Error general en limpieza: {general_error}")

def iniciar_scheduler() -> BackgroundScheduler:
    """
    Inicia el programador que ejecuta la limpieza cada 7 días.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=limpiar_archivos_no_registrados, trigger="interval", days=7)
    scheduler.start()
    return scheduler


if __name__ == '__main__':
    with app.app_context():
        print("▶ Ejecutando limpieza inicial...")
        limpiar_archivos_no_registrados()

        print("▶ Iniciando scheduler (intervalo: cada 7 días)...")
        scheduler = iniciar_scheduler()

        try:
            print("✅ Scheduler en ejecución. Pulsa Ctrl+C para detener.")
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            print("🛑 Scheduler detenido.")
