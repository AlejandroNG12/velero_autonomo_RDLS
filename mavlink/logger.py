#!/usr/bin/env python3
from pymavlink import mavutil
import logging
import time

from storage.db import (
    get_db_connection,
    init_db,
    insert_gps,
    insert_attitude,
    insert_imu,
    insert_wind,
)

DEVICE = "/dev/serial0"
BAUD   = 57600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

INTERESTING = {
    "GLOBAL_POSITION_INT",
    "ATTITUDE",
    "RAW_IMU",
    "SCALED_IMU",
    "WIND",
    "WIND_COV",
}

LOG_INTERVAL = {
    "GLOBAL_POSITION_INT": 1.0,   # GPS cada 1 segundo
    "ATTITUDE":            1.0,   # actitud cada 1 s
    "RAW_IMU":             1.0,
    "SCALED_IMU":          1.0,
    "WIND_COV":            1.0,
    "WIND":                1.0,
}


def connect_pixhawk():
    logging.info(f"Conectando a {DEVICE} @ {BAUD} baud...")
    master = mavutil.mavlink_connection(DEVICE, baud=BAUD)

    logging.info("Esperando heartbeat...")
    master.wait_heartbeat()
    logging.info(
        f"Heartbeat de sistema {master.target_system}, componente {master.target_component}"
    )
    return master


def main():
    conn = get_db_connection()
    init_db(conn)

    master = connect_pixhawk()

    last_logged = {msg_type: 0.0 for msg_type in LOG_INTERVAL.keys()}

    try:
        while True:
            msg = master.recv_match(blocking=True, timeout=1.0)
            if msg is None:
                continue

            mtype = msg.get_type()

            if mtype not in INTERESTING:
                continue

            if mtype not in LOG_INTERVAL:
                continue

            now = time.time()
            if now - last_logged[mtype] < LOG_INTERVAL[mtype]:
                continue

            last_logged[mtype] = now

            try:
                if mtype == "GLOBAL_POSITION_INT":
                    insert_gps(conn, msg)
                    logging.info("GPS guardado")

                elif mtype == "ATTITUDE":
                    insert_attitude(conn, msg)
                    logging.info("Actitud guardada")

                elif mtype in ("RAW_IMU", "SCALED_IMU"):
                    insert_imu(conn, msg)
                    logging.info("IMU guardada")

                elif mtype in ("WIND", "WIND_COV"):
                    insert_wind(conn, msg)
                    logging.info(f"Viento guardado ({mtype})")

            except Exception as e:
                logging.error(f"Error insertando {mtype}: {e}")

    except KeyboardInterrupt:
        logging.info("Saliendo por Ctrl+C")

    finally:
        conn.close()
        logging.info("Conexión BD cerrada.")


if __name__ == "__main__":
    main()
