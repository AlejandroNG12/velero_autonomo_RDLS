import os

# --- RUTAS DE SISTEMA ---
# Detecta automáticamente la carpeta del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "storage", "telemetria.db")

# --- CONFIGURACIÓN VIENTO (NMEA2000 -> NMEA0183) ---
# Puerto del conversor Actisense NGT-1 (USB)
PORT_WIND_IN = "/dev/ttyUSB0"  

# Puerto UART de la Raspberry (GPIO) hacia TELEM2 de la Pixhawk
# Usamos /dev/serial0 que es el enlace simbólico recomendado en Raspberry Pi
PORT_WIND_OUT = "/dev/serial0" 

# Baudios para NMEA0183 
BAUD_WIND_OUT = 4800           

# --- CONFIGURACIÓN MAVLINK (PIXHAWK) ---
# Conexión por el puerto USB micro/C de la Pixhawk
PORT_MAVLINK = "/dev/ttyACM0"  
BAUD_MAVLINK = 57600           

# --- INTERVALOS ---
# Frecuencia de guardado en la base de datos (en segundos)
WIND_SAVE_INTERVAL = 1.0
