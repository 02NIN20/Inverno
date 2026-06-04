#!/usr/bin/env python3
"""
export_tinyml_c.py — Exporta tinyml_model.npz a un header C (tinyml_model_data.h)
con los pesos INT8 y escalas per-channel listas para embeber en el ESP32-S3.
"""
import numpy as np
from pathlib import Path

# Cargar modelo
m = np.load("tinyml_model.npz")
w0, w1, w2 = m["w0"], m["w1"], m["w2"]
b0, b1, b2 = m["b0"], m["b1"], m["b2"]
sw0, sw1, sw2 = m["sw0"], m["sw1"], m["sw2"]
sb0, sb1, sb2 = m["sb0"], m["sb1"], m["sb2"]
x_mean, x_std = m["x_mean"], m["x_std"]
y_mean, y_std = m["y_mean"], m["y_std"]

print(f"w0 shape: {w0.shape} (input 9 -> 32)")
print(f"w1 shape: {w1.shape} (32 -> 16)")
print(f"w2 shape: {w2.shape} (16 -> 1)")
print(f"Total params: {w0.size + b0.size + w1.size + b1.size + w2.size + b2.size}")
print(f"sw0 shape: {sw0.shape} (per-channel output 32)")
print(f"sw1 shape: {sw1.shape} (per-channel output 16)")

def to_c_array_int8(arr, name, indent="  "):
    """Convierte ndarray int8 a literal C: const int8_t NAME[N] = { ... };"""
    flat = arr.flatten()
    lines = []
    for i in range(0, len(flat), 16):
        chunk = flat[i:i+16]
        lines.append(", ".join(str(int(x)) for x in chunk))
    body = ",\n  ".join(lines)
    return f"static const int8_t {name}[{flat.size}] = {{\n  {body}\n}};"

def to_c_array_float(arr, name):
    """Convierte ndarray float32 a literal C."""
    flat = arr.flatten()
    lines = []
    for i in range(0, len(flat), 8):
        chunk = flat[i:i+8]
        lines.append(", ".join(f"{float(x):.6e}f" for x in chunk))
    body = ",\n  ".join(lines)
    return f"static const float {name}[{flat.size}] = {{\n  {body}\n}};"

# Generar header
header = """/*
 * tinyml_model_data.h
 * Auto-generado por export_tinyml_c.py desde tinyml_model.npz
 * Modelo: Dense[9 -> 32 -> 16 -> 1], ReLU, INT8 per-channel
 * Entrenamiento: 8781 h Open-Meteo Bogotá 2024 (RMSE 0.81 °C)
 */
#ifndef TINYML_MODEL_DATA_H
#define TINYML_MODEL_DATA_H

#include <stdint.h>

#define TINYML_N_FEATURES  9
#define TINYML_N_HIDDEN_1  32
#define TINYML_N_HIDDEN_2  16
#define TINYML_N_OUTPUT    1
#define TINYML_X_MAX       4.0f   /* max abs value of normalized input */

"""

header += to_c_array_int8(w0, "tinyml_w0") + "\n\n"
header += to_c_array_int8(w1, "tinyml_w1") + "\n\n"
header += to_c_array_int8(w2, "tinyml_w2") + "\n\n"
header += to_c_array_int8(b0, "tinyml_b0") + "\n\n"
header += to_c_array_int8(b1, "tinyml_b1") + "\n\n"
header += to_c_array_int8(b2, "tinyml_b2") + "\n\n"

# Escalas per-channel
header += f"static const float tinyml_sw0[TINYML_N_HIDDEN_1] = {{\n  "
header += ", ".join(f"{float(s):.6e}f" for s in sw0)
header += "\n};\n\n"

header += f"static const float tinyml_sw1[TINYML_N_HIDDEN_2] = {{\n  "
header += ", ".join(f"{float(s):.6e}f" for s in sw1)
header += "\n};\n\n"

header += f"static const float tinyml_sw2[TINYML_N_OUTPUT] = {{\n  "
header += ", ".join(f"{float(s):.6e}f" for s in sw2)
header += "\n};\n\n"

# Escalas de bias (escalares)
header += f"static const float tinyml_sb0 = {float(sb0):.6e}f;\n"
header += f"static const float tinyml_sb1 = {float(sb1):.6e}f;\n"
header += f"static const float tinyml_sb2 = {float(sb2):.6e}f;\n\n"

# Normalización de entrada
header += f"static const float tinyml_x_mean[TINYML_N_FEATURES] = {{\n  "
header += ", ".join(f"{float(x):.6e}f" for x in x_mean)
header += "\n};\n\n"

header += f"static const float tinyml_x_std[TINYML_N_FEATURES] = {{\n  "
header += ", ".join(f"{float(x):.6e}f" for x in x_std)
header += "\n};\n\n"

# Desnormalización de salida
header += f"static const float tinyml_y_mean = {float(y_mean):.6e}f;\n"
header += f"static const float tinyml_y_std  = {float(y_std):.6e}f;\n\n"

header += "#endif /* TINYML_MODEL_DATA_H */\n"

# Guardar
out_path = Path("main/tinyml_model_data.h")
out_path.write_text(header)
size_kb = out_path.stat().st_size / 1024
print(f"\n[export] Header C generado: {out_path} ({size_kb:.1f} KB)")
print(f"[export] Total bytes de pesos: {w0.size + w1.size + w2.size + b0.size + b1.size + b2.size}")
