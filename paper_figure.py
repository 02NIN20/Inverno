#!/usr/bin/env python3
"""
paper_figure.py -- Figura estilo publicacion cientifica para proyecto de metodologia
Combina: modelo simulacion + datos reales (si disponibles) + diagrama del sistema
Genera: paper_figure.png (figura multi-panel calidad paper)
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

# ─── Configuracion estilo paper ───
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "lines.linewidth": 1.0,
})

COLORS = {
    "sim": "#1f77b4",
    "real": "#d62728",
    "co2": "#2ca02c",
    "rh": "#9467bd",
    "etr": "#8c564b",
    "vent": "#e377c2",
}


def load_simulation():
    """Carga datos simulados"""
    sim_path = Path("simulacion.csv")
    if not sim_path.exists():
        print("[!] simulacion.csv no encontrado. Ejecuta simulation.py primero.")
        return None
    return pd.read_csv(sim_path)


def load_real_data():
    """Carga datos reales del ESP32"""
    real_path = Path("datos_real.csv")
    if not real_path.exists() or real_path.stat().st_size == 0:
        return None
    df = pd.read_csv(real_path)
    # Rename columns to English
    df["time_s"] = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    return df


def create_paper_figure(sim_df, real_df, output="paper_figure.png"):
    """Genera figura de 4 paneles estilo paper cientifico"""

    fig = plt.figure(figsize=(8.5, 10))
    gs = gridspec.GridSpec(5, 2, figure=fig,
                           height_ratios=[1, 1, 1, 0.7, 0.6],
                           hspace=0.4, wspace=0.35)

    # ── Panel A: Temperatura y Humedad Relativa (ultimos 3 dias sim) ──
    ax1 = fig.add_subplot(gs[0, :])
    if sim_df is not None:
        mask = sim_df["day"] >= sim_df["day"].max() - 3
        d = sim_df[mask]
        hours = d["hour"] + (d["day"] - d["day"].min()) * 24
        ax1.plot(hours, d["Tin_C"], color=COLORS["sim"], label=r"$T_{in}$ Sim",
                 alpha=0.8)
        ax1.plot(hours, d["Tout_C"], color="gray", linestyle="--",
                 label=r"$T_{out}$", alpha=0.5)
        ax1_twin = ax1.twinx()
        ax1_twin.plot(hours, d["RH_pct"], color=COLORS["rh"], linestyle=":",
                      label=r"RH Sim", alpha=0.8)
        if real_df is not None:
            # Plot real data if columns exist
            pass
    ax1.set_ylabel(r"Temperatura ($^\circ$C)")
    ax1_twin.set_ylabel("Humedad Relativa (%)")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    ax1.set_title("(a) Temperatura y Humedad Relativa | Modelo 3 dias", loc="left",
                  fontweight="bold")

    # ── Panel B: CO2 estimado ──
    ax2 = fig.add_subplot(gs[1, :])
    if sim_df is not None:
        mask = sim_df["day"] >= sim_df["day"].max() - 3
        d = sim_df[mask]
        hours = d["hour"] + (d["day"] - d["day"].min()) * 24
        ax2.fill_between(hours, 350, d["Cin_ppm"], alpha=0.3, color=COLORS["co2"])
        ax2.plot(hours, d["Cin_ppm"], color=COLORS["co2"], label=r"$CO_2$ Sim")
        ax2.axhline(y=420, color="gray", linestyle="--", alpha=0.5,
                    label=r"$CO_2$ Ambiente (420 ppm)")
        if real_df is not None and "co2_est_ppm" in real_df.columns:
            r = real_df.dropna(subset=["co2_est_ppm"])
            if len(r) > 0:
                ax2.scatter(r["time_s"] / 3600.0, r["co2_est_ppm"],
                           color=COLORS["real"], s=5, alpha=0.6, label=r"$CO_2$ Real")
    ax2.set_ylabel(r"$CO_2$ (ppm)")
    ax2.legend(loc="upper right")
    ax2.set_title("(b) Concentracion de CO2 Estimada", loc="left", fontweight="bold")

    # ── Panel C: Evapotranspiracion ──
    ax3 = fig.add_subplot(gs[2, 0])
    if sim_df is not None:
        mask = sim_df["day"] >= sim_df["day"].max() - 3
        d = sim_df[mask]
        hours = d["hour"] + (d["day"] - d["day"].min()) * 24
        # Calculate hourly ETr rate
        etr_hourly = d["Etr_mm"].diff().fillna(0)
        ax3.fill_between(hours, 0, etr_hourly, color=COLORS["etr"],
                         alpha=0.5, label="ETr (mm/h)")
        ax3.plot(hours, etr_hourly, color=COLORS["etr"], alpha=0.8)
    ax3.set_ylabel("ETr (mm/h)")
    ax3.set_xlabel("Horas")
    ax3.set_title("(c) Evapotranspiracion de Referencia", loc="left",
                  fontweight="bold")

    # ── Panel D: Ventilacion ──
    ax4 = fig.add_subplot(gs[2, 1])
    if sim_df is not None:
        mask = sim_df["day"] >= sim_df["day"].max() - 3
        d = sim_df[mask]
        hours = d["hour"] + (d["day"] - d["day"].min()) * 24
        vent_state = (d["RH_pct"] > 85) | (d["Tin_C"] > 35)
        ax4.fill_between(hours, 0, vent_state.astype(float),
                         color=COLORS["vent"], alpha=0.3, step="post")
        ax4.plot(hours, d["RH_pct"], color=COLORS["rh"], alpha=0.7,
                 label="RH")
        ax4.axhline(y=85, color="red", linestyle="--", alpha=0.5,
                    label="Umbral 85%")
    ax4.set_ylabel("RH (%) / Ventilacion")
    ax4.set_xlabel("Horas")
    ax4.set_title("(d) Control de Ventilacion (RH > 85%)", loc="left",
                  fontweight="bold")
    ax4.legend(loc="upper right")

    # ── Panel E: Diagrama del sistema ──
    ax5 = fig.add_subplot(gs[3, :])
    ax5.set_xlim(0, 10)
    ax5.set_ylim(0, 3)
    ax5.axis("off")
    ax5.set_title("(e) Arquitectura del Sistema de Monitoreo", loc="left",
                  fontweight="bold")

    # Dibujar diagrama de bloques
    blocks = [
        (1, 1.5, "Sensores\n(AHT20+BMP280)", "#e8f5e9"),
        (3.5, 1.5, "ESP32-S3\nXIAO\n(Firmware C)", "#e3f2fd"),
        (6, 1.5, "Serial\n(CSV @115200)", "#fff3e0"),
        (8.5, 1.5, "Python\n(Sim.+Analisis)", "#fce4ec"),
    ]
    for x, y, label, color in blocks:
        rect = plt.Rectangle((x - 0.9, y - 0.5), 1.8, 1.0,
                             facecolor=color, edgecolor="black",
                             linewidth=0.8, alpha=0.7)
        ax5.add_patch(rect)
        ax5.text(x, y, label, ha="center", va="center", fontsize=7,
                 fontweight="bold")

    # Flechas
    arrows = [(2.8, 1.5, 2.6, 1.5), (5.1, 1.5, 5.1, 1.5),
              (7.5, 1.5, 7.6, 1.5)]
    for x1, y1, x2, y2 in arrows:
        ax5.annotate("", xy=(x2, y2), xytext=(x1, y1),
                     arrowprops=dict(arrowstyle="->", color="gray",
                                     lw=1.2))

    # ── Panel F: Tabla de metricas ──
    ax6 = fig.add_subplot(gs[4, :])
    ax6.axis("off")
    ax6.set_title("(f) Parametros del Sistema (Bogota, 2640 msnm)",
                  loc="left", fontweight="bold")

    table_data = [
        ["Parametro", "Valor", "Unidad", "Parametro", "Valor", "Unidad"],
        ["Presion atmosferica", "750", "hPa", "Vol. Invernadero", "50", "m$^3$"],
        ["Const. psicrometrica $\\gamma$", "0.048", "kPa/$^\\circ$C",
         "Area suelo", "20", "m$^2$"],
        ["Temp. exterior media", "14", "$^\\circ$C", "LAI", "2.5", "-"],
        ["CO$_2$ ambiente", "420", "ppm", "Poder calefactor", "2000", "W"],
        ["Umbral ventilacion RH", "85", "%", "Intervalo muestreo", "5", "s"],
    ]
    table = ax6.table(cellText=table_data, loc="center",
                      cellLoc="center", edges="horizontal")
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    for key, cell in table.get_celld().items():
        cell.set_linewidth(0.3)
        if key[0] == 0:
            cell.get_text().set_fontweight("bold")
            cell.set_facecolor("#f0f0f0")

    # ── Titulo general ──
    fig.suptitle(
        "Sistema de Optimizacion de Clima en Invernadero Andino\n"
        "Validacion con ESP32-S3 + Sensores AHT20/BMP280",
        fontsize=12, fontweight="bold", y=0.99)

    # ── Footer ──
    fig.text(0.5, 0.01,
             "Proyecto de Metodologia de la Investigacion | "
             "Bogota D.C., 2026 | XIAO ESP32S3 + ESP-IDF v6.1",
             ha="center", fontsize=7, fontstyle="italic", color="gray")

    fig.savefig(output, bbox_inches="tight")
    print(f"[+] Figura guardada: {output}")
    plt.close(fig)


def main():
    print("[*] Generando figura estilo paper...")
    sim_df = load_simulation()
    real_df = load_real_data()

    if sim_df is None:
        print("[!] Ejecutando simulacion primero...")
        from simulation import run_simulation
        sim_df = run_simulation(days=7, dt=60.0)
        sim_df.to_csv("simulacion.csv", index=False, float_format="%.4f")

    if real_df is not None:
        print(f"[+] Datos reales cargados: {len(real_df)} muestras")
    else:
        print("[i] Sin datos reales (datos_real.csv no encontrado)")

    create_paper_figure(sim_df, real_df)
    print("[+] Listo. Abre paper_figure.png")


if __name__ == "__main__":
    main()
