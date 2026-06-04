/*
 * tinyml_inference_timed.c
 * Wrapper que mide latencia usando esp_timer.
 * Solo se compila si se necesita benchmark; no afecta al main loop.
 */
#include "tinyml_inference.h"
#include "esp_timer.h"
#include <stdio.h>

float tinyml_predict_timed(const float x[9])
{
    int64_t t0 = esp_timer_get_time();
    float pred = tinyml_predict(x);
    int64_t t1 = esp_timer_get_time();
    int64_t dt_us = t1 - t0;
    printf("[tinyml] Inference took %lld us (%.3f ms)\n", (long long)dt_us, (float)dt_us / 1000.0f);
    return pred;
}
