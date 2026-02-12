# main.py
import threading
import time
import logging
from core.database import init_db
from config import SAVE_INTERVAL

# Configuramos el logging para ver qué pasa en cada hilo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s"
)

def start_system():
    logging.info("--- Iniciando SailBridge OS ---")
    
    # 1. Preparar la base de datos
    init_db()

    # 2. Definir los hilos (Placeholders para tus scripts de core/)
    # En el futuro, aquí importarás wind_manager y mavlink_manager
    def mock_thread_viento():
        logging.info("Hilo de VIENTO activo (Esperando hardware...)")
        while True: time.sleep(10)

    def mock_thread_mavlink():
        logging.info("Hilo MAVLINK activo (Esperando USB...)")
        while True: time.sleep(10)

    # 3. Lanzar hilos como Daemons
    t1 = threading.Thread(target=mock_thread_viento, name="WindThread", daemon=True)
    t2 = threading.Thread(target=mock_thread_mavlink, name="MavlinkThread", daemon=True)

    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1) # El main se queda vigilando
    except KeyboardInterrupt:
        logging.info("Apagando sistema de forma segura...")

if __name__ == "__main__":
    start_system()
