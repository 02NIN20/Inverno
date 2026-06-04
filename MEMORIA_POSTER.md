# MEMORIA DEL PÓSTER — Estado actual y figuras

## Especificaciones
- Formato: 500 × 870 mm (medio pliego), 1 página
- Fuente: Times New Roman, paleta olive/gold
- Generación: HTML + Playwright Chromium → PDF (~1.38 MB)
- Alternativa: LaTeX (`poster_latex.pdf`, Palatino via newpxtext)

## Estructura de columnas
- **Col 1** (izquierda): Introducción, Brechas, Objetivos, Modelo matemático, Metodología, Arquitectura del sistema, Referencias
- **Col 2** (derecha): Resultados (prototipo + simulación), Simulación RK4, Validación TinyML + Control, Conclusiones
- Gap entre columnas: 12mm

## Mapa de figuras

| # | Archivo | Sección | Contenido |
|---|---------|---------|-----------|
| Fig 1 | `figures/fig3_arch.svg` | §6 | Arquitectura ciber-físico del sistema |
| Fig 2 | `figures/fig1_temp_hum.png` | §7a | Prueba de concepto: T + HR (AHT20, 11 min) |
| Fig 3 | `figures/fig2_press_co2.png` | §7a | Presión BMP280 + CO₂ estimado (ciclo diurno) |
| Fig 4 | `figures/fig5_tinyml_arch.svg` | §7a | Arquitectura TinyML: Dense[9→32→16→1] SVG |
| Fig 5 | `figures/fig5_tinyml_plot.png` | §9 | Validación TinyML: scatter + serie temporal (datos reales) |
| — | `figures/fig4_sim.png` | §8 | Simulación RK4 7 días (sin número, referencia) |

## Datos de figuras
- **Fig 1 (Temp/Hum)**: 132 pts, 11 min, laboratorio, AHT20 I²C
- **Fig 2 (Presión/CO₂)**: P_med=767 hPa, γ=0.0495 kPa/°C (+2.3% vs teórico)
- **Fig 3 (Arquitectura)**: SVG manual, compatible con paleta del poster
- **Fig 4 (TinyML arch)**: SVG manual, 500×220 viewBox, 9 entradas (3 vars × 3 lags) → 3 capas → salida
- **Fig 5 (TinyML validación)**: 10×3.5" matplotlib, 2 paneles, RMSE=0.81°C datos reales 2024
- **Fig 4_sim (RK4)**: 8×5" matplotlib, 4 paneles, MC bands N=100, Sobol N=10⁴

## Modelo TinyML (Fig 4 + Fig 5)
- Arquitectura: Dense[9] → Dense[32] → Dense[16] → Dense[1], ReLU, INT8 per-channel
- Parámetros: 320 + 528 + 17 = **865** (incluyendo capa de entrada 9×32+32)
- RAM: ~2.7 KB (INT8), modelo completo < 50 KB (TFLite Micro)
- Entradas: (T_ext, HR_ext, R) en t, t-1, t-2 → 9 features
- Salida: T_ext a 1 h (condición de borde para EDOs)
- **Entrenamiento: 8781 h datos REALES de Open-Meteo Bogotá 2024** (4.71°N, 74.07°W, 2640 msnm)
- Split: 7024 h train / 1757 h test (20% hold-out temporal)
- **Resultados: RMSE = 0.81 °C, MAE = 0.57 °C (float32 = INT8)**
- Framework: scikit-learn MLPRegressor, cuantización manual INT8 per-channel

## Pendientes del poster
- [ ] Migrar inferencia TinyML a ESP32-S3 (TFLite Micro)
- [ ] Implementar RL-Guided MPC en ESP32-S3
- [ ] Validar TinyML con datos de estación meteorológica local (IDEAM)
- [ ] Remaining claims a bajar: SVG título "implementado", OE1 "calibrado", OE3 sin "(diseño)"
