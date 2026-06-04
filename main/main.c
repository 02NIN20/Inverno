#include <stdio.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "aht20.h"
#include "bmp280.h"
#include "co2_model.h"
#include "ventilation.h"
#include "tinyml_inference.h"

#define I2C_MASTER_SCL_IO     GPIO_NUM_6
#define I2C_MASTER_SDA_IO     GPIO_NUM_5
#define I2C_MASTER_FREQ_HZ    50000
#define LED_GPIO              GPIO_NUM_21
#define SAMPLE_INTERVAL_MS    5000

static const char *TAG = "MAIN";

static float gamma_psychro = 0.048f;

static float compute_etr(float net_radiation, float temp, float humidity, float wind_speed)
{
    float delta = 4098.0f * (0.6108f * expf((17.27f * temp) / (temp + 237.3f))) / ((temp + 237.3f) * (temp + 237.3f)) * 1000.0f; // Pa/C
    float es = 0.6108f * expf((17.27f * temp) / (temp + 237.3f)) * 1000.0f; // Pa
    float ea = es * (humidity / 100.0f); // Pa
    float vpd = es - ea;
    if (vpd < 0.0f) vpd = 0.0f;

    float gamma = gamma_psychro * 1000.0f; // Pa/C
    float Rn = net_radiation * (1.0f - 0.23f); // Rn = Rg * (1 - albedo), albedo = 0.23
    float G = 0.1f * Rn; // 10% de Rn
    float A_leaf = 2.5f * 20.0f; // LAI * AREA (2.5 * 20.0 = 50.0 m2)
    float rho_a = 1.2f; // RHO
    float cp = 1005.0f; // CP
    float ra = 50.0f; // RA
    float rs = 70.0f; // RS_MIN

    float numerator = delta * (Rn - G) + rho_a * cp * vpd / ra;
    float denominator = delta + gamma * (1.0f + rs / ra);

    if (denominator < 0.001f) return 0.0f;
    float ET_flux = numerator / denominator; // W/m2
    float ET_kg = (ET_flux / 2.45e6f) * A_leaf; // kg/s
    float ET_mm_h = (ET_kg * 3600.0f) / 20.0f; // (ET_kg * 3600) / AREA (20.0 m2)

    if (ET_mm_h < 0.0f) ET_mm_h = 0.0f;
    return ET_mm_h;
}

static bool scan_all_i2c(i2c_port_t *out_bus, int *out_sda, int *out_scl)
{
    printf("=== DIAGNOSTICO I2C: Probando todas las combinaciones ===\n");

    int configs[][2] = {
        {GPIO_NUM_6, GPIO_NUM_7},
        {GPIO_NUM_5, GPIO_NUM_6},
    };

    for (int c = 0; c < 2; c++) {
        for (int bus = 0; bus < 2; bus++) {
            i2c_config_t conf = {
                .mode = I2C_MODE_MASTER,
                .sda_io_num = configs[c][0],
                .scl_io_num = configs[c][1],
                .sda_pullup_en = GPIO_PULLUP_ENABLE,
                .scl_pullup_en = GPIO_PULLUP_ENABLE,
                .master.clk_speed = 50000,
                .clk_flags = 0,
            };
            i2c_param_config(bus, &conf);
            i2c_driver_install(bus, I2C_MODE_MASTER, 0, 0, 0);

            printf("  Bus I2C%d: SDA=GPIO%d SCL=GPIO%d @ 50kHz\n", bus, configs[c][0], configs[c][1]);
            int found = 0;
            for (int addr = 1; addr < 127; addr++) {
                i2c_cmd_handle_t cmd = i2c_cmd_link_create();
                i2c_master_start(cmd);
                i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
                i2c_master_stop(cmd);
                if (i2c_master_cmd_begin(bus, cmd, pdMS_TO_TICKS(20)) == ESP_OK) {
                    printf("    0x%02X encontrado!\n", addr);
                    found++;
                }
                i2c_cmd_link_delete(cmd);
            }

            if (found > 0) {
                *out_bus = bus;
                *out_sda = configs[c][0];
                *out_scl = configs[c][1];
                printf("  *** CONFIGURACION FUNCIONAL ENCONTRADA ***\n");
                printf("=== FIN DIAGNOSTICO ===\n");
                return true;
            }

            i2c_driver_delete(bus);
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }

    printf("=== FIN DIAGNOSTICO: Ningun sensor encontrado ===\n");
    return false;
}

void app_main(void)
{
    ESP_LOGI(TAG, "=== Invernadero Andino - XIAO ESP32S3 ===");
    ESP_LOGI(TAG, "Bogota 2640 msnm | P_atm = 750 hPa | gamma = 0.048 kPa/C");

    gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(LED_GPIO, 0);

    i2c_port_t active_bus = I2C_NUM_0;
    int active_sda = GPIO_NUM_5;
    int active_scl = GPIO_NUM_6;

    if (scan_all_i2c(&active_bus, &active_sda, &active_scl)) {
        printf("*** Sensores detectados en I2C%d, SDA=GPIO%d, SCL=GPIO%d ***\n",
               active_bus, active_sda, active_scl);
    } else {
        printf("*** ADVERTENCIA: Ningun sensor I2C detectado ***\n");
        printf("*** Verifique: alimentacion 3.3V, GND, SDA/SCL, soldaduras ***\n");
        printf("*** Usando configuracion por defecto ***\n");
    }

    // Init I2C with the working/default config
    i2c_config_t i2c_conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = active_sda,
        .scl_io_num = active_scl,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
        .clk_flags = 0,
    };
    esp_err_t ret = i2c_param_config(active_bus, &i2c_conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C param config failed: %d", ret);
    }
    ret = i2c_driver_install(active_bus, I2C_MODE_MASTER, 0, 0, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C driver install failed: %d", ret);
    }

    vTaskDelay(pdMS_TO_TICKS(200));

    printf("=== INICIALIZANDO SENSORES ===\n");
    aht20_init(active_bus);
    bmp280_init(active_bus);

    co2_model_init();
    ventilation_init();

    printf("uptime_s,vent_state,"
           "aht_temp_C,aht_hum_pct,"
           "bmp_temp_C,bmp_press_hPa,"
           "bmp_press_kPa,"
           "co2_est_ppm,etr_mm_h,"
           "tinyml_pred_C,tinyml_latency_us\n");
    fflush(stdout);

    int64_t start_time = esp_timer_get_time();
    uint32_t sample_count = 0;

    /* TinyML: historial de 3 muestras (T, HR, R) para lags t, t-1, t-2 */
    float tinyml_history[3][3] = {{0}};  /* [muestra_lag][T, HR, R] */
    int tinyml_filled = 0;                /* 0..3 */
    float last_tinyml_pred = NAN;
    int64_t last_tinyml_us = 0;

    while (1) {
        gpio_set_level(LED_GPIO, 1);

        float aht_temp = NAN, aht_hum = NAN;
        float bmp_temp = NAN, bmp_press = NAN;

        if (g_aht20_ok) {
            aht20_read(active_bus, &aht_temp, &aht_hum);
        }
        if (g_bmp280_ok) {
            bmp280_read(active_bus, &bmp_temp, &bmp_press);
        }

        float co2_est = co2_model_estimate(sample_count * SAMPLE_INTERVAL_MS / 1000);

        float temp_ref = isnanf(aht_temp) ? bmp_temp : aht_temp;
        float humidity_ref = isnanf(aht_hum) ? NAN : aht_hum;

        bool vent = false;
        if (!isnanf(temp_ref) && !isnanf(humidity_ref)) {
            vent = ventilation_control(humidity_ref, temp_ref);
        }

        float net_rad = 150.0f;
        float wind_spd = 0.8f;
        float etr = NAN;
        if (!isnanf(temp_ref) && !isnanf(humidity_ref)) {
            etr = compute_etr(net_rad, temp_ref, humidity_ref, wind_spd);
        }

        /* TinyML inference: actualizar historial y predecir si hay 3 muestras */
        if (!isnanf(bmp_temp) && !isnanf(humidity_ref)) {
            /* Shiftear historial (mover t-1 -> t-2, t -> t-1, nueva -> t) */
            tinyml_history[2][0] = tinyml_history[1][0];
            tinyml_history[2][1] = tinyml_history[1][1];
            tinyml_history[2][2] = tinyml_history[1][2];
            tinyml_history[1][0] = tinyml_history[0][0];
            tinyml_history[1][1] = tinyml_history[0][1];
            tinyml_history[1][2] = tinyml_history[0][2];
            tinyml_history[0][0] = bmp_temp;
            tinyml_history[0][1] = humidity_ref;
            tinyml_history[0][2] = net_rad;  /* usar R como proxy directo (no solar) */

            if (tinyml_filled < 3) tinyml_filled++;

            if (tinyml_filled == 3) {
                /* Construir vector de 9 features: lags 0, 1, 2 */
                float x[9];
                x[0] = tinyml_history[0][0]; x[1] = tinyml_history[0][1]; x[2] = tinyml_history[0][2];
                x[3] = tinyml_history[1][0]; x[4] = tinyml_history[1][1]; x[5] = tinyml_history[1][2];
                x[6] = tinyml_history[2][0]; x[7] = tinyml_history[2][1]; x[8] = tinyml_history[2][2];

                int64_t t0 = esp_timer_get_time();
                last_tinyml_pred = tinyml_predict(x);
                int64_t t1 = esp_timer_get_time();
                last_tinyml_us = t1 - t0;
            }
        }

        int64_t elapsed_us = esp_timer_get_time() - start_time;
        float elapsed_s = (float)elapsed_us / 1000000.0f;

        printf("%.1f,%d,"
               "%.2f,%.2f,"
               "%.2f,%.2f,%.2f,"
               "%.1f,%.4f,%.2f,%lld\n",
               elapsed_s,
               vent ? 1 : 0,
               aht_temp, aht_hum,
               bmp_temp, bmp_press,
               bmp_press / 10.0f,
               co2_est, etr,
               last_tinyml_pred,
               (long long)last_tinyml_us);
        fflush(stdout);

        gpio_set_level(LED_GPIO, 0);
        sample_count++;
        vTaskDelay(pdMS_TO_TICKS(SAMPLE_INTERVAL_MS));
    }
}
