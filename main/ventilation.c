#include "ventilation.h"

#define RH_THRESHOLD_HIGH 85.0f
#define RH_THRESHOLD_LOW  75.0f
#define TEMP_THRESHOLD    35.0f

static bool vent_state = false;

void ventilation_init(void)
{
    vent_state = false;
}

bool ventilation_control(float humidity, float temperature)
{
    if (humidity > RH_THRESHOLD_HIGH || temperature > TEMP_THRESHOLD) {
        vent_state = true;
    } else if (humidity < RH_THRESHOLD_LOW && temperature < TEMP_THRESHOLD - 2.0f) {
        vent_state = false;
    }
    return vent_state;
}
