from app import app
from app.utils.limpieza_programada import limpiar_archivos_no_registrados
from apscheduler.schedulers.background import BackgroundScheduler

def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=limpiar_archivos_no_registrados, trigger="interval", days=7)
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    with app.app_context():
        limpiar_archivos_no_registrados()
        scheduler = iniciar_scheduler()
    app.run(debug=True)
