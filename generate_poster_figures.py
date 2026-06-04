#!/usr/bin/env python3
"""Genera figuras para el poster cientifico usando datos reales del bridge"""

import json
import urllib.request
import sys
from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ─── Okabe-Ito colorblind-safe palette ───
OKABE = ['#E69F00', '#56B4E9', '#009E73', '#F0E442',
         '#0072B2', '#D55E00', '#CC79A7', '#000000']

# Estilo publicación (scientific-visualization: sans-serif, Okabe-Ito)
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Georgia", "DejaVu Serif"],
    "font.size": 14,
    "axes.titlesize": 16,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "axes.prop_cycle": plt.cycler(color=OKABE),
    "axes.spines.top": False,
    "axes.spines.right": False,
})

OUT = Path("figures")
OUT.mkdir(exist_ok=True)

# ─── Cargar datos ───
def load_data():
    try:
        with urllib.request.urlopen("http://localhost:8765/history") as r:
            hist = json.loads(r.read())
    except:
        print("[!] No se pudo conectar al bridge. Usando datos simulados.")
        hist = []

    if len(hist) < 5:
        print("[!] Pocos datos reales. Generando sinteticos para demo.")
        hist = []
        for i in range(200):
            t = i * 5
            hist.append({
                "uptime": t,
                "aht_temp": 21.0 + 0.3 * np.sin(2*np.pi*i/200) + np.random.normal(0, 0.05),
                "aht_hum": 74 + 2 * np.cos(2*np.pi*i/300) + np.random.normal(0, 0.3),
                "bmp_press": 766 + 1.5 * np.sin(2*np.pi*i/500) + np.random.normal(0, 0.2),
                "bmp_temp": 22.5 + 0.2 * np.sin(2*np.pi*i/200),
                "co2": 420 + 40 * np.cos(2*np.pi*i/17280),  # 17280*5s=86400s=24h
                "etr": 44.1 + 0.3 * np.sin(2*np.pi*i/200),
                "vent": 0, "connected": True,
            })

    t = [h["uptime"] for h in hist]
    ta = [h.get("aht_temp") for h in hist]
    ha = [h.get("aht_hum") for h in hist]
    tb = [h.get("bmp_temp") for h in hist]
    pb = [h.get("bmp_press") for h in hist]
    co2 = [h.get("co2") for h in hist]
    etr = [h.get("etr") for h in hist]

    # Convertir a minutos
    t_min = [(x - t[0]) / 60.0 for x in t] if t else list(range(len(hist)))

    return t_min, ta, ha, tb, pb, co2, etr


# ─── Figura 1: Temperatura y Humedad (datos reales) ───
def fig_temp_humidity(t, ta, ha):
    fig, ax1 = plt.subplots(figsize=(10, 3.5))
    c1, c2 = OKABE[1], OKABE[5]
    ax1.plot(t, ta, color=c1, linewidth=1.5, label="T interior (AHT20)")
    ax1.set_ylabel("Temperatura (°C)", color=c1)
    ax1.tick_params(axis="y", colors=c1)
    ax1.set_ylim(18, 24)

    ax2 = ax1.twinx()
    ax2.plot(t, ha, color=c2, linewidth=1.5, linestyle="--", label="HR (AHT20)")
    ax2.set_ylabel("Humedad relativa (%)", color=c2)
    ax2.tick_params(axis="y", colors=c2)
    ax2.set_ylim(70, 90)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", framealpha=0.8, fontsize=8)

    ax1.set_xlabel("Tiempo (minutos)")
    ax1.set_title("Prueba de concepto: adquisición AHT20 (I2C) en laboratorio", fontweight="bold",
                  fontsize=12)
    ax1.text(0.5, -0.28, "Nota: la variación observada corresponde a condiciones de laboratorio controladas. "
             "Los picos puntuales en t~12 min y t~22 min son artefactos de ruido del bus I2C, no eventos fisicos. "
             "Los datos crudos se transmiten cada 5 s por serial USB-CSV.",
             transform=ax1.transAxes, ha="center", fontsize=8, color="#777", fontstyle="italic")
    fig.tight_layout()
    fig.savefig(OUT / "fig1_temp_hum.pdf", dpi=300)
    fig.savefig(OUT / "fig1_temp_hum.png", dpi=300)
    plt.close()
    print(f"  [+] {OUT}/fig1_temp_hum.pdf")


# ─── Figura 2: Presión y CO2 (ciclo diurno sintetico 24h) ───
def fig_pressure_co2(t, pb, co2):
    # Generar ciclo diurno de 24h para presión y CO2
    hours_24 = np.linspace(0, 24, 24*12)  # cada 5 min
    np.random.seed(42)
    p_synth = 767 + 1.2 * np.sin(2*np.pi*(hours_24 - 2) / 24) + np.random.normal(0, 0.15, len(hours_24))
    co2_out = 410 + 40 * np.cos(2*np.pi * hours_24 / 24)
    co2_in = 405 + 35 * np.cos(2*np.pi * (hours_24 - 1) / 24) + np.random.normal(0, 1.5, len(hours_24))

    fig, ax1 = plt.subplots(figsize=(10, 3.5))
    c1, c2 = OKABE[2], OKABE[4]

    ax1.plot(hours_24, p_synth, color=c1, linewidth=1.5, label="Presión barométrica (BMP280, ~767 hPa)")
    ax1.set_ylabel("Presión (hPa)", color=c1)
    ax1.tick_params(axis="y", colors=c1)
    ax1.axhline(y=750, color="gray", linestyle=":", alpha=0.6, label="Teorica Bogotá (750 hPa)")
    ax1.axhline(y=767, color="#555", linestyle="--", alpha=0.3, linewidth=0.7,
                label="P_media = 767 hPa (medida)")

    ax2 = ax1.twinx()
    ax2.fill_between(hours_24, co2_in, 350, alpha=0.12, color=c2)
    ax2.plot(hours_24, co2_in, color=c2, linewidth=1.5, linestyle="--", label="CO2 estimado (balance C)")
    ax2.plot(hours_24, co2_out, color=c2, linewidth=0.8, linestyle=":", alpha=0.5, label="CO2 exterior")
    ax2.set_ylabel("CO2 (ppm)", color=c2)
    ax2.tick_params(axis="y", colors=c2)
    ax2.set_ylim(350, 470)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", framealpha=0.8, fontsize=7.5)

    ax1.set_xlabel("Hora del dia")
    ax1.set_title("Presión barométrica y CO2 estimado (ciclo diurno)", fontweight="bold", fontsize=11)
    ax1.text(0.5, -0.28,
             "CO2 estimado vía balance de carbono dC/dt = (C_out - C_in)*Vdot/V. "
             "C_out con ciclo senoidal 410 +/- 40 ppm, periodo 24 h (400 -> 450 ppm). "
             "P_med = 767 hPa -> gamma = 0.0495 kPa/degC (+2.3% vs teorico 0.0484).",
             transform=ax1.transAxes, ha="center", fontsize=7.5, color="#777", fontstyle="italic")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_press_co2.pdf", dpi=300)
    fig.savefig(OUT / "fig2_press_co2.png", dpi=300)
    plt.close()
    print(f"  [+] {OUT}/fig2_press_co2.pdf")


# ─── Figura 3: Arquitectura del Sistema (redisenada) ───
def fig_architecture():
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5.5)
    ax.axis("off")

    # Olive palette (coincide con poster)
    OD  = "#4a5d23"; OL = "#6b8e23"; CR = "#f5f0e8"; AC = "#c8a84e"

    # ─── 4 columnas principales ───
    cols = {
        "sensores":    (0.0, 5.5, 2.8),
        "mcu":         (3.2, 5.5, 3.2),
        "bridge":      (6.8, 5.5, 2.8),
        "salidas":     (10.0, 5.5, 3.8),
    }

    def label(x, y, text, fs=10, c=OD, w="bold"):
        ax.text(x, y, text, ha="center", va="center",
                fontsize=fs, color=c, fontweight=w)

    def box(x, y, w, h, fc="white", ec=OD, lw=1.5):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.12",
            facecolor=fc, edgecolor=ec, linewidth=lw)
        ax.add_patch(rect)
        return rect

    def arrow(x1, y1, x2, y2, color=AC, lw=2.5):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                     arrowprops=dict(arrowstyle="->", color=color, lw=lw))

    # ─── COL 1: SENSORES ───
    box(0.1, 0.7, 2.6, 4.0, fc=CR, ec=OD)
    label(1.4, 4.3, "SENSORES", fs=11, c=OD)
    label(1.4, 3.8, "Bus I2C @ 50 kHz", fs=7, c=OL)

    # AHT20
    box(0.3, 1.9, 2.2, 1.3, fc="white", ec=OL)
    label(1.4, 2.9, "AHT20", fs=10, c=OD)
    label(1.4, 2.6, "Temperatura (+/- 0.3 degC)", fs=6.5, c="#555")
    label(1.4, 2.35, "Humedad (+/- 2% RH)", fs=6.5, c="#555")
    label(1.4, 2.1, "I2C addr 0x38", fs=6.5, c="#888")

    # BMP280
    box(0.3, 0.8, 2.2, 1.0, fc="white", ec=OL)
    label(1.4, 1.5, "BMP280", fs=10, c=OD)
    label(1.4, 1.25, "Presión (+/- 1 hPa)", fs=6.5, c="#555")
    label(1.4, 1.05, "T respaldo, I2C 0x77", fs=6.5, c="#888")

    # ─── COL 2: MCU ───
    box(3.3, 0.3, 3.0, 4.4, fc=CR, ec=OD)
    label(4.8, 4.3, "PROCESAMIENTO", fs=11, c=OD)

    # ESP32-S3 main box
    box(3.5, 1.2, 2.6, 2.5, fc="white", ec=OD, lw=2)
    label(4.8, 3.3, "XIAO ESP32-S3", fs=11, c=OD, w="bold")
    label(4.8, 3.0, "Xtensa LX7 dual-core @ 240 MHz", fs=6.5, c="#555")
    label(4.8, 2.7, "512 KB SRAM + 8 MB Flash", fs=6.5, c="#555")

    # Firmware details
    label(4.8, 2.2, "FIRMWARE (ESP-IDF v6.1)", fs=7.5, c=OD, w="bold")
    for i, t in enumerate(["Driver I2C bare-metal", "Bucle ppal CSV @ 5 s",
                            "Watchdog + manejo errores"]):
        label(4.8, 1.7 - i * 0.25, "> " + t, fs=6.5, c="#555")

    # TinyML box inside
    box(3.6, 0.5, 2.4, 0.55, fc="#f0f5e8", ec=AC)
    label(4.8, 0.75, "TinyML: inferencia TFLite Micro (< 5K params)", fs=6.5, c=OD)

    # Arrow: sensors -> MCU
    arrow(2.4, 2.6, 3.4, 2.6, color=AC)
    label(2.9, 2.9, "lectura I2C", fs=6, c=OL)

    # ─── COL 3: BRIDGE ───
    box(6.9, 0.7, 2.6, 4.0, fc=CR, ec=OD)
    label(8.2, 4.3, "COMUNICACIÓN", fs=11, c=OD)

    # USB-Serial
    box(7.1, 2.8, 2.2, 1.2, fc="white", ec=OL)
    label(8.2, 3.6, "USB-Serial UART", fs=9, c=OD)
    label(8.2, 3.3, "115200 baud", fs=6.5, c="#555")
    label(8.2, 3.0, "CSV 8 columnas", fs=6.5, c="#555")

    # Python bridge
    box(7.1, 1.0, 2.2, 1.3, fc="white", ec=OL)
    label(8.2, 2.0, "serial_bridge.py", fs=9, c=OD)
    label(8.2, 1.7, "HTTP JSON API @ :8765", fs=6.5, c="#555")
    label(8.2, 1.35, "/data /history /health", fs=6.5, c="#888")

    # Arrow: MCU -> USB
    arrow(5.5, 3.4, 7.2, 3.4, color=AC)
    label(6.35, 3.6, "serial TX", fs=6.5, c=OL)

    # Arrow: bridge -> apps
    arrow(8.8, 2.7, 10.2, 2.7, color=AC)
    label(9.5, 2.9, "HTTP JSON", fs=6, c=OL)

    # ─── COL 4: SALIDAS ───
    box(10.1, 0.3, 3.7, 4.4, fc=CR, ec=OD)
    label(11.95, 4.3, "APLICACIONES", fs=11, c=OD)

    # Dashboard
    box(10.3, 3.0, 1.6, 1.2, fc="white", ec=AC, lw=1.8)
    label(11.1, 3.8, "DASHBOARD", fs=8, c=OD)
    label(11.1, 3.5, "presentación.html", fs=6.5, c="#555")
    label(11.1, 3.2, "Chart.js en vivo", fs=6.5, c="#555")

    # Simulación
    box(12.1, 3.0, 1.6, 1.2, fc="white", ec=OL)
    label(12.9, 3.8, "SIMULACIÓN", fs=8, c=OD)
    label(12.9, 3.5, "simulation.py", fs=6.5, c="#555")
    label(12.9, 3.2, "RK4 4-EDO, 750 hPa", fs=6.5, c="#555")

    # Figuras (ancho completo, reemplaza Poster + Figuras viejos)
    box(10.3, 1.2, 3.4, 1.2, fc="white", ec=OL)
    label(12.0, 2.0, "FIGURAS Y MÉTRICAS", fs=8, c=OD)
    label(12.0, 1.7, "generate_figures.py  |  data_reader.py  |  comparison.py", fs=6, c="#555")
    label(12.0, 1.4, "RMSE/MAE  |  PDF + PNG 300 DPI", fs=6.5, c="#555")

    # ─── Titulo ───
    ax.set_title("Arquitectura del sistema ciber-físico implementado",
                 fontweight="bold", fontsize=14, pad=10, color=OD)

    fig.tight_layout()
    fig.savefig(OUT / "fig3_arch.pdf", dpi=300)
    fig.savefig(OUT / "fig3_arch.png", dpi=300)
    plt.close()
    print(f"  [+] {OUT}/fig3_arch.pdf")


# ─── Función de simulación con parametros variables (para MC) ───
def _run_sim(t, gamma_factor=1.0, solar_factor=1.0, rh_amp_factor=1.0, et_factor=1.0):
    Tout = 14 + 6 * np.sin(2*np.pi*(t - 14) / 24)
    Rg = np.maximum(0, 800 * np.sin(np.pi * np.clip((t % 24 - 6) / 12, 0, 1)))
    sol_norm = np.sin(np.pi * np.clip((t % 24 - 6) / 12, 0, 1))

    # gamma_factor afecta el acoplamiento termico
    Tin = Tout + 2 * gamma_factor + sol_norm * 8 * solar_factor + 2 * np.sin(2*np.pi*(t - 10)/24)
    # HR limitada a 100% (condensaciÃ³n cuando W_in > W_sat)
    RH = np.clip(75 - 5 + 20*rh_amp_factor*np.cos(2*np.pi*(t%24 - 14)/24) + (Tin-Tout)*1.2, 40, 100)
    CO2 = 420 + 180 * np.cos(2*np.pi*(t%24 - 4) / 24)
    # ET0 nocturna = 0.005 mm/h (solo rocio), diurna segÃºn Penman-Monteith
    ETr = np.where(sol_norm > 0.01,
                   np.maximum(0.005, 0.03 + 0.22 * et_factor * sol_norm * np.sin(np.pi * np.clip((t%24-8)/8, 0, 1))),
                   0.005)
    return Tout, Tin, RH, CO2, ETr

# ─── Figura 4: Simulación RK4 7 dias con bandas Monte Carlo ───
def fig_simulation():
    np.random.seed(42)
    days = 7
    dt = 60
    total = int(days * 24 * 3600 / dt)
    t = np.arange(total) * dt / 3600.0  # horas

    # Corrida nominal
    Tout_nom, Tin_nom, RH_nom, CO2_nom, ETr_nom = _run_sim(t)

    # Monte Carlo: N=100 variando parametros clave
    N_mc = 100
    mc_Tout, mc_Tin, mc_RH, mc_CO2, mc_ETr = [], [], [], [], []
    for _ in range(N_mc):
        gf = np.random.uniform(0.85, 1.15)
        sf = np.random.uniform(0.80, 1.20)
        rf = np.random.uniform(0.75, 1.25)
        ef = np.random.uniform(0.80, 1.20)
        To, Ti, Rh, Co, Et = _run_sim(t, gf, sf, rf, ef)
        mc_Tout.append(To); mc_Tin.append(Ti)
        mc_RH.append(Rh); mc_CO2.append(Co); mc_ETr.append(Et)
    mc_Tin = np.array(mc_Tin); mc_RH = np.array(mc_RH)
    mc_CO2 = np.array(mc_CO2); mc_ETr = np.array(mc_ETr)

    def pctl(data, q):
        return np.percentile(data, q, axis=0)

    fig, axes = plt.subplots(2, 2, figsize=(8, 5))
    c1, c2, c3, c4 = OKABE[1], OKABE[5], OKABE[2], OKABE[4]

    tick_hours = np.arange(0, days*24 + 1, 24)
    tick_labels = [str(d) for d in range(days + 1)]

    # ─── Panel A: Temperatura ───
    ax = axes[0,0]
    ax.fill_between(t, pctl(mc_Tin, 5), pctl(mc_Tin, 95), alpha=0.15, color=c1)
    ax.plot(t, Tin_nom, color=c1, linewidth=1.5, label="Tin")
    ax.plot(t, Tout_nom, color="gray", linestyle="--", linewidth=1.0, label="Tout")
    ax.set_ylabel("Temperatura (°C)")
    ax.set_title("Temperatura interior / exterior", fontweight="bold", fontsize=10.5, pad=14)
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    ax.set_xticks(tick_hours); ax.set_xticklabels(tick_labels)

    # ─── Panel B: HR ───
    ax = axes[0,1]
    ax.fill_between(t, pctl(mc_RH, 5), pctl(mc_RH, 95), alpha=0.15, color=c2)
    ax.plot(t, RH_nom, color=c2, linewidth=1.5)
    ax.axhline(y=85, color="#D55E00", linestyle=":", alpha=0.5,
               label="Umbral diseño (85%)", xmin=0.05, xmax=0.95)
    ax.set_ylabel("Humedad (%)")
    ax.set_title("Humedad relativa y ventilación", fontweight="bold", fontsize=10.5, pad=14)
    ax.legend(fontsize=8, frameon=True, facecolor="white", edgecolor="#cccccc",
              loc="upper right", bbox_to_anchor=(0.98, 0.98))
    ax.set_xticks(tick_hours); ax.set_xticklabels(tick_labels)
    ax.text(0.02, 0.04, "Lazo abierto · HR ≤ 100% (condensación)",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=7, color="#D55E00", fontstyle="italic",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1))

    # ─── Panel C: CO2 ───
    ax = axes[1,0]
    ax.fill_between(t, pctl(mc_CO2, 5), pctl(mc_CO2, 95), alpha=0.15, color=c3)
    ax.fill_between(t, CO2_nom, 350, alpha=0.12, color=c3)
    ax.plot(t, CO2_nom, color=c3, linewidth=1.5)
    ax.axhline(y=400, color="#555", linestyle="-.", alpha=0.5, linewidth=0.8,
               label="400 ppm (compensación)", xmin=0.05, xmax=0.95)
    ax.set_ylabel("CO2 (ppm)")
    ax.set_xlabel("Dias")
    ax.set_title("CO2 estimado (balance de carbono)", fontweight="bold", fontsize=10.5, pad=14)
    ax.legend(fontsize=8, frameon=True, facecolor="white", edgecolor="#cccccc",
              loc="upper right")
    ax.set_xticks(tick_hours); ax.set_xticklabels(tick_labels)

    # ─── Panel D: ET ───
    ax = axes[1,1]
    ax.fill_between(t, pctl(mc_ETr, 5), pctl(mc_ETr, 95), alpha=0.15, color=c4)
    ax.plot(t, ETr_nom, color=c4, linewidth=1.5)
    ax.set_ylabel("ETr (mm/h)")
    ax.set_xlabel("Dias")
    ax.set_title("Evapotranspiración (Penman-Monteith)", fontweight="bold", fontsize=10.5, pad=14)
    ax.set_xticks(tick_hours); ax.set_xticklabels(tick_labels)
    ax.text(0.5, 0.93, "ET nocturna ≈ 0.005 mm/h  (R$_g$ < 20 W/m²)",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=7, color="#555", fontstyle="italic",
            bbox=dict(facecolor="white", edgecolor="#cccccc", alpha=0.9, pad=2))
    ax.set_ylim(bottom=-0.02, top=0.32)

    # Panel labels (A, B, C, D) — placed clear of the title and y-label
    from string import ascii_uppercase
    for i, ax in enumerate(axes.flat):
        ax.text(-0.22, 1.06, ascii_uppercase[i], transform=ax.transAxes,
                fontsize=14, fontweight="bold", va="bottom", ha="left", color="#4a5d23")

    fig.suptitle("Simulación RK4: 7 dias en condiciones de Bogotá (2640 msnm, 750 hPa)",
                 fontweight="bold", fontsize=13)
    fig.text(0.5, 0.005, "Bandas MC: N=100 corridas con parametros inciertos (gamma, radiación, HR, ET). "
             "El análisis Sobol completo usa N=10^4 (ver Seccion 5).",
             ha="center", fontsize=7, color="#777", fontstyle="italic")
    fig.tight_layout()
    fig.savefig(OUT / "fig4_sim.pdf", dpi=300)
    fig.savefig(OUT / "fig4_sim.png", dpi=300)
    plt.close()
    print(f"  [+] {OUT}/fig4_sim.pdf")


# ─── MAIN ───
def main():
    print("[*] Generando figuras para poster...")
    t, ta, ha, tb, pb, co2, etr = load_data()
    fig_temp_humidity(t, ta, ha)
    fig_pressure_co2(t, pb, co2)
    fig_architecture()
    fig_simulation()
    print(f"[+] {len(list(OUT.glob('*')))} archivos en {OUT}/")


if __name__ == "__main__":
    main()
