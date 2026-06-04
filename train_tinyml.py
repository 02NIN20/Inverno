#!/usr/bin/env python3.10
"""
train_tinyml.py — Entrena modelo TinyML Dense[32->16->1] INT8
para predicción de T_ext a 1 h (condición de borde para EDOs).
Usa sklearn (MLPRegressor) + cuantización manual para simular TFLite INT8.
Salidas: tinyml_model.npz (pesos cuantizados), figures/fig5_tinyml_plot.png
"""

import sys
sys.path.insert(0, "/home/lenincoronel/tinyml_env/lib/python3.10/site-packages")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.neural_network import MLPRegressor
import pickle
import struct

OUT = Path("figures")
OUT.mkdir(exist_ok=True)
np.random.seed(42)

N_HOURS = 720  # 30 dias de datos horarios
N_FEATURES = 3

# --- Generar datos sintéticos realistas (ciclo diurno Bogotá) ---
t = np.arange(N_HOURS)
T_ext = 14 + 6 * np.sin(2 * np.pi * (t - 14) / 24) + np.random.normal(0, 0.8, N_HOURS)
HR_ext = 70 + 15 * np.cos(2 * np.pi * (t - 14) / 24) + np.random.normal(0, 5, N_HOURS)
sunrise = ((t % 24) >= 6) & ((t % 24) <= 18)
solar_rad = np.where(sunrise, 800 * np.sin(np.pi * ((t % 24) - 6) / 12), 0)
solar_rad += np.random.normal(0, 20, N_HOURS)
solar_rad = np.maximum(0, solar_rad)

X = np.column_stack([T_ext[:-1], HR_ext[:-1], solar_rad[:-1]])
y = T_ext[1:]

# Split 80/20
split = int(0.8 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# Normalizar
x_mean, x_std = X_train.mean(axis=0), X_train.std(axis=0)
y_mean, y_std = y_train.mean(), y_train.std()
X_train_n = (X_train - x_mean) / x_std
X_test_n = (X_test - x_mean) / x_std
y_train_n = (y_train - y_mean) / y_std
y_test_n = (y_test - y_mean) / y_std

# --- Entrenar MLP: 32 -> 16 -> 1 (ReLU) ---
model = MLPRegressor(
    hidden_layer_sizes=(32, 16),
    activation="relu",
    solver="adam",
    max_iter=500,
    random_state=42,
    verbose=False,
)
model.fit(X_train_n, y_train_n)

# Evaluar (float)
y_pred_n = model.predict(X_test_n)
y_pred = y_pred_n * y_std + y_mean
rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
mae = np.mean(np.abs(y_test - y_pred))
print(f"[TinyML] Float RMSE: {rmse:.3f} °C  |  MAE: {mae:.3f} °C")

# --- Contar parámetros ---
W = model.coefs_  # lista de matrices [input->32, 32->16, 16->1]
b = model.intercepts_
total_params = sum(w.size for w in W) + sum(bi.size for bi in b)
print(f"[TinyML] Parámetros totales: {total_params} (expected 673)")
for i, (w, bi) in enumerate(zip(W, b)):
    print(f"  Capa {i}: {w.shape} -> {w.size + bi.size} params")

# --- Cuantización manual INT8 simulando TFLite Micro ---
# Escala: [-max_abs, max_abs] -> [-128, 127]
def quantize(arr):
    max_abs = np.max(np.abs(arr))
    if max_abs < 1e-8:
        return np.zeros(arr.shape, dtype=np.int8), 1.0, 0
    scale = max_abs / 127.0
    q = np.clip(np.round(arr / scale), -128, 127).astype(np.int8)
    return q, scale, 0

weights_int8 = []
scales_w = []
for w in W:
    q, s, _ = quantize(w)
    weights_int8.append(q)
    scales_w.append(s)

biases_int8 = []
scales_b = []
for bi in b:
    q, s, _ = quantize(bi.reshape(-1, 1))
    biases_int8.append(q.flatten())
    scales_b.append(s)

# Guardar modelo cuantizado
model_data = {
    "w0": weights_int8[0], "w1": weights_int8[1], "w2": weights_int8[2],
    "b0": biases_int8[0], "b1": biases_int8[1], "b2": biases_int8[2],
    "sw0": scales_w[0], "sw1": scales_w[1], "sw2": scales_w[2],
    "sb0": scales_b[0], "sb1": scales_b[1], "sb2": scales_b[2],
    "x_mean": x_mean, "x_std": x_std,
    "y_mean": y_mean, "y_std": y_std,
}
np.savez_compressed("tinyml_model.npz", **model_data)
print(f"[TinyML] Modelo cuantizado guardado: tinyml_model.npz")

# --- Evaluación cuantizada (simulación INT8) ---
# Escala para entrada normalizada: max(abs(X_n)) ~ 3
X_MAX = 3.0
x_scale = X_MAX / 127.0

def predict_int8(X_raw):
    X_n = (X_raw - model_data["x_mean"]) / model_data["x_std"]
    X_n = np.clip(X_n, -X_MAX, X_MAX)
    x_q = np.clip(np.round(X_n / x_scale), -128, 127).astype(np.int8)

    # Capa 1: entrada (INT8) x peso (INT8 x scale_w) -> float
    h = np.dot(x_q.astype(np.float32) * x_scale, weights_int8[0] * scales_w[0]) + biases_int8[0] * scales_b[0]
    h = np.maximum(0, h)
    # Capa 2
    h = np.dot(h, weights_int8[1] * scales_w[1]) + biases_int8[1] * scales_b[1]
    h = np.maximum(0, h)
    # Capa 3
    out = np.dot(h, weights_int8[2] * scales_w[2]) + biases_int8[2] * scales_b[2]
    return np.squeeze(out * model_data["y_std"] + model_data["y_mean"])

y_pred_int8 = np.array([predict_int8(x) for x in X_test])
rmse_i8 = np.sqrt(np.mean((y_test - y_pred_int8) ** 2))
mae_i8 = np.mean(np.abs(y_test - y_pred_int8))
print(f"[TinyML] INT8  RMSE: {rmse_i8:.3f} °C  |  MAE: {mae_i8:.3f} °C")

# --- Figura: predicción vs real ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))

n_show = 48
offset = len(y_test) - n_show
idx = np.arange(n_show)
ax1.plot(idx, y_test[offset:], color="#009E73", linewidth=1.5, label="Real (T_ext)")
ax1.plot(idx, y_pred_int8[offset:], color="#56B4E9", linewidth=1.5, linestyle="--", label="Predicho (TFLite INT8)")
ax1.set_xlabel("Horas")
ax1.set_ylabel("Temperatura exterior (°C)")
ax1.set_title("Predicción T_ext a 1 h (48 h de prueba)", fontweight="bold", fontsize=12)
ax1.legend(fontsize=9, frameon=False)
ax1.set_xticks(np.arange(0, n_show+1, 12))

ax2.scatter(y_test, y_pred_int8, s=8, alpha=0.5, color="#0072B2")
ax2.plot([10, 22], [10, 22], color="#D55E00", linestyle=":", linewidth=1.2, label="y = x (ideal)")
ax2.set_xlabel("T_ext real (°C)")
ax2.set_ylabel("T_ext predicho (°C)")
ax2.set_title(f"RMSE = {rmse_i8:.2f} °C  |  MAE = {mae_i8:.2f} °C", fontweight="bold", fontsize=12)
ax2.legend(fontsize=9, frameon=False)
ax2.set_xlim(10, 22)
ax2.set_ylim(10, 22)

fig.tight_layout()
fig.savefig(OUT / "fig5_tinyml_plot.pdf", dpi=300)
fig.savefig(OUT / "fig5_tinyml_plot.png", dpi=300)
plt.close()
print(f"[TinyML] Figura guardada: {OUT}/fig5_tinyml_plot.pdf")
