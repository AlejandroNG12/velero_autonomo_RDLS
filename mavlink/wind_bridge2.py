#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging

from pymavlink import mavutil

from storage.db import get_db_connection, init_db, insert_wind

# Puerto del Actisense NGT-1 (NMEA2000 -> USB)
ACTISENSE_PORT = "/dev/ttyUSB0"

# Puerto MAVLink hacia la Pixhawk (TELEM2 normalmente)
PIXHAWK_DEV = "/dev/serial0"
PIXHAWK_BAUD = 57600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class FakeWindMsg:
    """
    Mensaje 'falso' con la misma interfaz que un mensaje MAVLink WIND,
    para poder reutilizar insert_wind(conn, msg) sin tocar tu db.py.
    """
    def __init__(self, speed_ms: float, direction_deg: float, speed_z: float = 0.0):
        self.speed = speed_ms          # m/s
        self.direction = direction_deg # grados
        self.speed_z = speed_z         # m/s

    def get_type(self):
        return "WIND"


def main():
    # Referencia de tiempo para time_boot_ms
    start_time = time.time()

    # --- 1) Conexión a BD ---
    conn = get_db_connection()
    init_db(conn)

    # --- 2) Conexión MAVLink a Pixhawk ---
    logging.info(f"Conectando a Pixhawk en {PIXHAWK_DEV} @ {PIXHAWK_BAUD} baud...")
    master = mavutil.mavlink_connection(PIXHAWK_DEV, baud=PIXHAWK_BAUD, source_system=1, source_component=1)

    logging.info("Esperando heartbeat de la Pixhawk...")
    master.wait_heartbeat()
    logging.info(
        f"Heartbeat recibido: sistema {master.target_system}, "
        f"componente {master.target_component}"
    )

    # --- 3) Pipeline Actisense -> analyzer -json ---
    logging.info("Lanzando actisense-serial + analyzer -json...")
    p1 = subprocess.Popen(
        ["actisense-serial", ACTISENSE_PORT],
        stdout=subprocess.PIPE,
    )
    p2 = subprocess.Popen(
        ["analyzer", "-json"],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # silenciar logs INFO de analyzer
    )

    logging.info("Bridge NMEA2000 -> MAVLink WIND iniciado")

    try:
        for raw in p2.stdout:
            # Leer línea JSON desde analyzer
            try:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                obj = json.loads(line)
            except Exception:
                continue

            # Solo PGN de viento
            if obj.get("pgn") != 130306:
                continue

            fields = obj.get("fields", {})
            try:
                wind_speed_ms = float(fields["Wind Speed"])   # m/s
                wind_angle_deg = float(fields["Wind Angle"])  # grados (desde donde sopla)
            except (KeyError, ValueError):
                continue

            # Enviar MAVLink WIND
            direction_rad = math.radians(wind_angle_deg)
            time_boot_ms = int((time.time() - start_time) * 1000)
            speed_z = 0.0

            try:
                master.mav.wind_send(
                    wind_speed_ms,
                    direction_rad,
                    speed_z
                )
            except Exception as e:
                logging.error(f"Error enviando MAVLink WIND: {e}")
                continue

            # Guardar en BD reutilizando insert_wind
            try:
                fake_msg = FakeWindMsg(
                    speed_ms=wind_speed_ms,
                    direction_deg=wind_angle_deg,
                    speed_z=speed_z,
                )
                insert_wind(conn, fake_msg)
            except Exception as e:
                logging.error(f"Error insertando viento en BD: {e}")

            logging.info(
                f"Viento enviado/guardado (WIND): "
                f"speed={wind_speed_ms:.2f} m/s, dir={wind_angle_deg:.1f}°"
            )

    except KeyboardInterrupt:
        logging.info("Saliendo por Ctrl+C")

    finally:
        conn.close()
        logging.info("Conexión BD cerrada.")
        # Intentar cerrar también los procesos hijos
        try:
            p1.terminate()
        except Exception:
            pass
        try:
            p2.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
