#!/usr/bin/env bash
# build_flash.sh — Compila y flashea firmware TinyML en ESP32-S3
# Ejecutar: ./build_flash.sh

set -e

# 1) Cargar entorno ESP-IDF
if [ -f /home/lenincoronel/esp/esp-idf/export.sh ]; then
    source /home/lenincoronel/esp/esp-idf/export.sh > /dev/null 2>&1
else
    echo "ERROR: ESP-IDF no encontrado en /home/lenincoronel/esp/esp-idf/"
    exit 1
fi

# 2) Verificar idf.py
if ! command -v idf.py &> /dev/null; then
    echo "ERROR: idf.py no esta en PATH. Revisa la instalacion de ESP-IDF."
    exit 1
fi

# 3) Compilar
echo "=== Compilando firmware ==="
cd /home/lenincoronel/Overall/BajoNivel/greenhouse_monitor
idf.py set-target esp32s3
idf.py build

# 4) Flashear (puerto /dev/ttyACM0)
echo ""
echo "=== Flasheando en /dev/ttyACM0 ==="
read -p "Conectar ESP32-S3 y presionar ENTER para continuar..." dummy
idf.py -p /dev/ttyACM0 flash

# 5) Monitor serial
echo ""
echo "=== Monitor serial (Ctrl+] para salir) ==="
read -p "Presionar ENTER para abrir monitor..." dummy
idf.py -p /dev/ttyACM0 monitor
