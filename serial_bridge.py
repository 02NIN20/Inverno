#!/usr/bin/env python3
"""
serial_bridge.py -- Lee datos del ESP32 por serial y los sirve via HTTP (JSON)
Incluye inferencia TinyML para predicción de T_ext.
Ejecutar: python3 serial_bridge.py
Luego abre presentacion.html en el navegador.
"""

import sys
import json
import time
import threading
import numpy as np
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, "/home/lenincoronel/.local/share/pipx/venvs/pyserial/lib/python3.14/site-packages")
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200
HTTP_PORT = 8765

# ─── TinyML model ───
tinyml_model = None

def load_tinyml():
    global tinyml_model
    try:
        data = np.load("tinyml_model.npz")
        tinyml_model = {
            "w0": data["w0"], "w1": data["w1"], "w2": data["w2"],
            "b0": data["b0"], "b1": data["b1"], "b2": data["b2"],
            "sw0": data["sw0"], "sw1": data["sw1"], "sw2": data["sw2"],
            "sb0": data["sb0"], "sb1": data["sb1"], "sb2": data["sb2"],
            "x_mean": data["x_mean"], "x_std": data["x_std"],
            "y_mean": data["y_mean"], "y_std": data["y_std"],
        }
        total = data['w0'].size + data['b0'].size + data['w1'].size + data['b1'].size + data['w2'].size + data['b2'].size
        arch = "Dense[9->32->16->1] INT8" if data['w0'].shape[0] == 9 else f"Dense[{data['w0'].shape[0]}->{data['w0'].shape[1]}->...->1] INT8"
        print(f"[tinyml] Modelo cargado: {total} params ({arch})")
        return True
    except Exception as e:
        print(f"[tinyml] No se pudo cargar: {e}")
        return False

# Predict T_ext from (text, hr_ext, solar_rad)
# Modelo real: 9 entradas = (T, HR, R) en t, t-1, t-2
# Requiere mantener historial corto de (T, HR, R)
X_MAX = 4.0
x_scale = X_MAX / 127.0
_tinyml_history = []  # cola de (T, HR, R) de las ultimas 3 lecturas

def tinyml_predict(text, hr_ext, solar_rad):
    if tinyml_model is None:
        return None, None
    try:
        m = tinyml_model
        # Mantener historial de 3 lecturas para lags t, t-1, t-2
        global _tinyml_history
        _tinyml_history.append((text, hr_ext, solar_rad))
        if len(_tinyml_history) > 3:
            _tinyml_history = _tinyml_history[-3:]
        if len(_tinyml_history) < 3:
            return None, None  # esperar a tener 3 muestras

        # Construir vector de 9 features: lags 0, 1, 2
        # x[0..2] = (T,HR,R) en t, x[3..5] = en t-1, x[6..8] = en t-2
        x = np.zeros(9, dtype=np.float64)
        for lag, (t, h, r) in enumerate(reversed(_tinyml_history)):
            x[lag*3 + 0] = t
            x[lag*3 + 1] = h
            x[lag*3 + 2] = r

        # Normalizar
        xn = (x - m["x_mean"]) / m["x_std"]
        xn = np.clip(xn, -X_MAX, X_MAX)
        xq = (np.clip(np.round(xn / x_scale), -128, 127) * x_scale).astype(np.float64)

        # Forward INT8 per-channel
        # Capa 1: w0 shape (9, 32), per-output scale (32,)
        w0 = m["w0"].astype(np.float64) * m["sw0"][None, :]
        h1 = np.dot(xq, w0) + m["b0"].astype(np.float64) * float(m["sb0"])
        h1 = np.maximum(0, h1)
        h1_max = max(np.max(np.abs(h1)), 1e-8)
        h1_scale = h1_max / 127.0
        h1q = np.clip(np.round(h1 / h1_scale), -128, 127) * h1_scale

        # Capa 2
        w1 = m["w1"].astype(np.float64) * m["sw1"][None, :]
        h2 = np.dot(h1q, w1) + m["b1"].astype(np.float64) * float(m["sb1"])
        h2 = np.maximum(0, h2)
        h2_max = max(np.max(np.abs(h2)), 1e-8)
        h2_scale = h2_max / 127.0
        h2q = np.clip(np.round(h2 / h2_scale), -128, 127) * h2_scale

        # Capa 3
        out = np.dot(h2q, m["w2"].flatten().astype(np.float64) * m["sw2"]) + m["b2"].astype(np.float64) * float(m["sb2"])
        t_pred = float(out[0] * float(m["y_std"]) + float(m["y_mean"]))
        return t_pred, float(h1[0])
    except Exception as e:
        print(f"[tinyml] Error inferencia: {e}")
        return None, None

# Datos compartidos (thread-safe via GIL para escrituras atomicas de dict)
latest = {
    "uptime": 0, "vent": 0, "aht_temp": None, "aht_hum": None,
    "bmp_temp": None, "bmp_press": None, "bmp_press_kpa": None,
    "co2": None, "etr": None, "timestamp": "",
    "connected": False, "aht_ok": False, "bmp_ok": False,
    "tinyml_pred": None, "tinyml_ok": False,
}

history = []
MAX_HISTORY = 720  # 1 hora a 5s


def serial_reader():
    global latest
    print(f"[bridge] Conectando a {PORT} @ {BAUD}...")
    while True:
        try:
            ser = serial.Serial(PORT, BAUD, timeout=2)
            latest["connected"] = True
            print(f"[bridge] Conectado. Esperando datos...")
            break
        except Exception as e:
            print(f"[bridge] Esperando puerto... ({e})")
            time.sleep(2)

    buffer = ""
    while True:
        try:
            chunk = ser.read(256)
            if chunk:
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line or not "," in line:
                        continue
                    parts = line.split(",")
                    if len(parts) < 9:
                        continue
                    try:
                        latest["uptime"] = float(parts[0])
                        latest["vent"] = int(parts[1])
                        latest["aht_temp"] = float(parts[2]) if parts[2] != "nan" else None
                        latest["aht_hum"] = float(parts[3]) if parts[3] != "nan" else None
                        latest["bmp_temp"] = float(parts[4]) if parts[4] != "nan" else None
                        latest["bmp_press"] = float(parts[5]) if parts[5] != "nan" else None
                        latest["bmp_press_kpa"] = float(parts[6]) if parts[6] != "nan" else None
                        latest["co2"] = float(parts[7]) if parts[7] != "nan" else None
                        latest["etr"] = float(parts[8]) if parts[8] != "nan" else None
                        latest["aht_ok"] = latest["aht_temp"] is not None
                        latest["bmp_ok"] = latest["bmp_temp"] is not None
                        latest["timestamp"] = time.strftime("%H:%M:%S")

                        # TinyML inference (HourOfDay for solar proxy, HR_ext from AHT)
                        if latest["aht_temp"] is not None and latest["bmp_temp"] is not None:
                            hour = (latest["uptime"] / 3600) % 24
                            solar_proxy = 800 * np.sin(np.pi * ((hour - 6) / 12)) if 6 <= hour <= 18 else 0
                            solar_proxy = max(0, solar_proxy)
                            t_pred, _ = tinyml_predict(latest["bmp_temp"], latest["aht_hum"] or 70, solar_proxy)
                            latest["tinyml_pred"] = t_pred
                            latest["tinyml_ok"] = t_pred is not None

                        history.append(dict(latest))
                        if len(history) > MAX_HISTORY:
                            history.pop(0)
                    except (ValueError, IndexError):
                        pass
        except Exception as e:
            print(f"[bridge] Error serial: {e}")
            latest["connected"] = False
            try: ser.close()
            except: pass
            time.sleep(2)
            while True:
                try:
                    ser = serial.Serial(PORT, BAUD, timeout=2)
                    latest["connected"] = True
                    print(f"[bridge] Reconectado.")
                    break
                except:
                    time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(latest).encode())
        elif self.path == "/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(history[-360:]).encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "connected": latest["connected"]}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK - /data /history /health")

    def log_message(self, format, *args):
        pass


def main():
    print(f"[bridge] Iniciando puente serial-HTTP en http://localhost:{HTTP_PORT}")
    load_tinyml()
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    print(f"[bridge] Endpoints:")
    print(f"  http://localhost:{HTTP_PORT}/data    - ultima lectura")
    print(f"  http://localhost:{HTTP_PORT}/history - historico reciente")
    print(f"  http://localhost:{HTTP_PORT}/health  - estado")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bridge] Detenido.")


if __name__ == "__main__":
    main()
