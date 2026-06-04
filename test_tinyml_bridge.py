#!/usr/bin/env python3
"""
test_tinyml_bridge.py — Test del bridge TinyML con datos sintéticos
Mock del CSV que mandaría el ESP32, validando inferencia.
"""
import sys
sys.path.insert(0, "/home/lenincoronel/Overall/BajoNivel/greenhouse_monitor")
import numpy as np
import json

# Cargar el modelo
from serial_bridge import load_tinyml, tinyml_predict, latest

assert load_tinyml(), "No se pudo cargar TinyML"

# Generar 3 días de datos sintéticos Bogotá
print("\n[Test] Generando 3 días de datos sintéticos...")
hours = np.arange(0, 72, 0.5)  # cada 30 min
T_out = 14 + 6 * np.sin(2 * np.pi * (hours - 14) / 24) + np.random.normal(0, 0.5, len(hours))
HR_out = 70 + 15 * np.cos(2 * np.pi * (hours - 14) / 24) + np.random.normal(0, 3, len(hours))
solar = np.where((hours % 24 >= 6) & (hours % 24 <= 18),
                 800 * np.sin(np.pi * ((hours % 24) - 6) / 12), 0)
solar = np.maximum(0, solar + np.random.normal(0, 10, len(hours)))

# Simular que llega cada 30 min al bridge
preds_ok = 0
preds_fail = 0
errors = []

for i in range(len(hours)):
    t, h, r = float(T_out[i]), float(HR_out[i]), float(solar[i])
    t_pred, _ = tinyml_predict(t, h, r)
    if t_pred is not None:
        # La prediccion es T(t+1), y la "real" futura es T_out[i+1] (si existe)
        if i + 1 < len(hours):
            real_next = T_out[i + 1]
            err = abs(t_pred - real_next)
            errors.append(err)
        preds_ok += 1
    else:
        preds_fail += 1

print(f"\n[Test] Predicciones OK: {preds_ok} | Fail: {preds_fail}")
if errors:
    errors = np.array(errors)
    print(f"[Test] Error en inferencia T(t+1):")
    print(f"  RMSE = {np.sqrt(np.mean(errors**2)):.3f} °C")
    print(f"  MAE  = {np.mean(errors):.3f} °C")
    print(f"  Max  = {np.max(errors):.3f} °C")
    print(f"  Std  = {np.std(errors):.3f} °C")
    print(f"  Errores < 1°C: {(errors < 1.0).mean()*100:.1f}%")
    print(f"  Errores < 2°C: {(errors < 2.0).mean()*100:.1f}%")
