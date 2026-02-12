#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging
import serial
from storage import db  # Mantenemos tu conexión a base de datos

# ----------------------------------------------------------
# CONFIGURACIÓN ORIGINAL
# ----------------------------------------------------------
ACTISENSE_PORT = "/dev/ttyUSB0"    
PIXHAWK_DEV    = "/dev/serial0"       
PIXHAWK_BAUD   = 4800                
WIND_SAVE_INTERVAL = 1.0  # Guardar en DB cada 1s

# Variables de estado globales
last_db_save = 0.0
last_wind_dir = None
last_wind_speed = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WIND-DB] %(message)s"
)

# ----------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------
def nmea_checksum(sentence):
    c = 0
    for ch in sentence:
        c ^= ord(ch)
    return "{:02X}".format(c)

def build_mwv_sentence(wind_dir_deg, wind_speed_knots):
    body = f"WIMWV,{wind_dir_deg:.1f},R,{wind_speed_knots:.1f},N,A"
    checksum = nmea_checksum(body)
    return f"${body}*{checksum}"

# ----------------------------------------------------------
# PROCESO PRINCIPAL
# ----------------------------------------------------------
def main():
    # Declaramos globales para poder modificarlas
    global last_db_save, last_wind_dir, last_wind_speed

    logging.info("Iniciando módulo de viento con guardado en DB y Dashboard.")
    
    # 1. Conexión a BD
    try:
        conn = db.get_db_connection()
        db.init_db(conn)
    except Exception as e:
        logging.error(f"Error con la base de datos: {e}")
        return
    
    # 2. Abrir UART hacia Pixhawk
    try:
        ser = serial.Serial(PIXHAWK_DEV, PIXHAWK_BAUD, timeout=1)
    except Exception as e:
        logging.error(f"No se pudo abrir {PIXHAWK_DEV}: {e}")
        return

    # 3. Lanzar Actisense y Analyzer
    try:
        p1 = subprocess.Popen(["actisense-serial", "-p", ACTISENSE_PORT], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["analyzer", "-json"], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f"Error iniciando actisense/analyzer: {e}")
        return

    print("\n" + "="*60)
    print(" MONITORIZACIÓN ACTIVA: VIENTO -> PIXHAWK + SQLITE")
    print("="*60 + "\n")

    try:
        for raw in p2.stdout:
            line = raw.decode("utf-8", errors="ignore").strip()
            now = time.time()
            if not line: continue

            try:
                obj = json.loads(line)
            except: continue

            # Filtrar PGN 130306
            if obj.get("pgn") == 130306:
                fields = obj.get("fields", {})

                try:
                    wind_speed_ms = float(fields.get("Wind Speed", 0.0))
                    wind_angle_rad = float(fields.get("Wind Angle", 0.0))

                    wind_speed_knots = wind_speed_ms * 1.94384
                    wind_dir_deg = math.degrees(wind_angle_rad) % 360

                    # A. Guardar en BD según intervalo
                    if now - last_db_save >= WIND_SAVE_INTERVAL:
                        db.insert_wind_NMEA(conn, wind_speed_ms, wind_dir_deg)
                        last_db_save = now
                    
                    # B. Enviar MWV a Pixhawk
                    mwv = build_mwv_sentence(wind_dir_deg, wind_speed_knots)
                    ser.write((mwv + "\r\n").encode("ascii"))

                    # C. VISUALIZACIÓN EN UNA LÍNEA (Tu petición)
                    print(f"\r⛵ DIR: {wind_dir_deg:5.1f}° | VEL: {wind_speed_knots:4.1f} kn | DB: OK | SENTENCIA: {mwv}", end="")

                except Exception as e:
                    continue

    except KeyboardInterrupt:
        print("\n\nFinalizando por usuario...")
    finally:
        conn.close()
        ser.close()
        p1.terminate()
        p2.terminate()

if __name__ == "__main__":
    main()
