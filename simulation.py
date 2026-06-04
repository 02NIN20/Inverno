#!/usr/bin/env python3
"""
simulation.py -- Modelo dinamico de invernadero andino (4 EDOs acopladas)
Basado en el modelo de la documentacion del proyecto.
Resuelve con RK4 sobre 7 dias, condiciones de Bogota (2640 msnm, 750 hPa).
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ─── Constantes para Bogota (2640 msnm) ───
P_ATM = 750.0         # hPa
GAMMA = 0.048         # kPa/C (constante psicrometrica corregida)
CP = 1005.0           # J/(kg*K) calor especifico del aire
RHO = 1.2             # kg/m3 densidad del aire
VOL = 50.0            # m3 volumen del invernadero
AREA = 20.0           # m2 area del suelo
H_CROP = 0.3          # m altura del cultivo
LAT = 4.6             # grados (Bogota)
T_OUT_MEAN = 14.0     # C temp externa media
T_OUT_AMP = 6.0       # C amplitud diurna
RH_OUT = 75.0         # % humedad externa
CO2_OUT = 420.0       # ppm CO2 externo
WIND = 0.8            # m/s velocidad del viento

# Parametros de ventilacion
VENT_AREA = 0.5       # m2 area de ventilacion
CD = 0.6              # coeficiente de descarga

# Parametros de calefaccion
HEATER_POWER = 2000.0 # W

# Parametros del cultivo (Penman-Monteith)
RS_MIN = 70.0         # s/m resistencia estomatica minima
RA = 50.0             # s/m resistencia aerodinamica
LAI = 2.5             # indice de area foliar

# Parametros de CO2
P_MAX = 2.5e-6        # kg/m2/s tasa maxima de fotosintesis
CO2_COMP = 40.0       # ppm punto de compensacion de CO2
TAU_CO2 = 3600.0      # s constante de tiempo de mezcla

# Radiacion solar
SOLAR_CONST = 1367.0  # W/m2
TAU_ATM = 0.65        # transmitancia atmosferica
ALBEDO = 0.23         # albedo del cultivo
SOLAR_MAX = SOLAR_CONST * TAU_ATM * np.sin(np.radians(LAT + 23.5))


def saturation_pressure(temp_C):
    """Presion de saturacion en kPa (formula de Tetens)"""
    return 0.6108 * np.exp(17.27 * temp_C / (temp_C + 237.3))


def slope_saturation(temp_C):
    """Derivada de la presion de saturacion (kPa/C)"""
    es = saturation_pressure(temp_C)
    return 4098.0 * es / (temp_C + 237.3) ** 2


def solar_radiation(t, day_length=12.0, sunrise=6.0):
    """Radiacion solar sinusoidal diurna (W/m2)"""
    hour = (t / 3600.0) % 24.0
    if hour < sunrise or hour > sunrise + day_length:
        return 0.0
    frac = (hour - sunrise) / day_length
    return SOLAR_MAX * np.sin(np.pi * frac)


def outdoor_temperature(t):
    """Temperatura exterior con ciclo diurno (C)"""
    hour = (t / 3600.0) % 24.0
    return T_OUT_MEAN + T_OUT_AMP * np.sin(2 * np.pi * (hour - 14) / 24.0)


def ventilation_rate(temp_in, temp_out, wind_speed, vent_state):
    """Tasa de ventilacion (m3/s)"""
    if not vent_state:
        return 0.2 * VENT_AREA * wind_speed / 3600.0  # infiltracion minima
    g = 9.81
    h = 1.5  # altura de la apertura
    dt = abs(temp_in - temp_out)
    if dt < 0.01:
        dt = 0.01
    stack = CD * VENT_AREA * np.sqrt(2 * g * h * dt / (temp_in + 273.0))
    wind = 0.5 * CD * VENT_AREA * wind_speed
    return np.sqrt(stack**2 + wind**2)


def rhs(t, y):
    """Sistema de 4 EDOs: Tin, Win, Cin, Etr acumulado"""
    Tin, Win, Cin, _Etr = y

    # --- Variables auxiliares ---
    Tout = outdoor_temperature(t)
    Rg = solar_radiation(t)
    es_in = saturation_pressure(Tin)
    es_out = saturation_pressure(Tout)
    ea_out = es_out * (RH_OUT / 100.0)
    Win_sat = 0.622 * es_in / (P_ATM / 10.0 - es_in) * 1000.0  # g/kg
    Wout = 0.622 * ea_out / (P_ATM / 10.0 - ea_out) * 1000.0

    # --- Control de ventilacion ---
    RH_in = (Win / Win_sat) * 100.0 if Win_sat > 0 else 0
    vent = (RH_in > 85.0 or Tin > 35.0)
    Q_vent = ventilation_rate(Tin, Tout, WIND, vent)

    # --- Control de calefaccion ---
    heater = 0.0
    if Tin < 12.0:
        heater = HEATER_POWER
    elif Tin < 15.0:
        heater = HEATER_POWER * (15.0 - Tin) / 3.0

    # --- Evapotranspiracion Fisiologica (Penman-Monteith) ---
    delta = slope_saturation(Tin) * 1000.0  # Pa/C
    gamma = GAMMA * 1000.0                  # Pa/C
    Rn = Rg * (1.0 - ALBEDO)                 # W/m2
    G = 0.1 * Rn                             # W/m2 flujo de calor en suelo
    
    es_Pa = es_in * 1000.0                  # Pa
    ea_Pa = es_Pa * (RH_in / 100.0) if RH_in > 0 else ea_out * 1000.0
    vpd_Pa = max(es_Pa - ea_Pa, 0.0)        # Pa
    
    A_leaf = LAI * AREA                     # m2 de hojas

    if Rg > 10.0:
        rs = RS_MIN
        # PM formula
        num_pm = delta * (Rn - G) + RHO * CP * (vpd_Pa) / RA
        den_pm = delta + gamma * (1.0 + rs / RA)
        ET_flux = num_pm / den_pm            # W/m2
        ET_kg = (ET_flux / 2.45e6) * A_leaf # kg/s (tasa de vapor de agua)
    else:
        # Transpiracion nocturna minima (rocio / transpiracion residual)
        ET_kg = (0.005 * AREA) / 3600.0     # 0.005 mm/h -> kg/s

    ET_mm_h = (ET_kg * 3600.0) / AREA       # mm/h

    # --- Balance de temperatura ---
    Q_solar = Rg * (1.0 - ALBEDO) * AREA * 0.5
    Q_vent_sensible = RHO * CP * Q_vent * (Tin - Tout)
    Q_et_latent = ET_kg * 2.45e6            # W (calor latente)
    dTin = (Q_solar + heater - Q_vent_sensible - Q_et_latent) / (RHO * CP * VOL)
    dTin = np.clip(dTin, -0.5, 0.5)         # limite razonable de cambio

    # --- Balance de humedad ---
    Q_et_hum = ET_kg / RHO                  # m3 vapor/s equivalente
    Q_vent_hum = Q_vent * (Win - Wout) / 1000.0
    dWin = (Q_et_hum - Q_vent_hum) / VOL * 1000.0  # g/kg por s
    dWin = np.clip(dWin, -5.0, 5.0)

    # --- Balance de CO2 (corregido) ---
    P_n = 0.0
    if Cin > CO2_COMP and Rg > 10.0:
        P_n = P_MAX * min(Cin - CO2_COMP, 400.0) / max(Cin + 200.0, 1.0)
        P_n *= Rg / (Rg + 100.0)
    
    # fotosintesis consume P_n * A_leaf kg/s de CO2
    # convertimos a ppm/s: dCin_photo = -P_n * A_leaf * 1e6 / (RHO * VOL)
    dCin = -P_n * A_leaf * 1e6 / (RHO * VOL)
    dCin += (CO2_OUT - Cin) / TAU_CO2       # ventilacion/mezcla
    dCin = np.clip(dCin, -10.0, 10.0)

    # --- ETr acumulado (mm/s) ---
    dEtr = ET_mm_h / 3600.0

    return np.array([dTin, dWin, dCin, dEtr], dtype=np.float64)


def rk4_step(t, y, dt):
    k1 = rhs(t, y)
    k2 = rhs(t + dt/2, y + dt/2 * k1)
    k3 = rhs(t + dt/2, y + dt/2 * k2)
    k4 = rhs(t + dt, y + dt * k3)
    return y + dt / 6 * (k1 + 2*k2 + 2*k3 + k4)


def run_simulation(days=7, dt=60.0):
    """
    Ejecuta la simulacion del invernadero.
    Retorna DataFrame con series de tiempo.
    """
    total_time = days * 24 * 3600
    n_steps = int(total_time / dt)

    y = np.array([14.0,   # Tin (C)
                   8.0,   # Win (g/kg)
                 420.0,   # Cin (ppm)
                   0.0])  # Etr acumulado (mm)

    t = 0.0
    results = []

    for step in range(n_steps):
        results.append([t] + list(y) + [solar_radiation(t),
                                          outdoor_temperature(t)])

        y = rk4_step(t, y, dt)
        t += dt

    columns = ["time_s", "Tin_C", "Win_g_kg", "Cin_ppm", "Etr_mm",
               "Rg_W_m2", "Tout_C"]
    df = pd.DataFrame(results, columns=columns)

    # Calcular humedad relativa con proteccion contra division por cero
    df["es_kPa"] = df["Tin_C"].apply(saturation_pressure)
    df["Win_sat"] = 0.622 * df["es_kPa"] / (P_ATM / 10.0 - df["es_kPa"]) * 1000.0
    df["Win_sat"] = df["Win_sat"].clip(lower=0.001)
    df["RH_pct"] = (df["Win_g_kg"] / df["Win_sat"]) * 100.0
    df["RH_pct"] = df["RH_pct"].clip(0, 100)

    # Clipear valores fisicamente imposibles
    df["Tin_C"] = df["Tin_C"].clip(-10, 60)
    df["Win_g_kg"] = df["Win_g_kg"].clip(0, 50)
    df["Cin_ppm"] = df["Cin_ppm"].clip(100, 2000)

    # Timestamp
    df["hour"] = (df["time_s"] / 3600.0) % 24.0
    df["day"] = (df["time_s"] / 86400.0).astype(int)

    return df


def main():
    out_path = Path("simulacion.csv")
    print(f"[*] Ejecutando simulacion 7 dias (Bogota, 2640 msnm)...")
    df = run_simulation(days=7, dt=60.0)
    df.to_csv(out_path, index=False, float_format="%.4f")
    print(f"[+] Datos guardados en {out_path}")
    print(f"[+] {len(df)} filas, {len(df.columns)} columnas")
    print(f"[+] Tin range: {df['Tin_C'].min():.1f} - {df['Tin_C'].max():.1f} C")
    print(f"[+] RH range:  {df['RH_pct'].min():.1f} - {df['RH_pct'].max():.1f} %")
    print(f"[+] CO2 range: {df['Cin_ppm'].min():.0f} - {df['Cin_ppm'].max():.0f} ppm")


if __name__ == "__main__":
    main()
