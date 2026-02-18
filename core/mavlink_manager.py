from pymavlink import mavutil
import time
import logging
import math
from config import PORT_MAVLINK, BAUD_MAVLINK
from core.database import insert_data

def mavlink_loop():
    logging.info(f"Intentando conectar con Pixhawk en {PORT_MAVLINK}...")
    
    while True:
        try:
            # Crear conexión MAVLink
            master = mavutil.mavlink_connection(PORT_MAVLINK, baud=BAUD_MAVLINK)
            
            # Esperar el primer latido (Heartbeat)
            logging.info("Esperando Heartbeat...")
            master.wait_heartbeat()
            logging.info("¡Pixhawk conectada!")

            while True:
                # Recibimos cualquier mensaje de interés
                msg = master.recv_match(
                    type=['GLOBAL_POSITION_INT', 'ATTITUDE', 'SERVO_OUTPUT_RAW'], 
                    blocking=True, 
                    timeout=1.0
                )
                
                if not msg:
                    continue

                data_update = {}
                msg_type = msg.get_type()

                if msg_type == 'GLOBAL_POSITION_INT':
                    data_update['lat'] = msg.lat / 1e7
                    data_update['lon'] = msg.lon / 1e7
                    data_update['alt'] = msg.relative_alt / 1000.0
                
                elif msg_type == 'ATTITUDE':
                    # Convertimos radianes a grados
                    data_update['roll'] = round(math.degrees(msg.roll), 1)
                    data_update['pitch'] = round(math.degrees(msg.pitch), 1)
                    data_update['yaw'] = round(math.degrees(msg.yaw), 1)

                elif msg_type == 'SERVO_OUTPUT_RAW':
                    # Canal 1 suele ser Timón, Canal 3 suele ser Vela (ajustar según config ArduPilot)
                    data_update['servo_rudder'] = msg.servo1_raw
                    data_update['servo_sail'] = msg.servo3_raw

                if data_update:
                    insert_data(data_update)

        except Exception as e:
            logging.error(f"Error en enlace MAVLink: {e}")
            logging.info("Reintentando conexión en 5 segundos...")
            time.sleep(5)
