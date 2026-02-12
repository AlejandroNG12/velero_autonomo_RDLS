#!/usr/bin/env python3
import time
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# -------------------------------------------------------------------
# RUTA A LA BD (la misma que en build_telemetry_table.py)
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "telemetria.db"


# -------------------------------------------------------------------
# UTILIDAD: LEER DE telemetry_samples
# -------------------------------------------------------------------

def fetch_telemetry_samples(hours: float | None = None, limit: int = 1000):
    """
    Devuelve una lista de diccionarios con muestras combinadas de:
    - GPS (lat, lon, alt, sog, hdg)
    - Viento (wind_speed_kn, wind_dir_deg)
    - Actitud (roll_deg, pitch_deg, yaw_deg)

    leyendo de telemetry_samples.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if hours is not None:
        ts_min = time.time() - hours * 3600.0
        cur.execute(
            """
            SELECT
                timestamp_utc,
                timestamp_text,
                lat_deg,
                lon_deg,
                alt_msl_m,
                sog_kn,
                hdg_deg,
                wind_speed_ms,
                wind_speed_kn,
                wind_dir_deg,
                wind_vertical,
                roll_deg,
                pitch_deg,
                yaw_deg
            FROM telemetry_samples
            WHERE timestamp_utc >= ?
            ORDER BY timestamp_utc ASC
            LIMIT ?;
            """,
            (ts_min, limit),
        )
    else:
        cur.execute(
            """
            SELECT
                timestamp_utc,
                timestamp_text,
                lat_deg,
                lon_deg,
                alt_msl_m,
                sog_kn,
                hdg_deg,
                wind_speed_ms,
                wind_speed_kn,
                wind_dir_deg,
                wind_vertical,
                roll_deg,
                pitch_deg,
                yaw_deg
            FROM telemetry_samples
            ORDER BY timestamp_utc ASC
            LIMIT ?;
            """,
            (limit,),
        )

    rows = cur.fetchall()
    conn.close()

    data = []
    for (
        ts_utc,
        ts_text,
        lat,
        lon,
        alt,
        sog_kn,
        hdg_deg,
        wind_ms,
        wind_kn,
        wind_dir_deg,
        wind_vertical,
        roll_deg,
        pitch_deg,
        yaw_deg,
    ) in rows:
        # timestamp ISO
        try:
            ts_iso = datetime.fromtimestamp(ts_utc).isoformat(sep=" ")
        except Exception:
            ts_iso = ts_text or ""

        data.append(
            {
                "timestamp_utc": ts_utc,
                "timestamp_iso": ts_iso,
                "lat_deg": lat,
                "lon_deg": lon,
                "alt_msl_m": alt,
                "sog_kn": sog_kn,
                "hdg_deg": hdg_deg,
                "wind_speed_ms": wind_ms,
                "wind_speed_kn": wind_kn,
                "wind_dir_deg": wind_dir_deg,
                "wind_vertical": wind_vertical,
                "roll_deg": roll_deg,
                "pitch_deg": pitch_deg,
                "yaw_deg": yaw_deg,
            }
        )

    return data


# -------------------------------------------------------------------
# RUTA API (JSON)
# -------------------------------------------------------------------

@app.route("/api/telemetry")
def api_telemetry():
    """
    Devuelve la telemetria combinada (GPS + viento + actitud) desde telemetry_samples.

    Parametro opcional:
      - hours: ultimas N horas (float)
    """
    hours_str = request.args.get("hours")
    hours = float(hours_str) if hours_str not in (None, "") else None

    data = fetch_telemetry_samples(hours=hours)
    return jsonify(data)


# -------------------------------------------------------------------
# PAGINA PRINCIPAL (HTML + JS con Chart.js)
# -------------------------------------------------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Velero autonomo - Telemetria</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0b1020;
      color: #f4f4f4;
      margin: 0;
      padding: 0;
    }
    header {
      padding: 1rem 1.5rem;
      background: #131a33;
      border-bottom: 1px solid #222a4a;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    header h1 {
      font-size: 1.2rem;
      margin: 0;
    }
    .container {
      padding: 1rem 1.5rem 2rem;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .card {
      background: #151b36;
      border-radius: 8px;
      padding: 0.75rem 1rem;
      border: 1px solid #20284a;
    }
    .card h2 {
      font-size: 0.9rem;
      margin: 0 0 0.5rem;
      color: #b0b8ff;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .metric {
      font-size: 1.3rem;
      font-weight: 600;
    }
    .metric-sub {
      font-size: 0.85rem;
      opacity: 0.8;
    }
    .charts {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.5rem;
    }
    .chart-card {
      background: #151b36;
      border-radius: 8px;
      padding: 0.75rem 1rem 1rem;
      border: 1px solid #20284a;
      height: 600px; /* altura fija */
    }
    .chart-card canvas {
      width: 100% !important;
      height: 200px !important; /* altura fija del canvas */
      display: block;
    }
    footer {
      text-align: center;
      font-size: 0.75rem;
      color: #8088aa;
      padding: 0.75rem;
      border-top: 1px solid #20284a;
      background: #101528;
    }
    select {
      background: #1b2342;
      color: #f4f4f4;
      border-radius: 4px;
      border: 1px solid #283255;
      padding: 0.25rem 0.5rem;
      font-size: 0.85rem;
    }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <header>
    <h1>? Velero autonomo - Telemetria</h1>
    <div>
      <label for="hoursSelect">Rango:</label>
      <select id="hoursSelect">
        <option value="1">Ultima 1 hora</option>
        <option value="6">Ultimas 6 horas</option>
        <option value="24">Ultimas 24 horas</option>
        <option value="" selected>Todo</option>
      </select>
    </div>
  </header>

  <div class="container">
    <div class="cards">
      <div class="card">
        <h2>Posicion</h2>
        <div class="metric" id="posMetric">-</div>
        <div class="metric-sub" id="altMetric">Altitud: -</div>
      </div>
      <div class="card">
        <h2>Movimiento</h2>
        <div class="metric" id="sogMetric">SOG: -</div>
        <div class="metric-sub" id="cogMetric">COG: -</div>
      </div>
      <div class="card">
        <h2>Viento</h2>
        <div class="metric" id="windSpdMetric">-</div>
        <div class="metric-sub" id="windDirMetric">Direccion: -</div>
      </div>
    </div>

    <div class="charts">
      <div class="chart-card">
        <h3>Velocidad y rumbo (tiempo)</h3>
        <canvas id="gpsChart"></canvas>
      </div>
      <div class="chart-card">
        <h3>Viento (tiempo)</h3>
        <canvas id="windChart"></canvas>
      </div>
    </div>
  </div>

  <footer>
    Datos combinados desde telemetry_samples (GPS + viento + actitud).
  </footer>

  <script>
    const hoursSelect = document.getElementById("hoursSelect");
    let gpsChart = null;
    let windChart = null;

    async function fetchJson(url) {
      const res = await fetch(url);
      if (!res.ok) throw new Error("Error al cargar " + url);
      return await res.json();
    }

    function updateCards(telemetryData) {
      const posMetric = document.getElementById("posMetric");
      const altMetric = document.getElementById("altMetric");
      const sogMetric = document.getElementById("sogMetric");
      const cogMetric = document.getElementById("cogMetric");
      const windSpdMetric = document.getElementById("windSpdMetric");
      const windDirMetric = document.getElementById("windDirMetric");

      if (telemetryData.length > 0) {
        const last = telemetryData[telemetryData.length - 1];

        // Posicion
        if (last.lat_deg != null && last.lon_deg != null) {
          posMetric.textContent = `${last.lat_deg.toFixed(5)}, ${last.lon_deg.toFixed(5)}`;
        } else {
          posMetric.textContent = "Sin datos";
        }

        if (last.alt_msl_m != null) {
          altMetric.textContent = `Altitud: ${last.alt_msl_m.toFixed(1)} m`;
        } else {
          altMetric.textContent = "Altitud: N/D";
        }

        // Movimiento
        if (last.sog_kn != null) {
          sogMetric.textContent = `SOG: ${last.sog_kn.toFixed(2)} kn`;
        } else {
          sogMetric.textContent = "SOG: N/D";
        }

        if (last.hdg_deg != null) {
          cogMetric.textContent = `COG: ${last.hdg_deg.toFixed(1)}º`;
        } else {
          cogMetric.textContent = "COG: N/D";
        }

        // Viento
        if (last.wind_speed_kn != null) {
          windSpdMetric.textContent = `${last.wind_speed_kn.toFixed(1)} kn`;
        } else {
          windSpdMetric.textContent = "-";
        }

        if (last.wind_dir_deg != null) {
          windDirMetric.textContent = `Direccion: ${last.wind_dir_deg.toFixed(0)}º`;
        } else {
          windDirMetric.textContent = "Direccion: N/D";
        }

      } else {
        posMetric.textContent = "Sin datos";
        altMetric.textContent = "Altitud: -";
        sogMetric.textContent = "SOG: -";
        cogMetric.textContent = "COG: -";
        windSpdMetric.textContent = "-";
        windDirMetric.textContent = "Direccion: -";
      }
    }

    function updateCharts(telemetryData) {
      const gpsCtx = document.getElementById("gpsChart").getContext("2d");
      const windCtx = document.getElementById("windChart").getContext("2d");

      const labels = telemetryData.map(d => d.timestamp_iso);
      const sogSeries = telemetryData.map(d => d.sog_kn);
      const cogSeries = telemetryData.map(d => d.hdg_deg);

      const windSpdSeries = telemetryData.map(d => d.wind_speed_kn);
      const windDirSeries = telemetryData.map(d => d.wind_dir_deg);

      // Crear / actualizar grafico GPS
      if (!gpsChart) {
        gpsChart = new Chart(gpsCtx, {
          type: "line",
          data: {
            labels: labels,
            datasets: [
              {
                label: "SOG (kn)",
                data: sogSeries,
                borderWidth: 1.5,
              },
              {
                label: "COG (º)",
                data: cogSeries,
                borderWidth: 1.5,
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
          }
        });
      } else {
        gpsChart.data.labels = labels;
        gpsChart.data.datasets[0].data = sogSeries;
        gpsChart.data.datasets[1].data = cogSeries;
        gpsChart.update();
      }

      // Crear / actualizar grafico viento
      if (!windChart) {
        windChart = new Chart(windCtx, {
          type: "line",
          data: {
            labels: labels,
            datasets: [
              {
                label: "Viento (kn)",
                data: windSpdSeries,
                borderWidth: 1.5,
              },
              {
                label: "Direccion (º)",
                data: windDirSeries,
                borderWidth: 1.5,
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
          }
        });
      } else {
        windChart.data.labels = labels;
        windChart.data.datasets[0].data = windSpdSeries;
        windChart.data.datasets[1].data = windDirSeries;
        windChart.update();
      }
    }

    async function cargarDatosYActualizar() {
      try {
        const hoursValue = hoursSelect.value;
        const hoursParam = hoursValue ? `?hours=${hoursValue}` : "";

        const telemetryData = await fetchJson("/api/telemetry" + hoursParam);

        updateCards(telemetryData);
        updateCharts(telemetryData);
      } catch (err) {
        console.error("Error cargando datos:", err);
      }
    }

    hoursSelect.addEventListener("change", () => {
      cargarDatosYActualizar();
    });

    // Cargar al entrar
    cargarDatosYActualizar();
    // Refrescar cada 30 s
    setInterval(cargarDatosYActualizar, 30000);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


# -------------------------------------------------------------------
# EJECUCION
# -------------------------------------------------------------------

if __name__ == "__main__":
    # Escuchar en todas las interfaces, puerto 8501
    app.run(host="0.0.0.0", port=8501, debug=False)
