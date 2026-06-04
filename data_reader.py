#!/usr/bin/env python3
"""
data_reader.py -- Captura datos CSV del puerto serial (XIAO ESP32S3)
Uso: python data_reader.py [--port /dev/ttyACM0] [--baud 115200] [--out datos_real.csv] [--duration 3600]
"""

import sys
import argparse
import csv
import time
import threading
from pathlib import Path

sys.path.insert(0, "/home/lenincoronel/.local/share/pipx/venvs/pyserial/lib/python3.14/site-packages")
import serial


def main():
    parser = argparse.ArgumentParser(description="Captura datos serial del invernadero")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Puerto serial")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate")
    parser.add_argument("--out", default="datos_real.csv", help="Archivo de salida")
    parser.add_argument("--duration", type=float, default=0,
                        help="Duracion en segundos (0 = infinito)")
    parser.add_argument("--skip-lines", type=int, default=0,
                        help="Lineas de boot a ignorar")
    args = parser.parse_args()

    print(f"[*] Conectando a {args.port} @ {args.baud} baud...")
    try:
        ser = serial.Serial(args.port, args.baud, timeout=2)
    except serial.SerialException as e:
        print(f"[!] Error abriendo puerto: {e}")
        sys.exit(1)

    print(f"[*] Guardando en {args.out}")
    out_path = Path(args.out)
    header_written = out_path.exists()

    f = open(args.out, "a", newline="")
    writer = csv.writer(f)

    start_time = time.time()
    line_count = 0
    data_started = False

    def check_duration():
        if args.duration > 0 and time.time() - start_time >= args.duration:
            print("\n[*] Duracion alcanzada. Cerrando...")
            ser.close()
            f.close()
            sys.exit(0)

    print("[*] Esperando datos (Ctrl+C para detener)...")

    try:
        while True:
            line = ser.readline()
            if not line:
                check_duration()
                continue

            decoded = line.decode("utf-8", errors="replace").strip()

            if not data_started:
                if decoded.startswith("uptime_s") or decoded.startswith("timestamp"):
                    data_started = True
                    if not header_written:
                        writer.writerow(decoded.split(","))
                        header_written = True
                    print(f"[+] Cabecera: {decoded}")
                    f.flush()
                    continue
                if args.skip_lines > 0:
                    args.skip_lines -= 1
                    continue
                if "uptime_s" in decoded or "I2C" in decoded or "AHT20" in decoded or "BMP280" in decoded or "MAIN" in decoded:
                    print(f"    {decoded}")
                    continue
                continue

            if "," not in decoded:
                continue

            parts = decoded.split(",")
            if len(parts) < 5:
                continue

            writer.writerow(parts)
            line_count += 1
            if line_count % 10 == 0:
                f.flush()
                elapsed = time.time() - start_time
                print(f"    [{elapsed:.0f}s] {line_count} muestras | {decoded[:80]}...")

            check_duration()

    except KeyboardInterrupt:
        print("\n[*] Interrumpido por usuario")
    finally:
        ser.close()
        f.close()
        print(f"[*] {line_count} muestras guardadas en {args.out}")


if __name__ == "__main__":
    main()
