# Inverno — Sistema de Control Climático para Invernaderos Andinos

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.5.3-blue)](https://github.com/espressif/esp-idf)
[![Platform](https://img.shields.io/badge/platform-ESP32--S3-orange)](https://www.espressif.com/en/products/socs/esp32-s3)
[![TinyML](https://img.shields.io/badge/TinyML-INT8--bare--metal-green)](#m%C3%B3dulo-tinyml-embebido)
[![Status](https://img.shields.io/badge/status-prototype--validated-success)]()

> **Propuesta de sistema de control de clima para invernaderos andinos mediante modelos acoplados de cuatro variables y MPC guiado por RL, con módulo TinyML embebido en ESP32-S3.**

**Autor:** Lenin Yudain Coronel Pacheco — Ingeniería de Sistemas, Universidad Distrital Francisco José de Caldas (Bogotá D.C., Colombia).

---

## 1. Resumen

Este repositorio contiene los artefactos de la propuesta de investigación dirigida a invernaderos altoandinos (~2640 msnm, 750 hPa) y reúne:

| Componente | Estado | Artefacto |
|---|---|---|
| Modelo acoplado de 4 EDOs (T, W, C, Et) | Simulado, análisis Sobol + Monte Carlo N=10⁴ | `simulation.py` |
| RL-Guided MPC (H_p = 10 min) | Diseño, pendiente de portar a C | `main/` (futuro) |
| **Módulo TinyML embebido** | **Implementado y validado en ESP32-S3** | `main/tinyml_inference.c` |
| Bridge Python → PC → dashboard | Funcional, puerto 8765 | `serial_bridge.py` |
| Póster científico 500×870mm | Versión PDF + HTML + LaTeX | `poster_cientifico.pdf` |
| Guía de presentación interactiva | 12 secciones con búsqueda | `guia_presentacion.html` |

### Métricas clave (validadas en hardware real)

- **TinyML:** Dense[9→32→16→1], 865 parámetros INT8 per-channel, ~6.1 KB de pesos.
- **Datos de entrenamiento:** 8 781 horas reales de Open-Meteo Bogotá 2024 (T, HR, R).
- **Precisión fuera de muestra:** RMSE = 0.81 °C, MAE = 0.57 °C (float32 ≡ INT8).
- **Latencia de inferencia en ESP32-S3 (XIAO):** 223 ± 10 µs @ 240 MHz → ~4 500 inf/s.
- **Margen sobre el objetivo:** 450× (objetivo inicial = 100 ms).
- **Consumo del microcontrolador:** < 50 mW en inferencia continua.

---

## 2. Estructura del repositorio

```
Inverno/
├── README.md                       ← este archivo
├── LICENSE
│
├── poster_cientifico.html          ← póster principal (500×870mm, 1 página)
├── poster_cientifico.pdf           ← PDF generado con Playwright
├── poster_cientifico.tex           ← espejo LaTeX (tikzposter, A0 portrait)
├── html_to_pdf.py                  ← conversión HTML → PDF
├── generate_poster_figures.py      ← figuras matplotlib (Okabe-Ito, 300 DPI)
│
├── presentacion.html               ← dashboard web con pestaña TinyML
├── serial_bridge.py                ← puente USB→HTTP + inferencia TinyML
│
├── simulation.py                   ← modelo RK4 de 4 EDOs acopladas
├── comparison.py                   ← validación contra Open-Meteo
├── data_reader.py                  ← lector de CSV de sensores
│
├── train_tinyml_real.py            ← entrenamiento v2 con datos reales
├── export_tinyml_c.py              ← npz → header C para ESP32
├── tinyml_model.npz                ← modelo cuantizado (865 params)
├── openmeteo_bogota_2024.json      ← dataset de entrenamiento
│
├── main/                           ← firmware ESP-IDF bare-metal
│   ├── main.c                      ← loop principal + CSV 11 columnas
│   ├── tinyml_inference.c/.h       ← forward pass INT8 per-channel (137 LoC)
│   ├── tinyml_model_data.h         ← pesos y escalas (6.1 KB)
│   ├── aht20.c/.h                  ← driver temperatura/humedad
│   ├── bmp280.c/.h                 ← driver presión
│   ├── co2_model.c/.h              ← modelo de CO2 estimado
│   ├── ventilation.c/.h            ← actuador de ventilación
│   └── CMakeLists.txt
│
├── figures/                        ← figuras del póster (PDF + PNG)
│   ├── fig1_temp_hum.*             ← dinámica T y HR (3 altitudes)
│   ├── fig2_press_co2.*            ← presión y CO2 (3 altitudes)
│   ├── fig3_arch.svg               ← arquitectura ciber-físico
│   ├── fig4_sim.*                  ← simulación RK4 de 7 días
│   ├── fig5_tinyml_arch.svg        ← arquitectura TinyML
│   └── fig5_tinyml_plot.*          ← validación con datos reales
│
├── guia_presentacion.html          ← guía interactiva de 12 secciones
├── UDlogo.png                      ← logo Universidad Distrital
│
└── docs/                           ← documentos de soporte
    ├── Inverno.md                  ← paper en formato IEEE
    ├── TINYML_EMBEBIDO.md          ← bitácora del port TinyML→C→ESP32
    ├── MEMORIA_PROYECTO.md         ← contexto general del proyecto
    ├── MEMORIA_SESION.md           ← bitácora por sesión de trabajo
    └── MEMORIA_POSTER.md           ← estado y figuras del póster
```

---

## 3. Inicio rápido

### 3.1 Ver el póster y la guía (sin compilar nada)

```bash
# Póster (PDF)
xdg-open poster_cientifico.pdf

# Póster editable
$EDITOR poster_cientifico.html

# Regenerar PDF
python3 html_to_pdf.py
```

### 3.2 Reproducir el entrenamiento TinyML (requiere `numpy`, `scikit-learn`)

```bash
# 1) Descargar dataset (~315 KB) si no está presente
#    URL: archive-api.open-meteo.com → Bogotá 2024
python3 -c "
import urllib.request, json
url = ('https://archive-api.open-meteo.com/v1/archive'
       '?latitude=4.7110&longitude=-74.0721'
       '&start_date=2024-01-01&end_date=2024-12-31'
       '&hourly=temperature_2m,relative_humidity_2m,shortwave_radiation'
       '&timezone=America%2FBogota')
urllib.request.urlretrieve(url, 'openmeteo_bogota_2024.json')
"

# 2) Entrenar Dense[9→32→16→1] y exportar a C
python3 train_tinyml_real.py
python3 export_tinyml_c.py
```

### 3.3 Compilar y flashear el firmware (ESP-IDF v5.5.3)

```bash
source /path/to/esp-idf/export.sh
cd main && idf.py set-target esp32s3 && idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

> El binario resultante ocupa ~224 KB de la partición de aplicación. El log CSV de 11 columnas se envía por USB a 115200 baud cada 5 s.

### 3.4 Lanzar el dashboard y el bridge

```bash
# Terminal 1: bridge (lee USB, ejecuta TinyML, expone JSON en :8765)
python3 serial_bridge.py --port /dev/ttyACM0 --http-port 8765

# Terminal 2: dashboard
python3 -m http.server 8000
# Abrir http://localhost:8000/presentacion.html
```

---

## 4. Módulo TinyML embebido

| Aspecto | Valor |
|---|---|
| Arquitectura | `Dense[9→32→16→1]` con activación ReLU |
| Entradas | (T, HR, R) en t, t−1, t−2 (9 features lagged) |
| Parámetros | 865 (entrada 9×32+32 = 320 + 528 + 17) |
| Tamaño en flash | 6.1 KB (pesos + escalas per-channel) |
| Cuantización | INT8 per-channel (simulando TFLite Micro) |
| Datos de entrenamiento | 8 781 h Open-Meteo Bogotá 2024 |
| RMSE / MAE float32 | 0.81 °C / 0.57 °C (split 80/20 temporal) |
| RMSE / MAE INT8 | 0.81 °C / 0.57 °C (idéntico al float) |
| Latencia ESP32-S3 @ 240 MHz | 223.2 ± 9.8 µs (n = 18, 90 s) |
| Throughput efectivo | ~4 500 inferencias/s (1 CPU core) |
| Consumo de RAM | < 3 KB durante inferencia |
| Framework | C bare-metal propio (sin TFLite Micro) |

> El forward pass está implementado en `main/tinyml_inference.c` (137 líneas). Decidimos **no usar TFLite Micro** para evitar ~20 KB de runtime innecesarios dado que la arquitectura es fija.

Documentación detallada: [`docs/TINYML_EMBEBIDO.md`](docs/TINYML_EMBEBIDO.md).

---

## 5. Honestidad y limitaciones declaradas

- **El modelo NO está calibrado** contra datos medidos por nosotros en un invernadero real. Solo se simuló con datos meteorológicos públicos (Open-Meteo) y se comparó con ellos. La calibración con el piloto está planificada para una fase A-B-A posterior.
- **El RL-Guided MPC está diseñado** en simulación pero **no portado a C embebido** todavía. El firmware actual expone solo sensores y el módulo TinyML como pronóstico de condiciones de borde.
- **El CO₂ se modela con una regresión simple** a partir de T y HR, no con un sensor NDIR real. Esto es la principal limitación cuantitativa del modelo.
- **La HR máxima se limita a 100 %** en la simulación; el modelo simple no incluye la dinámica de saturación (W_sat) con lógica explícita de condensación.
- **El TinyML pronostica T_ext, no controla**: es una condición de borde que alimenta las EDOs, no forma parte del lazo de control.

---

## 6. Cómo citar

```bibtex
@techreport{coronel2026inverno,
  author  = {Coronel Pacheco, Lenin Yudain},
  title   = {Propuesta de sistema de control de clima para invernaderos
             andinos mediante modelos acoplados de cuatro variables
             y MPC guiado por RL, con módulo {TinyML} embebido en {ESP32-S3}},
  institution = {Universidad Distrital Francisco José de Caldas},
  year    = {2026},
  type    = {Propuesta de investigación},
  address = {Bogotá D.C., Colombia}
}
```

---

## 7. Licencia

Código fuente: **MIT License** (ver [`LICENSE`](LICENSE)).
Documentación y figuras: **CC-BY-4.0**.

---

## 8. Contacto

- **Autor:** Lenin Yudain Coronel Pacheco
- **Institución:** Universidad Distrital Francisco José de Caldas — Facultad de Ingeniería
- **Email:** lycoronelp@udistrital.edu.co
- **Repositorio:** https://github.com/02NIN20/Inverno
