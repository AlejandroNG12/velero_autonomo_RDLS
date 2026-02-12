#!/usr/bin/env python3
"""
main_unificado.py

Fusiona:
- Envío de viento NMEA0183 por UART (TELEM2) usando viento_nmea.py
- Recepción de telemetría MAVLink por USB usando telemetria_mavlink.py

Arquitectura:
- Viento:  UART /dev/serial0  @ 4800 baudios (TELEM2, NMEA/WindVane)
- MAVLink: USB  /dev/ttyACM0  @ 57600 baudios (Pixhawk USB, MAVLink)
"""

import threading
import time
import logging

from . import viento_nmea
from . import telemetria_mavlink


def viento_loop():
    """
    Hilo que lanza tu código actual de viento.
    viento_nmea.main() ya:
      - abre /dev/serial0 @ 4800
      - lanza actisense-serial + analyzer
      - genera y envía frases MWV hacia la Pixhawk
    """
    logging.info("[MAIN] Hilo VIENTO arrancando (UART → TELEM2, NMEA)")
    try:
        viento_nmea.main()
    except Exception as e:
        logging.exception(f"[MAIN] Error en hilo de viento: {e}")


def mavlink_loop():
    """
    Hilo que lanza tu código de telemetría MAVLink.
    Aquí sobreescribimos DEVICE y BAUD para usar el USB (/dev/ttyACM0).
    """
    logging.info("[MAIN] Hilo MAVLINK arrancando (USB → DB)")

    try:
        telemetria_mavlink.main()
    except Exception as e:
        logging.exception(f"[MAIN] Error en hilo MAVLink: {e}")


def main():
    # Configuración básica de logging (si ya la configuran los módulos, no pasa nada)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logging.info("[MAIN] Iniciando sistema unificado viento + MAVLink")
    logging.info(f"[MAIN] Viento por UART /dev/serial0, MAVLink por USB")

    t_viento = threading.Thread(target=viento_loop, daemon=True)
    t_mav    = threading.Thread(target=mavlink_loop, daemon=True)

    t_viento.start()
    t_mav.start()

    logging.info("[MAIN] Hilos lanzados. Pulsa Ctrl+C para salir.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("[MAIN] Saliendo por Ctrl+C")
        # Los hilos daemon se cerrarán al terminar el proceso.


if __name__ == "__main__":
    main()
