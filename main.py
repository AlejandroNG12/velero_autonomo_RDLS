import threading
import time
import logging
import os
import sys

# Configuración de logs para que se vean en consola y se guarden bien
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(threadName)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Importamos la configuración y los gestores
try:
    from config import WIND_SAVE_INTERVAL, DB_PATH
    from core.database import init_db
    from core.wind_manager import wind_loop
    from core.mavlink_manager import mavlink_loop
except ImportError as e:
    logging.error(f"Error importando módulos: {e}")
    sys.exit(1)

def main():
    logging.info("--- Iniciando SailBridge OS ---")

    # 1. Asegurar que existe la carpeta storage para la base de datos
    storage_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
        logging.info(f"Carpeta creada: {storage_dir}")

    # 2. Inicializar Base de Datos (Crea las tablas si no existen)
    init_db()
    logging.info("Base de datos lista.")

    # 3. Lanzar Hilo de Viento (Lectura de NMEA2000 y envío de NMEA0183)
    # Este hilo usa la lógica que ya te ha funcionado en el laboratorio
    wind_thread = threading.Thread(target=wind_loop, name="WindThread", daemon=True)
    
    # 4. Lanzar Hilo de MAVLink (Lectura de telemetría de la Pixhawk para el Dashboard)
    mavlink_thread = threading.Thread(target=mavlink_loop, name="MavlinkThread", daemon=True)

    # Iniciar hilos
    wind_thread.start()
    mavlink_thread.start()

    logging.info("Hilos de ejecución iniciados correctamente.")

    # Mantener el programa principal vivo para que no se cierren los hilos
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Deteniendo sistema por el usuario...")

if __name__ == "__main__":
    main()
