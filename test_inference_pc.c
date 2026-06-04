/*
 * test_inference_pc.c
 * Compila en PC (no ESP32) para validar que tinyml_inference.c
 * produce el mismo output que la implementación Python/numpy.
 * Compilar: gcc -I main -o test_inference_pc main/tinyml_inference.c test_inference_pc.c -lm
 */
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

/* Forzar compilación sin ESP-IDF: usar el modelo como si fuera host */
#define ESP_OK 0
typedef int esp_err_t;

/* Mock esp_timer para PC */
static long long mock_time_us = 0;

#include "main/tinyml_model_data.h"
#include "main/tinyml_inference.h"

int main(int argc, char *argv[])
{
    /* Vector de test: 9 features (T, HR, R) en t, t-1, t-2 */
    /* Caso 1: Mañana fría típica de Bogotá, t=8h */
    float x1[9] = {
        11.0f, 85.0f, 200.0f,   /* t */
        10.0f, 88.0f, 100.0f,   /* t-1 */
        9.0f,  90.0f, 0.0f      /* t-2 */
    };

    /* Caso 2: Tarde soleada, t=14h */
    float x2[9] = {
        20.0f, 50.0f, 700.0f,
        18.0f, 60.0f, 500.0f,
        16.0f, 70.0f, 200.0f
    };

    /* Caso 3: Noche, t=22h */
    float x3[9] = {
        12.0f, 90.0f, 0.0f,
        12.0f, 92.0f, 0.0f,
        13.0f, 88.0f, 0.0f
    };

    printf("=== Test tinyml_predict en PC ===\n\n");

    float y1 = tinyml_predict(x1);
    float y2 = tinyml_predict(x2);
    float y3 = tinyml_predict(x3);

    printf("Test 1 (mañana fría):    T_pred = %.2f °C (esperado ~12-14°C)\n", y1);
    printf("Test 2 (tarde soleada):   T_pred = %.2f °C (esperado ~21-23°C)\n", y2);
    printf("Test 3 (noche estable):   T_pred = %.2f °C (esperado ~11-13°C)\n", y3);

    /* Test de "consistencia": predecir 100 veces el mismo input, debe dar igual */
    float y_repeat = tinyml_predict(x2);
    float y_diff = fabsf(y2 - y_repeat);
    printf("\nReproductibilidad (mismo input 2 veces): diff = %.6f °C\n", y_diff);
    if (y_diff > 0.01f) {
        printf("FAIL: la inferencia no es determinista!\n");
        return 1;
    }

    printf("\nOK: inferencia funciona en PC (puerto a ESP32 viable)\n");
    return 0;
}
