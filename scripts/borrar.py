#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging
import serial

# ----------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------

ACTISENSE_PORT = "/dev/ttyUSB0"    # Actisense NMEA2000 → NMEA0183 JSON
PIXHAWK_DEV = "/dev/serial0"       # GPIO14/15 → TELEM2
PIXHAWK_BAUD = 4800                # NMEA 4800

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WIND] %(message)s"
)

# ----------------------------------------------------------
# VARIABLES DE ESTADO (para imprimir cada 5 segundos)
# ----------------------------------------------------------

last_wind_dir = None       # grados
last_wind_speed = None     # nudos
last_print_time = 0.0
PRINT_INTERVAL = 1.0       # segundos


# ----------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------

def nmea_checksum(sentence):
    """Calcula checksum NMEA (parte después del '$')."""
    c = 0
    for ch in sentence:
        c ^= ord(ch)
    return "{:02X}".format(c)


def build_mwv_sentence(wind_dir_deg, wind_speed_knots):
    """Construye frase MWV completa con *checksum*."""
    body = f"WIMWV,{wind_dir_deg:.1f},R,{wind_speed_knots:.1f},N,A"
    checksum = nmea_checksum(body)
    return f"${body}*{checksum}"


def print_wind_status():
    """Muestra estado cada 5 segundos."""
    if last_wind_dir is None or last_wind_speed is None:
        logging.info("Aún no hay datos de viento.")
        return

    logging.info(
        "Viento enviado a Pixhawk: {:.1f} kn @ {:.0f}°".format(
            last_wind_speed,
            last_wind_dir % 360,
        )
    )


# ----------------------------------------------------------
# PROCESO PRINCIPAL
# ----------------------------------------------------------

def main():

    global last_wind_dir, last_wind_speed, last_print_time

    logging.info("Iniciando módulo de viento NMEA → Pixhawk (TELEM2).")

    # Abrir UART hacia la Pixhawk
    try:
        ser = serial.Serial(PIXHAWK_DEV, PIXHAWK_BAUD, timeout=1)
        logging.info(f"Puerto serie abierto: {PIXHAWK_DEV} @ {PIXHAWK_BAUD}")
    except Exception as e:
        logging.error(f"No se pudo abrir {PIXHAWK_DEV}: {e}")
        return

    # Lanzar actisense-serial y analyzer (NMEA2000 → JSON)
    try:
        p1 = subprocess.Popen(
            ["actisense-serial", "-p", ACTISENSE_PORT],
            stdout=subprocess.PIPE
        )
        p2 = subprocess.Popen(
            ["analyzer", "-json"],
            stdin=p1.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        logging.info("Lectura NMEA2000 iniciada.")
    except Exception as e:
        logging.error(f"Error iniciando actisense/analyzer: {e}")
        return

    # Bucle principal
    try:
        for raw in p2.stdout:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Filtrar PGN de viento
            if obj.get("pgn") != 130306:
                continue

            fields = obj.get("fields", {})

            # Procesar viento
            try:
                wind_speed_ms = float(fields.get("Wind Speed", 0.0))
                wind_angle_rad = float(fields.get("Wind Angle", 0.0))

                wind_speed_knots = wind_speed_ms * 1.94384
                wind_dir_deg = math.degrees(wind_angle_rad)

                # Actualizar estado
                last_wind_dir = wind_dir_deg
                last_wind_speed = wind_speed_knots

                # Enviar MWV a Pixhawk
                mwv = build_mwv_sentence(wind_dir_deg, wind_speed_knots)
                ser.write(mwv.encode("ascii") + b"\r\n")

                # Imprimir cada 5 s
                now = time.time()
                if now - last_print_time >= PRINT_INTERVAL:
                    print_wind_status()
                    last_print_time = now

            except Exception as e:
                logging.error(f"Error procesando viento: {e}")
                continue

    finally:
        logging.info("Finalizando módulo de viento.")
        try:
            if ser.is_open:
                ser.close()
        except:
            pass

        try:
            p1.terminate()
        except:
            pass

        try:
            p2.terminate()
        except:
            pass


if __name__ == "__main__":
    main()
