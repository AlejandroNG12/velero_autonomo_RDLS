#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# ----------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "telemetria.db"   # adapta si tu DB está en storage/

# Si realmente está en storage/, cambia por:
# DB_PATH = BASE_DIR / "storage" / "telemetria.db"


# ----------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------

@st.cache_data
def cargar_gps(desde: float | None = None):
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT timestamp_utc, lat_deg, lon_deg, alt_msl_m, vel_m_s, hdg_deg
        FROM gps_samples
        ORDER BY timestamp_utc ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    df["dt"] = df["timestamp_utc"].apply(
        lambda t: datetime.fromtimestamp(t)
    )
    df.set_index("dt", inplace=True)

    # filtrar por tiempo si se pide
    if desde is not None:
        df = df[df.index >= datetime.fromtimestamp(desde)]

    # pasar m/s a nudos
    if "vel_m_s" in df.columns:
        df["sog_kn"] = df["vel_m_s"] * 1.94384

    return df


@st.cache_data
def cargar_viento(desde: float | None = None):
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT timestamp_utc, wind_speed_ms, wind_dir_deg
        FROM wind_samples
        ORDER BY timestamp_utc ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    df["dt"] = df["timestamp_utc"].apply(
        lambda t: datetime.fromtimestamp(t)
    )
    df.set_index("dt", inplace=True)

    if desde is not None:
        df = df[df.index >= datetime.fromtimestamp(desde)]

    df["wind_speed_kn"] = df["wind_speed_ms"] * 1.94384
    return df


# ----------------------------------------------------------
# INTERFAZ STREAMLIT
# ----------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Velero autónomo – Telemetría",
        layout="wide",
    )

    st.title("⛵ Velero autónomo – Panel de telemetría")

    # Selector de horizonte temporal
    st.sidebar.header("Filtro temporal")
    opcion_horas = st.sidebar.selectbox(
        "Mostrar datos de:",
        [
            "Última 1 hora",
            "Últimas 6 horas",
            "Últimas 24 horas",
            "Todo",
        ],
        index=2,
    )

    ahora = datetime.now()
    if opcion_horas == "Última 1 hora":
        desde_dt = ahora - timedelta(hours=1)
    elif opcion_horas == "Últimas 6 horas":
        desde_dt = ahora - timedelta(hours=6)
    elif opcion_horas == "Últimas 24 horas":
        desde_dt = ahora - timedelta(hours=24)
    else:
        desde_dt = None

    desde_ts = desde_dt.timestamp() if desde_dt is not None else None

    # Cargar datos
    gps_df = cargar_gps(desde_ts)
    viento_df = cargar_viento(desde_ts)

    # ------------------------------------------------------
    # RECUADROS RESUMEN
    # ------------------------------------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Posición actual")
        if not gps_df.empty:
            ult = gps_df.iloc[-1]
            st.metric(
                label="Latitud / Longitud",
                value=f"{ult['lat_deg']:.5f}, {ult['lon_deg']:.5f}",
            )
            st.metric(
                label="Altitud (msl)",
                value=f"{ult['alt_msl_m']:.1f} m" if pd.notna(ult["alt_msl_m"]) else "N/D",
            )
        else:
            st.write("Sin datos GPS.")

    with col2:
        st.subheader("Movimiento")
        if not gps_df.empty:
            ult = gps_df.iloc[-1]
            sog = ult.get("sog_kn", None)
            hdg = ult.get("hdg_deg", None)
            st.metric(
                label="SOG",
                value=f"{sog:.2f} kn" if sog is not None and pd.notna(sog) else "N/D",
            )
            st.metric(
                label="COG",
                value=f"{hdg:.1f}°" if hdg is not None and pd.notna(hdg) else "N/D",
            )
        else:
            st.write("Sin datos de velocidad.")

    with col3:
        st.subheader("Viento")
        if not viento_df.empty:
            ult_v = viento_df.iloc[-1]
            st.metric(
                label="Velocidad viento",
                value=f"{ult_v['wind_speed_kn']:.1f} kn",
            )
            st.metric(
                label="Dirección viento",
                value=f"{ult_v['wind_dir_deg']:.0f}°",
            )
        else:
            st.write("Sin datos de viento.")

    st.markdown("---")

    # ------------------------------------------------------
    # TRAYECTORIA GPS (MAPA)
    # ------------------------------------------------------
    st.subheader("Trayectoria GPS")

    if not gps_df.empty:
        mapa_df = gps_df[["lat_deg", "lon_deg"]].rename(
            columns={"lat_deg": "lat", "lon_deg": "lon"}
        )
        st.map(mapa_df)
    else:
        st.write("Sin datos GPS para mostrar en el mapa.")

    # ------------------------------------------------------
    # GRÁFICAS TIEMPO
    # ------------------------------------------------------
    col_gps, col_viento = st.columns(2)

    with col_gps:
        st.subheader("Velocidad y rumbo (tiempo)")
        if not gps_df.empty:
            chart_df = gps_df[["sog_kn", "hdg_deg"]].copy()
            st.line_chart(chart_df)
        else:
            st.write("Sin datos GPS.")

    with col_viento:
        st.subheader("Viento (tiempo)")
        if not viento_df.empty:
            chart_df = viento_df[["wind_speed_kn", "wind_dir_deg"]]
            st.line_chart(chart_df)
        else:
            st.write("Sin datos de viento.")

    st.markdown("---")
    st.caption("Datos obtenidos de telemetria.db en la Raspberry Pi.")


if __name__ == "__main__":
    main()
