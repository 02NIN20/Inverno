#include "bmp280.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include <math.h>

static const char *TAG = "BMP280";
bool g_bmp280_ok = false;
uint8_t g_bmp280_addr = 0;

static struct bmp280_calib calib;
static int32_t t_fine;

static uint16_t read16_le(const uint8_t *buf, int offset) {
    return (uint16_t)buf[offset] | ((uint16_t)buf[offset + 1] << 8);
}

static int16_t read16_signed(const uint8_t *buf, int offset) {
    return (int16_t)((uint16_t)buf[offset] | ((uint16_t)buf[offset + 1] << 8));
}

static esp_err_t bmp_read_reg(i2c_port_t port, uint8_t addr, uint8_t reg, uint8_t *data, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_READ, true);
    if (len > 1) i2c_master_read(cmd, data, len - 1, I2C_MASTER_ACK);
    i2c_master_read_byte(cmd, data + len - 1, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(port, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    return ret;
}

static esp_err_t bmp_write_reg(i2c_port_t port, uint8_t addr, uint8_t reg, uint8_t val)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true);
    i2c_master_write_byte(cmd, val, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(port, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    return ret;
}

esp_err_t bmp280_init(i2c_port_t i2c_port)
{
    esp_err_t ret;
    uint8_t id;

    vTaskDelay(pdMS_TO_TICKS(20));

    // Probe 0x76
    ret = bmp_read_reg(i2c_port, 0x76, 0xD0, &id, 1);
    if (ret == ESP_OK && id == BMP280_CHIP_ID) {
        g_bmp280_addr = 0x76;
        ESP_LOGI(TAG, "Found at 0x76 (id=0x%02X)", id);
    } else {
        // Probe 0x77
        ret = bmp_read_reg(i2c_port, 0x77, 0xD0, &id, 1);
        if (ret == ESP_OK && id == BMP280_CHIP_ID) {
            g_bmp280_addr = 0x77;
            ESP_LOGI(TAG, "Found at 0x77 (id=0x%02X)", id);
        } else {
            ESP_LOGE(TAG, "Not found (0x76 ret=%d id=0x%02X, 0x77 ret=%d id=0x%02X)",
                     ret, id, ret, id);
            return ESP_ERR_NOT_FOUND;
        }
    }

    // Reset
    ret = bmp_write_reg(i2c_port, g_bmp280_addr, BMP280_REG_RESET, BMP280_RESET_CMD);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Reset failed: %d", ret);
        return ret;
    }
    vTaskDelay(pdMS_TO_TICKS(15));

    // Read calibration
    uint8_t calib_data[24];
    ret = bmp_read_reg(i2c_port, g_bmp280_addr, 0x88, calib_data, 24);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Calib read failed: %d", ret);
        return ret;
    }

    calib.dig_T1 = read16_le(calib_data, 0);
    calib.dig_T2 = read16_signed(calib_data, 2);
    calib.dig_T3 = read16_signed(calib_data, 4);
    calib.dig_P1 = read16_le(calib_data, 6);
    calib.dig_P2 = read16_signed(calib_data, 8);
    calib.dig_P3 = read16_signed(calib_data, 10);
    calib.dig_P4 = read16_signed(calib_data, 12);
    calib.dig_P5 = read16_signed(calib_data, 14);
    calib.dig_P6 = read16_signed(calib_data, 16);
    calib.dig_P7 = read16_signed(calib_data, 18);
    calib.dig_P8 = read16_signed(calib_data, 20);
    calib.dig_P9 = read16_signed(calib_data, 22);

    ESP_LOGI(TAG, "Calib OK: T1=%u T2=%d T3=%d P1=%u", calib.dig_T1, calib.dig_T2, calib.dig_T3, calib.dig_P1);

    // Config: temp+press oversampling x4, normal mode
    ret = bmp_write_reg(i2c_port, g_bmp280_addr, BMP280_REG_CTRL_MEAS, 0x57);
    if (ret != ESP_OK) { ESP_LOGE(TAG, "Config ctrl_meas failed: %d", ret); return ret; }

    ret = bmp_write_reg(i2c_port, g_bmp280_addr, BMP280_REG_CONFIG, 0x10);
    if (ret != ESP_OK) { ESP_LOGE(TAG, "Config config failed: %d", ret); return ret; }

    g_bmp280_ok = true;
    ESP_LOGI(TAG, "Initialized OK at 0x%02X", g_bmp280_addr);
    return ESP_OK;
}

static float bmp280_compensate_temp(int32_t adc_T)
{
    int32_t var1 = ((((adc_T >> 3) - ((int32_t)calib.dig_T1 << 1))) *
                    ((int32_t)calib.dig_T2)) >> 11;
    int32_t var2 = (((((adc_T >> 4) - ((int32_t)calib.dig_T1)) *
                      ((adc_T >> 4) - ((int32_t)calib.dig_T1))) >> 12) *
                    ((int32_t)calib.dig_T3)) >> 14;
    t_fine = var1 + var2;
    return ((t_fine * 5 + 128) >> 8) / 100.0f;
}

static float bmp280_compensate_press(int32_t adc_P)
{
    int64_t var1 = ((int64_t)t_fine) - 128000;
    int64_t var2 = var1 * var1 * (int64_t)calib.dig_P6;
    var2 = var2 + ((var1 * (int64_t)calib.dig_P5) << 17);
    var2 = var2 + (((int64_t)calib.dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)calib.dig_P3) >> 8) +
           ((var1 * (int64_t)calib.dig_P1) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)calib.dig_P1) >> 33;
    if (var1 == 0) return 0.0f;
    int64_t p = 1048576 - (int64_t)adc_P;
    p = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)calib.dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)calib.dig_P8) * p) >> 19;
    p = ((p + var1 + var2) >> 8) + (((int64_t)calib.dig_P7) << 4);
    return (float)((uint64_t)p) / 25600.0f;
}

esp_err_t bmp280_read(i2c_port_t i2c_port, float *temperature, float *pressure)
{
    if (!g_bmp280_ok) return ESP_FAIL;

    uint8_t data[6];
    esp_err_t ret = bmp_read_reg(i2c_port, g_bmp280_addr, BMP280_REG_PRESS_MSB, data, 6);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Read failed: %d", ret);
        return ret;
    }

    int32_t adc_P = ((int32_t)data[0] << 12) | ((int32_t)data[1] << 4) | (data[2] >> 4);
    int32_t adc_T = ((int32_t)data[3] << 12) | ((int32_t)data[4] << 4) | (data[5] >> 4);

    *temperature = bmp280_compensate_temp(adc_T);
    *pressure = bmp280_compensate_press(adc_P);

    return ESP_OK;
}
