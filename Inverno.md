PROPUESTA DE INVESTIGACIÓN, VOL. 1, NO. 1, 2026

1

Sistema de Optimización de Clima en Invernaderos
Andinos
mediante Modelos Acoplados de Cuatro Variables
y Control Predictivo con TinyML Embebido

Lenin Yudain Coronel Pacheco, Estudiante, Ing. Sistemas

Resumen—Este documento presenta la propuesta de investiga-
ción para el desarrollo de un sistema autónomo de optimización
del microclima en invernaderos ubicados en zonas altoandinas
(2640 msnm, 750 hPa). El sistema integra: (i) un modelo dinámico
acoplado de cuatro variables de estado —temperatura interior
(Tin), humedad absoluta (Win), concentración de CO2 (Cin)
y evapotranspiración (Etr)— con corrección psicrométrica por
altitud; (ii) un controlador predictivo híbrido RL-Guided MPC;
y (iii) un módulo TinyML para predicción de perturbaciones con
redes neuronales de menos de 5K parámetros. La implementación
target es un ESP32-S3 operando sin conectividad externa. Los
resultados esperados incluyen: reducción ≥ 40 % en consumo
de agua, mejora ≥ 5 % en rendimiento y latencia de inferencia
< 100 ms. Se presenta la metodología en 5 fases (12 meses)
con validación experimental en invernadero piloto de 200 m2.
Palabras clave: Invernadero andino, modelos acoplados, TinyML,
RL-Guided MPC, ESP32-S3, agricultura de precisión.

Index Terms—Invernadero

acoplados,
TinyML, RL-Guided MPC, ESP32-S3, agricultura de precisión,
clima altoandino.

andino, modelos

I.

INTRODUCCIÓN

E L cambio climático y la creciente demanda de alimentos

plantean desafíos críticos para la agricultura mundial.
En Colombia, donde 2.1 millones de hectáreas se dedican
a actividades agrícolas, la variabilidad climática en regiones
andinas (1500–2800 msnm) genera pérdidas económicas sig-
nificativas. La agricultura en invernadero representa una alter-
nativa tecnológica viable, pero su adopción enfrenta barreras
críticas relacionadas con la falta de automatización inteligente,
modelos no calibrados para condiciones altoandinas y una
brecha tecnológica en computación embebida.

Este trabajo aborda simultáneamente estas brechas mediante
el desarrollo de un sistema integrado que combina modelado
dinámico con corrección por altitud, controlador RL-Guided
MPC adaptado a hardware limitado y módulo TinyML para
predicción de perturbaciones, todo ejecutado en un microcon-
trolador ESP32-S3 sin dependencia de conectividad externa.

Pregunta de Investigación:
¿Es posible implementar un sistema de control
predictivo basado en modelos acoplados (T, W, C, Et)
y TinyML en un microcontrolador ESP32-S3 que
reduzca el consumo de agua en ≥ 40 % y mejore el
rendimiento en ≥ 5 % en invernaderos altoandinos
colombianos, operando sin conectividad externa?

Figura 1: Pregunta central de investigación.

Dimensión 1 — Falta de automatización inteligente: Los
invernaderos en Colombia operan mayormente con sistemas
de control manual o supervisado. Esto genera: consumo de
agua ineficiente (40–60 % superior al de sistemas optimizados
[1]), variabilidad de microclima no controlada que afecta el
rendimiento, y decisiones de manejo basadas en experiencia
empírica en lugar de datos cuantitativos.

Dimensión 2 — Modelos climáticos no calibrados para
la altitud andina: Los modelos dinámicos disponibles fueron
desarrollados y validados para presión atmosférica estándar
(1013 hPa). En Bogotá (2640 msnm, ∼750 hPa), la constante
psicrométrica γ varía en un 28 % (Ecuación 6), lo que intro-
duce errores sistemáticos de predicción en evapotranspiración,
humedad y balance energético.

Dimensión 3 — Brecha en computación embebida: No
existe integración documentada de: resolución numérica de
sistemas acoplados de EDOs en microcontroladores, inferencia
de modelos TinyML simultánea con simulación dinámica, e
implementación de controladores predictivos en hardware con
< 1 MB de RAM [2].

II.

JUSTIFICACIÓN

La presente investigación se justifica desde tres dimensiones

complementarias:

II-A.

Justificación Científica

I-A.

Identificación del Problema

El problema de investigación se estructura en tres dimen-

siones interrelacionadas:

L. Y. Coronel P. es estudiante de Ingeniería de Sistemas, Universidad
Distrital Francisco José de Caldas, Bogotá D.C., Colombia. e-mail: lycoro-
nelp@correo.udistrital.edu.co

Vacío 1 — Clima andino: No existe modelo dinámi-
co calibrado y validado con análisis de incertidumbre
para condiciones de alta altitud (750 hPa), variabilidad
de radiación solar y baja oscilación térmica día/noche
(∆T < 15◦C) [3], [4].
Vacío 2 — Acoplamiento completo: Ausencia de sis-
temas que integren simultáneamente cuatro variables de

2

PROPUESTA DE INVESTIGACIÓN, VOL. 1, NO. 1, 2026

estado (T, W, C, Et) en controladores embebidos con
horizonte de predicción corto [5].
Vacío 3 — Integración numérica embebida: Ningún
trabajo implementa simultáneamente resolución numéri-
ca de EDOs acopladas + inferencia TinyML + control
predictivo en un microcontrolador Xtensa LX7 con 512
KB de SRAM [6].

II-B.

Justificación Tecnológica

Arquitectura escalable: Sistema basado en ESP32-S3
(costo unitario $8), con sensores de grado industrial
(BME688, SCD41) que permiten replicabilidad a bajo
costo.
Autonomía operativa: Diseño para funcionamiento sin
conexión a internet, crítico en zonas rurales andinas con
conectividad limitada.
Interoperabilidad: Compatibilidad con protocolos es-
tándar (MQTT, Modbus, LoRaWAN) para integración en
ecosistemas IoT.

II-C.

Justificación Socioeconómica

Contexto nacional: El sector agropecuario emplea a 3.7
millones de personas (DANE 2024). La horticultura bajo
invernadero es estratégica para seguridad alimentaria en
zonas de páramo andino.
Impacto cuantificable: Estudios internacionales repor-
tan ahorros de 40–66 % en agua y 11.4 % en rendimiento
con sistemas de IA embebida [1], [7].
Población objetivo: 2,300 unidades productivas en Cun-
dinamarca, Boyacá y Nariño; 87 % son pequeños y
medianos agricultores. El costo del sistema (∼$2,250)
es accesible frente a los ahorros anuales estimados de
$3.2–4.8 millones COP/ha/año.

III-A. Objetivo General

III. OBJETIVOS

Desarrollar e implementar un sistema autónomo de control
de microclima en invernaderos andinos mediante un modelo
acoplado de cuatro variables de estado (temperatura, humedad
absoluta, concentración de CO2 y evapotranspiración) integra-
do con un controlador predictivo adaptativo RL-Guided MPC
y un módulo de predicción TinyML, todo ejecutado en un
microcontrolador ESP32-S3 sin dependencia de conectividad
externa.

2. OE2 — Controlador adaptativo embebido (Meses 3–
7): Diseñar e implementar un controlador RL-Guided
MPC del caudal de ventilación con horizonte de predic-
ción corto (5–15 min) en ESP32-S3, validando estabili-
dad y robustez bajo perturbaciones climáticas reales.
Indicador: Seguimiento de setpoint de HR con desvia-
ción < ±5 %, tiempo de ejecución por iteración < 50
ms.

3. OE3 — Módulo TinyML de predicción (Meses 5–
8): Entrenar y cuantizar un modelo de red neuronal
superficial (< 5K parámetros, < 50 KB) para predicción
de radiación solar y temperatura exterior, con inferencia
en microcontrolador.
Indicador: Latencia < 100 ms, RMSE radiación < 50
W/m2, RMSE temperatura < 1◦C.

4. OE4 — Validación integral (Meses 8–12): Integrar los
tres componentes anteriores en el ESP32-S3 y validar
mediante diseño ABA de 12 semanas en invernadero
piloto de 200 m2 con cultivo de lechuga.
Indicador: Reducción ≥ 40 % en consumo de agua, me-
jora ≥ 5 % en rendimiento, diferencias estadísticamente
significativas (p < 0.05).

IV. MARCO TEÓRICO Y ESTADO DEL ARTE

Esta sección presenta los fundamentos teóricos que susten-
tan la investigación y revisa críticamente la literatura existente
para identificar vacíos y posicionar la contribución propuesta.

IV-A. Evolución del Modelado Dinámico de Invernaderos

La modelación dinámica de invernaderos inició con Van
Henten (1994), quien desarrolló un sistema jerárquico de dos
capas: control del cultivo (capa superior) y control climático
(capa inferior). Stanghellini [8] complementó este enfoque
con submodelos detallados de transpiración usando balance
energético, estableciendo que la tasa de evapotranspiración es
el criterio cuantitativo central para control de humedad.

López-Cruz et al. [3] realizaron una revisión exhaustiva
de más de 60 modelos dinámicos, concluyendo que: (a)
los modelos mecanicistas con pocos estados (3–6 variables)
son más útiles para control y optimización; (b) ninguno fue
sometido a análisis de incertidumbre; y (c) la gran mayoría
fue calibrada para clima europeo.

IV-B. Fundamentos del Modelo Acoplado Propuesto

IV-B1. Balance Energético: La dinámica térmica del aire

III-B. Objetivos Específicos

interior se describe mediante:

1. OE1 — Modelo dinámico calibrado (Meses 1–4):
Desarrollar un modelo acoplado de EDOs que integre las
cuatro variables de estado con corrección psicrométrica
por altitud, validado experimentalmente con datos de
invernadero en Bogotá D.C. (2640 msnm) y respaldado
por análisis de sensibilidad global (Morris, Sobol) e
incertidumbre (Monte Carlo con N = 104).
Indicador: RMSE < 1◦C (temperatura), < 5 % HR
(humedad relativa), < 50 ppm (CO2) en conjunto de
prueba.

Cp

dTin
dt

=

1
V

(cid:2)Qrad + Qcalef − Qvent − Qtransp

(cid:3)

(1)

donde Cp es la capacidad calorífica del aire (J/K·m3), V
el volumen interior (m3), Qrad la ganancia solar, Qcalef el
aporte de calefacción, Qvent las pérdidas por ventilación y
Qtransp el enfriamiento evaporativo.

IV-B2. Balance de Humedad Absoluta:
1
V

(cid:2)Wout ˙V + Etr − Win ˙V (cid:3)

dWin
dt

=

(2)

CORONEL et al.: OPTIMIZACIÓN DE CLIMA EN INVERNADEROS ANDINOS CON TINYML

3

IV-B3. Balance de CO2:
dCin
dt

1
V

=

(cid:2)Cout ˙V − PnAleaf + RdAleaf − Cin ˙V (cid:3)

Tabla I: Vacíos identificados en la literatura frente a la pro-
puesta

(3)

Vacío en literatura

Cómo lo aborda esta propuesta

IV-B4. Evapotranspiración: Penman-Monteith con Co-

rrección por Altitud:

Etr = Aleaf

∆(Rn − G) + ρacp(es − ea)/ra
∆ + γ(1 + rs/ra)

(4)

La constante psicrométrica se corrige por presión atmosfé-

rica:

γ =

cpP
0,622Lv

(5)

Para Bogotá (2640 msnm, P ≈ 750 hPa):

γBogot =

1003 × 750

0,622 × 2,501 × 106 ≈ 0,048 kPa ·◦ C−1

(6)

Esto representa un 28 % menos que el valor estándar γSL ≈

0,0665, generando errores sistemáticos si no se corrige [9].

IV-C. Control Predictivo en Invernaderos

IV-C1. Model Predictive Control (MPC): El MPC resuel-

ve en línea un problema de optimización:

J =

Hp
(cid:88)

k=0

∥xk − xref,k∥2

Q +

Hc(cid:88)

k=0

∥uk − uref,k∥2
R

(7)

Van Straten et al. [10] demostraron que MPC es efectivo
para control climático pero computacionalmente intensivo para
hardware embebido.

IV-C2. Aprendizaje por Refuerzo (RL): RL busca una
política π que maximiza la recompensa acumulada. Hemming
et al. [11] compararon sistemáticamente MPC vs. RL, con-
cluyendo que son complementarios: MPC ofrece estabilidad
nominal mientras RL maneja mejor la incertidumbre.

IV-C3. Arquitectura Híbrida RL-Guided MPC: Liang et
al. [12] propusieron una arquitectura donde RL construye el
costo terminal de MPC:

J RL
M P C =

Hp
(cid:88)

k=0

∥xk − xref,k∥2

Q + V RL(xHp )

(8)

Esta arquitectura no ha sido implementada en microcon-
troladores, lo que constituye el vacío central que aborda esta
investigación.

IV-D. TinyML para Agricultura de Precisión

Codeluppi et al. [13] alcanzaron RMSE de 0.289–0.402◦C
con modelos ANN de 150–300 parámetros en ESP32. Ihoume
et al. [7] desarrollaron TinyML multietiqueta con solo 151
parámetros logrando 97 % de exactitud.

Limitación crítica identificada: Ningún trabajo previo
integra TinyML con resolución numérica de EDOs acopladas
en tiempo real dentro de un mismo microcontrolador [2], [6].

Modelos no calibrados para cli-
ma andino
Sin análisis de incertidumbre
en modelos
Acoplamiento incompleto de
variables
RL-Guided MPC no imple-
mentado en HW embebido
TinyML sin integración con si-
mulación numérica

Corrección psicrométrica + validación
a 2640 msnm
Sobol + Monte Carlo con N = 104

4 EDOs acopladas (T, W, C, Et)

Portabilidad a ESP32-S3 con horizonte
reducido
Pipeline híbrido RK4 + inferencia
TFLite Micro

V. ALCANCE Y LIMITACIONES

V-A. Alcance del Proyecto

Cobertura técnica: Sistema completo desde sensori-
incluyendo modelo dinámico,
zación hasta actuación,
control predictivo y módulo TinyML en un solo micro-
controlador.
Escala: Validación en invernadero piloto de 200 m2 con
escalabilidad demostrada a 500 m2 mediante arquitectura
modular.
Cultivo: Validación con lechuga (ciclo corto, respuesta
rápida a cambios climáticos), extensible a tomate y fresa
mediante recalibración.
Cobertura geográfica: Clima andino colombiano (Cfb
Köppen, 2640 msnm). La metodología de calibración es
transferible a otras altitudes.
Hardware: Implementación en ESP32-S3 (240 MHz
dual-core, 512 KB SRAM + 8 MB PSRAM) sin depen-
dencia de conectividad externa.

V-B. Limitaciones Reconocidas

1. Climas extremos: El modelo no ha sido validado
para desiertos cálidos (BWh) o climas polares (ET).
Su precisión en esos entornos no está garantizada sin
recalibración.

2. Cultivos especializados: Cultivos con requerimientos
microclimáticos atípicos (orquídeas, hongos shiitake)
requerirían recalibración completa de los parámetros del
modelo.

3. Escala industrial: Para invernaderos > 1 Ha, la arqui-
tectura necesitaría distribución multi-nodo con coordi-
nación jerárquica, lo que excede el alcance actual.
4. Interoperabilidad: La compatibilidad con sistemas de
control propietarios (PLC, SCADA) es limitada y reque-
riría desarrollo de gateways específicos.

5. Generalización estadística: Los resultados de valida-
ción se obtendrán en un solo invernadero piloto. La
significancia estadística se garantiza mediante diseño
ABA, pero la replicabilidad en múltiples sitios queda
para trabajo futuro.

6. Mantenimiento: El sistema requiere capacitación básica
del usuario final para calibración periódica de sensores
y actualización de firmware.

4

PROPUESTA DE INVESTIGACIÓN, VOL. 1, NO. 1, 2026

2026

01 02 03 04 05 06 07 08 09 10 11 12

Tabla II: Métricas de éxito cuantificables por objetivo especí-
fico

Métrica

Objetivo

Instrumento

A. Modelado y calibración

A.3 Campaña medición

A.2 Formulación EDOs

A.4 Est. parámetros + incerti-
dumbre

Validación modelo

B. Control predictivo

B.1–B.2 Simulación off-line

B.3 Entrenamiento RL (PPO)

B.4 Pruebas robustez

Controlador listo

C. Módulo TinyML

C.1–C.2 Entrenamiento red

C.3 Cuantización INT8

C.4 Implementación ESP32

Modelo cuantizado

D. Integración embebida

D.1 RK4 en C optimizado

D.2 Ensamble stack

D.3 Pruebas estrés (>72 h)

Sistema operativo

E. Validación en campo

E.1 Instalación/calibración

E.2 Diseño ABA (12 semanas)

E.3 Análisis estadístico

E.4 Documentación

Informe final

Figura 2: Cronograma de ejecución (12 meses) organizado por
fases.

V-C.

Supuestos del Proyecto

1. Disponibilidad de invernadero piloto con acceso conti-

nuo durante 12 meses.

2. Acceso a instrumentación de calibración de referencia

(estación meteorológica certificada).

3. Estabilidad en suministro de componentes electrónicos

durante la ejecución.

4. Condiciones climáticas representativas durante el perío-
do de validación (variabilidad esperada dentro de rangos
históricos).

< 1◦C
< 5 % HR
< 50 W/m2
< 100 ms

RMSE modelo (Tin)
RMSE modelo (Win)
Error predicción radiación
Latencia
inferencia
TinyML
Consumo energético por
inf.
Estabilidad sistema embe-
bido
Reducción
agua
Mejora rendimiento cultivo ≥ 5 %
Costo total del sistema

consumo

de

≥ 40 %

< 50 mW

< $2, 500 USD

> 72 h sin fallo

Validación 15 % datos
Validación 15 % datos
Test vs. piranómetro
Medición ciclo CPU

Medición corriente

Prueba continua

Diseño ABA (12 sem)

Diseño ABA (12 sem)
Facturación real

Tabla III: Presupuesto detallado del proyecto

Ítem

Cant.

Costo (USD)

Microcontroladores ESP32-S3 + periféricos
Sensores temperatura/humedad SHT45
Sensores CO2 SCD41
Módulos LoRa (comunicación)
Actuadores (ventilación, calefacción, nebulización)
Raspberry Pi 4 (gateway local)
Componentes electrónicos (PCB, resistencias, etc.)
Herramientas de prototipado (soldadura, medición)

Subtotal hardware
Software y licencias (simuladores, IDEs)
Contingencias (15 %)

Total general

15
15
3
5
5
1
-
-

-
-

120
180
105
125
200
75
150
200

1,155
300
218

1,673

5. Cooperación de expertos agrícolas para determinación
de criterios de cultivo y evaluación de rendimiento.

VI. RESULTADOS ESPERADOS Y MÉTRICAS DE ÉXITO

VII. PRESUPUESTO Y RECURSOS

VII-A. Recursos Humanos

Investigador principal (estudiante): dedicación 100 %,
responsable de modelado, desarrollo y análisis.
Director (profesor asociado): supervisión científica, 25 %
dedicación.
Asesor agrícola: criterios de cultivo y validación en
campo, 10 % dedicación.

VII-B. Recursos Materiales

VII-C.

Infraestructura

Laboratorio de automatización (20 m2) con equipos de
medición (osciloscopio, multímetros, fuente de poder).
Invernadero piloto de 200 m2 con estructura de túnel y
cubierta de polietileno.
Estación meteorológica automática (Davis Vantage Pro2)
como referencia de calibración.
Licencias educacionales de MATLAB.

CORONEL et al.: OPTIMIZACIÓN DE CLIMA EN INVERNADEROS ANDINOS CON TINYML

5

[3] I. L. López-Cruz, A. Ramírez-Arias, and A. Rojano-Aguilar, “Deve-
lopment and analysis of dynamical mathematical models of greenhouse
climate: a review,” European Journal of Horticultural Science, vol. 83,
no. 5, pp. 269–279, 2018.

[4] A. Queralt, “Advanced modeling framework for the simulation of
greenhouse climate and the integration of sustainable energy solutions,”
Ph.D. dissertation, Université de Liège, 2024.

[5] J. Chen, M. Li, and Q. Wang, “Coupled heat and mass transfer model
for greenhouse environment prediction,” Biosystems Engineering, vol.
204, pp. 1–15, 2021.

[6] J. Morales-García, A. Bueno-Crespo, R. Martínez-España et al., “Eva-
luation of low-power devices for smart greenhouse development,” The
Journal of Supercomputing, vol. 79, pp. 10 277–10 299, 2023.

[7] I. Ihoume, R. Tadili, N. Arbaoui, M. Benchrifa, A. Idrissi, and M. Daou-
di, “Developing a multi-label TinyML machine learning model for an
active and optimized greenhouse microclimate control from multivariate
sensed data,” Smart Agricultural Technology, vol. 2, p. 100039, 2022.
[8] C. Stanghellini, “Transpiration of greenhouse crops: An aid to climate
management,” Ph.D. dissertation, Agricultural University of Wagenin-
gen, 1987.

[9] M. S. Islam, T. Oki, and R. Oki, “Modeling the effect of elevated CO2
and climate change on reference evapotranspiration in the semi-arid
central great plains,” Transactions of the ASABE, vol. 55, no. 6, pp.
2135–2146, 2012.

[10] G. van Straten, G. van Willigenburg, E. van Henten, and R. van
Ooteghem, Optimal Control of Greenhouse Cultivation. CRC Press,
2020.

[11] S. Hemming, H. F. de Zwart, A. Elings et al., “Reinforcement learning
versus model predictive control on greenhouse climate control,” Com-
puters and Electronics in Agriculture, vol. 210, p. 107924, 2023.
[12] S. Msaad, M. Harraway, and R. D. McAllister, “RL-guided MPC for

autonomous greenhouse control,” IFAC-PapersOnLine, 2025.

[13] G. Codeluppi, L. Davoli, and G. Ferrari, “Forecasting air temperature
on edge devices with embedded AI,” Sensors, vol. 21, no. 12, p. 3973,
2021.

Lenin Yudain Coronel Pacheco Estudiante de Ingeniería de Sistemas,
Universidad Distrital Francisco José de Caldas. Su investigación se centra
en sistemas embebidos, TinyML y modelado dinámico para agricultura de
precisión en contextos altoandinos.

Tabla IV: Matriz de riesgos, impacto y mitigación

Riesgo

Prob.

Estrategia de mitigación

Error en modelado >
10 %

Alta

Bajo
TinyML

desempeño

Media

Falta de componentes
electrónicos

Media

Condiciones climáticas
atípicas

Baja

Problemas de integra-
ción HW/SW
Desviación en crono-
grama

Media

Media

Validación incremental con submo-
delos independientes; recalibración
con datos adicionales
Arquitectura híbrida con fallback a
PID clásico; rediseño de arquitec-
tura si es necesario
Identificación de proveedores alter-
nativos; diseño modular con com-
patibilidad pin-a-pin
Simulación de escenarios extre-
mos; extensión del período de va-
lidación
Integración continua con pruebas
semanales; CI/CD para firmware
Buffer de 1 mes en la planificación;
priorización de entregables críticos

VIII. ANÁLISIS DE RIESGOS

IX. CONCLUSIONES

IX-A. Contribuciones Esperadas

1. Teórica: Primer modelo dinámico acoplado de cuatro
variables de estado con análisis de incertidumbre (Sobol,
Monte Carlo) calibrado para clima andino colombiano,
incluyendo corrección psicrométrica por altitud.

2. Metodológica: Framework para implementación de RL-
Guided MPC en hardware embebido con restricciones
computacionales reales (512 KB SRAM + 8 MB PS-
RAM, 240 MHz).

3. Tecnológica: Primera integración documentada de re-
solución numérica de EDOs + inferencia TinyML +
control predictivo en un microcontrolador ESP32-S3 sin
conectividad externa.

4. Práctica: Sistema de bajo costo (∼$2,250) que reduce
≥ 40 % el consumo de agua y mejora ≥ 5 % el ren-
dimiento, accesible a pequeños y medianos productores
colombianos.

IX-B. Trabajo Futuro

Integración de visión computacional para monitoreo fe-
nológico automatizado
Extensión a agricultura vertical e hidroponía de alta
densidad
Desarrollo de gemelos digitales (digital twins) para si-
mulación en tiempo real
Implementación de plataforma colaborativa de modelos
específicos por cultivo y clima
Validación multi-sitio en 3 departamentos (Cundinamar-
ca, Boyacá, Nariño)

REFERENCIAS

[1] Y. Zhang, M. Henke, Y. Li et al., “Develop a smart microclimate control
system for greenhouses through system dynamics and machine learning
techniques,” Water, vol. 14, no. 23, p. 3941, 2022.

[2] A. Banakar and R. M. Goudar, “Tinyml for edge computing in iot-based
greenhouse monitoring systems,” Internet of Things, vol. 19, p. 100548,
2022.


