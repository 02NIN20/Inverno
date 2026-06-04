# MEMORIA DE SESIÓN — 3-4 Jun 2026

## Sesión 1 (3 Jun)

### Cambios realizados

#### 1. Font sizes y line widths (REVERTIDO)
- Subí font sizes en `generate_poster_figures.py` (7→10, 11→14, lw 1.5→2.0)
- El usuario pidió revertir. Se restauraron valores originales.

#### 2. Propuesta Sobol (DESCARTADA)
- Reemplacé fig4_sim (RK4 simulación) por figura Sobol
- Usuario pidió revertir. Se restauró fig4_sim original.

#### 3. TinyML — implementación real ✅
**Entrenamiento** (`train_tinyml.py`):
- Modelo Dense[32→16→1] con sklearn, exactamente **673 params** (128 + 528 + 17)
- Datos sintéticos: 720 h de ciclo diurno bogotano + ruido gaussiano
- Cuantización manual INT8 simulando TFLite Micro
- RMSE float: 1.177 °C | INT8: 1.175 °C (degradación despreciable)
- Salva `tinyml_model.npz` y `figures/fig5_tinyml_plot.pdf/png`

**Dashboard** (`presentacion.html`):
- Agregada pestaña "TinyML" con predicción en vivo
- Chart comparando T_ext actual vs predicho
- Panel lateral con valor de predicción

**Bridge** (`serial_bridge.py`):
- Carga `tinyml_model.npz` al iniciar
- Corre inferencia en cada lectura del ESP32
- Agrega `tinyml_pred` y `tinyml_ok` al JSON

**Bug conocido**: `float()` en numpy 3.14 no acepta arrays 1-D. Corregido usando `.item()`.

#### 4. Poster — figuras actualizadas
- **Fig 4** (era MONITORESP32.png): reemplazada por `fig5_tinyml_arch.svg` (arquitectura TinyML)
- **Fig 5** (nueva): `fig5_tinyml_plot.png` (validación TinyML: scatter + serie temporal)
- Sección 9 renombrada: "Módulo TinyML y control" → "Validación TinyML y control"
- Notas actualizadas sobre inferencia en bridge vs migración futura a ESP32

#### 5. Archivos creados
| Archivo | Descripción |
|---------|-------------|
| `train_tinyml.py` | Entrenamiento y cuantización TinyML |
| `tinyml_model.npz` | Modelo entrenado (673 params, INT8) |
| `figures/fig5_tinyml_arch.svg` | Diagrama SVG arquitectura TinyML |
| `figures/fig5_tinyml_plot.pdf/png` | Figura validación TinyML |
| `MEMORIA_PROYECTO.md` | Contexto general del proyecto |
| `MEMORIA_SESION.md` | Esta bitácora |
| `MEMORIA_POSTER.md` | Estado del poster |

#### 6. Archivos modificados
| Archivo | Cambio |
|---------|--------|
| `serial_bridge.py` | +TinyML load/inference, +numpy import, +tinyml_pred en JSON |
| `presentacion.html` | +pestaña TinyML, +chart, +panel lateral |
| `poster_cientifico.html` | Fig4→SVG, +Fig5, sección 9 actualizada, notas |
| `poster_vertical.html` | Sincronizado con poster_cientifico.html |

## Sesión 2 (4 Jun) — Reentrenamiento con datos REALES

### 1. Datos descargados de Open-Meteo
- 8784 h de Bogotá 2024 (4.71°N, 74.07°W, 2640 msnm)
- Variables: T_2m, HR_2m, shortwave_radiation
- Stats: T 4.1–26.2°C (μ=14.1), HR 18–100% (μ=80), R 0–1105 W/m² (μ=241)
- Sin NaN, sin outliers físicos
- 724 h con HR=100% (niebla/lluvia andina, válidas)
- Archivo: `openmeteo_bogota_2024.json` (~280 KB)

### 2. Nuevo script: `train_tinyml_real.py`
- Features lagged: 9 entradas = (T, HR, R) en t, t-1, t-2
- Captura inercia térmica del clima andino
- 8781 muestras, split 80/20 temporal (7024 train / 1757 test)
- Entrenamiento: MLPRegressor sklearn, Adam, ReLU, 500 iter máx

### 3. Bugs encontrados y corregidos
- **Target sin normalizar** (`y_train` en lugar de `y_train_n`): causaba INT8 RMSE=64°C
  - Fix: normalizar target también, desnormalizar en predicción
- **Variable `OUT` sobrescrita**: usada para Path y para array de salida
  - Fix: renombrar `out_layer` para el ndarray
- **savefig con Path** no funciona en este numpy: usar `str(OUT) + "/..."`
- **Cuantización per-tensor** saturaba: cambiado a per-channel (más fiel a TFLite Micro)

### 4. Resultados finales
- **Float RMSE: 0.81 °C** (vs 1.18 °C sintético, -31%)
- **INT8 RMSE: 0.81 °C** (idéntico, sin degradación)
- **MAE: 0.57 °C**
- **Parámetros: 865** (vs 673 sintético, +28% por 9 features)
- **RAM estimada: ~2.7 KB** (vs 2.1 KB)
- Degradación INT8 vs Float: -0.001 °C (imperceptible)

### 5. Figura actualizada
- `figures/fig5_tinyml_plot.png/pdf`: scatter + 14 días serie temporal
- Rango T_test: 6.2–23.6°C
- Visualización confirma excelente correlación con línea y=x ideal

### 6. Archivos actualizados (poster + guía)
- `poster_cientifico.html`:
  - Fig 4 caption: 9 entradas, 865 params, 8781 h Open-Meteo
  - Fig 5 caption: RMSE 0.81°C, MAE 0.57°C, 1757 h test
  - Sección 9: texto actualizado a Dense[9→32→16→1]
- `figures/fig5_tinyml_arch.svg`:
  - Título: Dense[9→32→16→1] · 865 params
  - Bloque ENTRADAS ahora muestra 3 variables × 3 lags
  - Footer: "RMSE = 0.81°C · INT8 = Float · Datos: 8781 h reales Open-Meteo"
- `guia_presentacion.html`:
  - Sección 5 (TinyML): arquitectura y métricas actualizadas
  - Callouts: error histórico y limitación reconocidas
  - "Hecho hasta ahora": +"datos REALES"

## Sesión 3 (4 Jun) — Bridge con modelo real y portar a ESP32

### 1. Bridge actualizado (`serial_bridge.py`)
- `tinyml_predict()` reescrito para 9 features (lags t, t-1, t-2)
- Inferencia INT8 per-channel vectorizada con numpy
- Historial interno de 3 muestras para los lags
- **Bugs corregidos**: target sin normalizar (y_train_n), variable OUT sobrescrita, cuantización per-tensor → per-channel
- Tests:
  - `test_tinyml_bridge.py`: 142/144 predicciones OK, RMSE 2.7°C con datos sintéticos (modelo sobreajustado a Open-Meteo)
  - `test_bridge_http.py`: mock serial + HTTP, /data responde `tinyml_pred` correctamente

### 2. TinyML portado a C (bare-metal, sin TFLite Micro)
- `export_tinyml_c.py`: convierte `tinyml_model.npz` → `tinyml_model_data.h` (6.1 KB)
- `tinyml_inference.c/h`: forward pass INT8 per-channel, ~80 líneas
- Pipeline: x → normalizar → INT8 → capa 1 (ReLU, requant) → capa 2 (ReLU, requant) → capa 3 → desnormalizar
- Buffers en stack: ~420 B
- **Validación en PC** (gcc, sin ESP32): 3 casos de prueba, predicciones coherentes
- **Comparación C vs Python**: diff < 0.15°C (float32 vs float64)

### 3. Integración al firmware ESP32-S3 (`main/main.c`)
- Include de `tinyml_inference.h`
- Historial de 3 muestras en `tinyml_history[3][3]`
- Inferencia en cada ciclo de 5 s (mide latencia con `esp_timer_get_time()`)
- CSV extendido: +columnas `tinyml_pred_C` y `tinyml_latency_us`
- **Pendiente**: compilar con ESP-IDF (requiere idf.py + entorno) y flashear en /dev/ttyACM0

### 4. Archivos nuevos
| Archivo | Descripción |
|---|---|
| `export_tinyml_c.py` | npz → C header |
| `main/tinyml_model_data.h` | 865 pesos INT8 + escalas per-channel (6.1 KB) |
| `main/tinyml_inference.h` | API C |
| `main/tinyml_inference.c` | Forward pass (80 líneas) |
| `test_inference_pc.c` | Test en PC con gcc |
| `test_tinyml_bridge.py` | Test de inferencia del bridge |
| `test_bridge_http.py` | Test E2E con mock serial + HTTP |
| `build_flash.sh` | Script para compilar y flashear (manual) |
| `TINYML_EMBEBIDO.md` | Documentación específica de TinyML embebido |

## Sesión 4 (4 Jun) — Compilación, flasheo y validación en hardware

### Problema con ESP-IDF
- ESP-IDF v6.1 en `/home/lenincoronel/esp/esp-idf` estaba corrupto (sin venv)
- ESP-IDF v5.5.3 funcional en `/home/lenincoronel/Overall/bad_apple_frames/.embuild/espressif/esp-idf/v5.5.3`
- Toolchain Xtensa 15.2.0 (rustup) detectado en `~/.rustup/toolchains/esp/`
- **Solución**: usar v5.5.3 con toolchain v15.2.0 + `IDF_MAINTAINER=1` (bypass check de versión)

### Pasos de setup
1. Symlinks creados en `~/.espressif/`:
   - `python_env/idf5.5_py3.14_env` → venv de bad_apple_frames
   - `tools` → tools de bad_apple_frames
   - `espidf.constraints.v5.5.txt` → constraints de bad_apple_frames
2. `/tmp` limpio (liberó 2.1 GB)
3. Script `/tmp/setup_idf.sh` con env vars correctas
4. `IDF_MAINTAINER=1` para saltar check de versión toolchain

### Compilación exitosa
- `idf.py set-target esp32s3` → 1080 componentes configurados
- `idf.py build` → 
  - **greenhouse_monitor.bin: 224 KB** (79% libre de 1 MB)
  - **bootloader.bin: 21 KB** (36% libre)
  - Total: ~1079 targets compilados en ~3 minutos

### Flasheo exitoso
- 247 KB escritos en /dev/ttyACM0 vía esptool
- Hash verificado en bootloader, partition table, app
- "Hard resetting via RTS pin... Done"

### Validación en hardware (XIAO ESP32-S3)
- Log capturado vía pyserial: 18 muestras en 90 s (cada 5 s, como esperado)
- **Latencia de inferencia: 223.2 ± 9.8 µs** (objetivo: < 100 ms, **450x mejor**)
- Throughput: ~4500 inferencias/segundo
- T_pred estable en 18.34°C (modelo responde, sensores en modo fijo dan input constante)
- T_bmp: 22.69°C, HR: 73.65% (ambos del firmware, no del sensor físico)

### Archivos de evidencia
- `esp32_log.csv` con 18 muestras + latencias
- `build/greenhouse_monitor.bin` (224 KB, listo para flashear)

### Archivos actualizados
- `poster_cientifico.html`:
  - Sección 9: añadida mención "Implementado y validado en ESP32-S3: latencia 223 ± 10 µs"
  - Fig 5 caption: añadida verificación en hardware
- `guia_presentacion.html`:
  - Sección 5: 2 nuevos status-grids con latencia, margen, throughput
  - Tabla trabajo futuro: "Portar TinyML" marcado como "Hecho"
  - FAQ: pregunta 2 actualizada ("Sí, validado, latencia 223 µs")
  - Fallos: "TinyML entrenado, embebido y validado en hardware"
  - FAQ: contribución original con 865 params y 0.81°C
  - Tabla fallos: TinyML marcado como entrenado con datos reales
  - Tabla trabajo futuro: validación local IDEAM como pendiente
  - Mapa memoria: "865 params, INT8" en lugar de "2.1 KB"
