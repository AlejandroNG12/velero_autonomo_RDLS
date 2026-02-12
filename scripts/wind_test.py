#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging
import serial

# --- CONFIGURACIÓN ---
ACTISENSE_PORT = "/dev/ttyUSB0"    # Veleta -> Raspberry
PIXHAWK_DEV    = "/dev/serial0"   # Raspberry -> Pixhawk (TELEM2)
PIXHAWK_BAUD   = 4800             # Baudios NMEA

# Configuración de logs para que se vea limpio
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def nmea_checksum(sentence):
    """Calcula el checksum XOR para NMEA."""
    c = 0
    for ch in sentence:
        c ^= ord(ch)
    return "{:02X}".format(c)

def build_mwv_sentence(wind_dir_deg, wind_speed_knots):
    """Construye la frase $WIMWV."""
    body = f"WIMWV,{wind_dir_deg:.1f},R,{wind_speed_knots:.1f},N,A"
    checksum = nmea_checksum(body)
    return f"${body}*{checksum}"

def main():
    print("-" * 50)
    print("SISTEMA DE MONITOREO DE VIENTO (NMEA2000 -> PIXHAWK)")
    print(f"Leyendo de: {ACTISENSE_PORT}")
    print(f"Enviando a: {PIXHAWK_DEV}")
    print("-" * 50)

    try:
        ser = serial.Serial(PIXHAWK_DEV, PIXHAWK_BAUD, timeout=1)
    except Exception as e:
        logging.error(f"No se pudo abrir el puerto serie: {e}")
        return

    # Iniciar procesos de Actisense
    try:
        p1 = subprocess.Popen(["actisense-serial", "-p", ACTISENSE_PORT], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["analyzer", "-json"], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f"Error al iniciar actisense/analyzer: {e}")
        return

    try:
        for raw in p2.stdout:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line: continue

            try:
                obj = json.loads(line)
            except: continue

            # Filtrar PGN de viento 130306
            if obj.get("pgn") == 130306:
                fields = obj.get("fields", {})
                
                speed_ms = float(fields.get("Wind Speed", 0.0))
                angle_rad = float(fields.get("Wind Angle", 0.0))

                # Conversiones
                speed_kn = speed_ms * 1.94384
                angle_deg = math.degrees(angle_rad) % 360

                # Enviar a Pixhawk
                mwv = build_mwv_sentence(angle_deg, speed_kn)
                ser.write((mwv + "\r\n").encode("ascii"))

                # --- VISUALIZACIÓN POR PANTALLA ---
                # Usamos \r y end="" para que se actualice en la misma línea
                print(f"\r⛵ VIENTO: {angle_deg:5.1f}° | VELOCIDAD: {speed_kn:4.1f} kn | SENTENCIA: {mwv}", end="")

    except KeyboardInterrupt:
        print("\n\nDeteniendo prueba...")
    finally:
        p1.terminate()
        p2.terminate()
        ser.close()

if __name__ == "__main__":
    main()
