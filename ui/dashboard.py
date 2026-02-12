import sys
import os
import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as mdates # <--- Nuevo: Para formatear el tiempo
import time

# Añadimos la carpeta raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM telemetria ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        # Convertimos el string de la DB a objeto datetime real de Python
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

st.set_page_config(page_title="SailBridge Dashboard", layout="wide")
st.title("⛵ SailBridge OS: Telemetría en Tiempo Real")

data = load_data()

if not data.empty:
    data_plot = data.iloc[::-1] # Invertir para que el tiempo fluya de izq a der
    last_row = data.iloc[0]

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Estado de Escora")
        st.metric("Roll Actual", f"{last_row['roll']}°")
        
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(data_plot['timestamp'], data_plot['roll'], color='#1f77b4', marker='.', markersize=4)
        
        # --- Formateo del Eje X (Tiempo) ---
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45) # Rotamos para que no se solapen
        ax.set_ylabel("Grados")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

    with col2:
        st.subheader("Dirección del Viento")
        st.metric("Viento Aparente", f"{last_row['wind_angle']}°")
        
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.plot(data_plot['timestamp'], data_plot['wind_angle'], color='#ff7f0e', marker='.', markersize=4)
        
        # --- Formateo del Eje X (Tiempo) ---
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45)
        ax2.set_ylabel("Grados")
        ax2.grid(True, alpha=0.3)
        st.pyplot(fig2)

    st.divider()
    st.subheader("📍 Posición Global y Servos")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latitud", f"{last_row['lat']:.5f}")
    c2.metric("Longitud", f"{last_row['lon']:.5f}")
    c3.metric("Timón (PWM)", f"{last_row['servo_rudder']}")
    c4.metric("Vela (PWM)", f"{last_row['servo_sail']}")
    
    st.caption(f"Última actualización: {last_row['timestamp'].strftime('%H:%M:%S')}")

    # --- BUCLE DE AUTO-REFRESCO ---
    time.sleep(2)
    st.rerun()

else:
    st.info("Esperando datos... Comprueba que 'simulator.py' esté funcionando.")
    time.sleep(5)
    st.rerun()
