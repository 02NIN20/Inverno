#!/usr/bin/env python3
"""
train_tinyml_real.py — Reentrena TinyML con datos REALES Open-Meteo Bogotá 2024.
Predice T_ext a 1 h usando T, HR, R en t, t-1, t-2 (9 features).
Arquitectura: Dense[9->32->16->1], cuantizada INT8, ~673 params.
"""
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.neural_network import MLPRegressor

OUT = Path("figures")
OUT.mkdir(exist_ok=True)
np.random.seed(42)

# --- Cargar datos reales ---
with open("openmeteo_bogota_2024.json") as f:
    data = json.load(f)
h = data["hourly"]
T = np.array(h["temperature_2m"], dtype=np.float32)
HR = np.array(h["relative_humidity_2m"], dtype=np.float32)
R = np.array(h["shortwave_radiation"], dtype=np.float32)

print(f"[Real] Cargadas {len(T)} horas reales (Bogotá 2024)")
print(f"  T: {T.min():.1f}–{T.max():.1f}°C, media {T.mean():.1f}°C")
print(f"  HR: {HR.min():.1f}–{HR.max():.1f}%, media {HR.mean():.1f}%")
print(f"  R:  {R.min():.0f}–{R.max():.0f} W/m², media {R.mean():.0f}")

# --- Features: 3 variables x 3 lags (t, t-1, t-2) = 9 features ---
# Lag 2 horas permite capturar inercia termica
# Estructura: para predecir T(t+1), usamos features en t, t-1, t-2
# T(t),HR(t),R(t) | T(t-1),HR(t-1),R(t-1) | T(t-2),HR(t-2),R(t-2)  ->  T(t+1)
N_total = len(T)
max_lag = 2
N = N_total - max_lag - 1  # numero de muestras validas

X = np.zeros((N, 9), dtype=np.float32)
for i in range(N):
    t = i + max_lag  # t=2..N_total-2
    X[i, 0] = T[t]
    X[i, 1] = HR[t]
    X[i, 2] = R[t]
    X[i, 3] = T[t-1]
    X[i, 4] = HR[t-1]
    X[i, 5] = R[t-1]
    X[i, 6] = T[t-2]
    X[i, 7] = HR[t-2]
    X[i, 8] = R[t-2]

y_next = T[max_lag + 1:]  # T(t+1) para t=2..N_total-2

print(f"\n[Real] X shape: {X.shape}, y shape: {y_next.shape}")
print(f"  Features: T(t),HR(t),R(t), T(t-1),HR(t-1),R(t-1), T(t-2),HR(t-2),R(t-2)")
print(f"  Target: T(t+1) — prediccion a 1 hora")

# --- Split temporal 80/20 (sin shuffle: respetar orden cronológico) ---
N = len(X)
split = int(0.8 * N)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y_next[:split], y_next[split:]

print(f"  Train: {len(X_train)} h, Test: {len(X_test)} h")
print(f"  Test: T={y_test.min():.1f}–{y_test.max():.1f}°C, media {y_test.mean():.1f}°C")

# --- Normalización ---
x_mean = X_train.mean(axis=0)
x_std = X_train.std(axis=0) + 1e-6
y_mean = y_train.mean()
y_std = y_train.std() + 1e-6
X_train_n = (X_train - x_mean) / x_std
X_test_n = (X_test - x_mean) / x_std
y_train_n = (y_train - y_mean) / y_std  # normalizar target tambien
y_test_n = (y_test - y_mean) / y_std

# --- Entrenar MLP: 9 -> 32 -> 16 -> 1 (target normalizado) ---
model = MLPRegressor(
    hidden_layer_sizes=(32, 16),
    activation="relu",
    solver="adam",
    max_iter=500,
    random_state=42,
    verbose=False,
)
model.fit(X_train_n, y_train_n)

y_pred_n = model.predict(X_test_n)
y_pred = y_pred_n * y_std + y_mean
rmse_f = np.sqrt(np.mean((y_test - y_pred) ** 2))
mae_f = np.mean(np.abs(y_test - y_pred))
print(f"\n[TinyML-Real] Float RMSE: {rmse_f:.3f} °C  |  MAE: {mae_f:.3f} °C")

# --- Conteo de parámetros ---
W = model.coefs_
b = model.intercepts_
total = sum(w.size for w in W) + sum(bi.size for bi in b)
print(f"[TinyML-Real] Parámetros totales: {total}")
for i, (w, bi) in enumerate(zip(W, b)):
    print(f"  Capa {i}: {w.shape} -> {w.size + bi.size} params")

# --- Cuantización INT8 per-output-channel (simula TFLite Micro) ---
# TFLite Micro escala cada filtro/neurona por separado, no el tensor entero.
# Esto preserva precisión en capas con neuronas de magnitudes heterogeneas.
def quantize_per_channel(arr_2d, axis=0):
    """Cuantiza por columna (axis=0 -> por output unit)."""
    max_abs = np.max(np.abs(arr_2d), axis=axis, keepdims=True)
    max_abs = np.where(max_abs < 1e-8, 1.0, max_abs)
    scale = (max_abs / 127.0).flatten()
    q = np.clip(np.round(arr_2d / scale[None, :]), -128, 127).astype(np.int8)
    return q, scale

def quantize_per_unit(arr_1d):
    max_abs = np.max(np.abs(arr_1d))
    if max_abs < 1e-8:
        return np.zeros(arr_1d.shape, dtype=np.int8), 1.0
    scale = max_abs / 127.0
    q = np.clip(np.round(arr_1d / scale), -128, 127).astype(np.int8)
    return q, scale

weights_q, scales_w = [], []
for w in W:
    q, s = quantize_per_channel(w, axis=0)
    weights_q.append(q)
    scales_w.append(s)

biases_q, scales_b = [], []
for bi in b:
    q, s = quantize_per_unit(bi)
    biases_q.append(q)
    scales_b.append(s)

# --- Inferencia INT8 simulada (cuantizacion per-channel, vectorizada) ---
X_MAX = 4.0
x_scale = X_MAX / 127.0

# Dequantizar pesos (matrices float con la escala de cada output unit)
W0 = weights_q[0].astype(np.float32) * scales_w[0][None, :]
W1 = weights_q[1].astype(np.float32) * scales_w[1][None, :]
W2 = weights_q[2].flatten().astype(np.float32) * scales_w[2]
B0 = biases_q[0].astype(np.float32) * scales_b[0]
B1 = biases_q[1].astype(np.float32) * scales_b[1]
B2 = biases_q[2].astype(np.float32) * scales_b[2]

# Forward cuantizado en batch (target esta normalizado)
Xn = np.clip((X_test - x_mean) / x_std, -X_MAX, X_MAX)
# Capa 1
H1_float = Xn @ W0 + B0
H1 = np.maximum(0, H1_float)
# Re-cuantizar activaciones capa 1
H1_MAX = max(np.max(np.abs(H1)), 1e-8)
H1_SC = H1_MAX / 127.0
H1_q = np.clip(np.round(H1 / H1_SC), -128, 127).astype(np.float32) * H1_SC
# Capa 2
H2 = np.maximum(0, H1_q @ W1 + B1)
H2_MAX = max(np.max(np.abs(H2)), 1e-8)
H2_SC = H2_MAX / 127.0
H2_q = np.clip(np.round(H2 / H2_SC), -128, 127).astype(np.float32) * H2_SC
# Capa 3
out_layer = H2_q @ W2 + B2
# Desnormalizar salida (target fue normalizado)
y_pred_int8 = out_layer * y_std + y_mean

rmse_i = np.sqrt(np.mean((y_test - y_pred_int8) ** 2))
mae_i = np.mean(np.abs(y_test - y_pred_int8))
print(f"[TinyML-Real] INT8  RMSE: {rmse_i:.3f} °C  |  MAE: {mae_i:.3f} °C")

# --- Guardar modelo ---
model_data = {
    "w0": weights_q[0], "w1": weights_q[1], "w2": weights_q[2],
    "b0": biases_q[0], "b1": biases_q[1], "b2": biases_q[2],
    "sw0": scales_w[0], "sw1": scales_w[1], "sw2": scales_w[2],
    "sb0": scales_b[0], "sb1": scales_b[1], "sb2": scales_b[2],
    "x_mean": x_mean, "x_std": x_std, "y_mean": y_mean, "y_std": y_std,
    "rmse_float": rmse_f, "rmse_int8": rmse_i,
    "mae_float": mae_f, "mae_int8": mae_i,
}
np.savez_compressed("tinyml_model.npz", **model_data)
print(f"[TinyML-Real] Guardado tinyml_model.npz")

# --- Figura: validación ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))

# Panel izquierdo: 14 días de test (336 h)
n_show = 14 * 24
offset = len(y_test) - n_show
idx = np.arange(n_show) / 24
ax1.plot(idx, y_test[offset:], color="#009E73", linewidth=1.2, label="Real (Open-Meteo)")
ax1.plot(idx, y_pred_int8[offset:], color="#56B4E9", linewidth=1.2, linestyle="--",
         label="Predicho (INT8)")
ax1.set_xlabel("Día")
ax1.set_ylabel("Temperatura exterior (°C)")
ax1.set_title("Predicción T_ext a 1 h — 14 días de test (datos reales)", fontweight="bold", fontsize=11)
ax1.legend(fontsize=9, frameon=False)
ax1.grid(alpha=0.3)

# Panel derecho: scatter
ax2.scatter(y_test, y_pred_int8, s=6, alpha=0.4, color="#0072B2")
lims = [float(min(y_test.min(), y_pred_int8.min())) - 0.5,
        float(max(y_test.max(), y_pred_int8.max())) + 0.5]
ax2.plot(lims, lims, color="#D55E00", linestyle=":", linewidth=1.2, label="y = x")
ax2.set_xlabel("T_ext real (°C)")
ax2.set_ylabel("T_ext predicho (°C)")
ax2.set_title(f"RMSE = {rmse_i:.2f} °C  |  MAE = {mae_i:.2f} °C", fontweight="bold", fontsize=11)
ax2.legend(fontsize=9, frameon=False)
ax2.set_xlim(lims)
ax2.set_ylim(lims)
ax2.grid(alpha=0.3)

fig.tight_layout()
fig.savefig(str(OUT) + "/fig5_tinyml_plot.pdf", dpi=300)
fig.savefig(str(OUT) + "/fig5_tinyml_plot.png", dpi=300)
plt.close()
print(f"[TinyML-Real] Figura guardada: figures/fig5_tinyml_plot.png/pdf")

# Resumen final
print(f"\n{'='*60}")
print(f"RESUMEN: TinyML entrenado con datos REALES Bogotá 2024")
print(f"  Horas totales: {N}  |  Train: {len(X_train)}  |  Test: {len(X_test)}")
print(f"  Parámetros: {total}  |  Float RMSE: {rmse_f:.2f}°C  |  INT8 RMSE: {rmse_i:.2f}°C")
print(f"  Degradación INT8 vs Float: {rmse_i - rmse_f:+.3f}°C")
print(f"{'='*60}")
