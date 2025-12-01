#!/usr/bin/env python3
import subprocess
import json
import math
import time
import logging

from pymavlink import mavutil

from storage.db import get_db_connection, init_db, insert_wind

ACTISENSE_PORT = "/dev/ttyUSB0"
PIXHAWK_DEV = "/dev/serial0"
PIXHAWK_BAUD = 57600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

class FakeWindMsg:
    """ Fake MAVLink WIND msg to reuse your DB insert logic """
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
        #source_system=1,
        #source_component=1
    )

    master.wait_heartbeat()
    logging.info("Heartbeat recibido de Pixhawk.")

    # ---- Pipeline que SÍ FUNCIONA en tu sistema ----
    logging.info("Lanzando pipeline Actisense → analyzer -json...")
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

            # leer línea JSON
            try:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                obj = json.loads(line)
            except Exception:
                continue

            # filtrar PGN 130306 (wind data)
            if obj.get("pgn") != 130306:
                continue

            fields = obj.get("fields", {})

            try:
                wind_speed_ms = float(fields["Wind Speed"])   # m/s
                wind_angle_deg = float(fields["Wind Angle"])  # grados
            except Exception:
                continue

            # --- CORRECCIÓN: convertir grados → radianes (MAVLink WIND requiere rad) ---
            wind_angle_rad = math.radians(wind_angle_deg)

            # --- speed_z siempre 0 para barcos ---
            speed_z = 0.0

# --- ENVIAR MENSAJE MAVLINK WIND (TRUE/APARENTE) ---
# ORDEN CORRECTO:
#   speed (m/s)
#   direction (radianes)
#   speed_z
     try:
        master.mav.wind_send(
        wind_speed_ms,      # velocidad viento (m/s)
        wind_angle_rad,     # dirección viento (rad)
        speed_z             # componente vertical (0 en barco)
     )
     except Exception as e:
        logging.error(f"Error enviando MAVLink WIND: {e}")
        continue

# --- ENVIAR TAMBIÉN VIENTO APARENTE AL HUD (WIND_ESTIMATE) ---
# Vector cartesiano en el marco del vehículo (x hacia delante, y hacia la derecha)
        apparent_x = wind_speed_ms * math.cos(wind_angle_rad)
        apparent_y = wind_speed_ms * math.sin(wind_angle_rad)

        try:
        master.mav.wind_estimate_send(
          apparent_x,   # viento en X (m/s)
          apparent_y,   # viento en Y (m/s)
          0.0           # viento vertical (no usamos)
        )
        except Exception as e:
          logging.error(f"Error enviando WIND_ESTIMATE: {e}")
            # --- GUARDAR EN BD ---
            try:
                fake_msg = FakeWindMsg(
                    speed_ms=wind_speed_ms,
                    direction_deg=wind_angle_deg,
                    speed_z=speed_z
                )
                insert_wind(conn, fake_msg)
            except Exception as e:
                logging.error(f"Error insertando BD: {e}")

            logging.info(
                f"WIND enviado OK: {wind_speed_ms:.2f} m/s, {wind_angle_deg:.1f}°"
            )

       except KeyboardInterrupt:
        logging.info("Ctrl+C pulsado, cerrando...")

     finally:
        conn.close()
        try: p1.terminate()
        except: pass
        try: p2.terminate()
        except: pass


if __name__ == "__main__":
    main()
