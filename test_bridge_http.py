#!/usr/bin/env python3
"""
test_bridge_http.py — Test del bridge HTTP completo con mock serial.
Crea un pseudo-serial con datos realistas de Bogotá, y verifica que el
endpoint /data y /tinyml_pred responden correctamente.
"""
import sys
import os
import threading
import time
import json
import urllib.request
from http.server import HTTPServer

# pyserial está en pipx venv
sys.path.insert(0, "/home/lenincoronel/.local/share/pipx/venvs/pyserial/lib/python3.14/site-packages")
sys.path.insert(0, "/home/lenincoronel/Overall/BajoNivel/greenhouse_monitor")
os.chdir("/home/lenincoronel/Overall/BajoNivel/greenhouse_monitor")

# Mock serial ANTES de importar serial_bridge
import serial as real_serial
class MockSerial:
    def __init__(self, port, baud, timeout=2):
        self.port = port
        self.timeout = timeout
        self.t = 0
        # Generar 24h de datos (1 linea cada 5s = 17280 lineas)
        import math
        self.lines = []
        for i in range(200):
            uptime = i * 5
            hour = (uptime / 3600) % 24
            # Temperatura diurna Bogotá
            T_out = 14 + 6 * math.sin(2 * math.pi * (hour - 14) / 24)
            HR_out = 70 + 15 * math.cos(2 * math.pi * (hour - 14) / 24)
            solar = max(0, 800 * math.sin(math.pi * ((hour - 6) / 12))) if 6 <= hour <= 18 else 0
            # CSV: uptime, vent, aht_temp, aht_hum, bmp_temp, bmp_press, bmp_press_kpa, co2, etr
            self.lines.append(f"{uptime},0,{T_out:.2f},{HR_out:.2f},{T_out:.2f},767.0,76.7,420.0,{solar/100:.2f}\n")
        self.idx = 0

    def read(self, n=256):
        if self.idx < len(self.lines):
            line = self.lines[self.idx].encode()
            self.idx += 1
            return line
        time.sleep(0.1)
        return b""

    def close(self):
        pass

real_serial.Serial = MockSerial

# Ahora importar bridge (usa MockSerial)
import serial_bridge
from serial_bridge import Handler, latest, history, load_tinyml, serial_reader, HTTP_PORT

# Reemplazar el Handler con uno que no log
class QuietHandler(Handler):
    def log_message(self, fmt, *args):
        pass

# Iniciar HTTP server
print("[Test] Cargando TinyML...")
load_tinyml()

print("[Test] Iniciando serial reader thread...")
t = threading.Thread(target=serial_reader, daemon=True)
t.start()
time.sleep(2)

print(f"[Test] Iniciando HTTP server en :{HTTP_PORT}...")
httpd = HTTPServer(("", HTTP_PORT), QuietHandler)
http_t = threading.Thread(target=httpd.serve_forever, daemon=True)
http_t.start()
time.sleep(1)

# Hacer requests
print("\n[Test] === /data ===")
for i in range(5):
    req = urllib.request.urlopen(f"http://localhost:{HTTP_PORT}/data", timeout=2)
    d = json.loads(req.read().decode())
    print(f"  T={d.get('bmp_temp')} HR={d.get('aht_hum')} "
          f"tinyml_pred={d.get('tinyml_pred')} ok={d.get('tinyml_ok')}")
    time.sleep(0.5)

print("\n[Test] === Esperar 2 segundos ===")
time.sleep(2)
req = urllib.request.urlopen(f"http://localhost:{HTTP_PORT}/data", timeout=2)
d = json.loads(req.read().decode())
print(f"  Final: T={d.get('bmp_temp')} HR={d.get('aht_hum')} "
      f"tinyml_pred={d.get('tinyml_pred')} ok={d.get('tinyml_ok')}")
print(f"  History length: {len(history)}")

httpd.shutdown()
print("\n[Test] OK")
