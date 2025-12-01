import serial
import time
import sys

# --- Parámetros de la Pixhawk (TELEM2) ---
# En Raspberry Pi, el puerto UART suele ser '/dev/ttyS0' o '/dev/ttyAMA0'.
# Asegúrate de habilitar el puerto serial de la RPi y deshabilitar la consola serial.
PUERTO_SERIAL = '/dev/serial0' # Ajusta esto si tu RPi usa '/dev/ttyAMA0'
BAUD_RATE = 4800             # NMEA 0183 estándar usa 4800 baudios

# --- Datos Fijos de Viento a Enviar ---
# Ángulo de Viento Relativo (120 grados)
ANGULO_VIENTO = 120.0
# Velocidad de Viento (3.0 m/s)
VELOCIDAD_VIENTO_MS = 3.0
# Convertir m/s a Nudos (aproximadamente)
VELOCIDAD_VIENTO_NUDOS = VELOCIDAD_VIENTO_MS * 1.94384

def calcular_checksum(sentencia):
    """Calcula el checksum NMEA (XOR de todos los caracteres entre $ y *)"""
    checksum = 0
    # Comenzar desde el primer carácter después de '$'
    for char in sentencia[1:]:
        checksum ^= ord(char)
    # Formatear el checksum como un string hexadecimal de 2 dígitos
    return f"{checksum:02X}"

def generar_mwv(angulo, velocidad, unidad_velocidad='N', referencia_angulo='R'):
    """Genera la sentencia NMEA 0183 MWV (Wind Speed and Angle)"""
    # Referencia de ángulo: R=Relative (relativo al vehículo/barco), T=True (respecto al Norte)
    # Unidad de velocidad: N=Nudos, M=Metros por segundo (No siempre soportado, N es común)
    
    # Formato: $WIMWV,AAA.A,R,VVV.V,N,A*CC
    
    data = f"WIMWV,{angulo:.1f},{referencia_angulo},{velocidad:.1f},{unidad_velocidad},A"
    checksum = calcular_checksum('$' + data)
    
    sentencia_completa = f"${data}*{checksum}\r\n"
    return sentencia_completa

def enviar_datos_nmea():
    """Inicializa el puerto serial y envía los datos de viento"""
    print(f"Puerto: {PUERTO_SERIAL} | Baudios: {BAUD_RATE}")
    
    try:
        # Inicializar la conexión serial
        ser = serial.Serial(PUERTO_SERIAL, BAUD_RATE, timeout=1)
        print("Puerto serial abierto con éxito.")
    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
        print("Asegúrate de que el puerto serial esté habilitado y la consola serial deshabilitada en la RPi.")
        sys.exit(1)

    try:
        while True:
            # 1. Generar la sentencia NMEA 0183 MWV (usando Nudos)
            mwv_sentence = generar_mwv(
                ANGULO_VIENTO,
                VELOCIDAD_VIENTO_NUDOS,
                unidad_velocidad='N',
                referencia_angulo='R'
            )
            
            # 2. Convertir a bytes y enviar
            data_to_send = mwv_sentence.encode('ascii')
            ser.write(data_to_send)
            
            print(f"Enviado: {mwv_sentence.strip()}")
            
            # Esperar 1 segundo antes de enviar el siguiente dato
            time.sleep(1) 

    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Puerto serial cerrado.")

if __name__ == "__main__":
    enviar_datos_nmea()
