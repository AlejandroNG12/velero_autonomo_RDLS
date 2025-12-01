#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging
import serial

ACTISENSE_PORT = "/dev/ttyUSB0"      # NGT-1
PIXHAWK_PORT = "/dev/serial0"        # UART GPIO14→Pixhawk RX
PIXHAWK_BAUD = 4800                  # NMEA baudrate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def nmea_checksum(sentence):
    cs = 0
    for c in sentence:
        cs ^= ord(c)
    return f"{cs:02X}"

def build_mwv(angle_deg, speed_ms):
    # Base sentence without checksum
    body = f"WIMWV,{angle_deg:.1f},R,{speed_ms:.2f},M,A"
    checksum = nmea_checksum(body)
    return f"${body}*{checksum}\r\n"

def main():

    logging.info("Abriendo puerto NMEA hacia Pixhawk...")
    ser = serial.Serial(PIXHAWK_PORT, PIXHAWK_BAUD, timeout=0.1)

    logging.info("Lanzando actisense-serial + analyzer -json...")
    p1 = subprocess.Popen(
        ["actisense-serial", ACTISENSE_PORT],
        stdout=subprocess.PIPE
    )
    p2 = subprocess.Popen(
        ["analyzer", "-json"],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    logging.info("Procesando datos de viento gWind → NMEA...")

    for raw in p2.stdout:
        try:
            line = raw.decode("utf-8").strip()
            if not line:
                continue

            obj = json.loads(line)

        except:
            continue

        # PGN 130306: Wind Data
        if obj.get("pgn") != 130306:
            continue

        fields = obj.get("fields", {})
        try:
            wind_speed = float(fields["Wind Speed"])    # m/s
            wind_angle = float(fields["Wind Angle"])    # grados
        except:
            continue

        # Construir sentencia NMEA
        sentence = build_mwv(wind_angle, wind_speed)
        ser.write(sentence.encode("ascii"))

        logging.info(f"Enviado NMEA → {sentence.strip()}")

if __name__ == "__main__":
    main()
