# MEMORIA DEL PROYECTO — Invernadero Andino

## Descripción
Propuesta de sistema de control de clima para invernaderos andinos (2640 msnm, Bogotá) mediante modelos acoplados de cuatro variables (T, W, C, Et) y control predictivo con TinyML embebido en ESP32-S3.

## Archivos clave del proyecto

| Archivo | Propósito |
|---------|-----------|
| `poster_cientifico.html` | Poster científico HTML (Playwright → PDF) |
| `poster_vertical.html` | Copia sincronizada de `poster_cientifico.html` |
| `html_to_pdf.py` | Conversión HTML → PDF via Playwright/Chromium |
| `generate_poster_figures.py` | Genera figuras matplotlib (Okabe-Ito, 300 DPI) |
| `serial_bridge.py` | Bridge serial USB → HTTP JSON (puerto 8765) |
| `presentacion.html` | Dashboard web en tiempo real (monitor ESP32) |
| `simulation.py` | Modelo RK4 (4 EDOs, 7 días, Bogotá 2640 msnm) |
| `data_reader.py` | Captura CSV serial a archivo |
| `train_tinyml.py` | Entrena modelo TinyML sintético (Dense[3→32→16→1], 673 params) |
| `train_tinyml_real.py` | Entrena modelo TinyML con datos REALES Open-Meteo Bogotá 2024 (Dense[9→32→16→1], 865 params, RMSE 0.81°C) |
| `openmeteo_bogota_2024.json` | Dataset 8784 h horarios de T, HR, R en Bogotá (4.71°N, 74.07°W) |
| `guia_presentacion.html` | Guía de presentación (12 secciones, buscador + tags) |
| `comparison.py` | Comparación de datos |
| `poster_quality_agent.py` | QA del poster |
| `Inverno.md` | Propuesta de investigación original |
| `tinyml_model.npz` | Modelo TinyML REAL (865 params INT8, RMSE 0.81°C, Open-Meteo 2024) |

## Hardware
- MCU: XIAO ESP32S3 (240 MHz LX7 dual-core, 512 KB SRAM + 8 MB PSRAM)
- Sensores: AHT20 (±0.3°C, ±2% RH) + BMP280 (±1 hPa)
- Bus I²C: SCL + SDA @ 50 kHz, direcciones 0x38 (AHT20), 0x76 (BMP280)
- Salida serial: CSV 8 columnas @ 115200 baud, 5 s
- Bridge Python: serial_bridge.py → HTTP JSON API @ :8765

## Arquitectura del sistema
```
Sensores I²C → ESP32-S3 (firmware C) → Serial USB-CSV → Bridge Python HTTP → Dashboard web
                                                                               → Simulación RK4
                                                                               → Análisis Sobol
                                                                               → TinyML inference
```

## Stack tecnológico
- **Poster**: HTML + CSS → Playwright (Chromium) → PDF 500×870mm
- **Figuras**: matplotlib, Okabe-Ito colormap, 300 DPI, Times New Roman
- **TinyML**: scikit-learn (MLPRegressor), numpy, cuantización INT8 manual
- **Dashboard**: HTML + Chart.js + fetch al bridge local
- **Simulación**: numpy RK4, 4 EDOs acopladas, bandas Monte Carlo

## Decisiones arquitectónicas clave
1. Bridge Python corre en PC conectada por USB; ESP32 solo adquiere datos
2. TinyML predice T_ext como condición de borde para EDOs (no es controlador)
3. MPC y RL-Guided MPC declarados "pendiente de implementación embebida"
4. Modelo de CO₂ usa C_out sintético — sin sensor directo
5. P = 750 hPa teórica (aunque BMP280 mide ~767 hPa, +2.3%)
6. HR máxima limitada a 100% (condensación); no hay lógica W_sat

## Próximos pasos
- [ ] Validación ABA (12 semanas, piloto 200 m², lechuga)
- [ ] Migrar inferencia TinyML al ESP32-S3 (TFLite Micro)
- [ ] Implementar RL-Guided MPC en ESP32-S3
- [ ] Validar TinyML con datos de estación local (IDEAM o sensor propio)
