import subprocess
import json
import math
import time
import logging
import serial
import os
import sys
from config import PORT_WIND_IN, PORT_WIND_OUT, BAUD_WIND_OUT, WIND_SAVE_INTERVAL
from core.database import insert_data

def calcular_checksum(sentencia):
    """Calcula el checksum NMEA (XOR de todos los caracteres entre $ y *)"""
    checksum = 0
    for char in sentencia[1:]:
        checksum ^= ord(char)
    return f"{checksum:02X}"

def generar_mwv(angulo, velocidad, unidad_velocidad='N', referencia_angulo='R'):
    """Genera la sentencia NMEA 0183 MWV ($WIMWV)"""
    # Formato: $WIMWV,AAA.A,R,VVV.V,N,A
    data = f"WIMWV,{angulo:.1f},{referencia_angulo},{velocidad:.1f},{unidad_velocidad},A"
    checksum = calcular_checksum('$' + data)
    return f"${data}*{checksum}\r\n"

def wind_loop():
    logging.info(f"🌀 Hilo de Viento iniciado (Modo Resiliente STDIN)")
    
    while True:
        ser_out = None
        p1 = None
        p2 = None
        
        try:
            # 0. Limpieza profunda y espera de liberación de puerto
            logging.info("Limpiando procesos antiguos y esperando al puerto...")
            os.system("pkill -9 -f actisense-serial")
            os.system("pkill -9 -f analyzer")
            time.sleep(2) 

            # 1. Abrir puerto serial hacia la Pixhawk
            ser_out = serial.Serial(PORT_WIND_OUT, BAUD_WIND_OUT, timeout=1)
            logging.info(f"✅ Puerto serial {PORT_WIND_OUT} listo.")

            # 2. Iniciar Pipeline (Estructura idéntica a tu script funcional)
            # Añadimos stdin=subprocess.PIPE para evitar el error de EOF
            p1 = subprocess.Popen(
                ["actisense-serial", PORT_WIND_IN],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=False
            )
            
            p2 = subprocess.Popen(
                ["analyzer", "-json"],
                stdin=p1.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False
            )

            logging.info("🚀 Pipeline Actisense -> Analyzer iniciado.")

            last_save = 0
            last_debug_print = 0

            # 3. Lectura de datos
            for raw in p2.stdout:
                try:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    
                    obj = json.loads(line)
                    if obj.get("pgn") != 130306:
                        continue

                    fields = obj.get("fields", {})
                    wind_speed_ms = float(fields.get("Wind Speed", 0))
                    wind_angle_deg = float(fields.get("Wind Angle", 0))
                    wind_speed_knots = wind_speed_ms * 1.94384

                    # A. Enviar a Pixhawk
                    mwv_sentence = generar_mwv(wind_angle_deg, wind_speed_knots)
                    ser_out.write(mwv_sentence.encode('ascii'))

                    now = time.time()
                    
                    # B. Monitorización por consola cada 3s
                    if now - last_debug_print >= 3.0:
                        logging.info(f"📡 MONITORIZACIÓN -> {mwv_sentence.strip()}")
                        last_debug_print = now

                    # C. Guardar en DB para el Dashboard
                    if now - last_save >= WIND_SAVE_INTERVAL:
                        insert_data({
                            "wind_angle": round(wind_angle_deg, 1),
                            "wind_speed": round(wind_speed_knots, 1)
                        })
                        last_save = now

                except Exception as e:
                    # Si falla una línea JSON, simplemente seguimos
                    continue

            logging.warning("⚠️ El flujo de datos se ha detenido inesperadamente.")

        except Exception as e:
            logging.error(f"❌ Error crítico en WindThread: {e}")
        
        finally:
            # Limpieza exhaustiva
            logging.info("Cerrando recursos de viento...")
            if ser_out and ser_out.is_open:
                ser_out.close()
            if p2: 
                p2.terminate()
                p2.wait()
            if p1: 
                p1.terminate()
                p1.wait()
            
            logging.info("🔄 Reintentando conexión de viento en 5 segundos...")
            time.sleep(5)
