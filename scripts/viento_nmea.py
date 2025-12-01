import subprocess
import json
import math
import time
import logging
import serial

ACTISENSE_PORT = "/dev/ttyUSB0"
PIXHAWK_DEV = "/dev/serial0"
PIXHAWK_BAUD = 4800

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def calcular_checksum(sentencia):
    checksum = 0
    for char in sentencia[1:]:
        checksum ^= ord(char)
    return f"{checksum:02X}"

def generar_mwv(angulo_deg, velocidad_ms):
    velocidad_nudos = velocidad_ms * 1.94384
    data = f"WIMWV,{angulo_deg:.1f},R,{velocidad_nudos:.1f},N,A"
    checksum = calcular_checksum('$' + data)
    return f"${data}*{checksum}\r\n"

def main():
    logging.info(f"Conectando a Pixhawk en {PIXHAWK_DEV} @ {PIXHAWK_BAUD}...")
    try:
        ser = serial.Serial(PIXHAWK_DEV, PIXHAWK_BAUD, timeout=1)
        logging.info("Puerto serial abierto.")
    except serial.SerialException as e:
        logging.error(f"Error abriendo puerto serial: {e}")
        return

    logging.info("Lanzando actisense-serial y analyzer...")
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

    logging.info("Procesando datos de viento...")

    try:
        for raw in p2.stdout:
            try:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                obj = json.loads(line)
            except:
                continue

            if obj.get("pgn") != 130306:
                continue

            fields = obj.get("fields", {})
            try:
                wind_speed_ms = float(fields["Wind Speed"])
                wind_angle_deg = float(fields["Wind Angle"])
            except:
                continue

            mwv_sentence = generar_mwv(wind_angle_deg, wind_speed_ms)

            try:
                ser.write(mwv_sentence.encode("ascii"))
            except Exception as e:
                logging.error(f"Error enviando MWV: {e}")
                continue

            logging.info(
                f"MENV: speed={wind_speed_ms:.2f} angle={wind_angle_deg:.1f} "
                f"MWV={mwv_sentence.strip()}"
            )

    except KeyboardInterrupt:
        logging.info("Interrumpido.")

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
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
