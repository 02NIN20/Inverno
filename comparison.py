#!/usr/bin/env python3
"""
comparison.py -- Compara simulacion vs datos reales con metricas RMSE/MAE
Uso: python comparison.py [simulacion.csv] [datos_real.csv]
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def rmse(y_true, y_pred):
    return np.sqrt(np.mean((y_true - y_pred) ** 2))


def mae(y_true, y_pred):
    return np.mean(np.abs(y_true - y_pred))


def main():
    sim_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("simulacion.csv")
    real_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("datos_real.csv")

    if not sim_path.exists():
        print(f"[!] {sim_path} no encontrado. Ejecuta simulation.py primero.")
        sys.exit(1)

    sim = pd.read_csv(sim_path)
    print(f"[+] Simulacion: {len(sim)} filas")

    if not real_path.exists() or real_path.stat().st_size == 0:
        print(f"[!] {real_path} no encontrado o vacío.")
        print("[*] Generando solo graficos de simulacion...")
        fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        mask = sim["day"] >= sim["day"].max() - 2
        d = sim[mask]
        hours = d["hour"] + (d["day"] - d["day"].min()) * 24
        axes[0].plot(hours, d["Tin_C"])
        axes[0].set_ylabel("Tin (C)")
        axes[1].plot(hours, d["RH_pct"])
        axes[1].set_ylabel("RH (%)")
        axes[2].plot(hours, d["Cin_ppm"])
        axes[2].set_ylabel("CO2 (ppm)")
        axes[2].set_xlabel("Horas")
        fig.suptitle("Simulacion Invernadero Andino (ultimos 2 dias)")
        fig.savefig("simulacion_plots.png", dpi=150)
        print("[+] simulacion_plots.png guardado")
        return

    real = pd.read_csv(real_path)
    real["time_s"] = pd.to_numeric(real.iloc[:, 0], errors="coerce")
    print(f"[+] Datos reales: {len(real)} filas")

    # Alinear timestamps (resamplear simulacion a timestamps reales)
    sim_t = sim["time_s"].values
    real_t = real["time_s"].dropna().values

    sim_temp = np.interp(real_t, sim_t, sim["Tin_C"].values)
    sim_rh = np.interp(real_t, sim_t, sim["RH_pct"].values)
    sim_co2 = np.interp(real_t, sim_t, sim["Cin_ppm"].values)

    # Extraer columnas reales (ajustar segun cabecera)
    real_temp = real.iloc[:, 2].values if real.shape[1] > 2 else None
    real_rh = real.iloc[:, 3].values if real.shape[1] > 3 else None

    # Calcular metricas
    print("\n--- Metricas de Error ---")
    for var_name, sim_vals, real_vals, unit in [
        ("Temperatura", sim_temp, real_temp, "C"),
        ("Humedad Rel.", sim_rh, real_rh, "%"),
        ("CO2", sim_co2, None, "ppm"),
    ]:
        if real_vals is not None:
            mask = ~np.isnan(sim_vals) & ~np.isnan(real_vals)
            if mask.sum() > 0:
                print(f"  {var_name}: RMSE={rmse(sim_vals[mask], real_vals[mask]):.3f} {unit}  "
                      f"MAE={mae(sim_vals[mask], real_vals[mask]):.3f} {unit}")

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    fig.suptitle("Comparacion Simulacion vs Datos Reales | Invernadero Andino")

    for i, (var, sim_vals, real_vals, ylabel) in enumerate([
        ("Temperatura", sim_temp, real_temp, "Temperatura (C)"),
        ("Humedad Relativa", sim_rh, real_rh, "Humedad Relativa (%)"),
        ("CO2", sim_co2, None, "CO2 (ppm)"),
    ]):
        ax = axes[i]
        ax.plot(real_t / 3600.0, sim_vals, label="Simulacion", alpha=0.8,
                color="#1f77b4", linewidth=1)
        if real_vals is not None:
            mask = ~np.isnan(real_vals)
            ax.scatter(real_t[mask] / 3600.0, real_vals[mask],
                      label="Real (ESP32)", alpha=0.6, s=10,
                      color="#d62728")
        ax.set_ylabel(ylabel)
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Tiempo (horas)")
    fig.savefig("comparacion_sim_real.png", dpi=200, bbox_inches="tight")
    print("[+] comparacion_sim_real.png guardado")


if __name__ == "__main__":
    main()
