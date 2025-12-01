#!/usr/bin/env python3
import os
import sqlite3
import csv

# 🔧 Cambia esta ruta si tu BD se llama distinto o está en otra carpeta
DB_PATH = "telemetria.db"

# Tablas de medidas que quieres exportar
TABLES = [
    "gps_samples",
    "attitude_samples",
    "imu_samples",
    "wind_samples",
]

OUTPUT_DIR = "outputs"
N_LAST = 50  # número de filas recientes a exportar


def export_table_last_n(conn, table, n, output_dir):
    cur = conn.cursor()

    # Intentamos ordenar por timestamp_utc si existe; si no, usamos rowid
    cur.execute(f"PRAGMA table_info({table})")
    cols_info = cur.fetchall()
    col_names = [c[1] for c in cols_info]

    if "timestamp_utc" in col_names:
        order_col = "timestamp_utc"
    else:
        order_col = "rowid"

    query = f"""
        SELECT *
        FROM {table}
        ORDER BY {order_col} DESC
        LIMIT ?
    """

    cur.execute(query, (n,))
    rows = cur.fetchall()

    if not rows:
        print(f"[INFO] La tabla {table} no tiene datos, no genero CSV.")
        return

    # Invertimos para que en el CSV salgan de más antiguo a más reciente
    rows = rows[::-1]

    # Nombres de columna
    headers = col_names

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"{table}_last{n}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"[OK] Exportados {len(rows)} registros de {table} -> {csv_path}")


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encuentra la base de datos en: {DB_PATH}")
        print("       Edita DB_PATH al principio del script con la ruta correcta.")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        for table in TABLES:
            try:
                export_table_last_n(conn, table, N_LAST, OUTPUT_DIR)
            except sqlite3.Error as e:
                print(f"[WARN] No se ha podido exportar {table}: {e}")
    finally:
        conn.close()
        print("[INFO] Conexión a la BD cerrada.")


if __name__ == "__main__":
    main()
