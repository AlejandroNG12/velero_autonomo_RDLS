# ⛵ SailBridge OS v1.0

**SailBridge OS** es un sistema de telemetría y monitorización en tiempo real para veleros autónomos. Está diseñado para ejecutarse en una **Raspberry Pi 4** (Debian Trixie) y actuar como puente de datos entre una controladora de vuelo **Pixhawk 6X**, sensores de viento NMEA2000 y una interfaz de usuario remota.

## 🏗️ Arquitectura del Sistema

El sistema utiliza una arquitectura modular basada en hilos (*multithreading*) para garantizar la resiliencia: si un sensor falla, el resto del sistema continúa operando.

### Componentes Core

- **`main.py`**: El orquestador principal. Inicia y supervisa los hilos de ejecución.
- **`core/database.py`**: Gestión de persistencia en **SQLite**. Centraliza el almacenamiento de datos de viento, GPS, actitud (roll/pitch/yaw) y estado de los servos.
- **`core/wind_manager.py`**: Procesa datos de viento NMEA2000 (PGN 130306) y los reenvía a la Pixhawk.
- **`core/mavlink_manager.py`**: Enlace con la Pixhawk mediante protocolo MAVLink para capturar telemetría crítica.
- **`config.py`**: Archivo centralizado de configuración (puertos serie, baudios y rutas).

### Interfaz de Usuario (UI)

- **`ui/dashboard.py`**: Panel de control visual desarrollado con **Streamlit**.
    - **Optimización ARM**: Diseñado para evitar errores de `Illegal Instruction` mediante el uso de **Matplotlib** en lugar de motores de renderizado pesados (No-Arrow architecture).
    - **Live Refresh**: Actualización automática de datos cada 2 segundos.
    - **Ejes Temporales**: Gráficas de evolución con marca de tiempo (HH:MM:SS).

## 🌐 Conectividad Remota

El acceso al dashboard se realiza a través de **Tailscale**. Esto permite:

1. Acceder al sistema desde cualquier lugar del mundo (móvil o PC).
2. Seguridad mediante cifrado punto a punto sin necesidad de abrir puertos en el router del puerto o usar IP pública.
3. IP fija interna (rango 100.x.x.x) para facilitar el acceso al servidor de Streamlit.

## 🚀 Instalación y Configuración

### 1. Requisitos de Sistema

Es necesario tener instalado Python 3.11+ y las librerías de desarrollo de la Raspberry:

```
sudo apt update
sudo apt install python3-numpy python3-pandas python3-matplotlib -y
```

### 2. Preparación del Entorno (VENV)

Para evitar conflictos de arquitectura en Raspberry Pi, creamos un entorno virtual que hereda los paquetes optimizados del sistema:

```
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install streamlit pymavlink pyserial
```

### 3. Configuración de Hardware

Edita el archivo `config.py` para asignar los puertos serie correctos (`/dev/ttyUSB0`, `/dev/ttyAMA0`, etc.) según tu conexión física.

## 🛠️ Guía de Uso

### Modo Real (En el barco)

Utiliza el script lanzador para iniciar todos los servicios de forma automática:

```
chmod +x run_system.sh
./run_system.sh
```

### Modo Simulación (En casa)

Si quieres probar la interfaz sin sensores conectados, lanza el simulador en una terminal aparte:

```
python3 simulator.py
```

### Monitorización de Logs

El núcleo del sistema guarda logs detallados en `logs_sistema.txt`. Puedes ver la actividad de los hilos con:

```
tail -f logs_sistema.txt
```

## ⚓ Notas de Ingeniería (Troubleshooting)

- **Error `Illegal Instruction`**: Resuelto eliminando la dependencia de `pyarrow`.
- **Acceso Externo**: El servidor se inicia en `0.0.0.0` para permitir conexiones desde la interfaz de red de Tailscale.
- **Base de Datos**: Se utiliza SQLite por su ligereza y resistencia a cortes de energía accidentales en el barco.

**Desarrollado como proyecto de telemetría para sistemas autónomos marítimos.**
