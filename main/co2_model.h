#pragma once

#include <stdint.h>
#include <time.h>

void co2_model_init(void);
float co2_model_estimate(time_t now);
