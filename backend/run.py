import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app import create_app
from app.utils.limpieza_programada import limpiar_archivos_no_registrados

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def tarea_segura():
    try:
        limpiar_archivos_no_registrados()
    except Exception as e:
        logger.error(f"Error en tarea programada: {e}")

def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=tarea_segura, trigger="interval", days=7)
    scheduler.start()
    logger.info("Scheduler iniciado para limpieza programada cada 7 días.")
    return scheduler

app = create_app()

if __name__ == "__main__":
    # Evita doble arranque con el reloader
    is_main = os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
    if is_main:
        with app.app_context():
            tarea_segura()
            iniciar_scheduler()

    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    app.run(debug=debug_mode)
