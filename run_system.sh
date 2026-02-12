#!/bin/bash

echo "⛵ Arrancando SailBridge OS..."

# 1. Cargar el entorno virtual
source venv/bin/activate

# 2. Lanzar el Núcleo (Viento + MAVLink) en segundo plano
# Redirigimos la salida a un log para que no ensucie la pantalla
python3 main.py > logs_sistema.txt 2>&1 &
MAIN_PID=$!
echo "✅ Núcleo iniciado (PID: $MAIN_PID). Guardando logs en logs_sistema.txt"

# 3. Lanzar el Simulador si quieres datos inmediatos (opcional)
# python3 simulator.py > /dev/null 2>&1 &

# 4. Lanzar el Dashboard de Streamlit
echo "📊 Abriendo Dashboard..."
OPENBLAS_CORETYPE=ARMV8 streamlit run ui/dashboard.py --server.address 0.0.0.0

# Al cerrar el Dashboard (Ctrl+C), el script matará el proceso del Núcleo
trap "kill $MAIN_PID" EXIT
