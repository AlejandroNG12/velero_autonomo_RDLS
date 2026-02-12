# core/database.py
import sqlite3
import logging
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Tabla unificada para fácil visualización
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            lat REAL, lon REAL, alt REAL,      -- GPS
            roll REAL, pitch REAL, yaw REAL,   -- Actitud
            wind_angle REAL, wind_speed REAL,  -- Viento
            servo_rudder INTEGER,              -- Timón (PWM)
            servo_sail INTEGER                 -- Vela (PWM)
        )
    """)
    conn.commit()
    conn.close()
    logging.info("Base de datos inicializada correctamente.")

def insert_data(data_dict):
    """Inserta un diccionario de datos en la tabla."""
    conn = get_connection()
    cursor = conn.cursor()
    columns = ', '.join(data_dict.keys())
    placeholders = ':' + ', :'.join(data_dict.keys())
    sql = f'INSERT INTO telemetria ({columns}) VALUES ({placeholders})'
    cursor.execute(sql, data_dict)
    conn.commit()
    conn.close()
