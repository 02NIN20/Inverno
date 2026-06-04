#include "aht20.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

static const char *TAG = "AHT20";
bool g_aht20_ok = false;

esp_err_t aht20_init(i2c_port_t i2c_port)
{
    esp_err_t ret;
    uint8_t cmd;

    vTaskDelay(pdMS_TO_TICKS(50));

    cmd = AHT20_CMD_INIT;
    ret = i2c_master_write_to_device(i2c_port, AHT20_ADDR, &cmd, 1, pdMS_TO_TICKS(100));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Soft reset failed: %d", ret);
        return ret;
    }
    vTaskDelay(pdMS_TO_TICKS(AHT20_INIT_DELAY_MS));

    uint8_t calib_cmd[] = {AHT20_CMD_CALIB, 0x08, 0x00};
    ret = i2c_master_write_to_device(i2c_port, AHT20_ADDR, calib_cmd, 3, pdMS_TO_TICKS(100));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Calibration cmd failed: %d", ret);
        return ret;
    }
    vTaskDelay(pdMS_TO_TICKS(20));

    uint8_t status;
    ret = i2c_master_read_from_device(i2c_port, AHT20_ADDR, &status, 1, pdMS_TO_TICKS(100));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Status read failed: %d", ret);
        return ret;
    }

    if ((status & 0x08) != 0x08) {
        ESP_LOGE(TAG, "Calibration not enabled, status=0x%02X", status);
        return ESP_FAIL;
    }

    if ((status & 0x80) != 0) {
        ESP_LOGW(TAG, "Sensor busy after init, status=0x%02X", status);
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    g_aht20_ok = true;
    ESP_LOGI(TAG, "Initialized OK");
    return ESP_OK;
}

esp_err_t aht20_read(i2c_port_t i2c_port, float *temperature, float *humidity)
{
    if (!g_aht20_ok) {
        return ESP_FAIL;
    }

    esp_err_t ret;
    uint8_t trigger[] = {AHT20_CMD_TRIGGER, 0x33, 0x00};
    ret = i2c_master_write_to_device(i2c_port, AHT20_ADDR, trigger, 3, pdMS_TO_TICKS(100));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Trigger failed: %d", ret);
        return ret;
    }

    vTaskDelay(pdMS_TO_TICKS(AHT20_MEASURE_DELAY_MS));

    uint8_t data[7] = {0};
    ret = i2c_master_read_from_device(i2c_port, AHT20_ADDR, data, 7, pdMS_TO_TICKS(100));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Read failed: %d", ret);
        return ret;
    }

    if (data[0] & 0x80) {
        ESP_LOGW(TAG, "Device busy");
        return ESP_ERR_TIMEOUT;
    }

    uint32_t raw_hum = ((uint32_t)data[1] << 12) | ((uint32_t)data[2] << 4) | (data[3] >> 4);
    uint32_t raw_temp = (((uint32_t)data[3] & 0x0F) << 16) | ((uint32_t)data[4] << 8) | data[5];

    *humidity = ((float)raw_hum / 1048576.0f) * 100.0f;
    *temperature = ((float)raw_temp / 1048576.0f) * 200.0f - 50.0f;

    return ESP_OK;
}
