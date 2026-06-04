#pragma once

#include <stdbool.h>

void ventilation_init(void);
bool ventilation_control(float humidity, float temperature);
