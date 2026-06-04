#pragma once

#include "driver/i2c.h"

#define AHT20_ADDR        0x38
#define AHT20_CMD_INIT    0xBE
#define AHT20_CMD_CALIB   0xE1
#define AHT20_CMD_TRIGGER 0xAC
#define AHT20_INIT_DELAY_MS   40
#define AHT20_MEASURE_DELAY_MS 80

extern bool g_aht20_ok;

esp_err_t aht20_init(i2c_port_t i2c_port);
esp_err_t aht20_read(i2c_port_t i2c_port, float *temperature, float *humidity);
