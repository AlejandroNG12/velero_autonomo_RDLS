# config.py
import os

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "storage", "telemetria.db")

# Configuración de Puertos
PORT_WIND_IN = "/dev/ttyUSB0"   # Veleta (Actisense)
PORT_WIND_OUT = "/dev/serial0"  # Hacia Pixhawk (TELEM2)
BAUD_WIND_OUT = 4800            #

PORT_MAVLINK = "/dev/ttyACM0"   # Pixhawk USB
BAUD_MAVLINK = 57600            #

# Frecuencias
SAVE_INTERVAL = 1.0  # Guardar en DB cada 1 segundo
