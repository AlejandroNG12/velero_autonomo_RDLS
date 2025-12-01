#!/usr/bin/env python3
import serial
import time

# -----------------------------
# CONFIGURACIÓN DEL PUERTO
# -----------------------------
PORT = "/dev/serial0"    # Raspberry Pi UART
BAUD = 4800              # NMEA 0183 estándar

ser = serial.Serial(PORT, BAUD, timeout=0.1)


# -----------------------------
# FUNCIÓN PARA CALCULAR CHECKSUM
# -----------------------------
def nmea_checksum(sentence):
    """
    Calcula el checksum NMEA (XOR de todos los caracteres entre $ y *).
    Devuelve dos caracteres hexadecimales en mayúsculas.
    """
    check = 0
    for c in sentence:
        check ^= ord(c)
    return f"{check:02X}"


# -----------------------------
# FUNCIÓN PARA ENVIAR MWV
# -----------------------------
def send_mwv(angle_deg, speed_ms):
    """
    Envía una sentencia MWV con formato:
    $WIMWV,angle,R,speed,M,A*CS
    """
    angle = float(angle_deg)
    speed = float(speed_ms)

    # Cuerpo sin "$" ni "*"
    body = f"WIMWV,{angle:.1f},R,{speed:.2f},M,A"

    # Cálculo del checksum
    cs = nmea_checksum(body)

    # Sentencia final
    sentence = f"${body}*{cs}\r\n"

    # Enviar por serial
    ser.write(sentence.encode('ascii'))

    print(f"Enviado → {sentence.strip()}")


# -----------------------------
# LOOP PRINCIPAL
# -----------------------------
if __name__ == "__main__":
    print("Enviando MWV a la Pixhawk (CTRL+C para salir)...")

    try:
        while True:
            # -----------------------------------------------------------
            # Aquí sustituyes "angle_deg" y "speed_ms" por tus valores
            # reales leídos del Actisense:
            #
            #   angle_deg = wind_angle_deg
            #   speed_ms  = wind_speed_ms
            #
            # Por ahora pongo valores de prueba:
            # -----------------------------------------------------------
            angle_deg = 135.0     # dirección ejemplo
            speed_ms = 5.3        # velocidad ejemplo

            send_mwv(angle_deg, speed_ms)
            time.sleep(0.2)       # 5 Hz (puedes bajar a 1Hz si quieres)

    except KeyboardInterrupt:
        print("Finalizado.")
        ser.close()
