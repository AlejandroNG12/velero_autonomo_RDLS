#!/usr/bin/env python3
"""
build_telemetry_table.py

Script para construir una tabla "ancha" telemetry_samples a partir de:
  - gps_samples
  - attitude_samples
  - wind_samples

Cada fila de telemetry_samples corresponde a un timestamp de GPS, y se
completa con los datos de actitud y viento más cercanos en el tiempo
(dentro de una tolerancia).

Uso (desde la raíz del proyecto velero_autonomo):

    source venv/bin/activate
    python scripts/build_telemetry_table.py
"""

import sqlite3
import math
from pathlib import Path
from datetime import datetime

# --------------------------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------------------------

# Ruta a la base de datos: /home/pi/velero_autonomo/storage/telemetria.db
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "telemetria.db"

# Tolerancia máxima para asociar muestras en segundos
MATCH_TOLERANCE = 0.5  # p.ej. actitud/viento a ±0.5 s del GPS


# --------------------------------------------------------------------
# FUNCIONES AUXILIARES
# --------------------------------------------------------------------

def get_connection():
    """Devuelve una conexión SQLite a la BD de telemetría."""
    conn = sqlite3.connect(DB_PATH)
    return conn


def create_telemetry_table(conn: sqlite3.Connection):
    """
    Crea la tabla ancha telemetry_samples si no existe.

    NOTA: No se hace DROP TABLE, solo se vacía (DELETE) antes de rellenar.
    """
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_samples (
            timestamp_utc   REAL PRIMARY KEY,
            timestamp_text  TEXT,

            -- GPS
            lat_deg         REAL,
            lon_deg         REAL,
            alt_msl_m       REAL,
            sog_kn          REAL,
            hdg_deg         REAL,

            -- Viento
            wind_speed_ms   REAL,
            wind_speed_kn   REAL,
            wind_dir_deg    REAL,
            wind_vertical   REAL,

            -- Actitud
            roll_deg        REAL,
            pitch_deg       REAL,
            yaw_deg         REAL
        );
        """
    )

    # Índice por si quieres consultas temporales rápidas
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry_samples(timestamp_utc);"
    )

    # Vaciar tabla (reconstruimos desde cero)
    cur.execute("DELETE FROM telemetry_samples;")
    conn.commit()


def fetch_nearest_attitude(cur: sqlite3.Cursor, ts: float):
    """
    Devuelve la muestra de actitud más cercana a ts, dentro de MATCH_TOLERANCE.
    Si no hay ninguna en ese rango, devuelve (None, None, None).
    """
    cur.execute(
        """
        SELECT timestamp_utc, roll_rad, pitch_rad, yaw_rad
        FROM attitude_samples
        WHERE ABS(timestamp_utc - ?) <= ?
        ORDER BY ABS(timestamp_utc - ?) ASC
        LIMIT 1;
        """,
        (ts, MATCH_TOLERANCE, ts),
    )
    row = cur.fetchone()
    if row is None:
        return None, None, None

    _, roll_rad, pitch_rad, yaw_rad = row

    if roll_rad is None or pitch_rad is None or yaw_rad is None:
        return None, None, None

    roll_deg = math.degrees(roll_rad)
    pitch_deg = math.degrees(pitch_rad)
    yaw_deg = math.degrees(yaw_rad)

    return roll_deg, pitch_deg, yaw_deg


def fetch_nearest_wind(cur: sqlite3.Cursor, ts: float):
    """
    Devuelve la muestra de viento más cercana a ts, dentro de MATCH_TOLERANCE.
    Si no hay ninguna en ese rango, devuelve (None, None, None, None).
    """
    cur.execute(
        """
        SELECT timestamp_utc, wind_speed_ms, wind_dir_deg, wind_vertical
        FROM wind_samples
        WHERE ABS(timestamp_utc - ?) <= ?
        ORDER BY ABS(timestamp_utc - ?) ASC
        LIMIT 1;
        """,
        (ts, MATCH_TOLERANCE, ts),
    )
    row = cur.fetchone()
    if row is None:
        return None, None, None, None

    _, wind_speed_ms, wind_dir_deg, wind_vertical = row

    if wind_speed_ms is None:
        wind_speed_kn = None
    else:
        wind_speed_kn = wind_speed_ms * 1.94384

    return wind_speed_ms, wind_speed_kn, wind_dir_deg, wind_vertical


# --------------------------------------------------------------------
# PROCESO PRINCIPAL
# --------------------------------------------------------------------

def rebuild_telemetry_table():
    """
    Reconstruye la tabla telemetry_samples a partir de gps_samples,
    attitude_samples y wind_samples.
    """
    print(f"[INFO] Usando base de datos: {DB_PATH}")

    conn = get_connection()
    cur = conn.cursor()

    # Crear (si no existe) y vaciar la tabla ancha
    print("[INFO] Creando/vaciando tabla telemetry_samples...")
    create_telemetry_table(conn)

    # Leer todas las muestras GPS (serán la base temporal)
    print("[INFO] Leyendo muestras GPS...")
    cur.execute(
        """
        SELECT timestamp_utc, lat_deg, lon_deg, alt_msl_m, vel_m_s, hdg_deg
        FROM gps_samples
        ORDER BY timestamp_utc ASC;
        """
    )
    gps_rows = cur.fetchall()
    total_gps = len(gps_rows)
    print(f"[INFO] Muestras GPS encontradas: {total_gps}")

    if total_gps == 0:
        print("[WARN] No hay datos en gps_samples. Nada que hacer.")
        conn.close()
        return

    inserted = 0

    for idx, (ts_utc, lat, lon, alt_msl_m, vel_ms, hdg_deg) in enumerate(gps_rows, start=1):
        # Conversión velocidad suelo a nudos
        sog_kn = vel_ms * 1.94384 if vel_ms is not None else None

        # Timestamp en texto
        try:
            timestamp_text = datetime.fromtimestamp(ts_utc).isoformat(sep=" ")
        except Exception:
            timestamp_text = None

        # Buscar actitud más cercana
        roll_deg, pitch_deg, yaw_deg = fetch_nearest_attitude(cur, ts_utc)

        # Buscar viento más cercano
        wind_speed_ms, wind_speed_kn, wind_dir_deg, wind_vertical = fetch_nearest_wind(cur, ts_utc)

        # Insertar fila en telemetry_samples
        conn.execute(
            """
            INSERT OR REPLACE INTO telemetry_samples (
                timestamp_utc, timestamp_text,
                lat_deg, lon_deg, alt_msl_m, sog_kn, hdg_deg,
                wind_speed_ms, wind_speed_kn, wind_dir_deg, wind_vertical,
                roll_deg, pitch_deg, yaw_deg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ts_utc, timestamp_text,
                lat, lon, alt_msl_m, sog_kn, hdg_deg,
                wind_speed_ms, wind_speed_kn, wind_dir_deg, wind_vertical,
                roll_deg, pitch_deg, yaw_deg,
            )
        )

        inserted += 1

        # Mensaje de progreso cada 500 filas
        if inserted % 500 == 0:
            conn.commit()
            print(f"[INFO] Procesadas {inserted}/{total_gps} filas GPS...")

    conn.commit()
    conn.close()

    print(f"[OK] Tabla telemetry_samples reconstruida.")
    print(f"[OK] Filas insertadas/actualizadas: {inserted}")


if __name__ == "__main__":
    rebuild_telemetry_table()
