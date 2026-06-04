#pragma once

#include "driver/i2c.h"

#define BMP280_ADDR_PRIMARY   0x76
#define BMP280_ADDR_SECONDARY 0x77

#define BMP280_REG_CHIPID     0xD0
#define BMP280_REG_RESET      0xE0
#define BMP280_REG_STATUS     0xF3
#define BMP280_REG_CTRL_MEAS  0xF4
#define BMP280_REG_CONFIG     0xF5
#define BMP280_REG_PRESS_MSB  0xF7
#define BMP280_REG_TEMP_XLSB  0xFC
#define BMP280_CHIP_ID        0x58
#define BMP280_RESET_CMD      0xB6

extern bool g_bmp280_ok;
extern uint8_t g_bmp280_addr;

struct bmp280_calib {
    uint16_t dig_T1;
    int16_t  dig_T2;
    int16_t  dig_T3;
    uint16_t dig_P1;
    int16_t  dig_P2;
    int16_t  dig_P3;
    int16_t  dig_P4;
    int16_t  dig_P5;
    int16_t  dig_P6;
    int16_t  dig_P7;
    int16_t  dig_P8;
    int16_t  dig_P9;
};

esp_err_t bmp280_init(i2c_port_t i2c_port);
esp_err_t bmp280_read(i2c_port_t i2c_port, float *temperature, float *pressure);
