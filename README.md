# ⛵ SailBridge OS

Sistema de telemetría y control para velero autónomo basado en **Raspberry Pi 4** y **Pixhawk 6X**.

## 🏗️ Arquitectura
El sistema es modular y utiliza hilos independientes para asegurar la resiliencia:
- **Core**: Gestión de base de datos (SQLite), lectura de viento (NMEA2000) y telemetría (MAVLink).
- **UI**: Dashboard en tiempo real usando Streamlit y Matplotlib (optimizado para arquitecturas ARM sin PyArrow).
- **Networking**: Acceso remoto global mediante Tailscale VPN.

## 🚀 Instalación rápida
1. Clonar repositorio.
2. Crear venv con paquetes del sistema: 
   `python3 -m venv --system-site-packages venv`
3. Instalar dependencias: 
   `pip install streamlit pandas matplotlib pymavlink pyserial`

## 🛠️ Ejecución
1. **Sistema Central**: `python3 main.py`
2. **Dashboard**: `streamlit run ui/dashboard.py --server.address 0.0.0.0`
3. **Simulador (Opcional)**: `python3 simulator.py`
