/*
 * tinyml_inference.h
 * Forward pass INT8 per-channel para Dense[9 -> 32 -> 16 -> 1] con ReLU.
 * Compilable en ESP32-S3 (bare-metal, sin librerías externas).
 */
#ifndef TINYML_INFERENCE_H
#define TINYML_INFERENCE_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Predice T_ext a 1 h a partir de (T, HR, R) en t, t-1, t-2.
 *
 * @param x  Vector de 9 features: [T, HR, R, T_lag1, HR_lag1, R_lag1, T_lag2, HR_lag2, R_lag2]
 * @return   T_ext predicha en °C, o NaN si el modelo no está disponible.
 */
float tinyml_predict(const float x[9]);

/**
 * @brief Versión que mide latencia en microsegundos usando esp_timer.
 *        Imprime por consola el tiempo de inferencia.
 */
float tinyml_predict_timed(const float x[9]);

#endif /* TINYML_INFERENCE_H */
