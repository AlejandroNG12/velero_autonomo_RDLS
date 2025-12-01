# config/settings.py

# Cadena de conexión principal a la Pixhawk (ArduRover en tu Pixhawk 6X)
# Formato serial: "serial:/dev/ttyACM0:115200"
# Formato UART (TELEM2, etc.): "serial:/dev/ttyAMA0:57600"
CONNECTION_STRING = "serial:/dev/ttyACM0:115200"

# ID del sistema (normalmente 1)
SYSID = 1

# Parámetros para reenvío por UDP a tu PC con QGroundControl
UDP_TARGET_IP = "192.168.1.100"   # <- pon aquí la IP de tu PC
UDP_TARGET_PORT = 14550           # puerto típico de QGC

# Timeout de espera de heartbeat (segundos)
HEARTBEAT_TIMEOUT = 30
