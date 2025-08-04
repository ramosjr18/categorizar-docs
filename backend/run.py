import os
import logging
from app import app
from app.utils.limpieza_programada import limpiar_archivos_no_registrados
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def tarea_segura():
    """Ejecuta la limpieza periódica con manejo de excepciones."""
    try:
        limpiar_archivos_no_registrados()
    except Exception as e:
        logger.error(f"Error en tarea programada: {e}")

def iniciar_scheduler():
    """
    Inicializa y arranca un scheduler en segundo plano
    que ejecuta la función limpiar_archivos_no_registrados cada 7 días.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=tarea_segura, trigger="interval", days=7)
    scheduler.start()
    logger.info("Scheduler iniciado para limpieza programada cada 7 días.")
    return scheduler

if __name__ == "__main__":
    with app.app_context():
        tarea_segura()
        scheduler = iniciar_scheduler()
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    app.run(debug=debug_mode)
