#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging

from pymavlink import mavutil

from storage.db import get_db_connection, init_db, insert_wind

# -----------------------------
# CONFIGURACIÓN
# -----------------------------
ACTISENSE_PORT = "/dev/ttyUSB0"    # NGT-1
PIXHAWK_DEV = "/dev/serial0"       # TELEM2
PIXHAWK_BAUD = 57600               # Pixhawk serial speed
# -----------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

class FakeWindMsg:
    """Fake WIND structure for DB insert compatibility."""
    def __init__(self, speed_ms, direction_deg, speed_z=0.0):
        self.speed = speed_ms
        self.direction = direction_deg
        self.speed_z = speed_z
    def get_type(self):
        return "WIND"


def main():
    start_time = time.time()

    # ---- BD ----
    conn = get_db_connection()
    init_db(conn)

    # ---- Pixhawk ----
    logging.info(f"Conectando a Pixhawk en {PIXHAWK_DEV} @ {PIXHAWK_BAUD}...")
    master = mavutil.mavlink_connection(
        PIXHAWK_DEV,
        baud=PIXHAWK_BAUD,
        source_system=1,
        source_component=190
    )

    master.wait_heartbeat()
    logging.info("Heartbeat recibido de Pixhawk.")

    # ---- Pipeline Actisense → analyzer (EL QUE TE FUNCIONA) ----
    logging.info("Lanzando actisense-serial + analyzer -json...")
    p1 = subprocess.Popen(
        ["actisense-serial", ACTISENSE_PORT],
        stdout=subprocess.PIPE,
    )
    p2 = subprocess.Popen(
        ["analyzer", "-json"],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    logging.info("Procesando datos de viento...")

    try:
        for raw in p2.stdout:

            # Leer línea JSON del analyzer
            try:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                obj = json.loads(line)
            except Exception:
                continue

            # Solo el PGN 130306 (Wind Data)
            if obj.get("pgn") != 130306:
                continue

            fields = obj.get("fields", {})

            try:
                wind_speed_ms = float(fields["Wind Speed"])   # m/s
                wind_angle_deg = float(fields["Wind Angle"])  # grados
            except Exception:
                continue

            # Convertir grados → radianes (NECESARIO para MAVLink)
            wind_angle_rad = math.radians(wind_angle_deg)

            # Barco → componente vertical siempre 0
            speed_z = 0.0

            # -----------------------------------------
            # 1) ENVIAR MAVLINK WIND (EL QUE USA EL AUTOPILOTO)
            # Formato correcto WIND(speed, direction_rad, speed_z)
            # -----------------------------------------
            try:
                master.mav.wind_send(
                    wind_angle_rad,     # direction (rad)
                    wind_speed_ms,      # speed (m/s)
                    speed_z             # vertical (0)
                )
            except Exception as e:
                logging.error(f"Error enviando MAVLink WIND: {e}")
                continue


            # -----------------------------------------
            # Guardar en BD usando tu API existente
            # -----------------------------------------
            try:
                fake_msg = FakeWindMsg(
                    speed_ms=wind_speed_ms,
                    direction_deg=wind_angle_deg,
                    speed_z=speed_z
                )
                insert_wind(conn, fake_msg)
            except Exception as e:
                logging.error(f"Error insertando viento en BD: {e}")

            logging.info(
                f"WIND enviado: {wind_speed_ms:.2f} m/s, "
                f"WIND enviado: {wind_angle_deg:.2f} º, "
                f"WIND enviado: {wind_angle_rad:.2f} rad, "


            )

    except KeyboardInterrupt:
        logging.info("Ctrl+C pulsado, cerrando...")

    finally:
        conn.close()
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
