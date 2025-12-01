#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging
from pymavlink import mavutil

from storage.db import get_db_connection, init_db, insert_wind

ACTISENSE_PORT = "/dev/ttyUSB0"   # NGT-1
PIXHAWK_DEV    = "/dev/serial0"   # TELEM2
PIXHAWK_BAUD   = 57600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

class FakeWindCovMsg:
    """Mensaje mínimo para reutilizar insert_wind(conn, msg)."""
    def __init__(self, wind_x, wind_y, wind_z, time_usec):
        self.wind_x = wind_x
        self.wind_y = wind_y
        self.wind_z = wind_z
        self.time_usec = time_usec

    def get_type(self):
        return "WIND_COV"


def main():
    # 1) BD
    conn = get_db_connection()
    init_db(conn)

    # 2) Pixhawk por MAVLink
    logging.info(f"Conectando a Pixhawk en {PIXHAWK_DEV} @ {PIXHAWK_BAUD}...")
    master = mavutil.mavlink_connection(PIXHAWK_DEV, baud=PIXHAWK_BAUD)
    logging.info("Esperando heartbeat...")
    master.wait_heartbeat()
    logging.info(
        f"Heartbeat de sistema {master.target_system}, comp {master.target_component}"
    )

    # 3) Pipeline N2K -> JSON
    logging.info("Lanzando actisense-serial + analyzer -json...")
    p1 = subprocess.Popen(
        ["actisense-serial", ACTISENSE_PORT],
        stdout=subprocess.PIPE,
    )
    p2 = subprocess.Popen(
        ["analyzer", "-json"],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
    )

    logging.info("Bridge NMEA2000 -> MAVLink WIND_COV iniciado")

    try:
        for raw in p2.stdout:
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
                wind_angle_deg = float(fields["Wind Angle"])  # grados (desde donde SOPLA)
            except (KeyError, ValueError):
                continue

            # Convertir a vector de viento en NED para WIND_COV
            # Aproximación simple: pasar de "desde" a "hacia" sumando 180º
            dir_rad = math.radians(wind_angle_deg + 180.0)
            wind_x = wind_speed_ms * math.cos(dir_rad)
            wind_y = wind_speed_ms * math.sin(dir_rad)
            wind_z = 0.0

            t_usec = int(time.time() * 1e6)

            # 3a) Enviar a Pixhawk por MAVLink
            master.mav.wind_cov_send(
                t_usec,
                wind_x,
                wind_y,
                wind_z,
                0.0, 0.0, 0.0,   # varianzas
                0.0, 0.0          # precisiones
            )

            # 3b) Guardar en BD reutilizando insert_wind
            fake_msg = FakeWindCovMsg(wind_x, wind_y, wind_z, t_usec)
            insert_wind(conn, fake_msg)

            logging.info(
                f"Viento enviado/guardado: speed={wind_speed_ms:.2f} m/s, "
                f"dir={wind_angle_deg:.1f}°"
            )

    except KeyboardInterrupt:
        logging.info("Saliendo por Ctrl+C")
    finally:
        conn.close()
        logging.info("Conexión BD cerrada.")


if __name__ == "__main__":
    main()
