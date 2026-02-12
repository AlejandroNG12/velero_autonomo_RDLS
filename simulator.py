# simulator.py
import time
import random
import logging
from core.database import insert_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SIM] %(message)s")

def simulate_sailing():
    logging.info("Simulador iniciado. Generando datos de navegación...")
    
    # Valores iniciales para que la simulación sea suave
    curr_roll = 0.0
    curr_wind = 180.0

    while True:
        # Generamos variaciones realistas
        curr_roll += random.uniform(-1.5, 1.5)
        curr_wind = (curr_wind + random.uniform(-5, 5)) % 360
        
        # Creamos el diccionario de datos
        data = {
            "lat": 40.4167 + random.uniform(-0.01, 0.01),
            "lon": -3.7033 + random.uniform(-0.01, 0.01),
            "alt": random.uniform(0, 5),
            "roll": round(max(-30, min(30, curr_roll)), 2), # Máximo 30 grados de escora
            "pitch": round(random.uniform(-5, 5), 2),
            "yaw": round(random.uniform(0, 360), 2),
            "wind_angle": round(curr_wind, 1),
            "wind_speed": round(random.uniform(5, 15), 1), # Viento entre 5 y 15 nudos
            "servo_rudder": random.randint(1100, 1900),    # PWM típico
            "servo_sail": random.randint(1000, 2000)
        }

        try:
            insert_data(data)
            logging.info(f"Insertado: Roll {data['roll']}° | Wind {data['wind_angle']}°")
        except Exception as e:
            logging.error(f"Error insertando en DB: {e}")

        time.sleep(1) # Frecuencia de 1Hz

if __name__ == "__main__":
    simulate_sailing()
