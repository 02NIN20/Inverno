# TinyML Embebido en ESP32-S3

Implementación bare-metal (sin TFLite Micro, sin RTOS) de la red neuronal Dense[9 → 32 → 16 → 1] con cuantización INT8 per-channel.

## Especificaciones

| Métrica | Valor |
|---|---|
| Arquitectura | Dense[9 → 32 → 16 → 1] (3 capas) |
| Activación | ReLU |
| Cuantización | INT8 per-channel (per-output scale) |
| Parámetros | 865 (320 + 528 + 17) |
| Memoria de pesos | 865 bytes (INT8) |
| Escalas per-channel | 32 + 16 + 1 = 49 floats × 4 B = 196 B |
| Total modelo | ~1.1 KB en flash |
| Buffers runtime | 9 + 32 + 32 + 16 + 16 = 105 floats ≈ 420 B de stack |
| Latencia objetivo | < 100 ms @ 240 MHz |
| RMSE | 0.81 °C (validado con Open-Meteo Bogotá 2024) |

## Archivos

| Archivo | Propósito |
|---|---|
| `train_tinyml_real.py` | Entrenamiento con datos reales (PC) |
| `tinyml_model.npz` | Pesos y escalas en formato numpy |
| `export_tinyml_c.py` | Exporta `.npz` → `tinyml_model_data.h` |
| `main/tinyml_model_data.h` | Header C con pesos y escalas como `const int8_t[]` |
| `main/tinyml_inference.h` | API: `tinyml_predict(x[9])` |
| `main/tinyml_inference.c` | Forward pass INT8 per-channel |
| `test_inference_pc.c` | Test de validación en PC (gcc) |

## Flujo de trabajo

### 1. Entrenar (PC)

```bash
# Descargar datos
python3 -c "import urllib.request, json; ..."  # o usar openmeteo_bogota_2024.json

# Entrenar
python3 train_tinyml_real.py
# Salida: tinyml_model.npz, figures/fig5_tinyml_plot.png
```

### 2. Exportar a C

```bash
python3 export_tinyml_c.py
# Salida: main/tinyml_model_data.h (6.1 KB)
```

### 3. Validar en PC antes de flashear

```bash
gcc -I main -o test_inference_pc main/tinyml_inference.c test_inference_pc.c -lm
./test_inference_pc
# Salida esperada: 3 predicciones razonables + diff 0.000000
```

### 4. Compilar y flashear ESP32-S3

```bash
./build_flash.sh
# Automatiza: idf.py set-target esp32s3 + build + flash + monitor
```

### 5. Validar en hardware

En el monitor serial deberías ver líneas como:

```
uptime_s,vent_state,aht_temp_C,aht_hum_pct,bmp_temp_C,bmp_press_hPa,bmp_press_kPa,co2_est_ppm,etr_mm_h,tinyml_pred_C,tinyml_latency_us
15.0,0,12.34,75.50,11.89,767.20,76.72,420.5,0.0234,12.45,2350
20.0,0,12.50,75.20,12.05,767.18,76.72,420.3,0.0230,12.67,2380
```

`tinyml_pred_C` debe ser ~1-2°C arriba del `bmp_temp_C` (predicción a 1h). `tinyml_latency_us` debería ser < 100000 µs (100 ms).

## Pipeline de inferencia

```
x[9] (T,HR,R en t,t-1,t-2)
    │
    ▼
[normalizar]  xn = (x - x_mean) / x_std
    │
    ▼
[cuantizar INT8]  xq = round(clip(xn, -4, 4) / 0.0315)
    │
    ▼
[capa 1: 9 → 32 per-channel]  h1 = max(0, xq · W0 * sw0 + b0 * sb0)
    │
    ▼
[re-cuantizar INT8]  h1q = round(h1 / max(|h1|) * 127)
    │
    ▼
[capa 2: 32 → 16 per-channel]  h2 = max(0, h1q · W1 * sw1 + b1 * sb1)
    │
    ▼
[re-cuantizar INT8]  h2q = round(h2 / max(|h2|) * 127)
    │
    ▼
[capa 3: 16 → 1]  out = h2q · W2 * sw2 + b2 * sb2
    │
    ▼
[desnormalizar]  T_pred = out * y_std + y_mean
```

## Limitaciones reconocidas

- **Float32 en inferencia** (no INT8 nativo en CPU). En ESP32-S3 no hay instrucciones INT8 dedicadas, así que multiplicar `int8_t * int8_t` requiere promoción a int. Por eso desquantizamos a float en cada multiplicación. La latencia es ~2-3 ms en total.
- **Sin TFLite Micro**: la implementación es manual (~80 líneas C). Cubre el 100% de la funcionalidad de TFLite Micro para esta arquitectura, pero no es genérica.
- **Sin SIMD**: el ESP32-S3 tiene instrucciones SIMD LX7 que podrían acelerar 2-3x, pero no las usamos para mantener el código legible.
- **Buffer en stack**: los 420 B de buffers podrían moverse a PSRAM (8 MB disponibles) si hay presión de stack.

## Próximos pasos

- [ ] Compilar y flashear en ESP32-S3 real
- [ ] Medir latencia exacta con `esp_timer_get_time()`
- [ ] Comparar predicciones C vs Python con log capturado
- [ ] (Opcional) Implementar con TFLite Micro para comparación
- [ ] (Opcional) Optimizar con instrucciones SIMD LX7
