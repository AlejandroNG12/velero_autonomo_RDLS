import sqlite3
import time
import math
import logging
import os

# Directorio donde está este fichero (storage/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ruta ABSOLUTA a telemetria.db dentro de storage/
DB_PATH = os.path.join(BASE_DIR, "telemetria.db")


# ============================================================
#   CONEXIÓN A BASE DE DATOS
# ============================================================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# ============================================================
#   CREACIÓN DE TABLAS
# ============================================================
def init_db(conn):
    cur = conn.cursor()

    # ---------- GPS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gps_samples (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp_utc  REAL NOT NULL,
        timestamp_text TEXT,
        time_boot_s    REAL,
        lat_deg        REAL NOT NULL,
        lon_deg        REAL NOT NULL,
        alt_msl_m      REAL,
        relative_alt_m REAL,
        vel_m_s        REAL,
        hdg_deg        REAL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gps_time ON gps_samples(timestamp_utc);")

    # ---------- ACTITUD ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attitude_samples (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp_utc  REAL NOT NULL,
        timestamp_text TEXT,
        time_boot_s    REAL,
        roll_rad       REAL NOT NULL,
        pitch_rad      REAL NOT NULL,
        yaw_rad        REAL NOT NULL,
        rollspeed      REAL,
        pitchspeed     REAL,
        yawspeed       REAL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_att_time ON attitude_samples(timestamp_utc);")

    # ---------- IMU ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS imu_samples (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp_utc  REAL NOT NULL,
        timestamp_text TEXT,
        time_boot_s    REAL,
        ax_mg          REAL,
        ay_mg          REAL,
        az_mg          REAL,
        gx_mrad_s      REAL,
        gy_mrad_s      REAL,
        gz_mrad_s      REAL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_imu_time ON imu_samples(timestamp_utc);")

    # ---------- VIENTO ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wind_samples (
    	id             INTEGER PRIMARY KEY AUTOINCREMENT,
    	timestamp_utc  REAL NOT NULL,
    	timestamp_text TEXT,
    	time_boot_s    REAL,
    	wind_speed_ms  REAL,
    	wind_dir_deg   REAL,
    	wind_vertical  REAL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wind_time ON wind_samples(timestamp_utc);")


    conn.commit()


# ============================================================
#   INSERCIÓN DE DATOS GPS
# ============================================================
def insert_gps(conn, msg):
    ts_utc = time.time()
    timestamp_text = time.strftime("%a %Y-%m-%d %H:%M:%S", time.localtime(ts_utc))

    try:
        time_boot_s = msg.time_boot_ms / 1000.0
    except:
        time_boot_s = None

    lat_deg = msg.lat / 1e7
    lon_deg = msg.lon / 1e7
    alt_m   = msg.alt / 1000.0
    rel_m   = msg.relative_alt / 1000.0

    vx_ms = msg.vx / 100.0
    vy_ms = msg.vy / 100.0
    vel_ms = math.sqrt(vx_ms**2 + vy_ms**2)

    hdg_deg = msg.hdg * 0.01 if msg.hdg != 65535 else None

    conn.execute("""
        INSERT INTO gps_samples (
            timestamp_utc, timestamp_text, time_boot_s,
            lat_deg, lon_deg, alt_msl_m,
            relative_alt_m, vel_m_s, hdg_deg
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        ts_utc, timestamp_text, time_boot_s,
        lat_deg, lon_deg, alt_m,
        rel_m, vel_ms, hdg_deg
    ))
    conn.commit()


# ============================================================
#   INSERCIÓN DE DATOS ACTITUD
# ============================================================
def insert_attitude(conn, msg):
    ts_utc = time.time()
    timestamp_text = time.strftime("%a %Y-%m-%d %H:%M:%S", time.localtime(ts_utc))

    try:
        time_boot_s = msg.time_boot_ms / 1000.0
    except:
        time_boot_s = None

    conn.execute("""
        INSERT INTO attitude_samples (
            timestamp_utc, timestamp_text, time_boot_s,
            roll_rad, pitch_rad, yaw_rad,
            rollspeed, pitchspeed, yawspeed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        ts_utc, timestamp_text, time_boot_s,
        msg.roll, msg.pitch, msg.yaw,
        msg.rollspeed, msg.pitchspeed, msg.yawspeed
    ))
    conn.commit()

# ============================================================
#   INSERCIÓN DE DATOS IMU
# ============================================================
def insert_imu(conn, msg):
    ts_utc = time.time()
    timestamp_text = time.strftime("%a %Y-%m-%d %H:%M:%S", time.localtime(ts_utc))

    try:
        time_boot_s = msg.time_boot_ms / 1000.0
    except:
        time_boot_s = None

    conn.execute("""
        INSERT INTO imu_samples (
            timestamp_utc, timestamp_text, time_boot_s,
            ax_mg, ay_mg, az_mg,
            gx_mrad_s, gy_mrad_s, gz_mrad_s
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        ts_utc, timestamp_text, time_boot_s,
        msg.xacc, msg.yacc, msg.zacc,
        msg.xgyro, msg.ygyro, msg.zgyro
    ))
    conn.commit()

# ============================================================
#   INSERCIÓN DE DATOS VIENTO NMEA
# ============================================================
def insert_wind_NMEA(conn, wind_speed_ms, wind_dir_deg, time_boot_s=None, wind_vertical=None):
    """
    Inserta una muestra de viento a partir de valores simples (no MAVLink),
    pensada para el flujo NMEA (Actisense + analyzer).
    """
    ts_utc = time.time()
    timestamp_text = time.strftime("%a %Y-%m-%d %H:%M:%S", time.localtime(ts_utc))

    conn.execute("""
        INSERT INTO wind_samples (
            timestamp_utc, timestamp_text, time_boot_s,
            wind_speed_ms, wind_dir_deg, wind_vertical
        ) VALUES (?, ?, ?, ?, ?, ?);
    """, (
        ts_utc, timestamp_text, time_boot_s,
        wind_speed_ms, wind_dir_deg, wind_vertical
    ))
    conn.commit()

# ============================================================
#   INSERCIÓN DE DATOS VIENTO MAVLINK
# ============================================================
def insert_wind(conn, msg):
    ts_utc = time.time()
    timestamp_text = time.strftime("%a %Y-%m-%d %H:%M:%S", time.localtime(ts_utc))

    mtype = msg.get_type()

    # --------- Mensaje WIND (Pixhawk) ---------
    if mtype == "WIND":
        # Algunos firmwares usan estos campos, por si acaso protegemos
        wind_speed_ms = getattr(msg, "speed", None)        # m/s
        wind_dir_deg  = getattr(msg, "direction", None)    # grados
        wind_vertical = getattr(msg, "speed_z", 0.0)       # opcional

        # Este mensaje normalmente NO lleva time_boot_ms → None
        time_boot_s = None

    # --------- Mensaje WIND_COV ---------
    elif mtype == "WIND_COV":
        # Magnitud horizontal
        wind_speed_ms = math.hypot(msg.wind_x, msg.wind_y)

        # Dirección a partir de componentes
        wind_dir_rad = math.atan2(msg.wind_y, msg.wind_x)
        wind_dir_deg = (math.degrees(wind_dir_rad) + 360) % 360

        wind_vertical = msg.wind_z

        # Algunos mensajes traen time_usec, por si acaso lo protegemos
        try:
            time_boot_s = msg.time_usec / 1e6   # microseg → s
        except AttributeError:
            time_boot_s = None

    else:
        # Si entra otro tipo de mensaje inesperado, salimos
        return

    try:
        conn.execute("""
            INSERT INTO wind_samples (
                timestamp_utc, timestamp_text, time_boot_s,
                wind_speed_ms, wind_dir_deg, wind_vertical
            ) VALUES (?, ?, ?, ?, ?, ?);
        """, (
            ts_utc, timestamp_text, time_boot_s,
            wind_speed_ms, wind_dir_deg, wind_vertical
        ))
        conn.commit()
        logging.info(f"Viento sample guardado ({mtype})")

    except Exception as e:
        logging.error(f"Error insertando viento ({mtype}): {e}")

# ============================================================
#   EJECUCIÓN DIRECTA (crear tablas)
# ============================================================
if __name__ == "__main__":
    conn = get_db_connection()
    init_db(conn)
    conn.close()
    print(f"[OK] Base de datos inicializada en {DB_PATH}")
