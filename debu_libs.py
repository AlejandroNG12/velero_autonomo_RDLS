import sys
print("--- Iniciando test de librerías ---")

try:
    import numpy
    print(f"✅ Numpy OK (Versión: {numpy.__version__})")
except Exception as e:
    print(f"❌ Error en Numpy: {e}")

try:
    import pandas
    print(f"✅ Pandas OK (Versión: {pandas.__version__})")
except Exception as e:
    print(f"❌ Error en Pandas: {e}")

try:
    import pyarrow
    print(f"✅ PyArrow OK (Versión: {pyarrow.__version__})")
except Exception as e:
    print(f"❌ Error en PyArrow: {e}")

print("--- Test finalizado ---")
