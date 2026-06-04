#include "co2_model.h"
#include <math.h>
#include <time.h>

#define CO2_AMBIENT     420.0f
#define CO2_AMPLITUDE   180.0f
#define CO2_PEAK_OFFSET 4.0f

void co2_model_init(void) {}

float co2_model_estimate(time_t now)
{
    // now es el tiempo transcurrido en segundos.
    // Obtenemos la hora del dia modulo 24 de forma directa y eficiente.
    float hour = (float)(now % 86400) / 3600.0f;

    float phase = (hour - CO2_PEAK_OFFSET) / 24.0f * 2.0f * M_PI;
    float diurnal = cosf(phase);

    float co2 = CO2_AMBIENT + CO2_AMPLITUDE * diurnal;
    if (co2 < 350.0f) co2 = 350.0f;
    if (co2 > 800.0f) co2 = 800.0f;
    return co2;
}
