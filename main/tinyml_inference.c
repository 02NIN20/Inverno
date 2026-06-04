/*
 * tinyml_inference.c
 * Forward pass INT8 per-channel para Dense[9 -> 32 -> 16 -> 1] con ReLU.
 * Auto-generado conceptualmente desde train_tinyml_real.py.
 *
 * Pipeline:
 *   x (9 floats) -> normalizar (x_mean, x_std) -> cuantizar [-4,4] a INT8
 *   -> capa densa 1: y = ReLU(W0 · x + b0) per-channel
 *   -> re-cuantizar activaciones a INT8
 *   -> capa densa 2: y = ReLU(W1 · h1 + b1) per-channel
 *   -> re-cuantizar activaciones a INT8
 *   -> capa densa 3: out = W2 · h2 + b2
 *   -> desnormalizar: T_pred = out * y_std + y_mean
 */
#include "tinyml_inference.h"
#include "tinyml_model_data.h"
#include <math.h>
#include <string.h>

static inline int8_t quantize_input(float v, float x_scale)
{
    float q = v / x_scale;
    if (q > 127.0f) q = 127.0f;
    if (q < -128.0f) q = -128.0f;
    return (int8_t)q;
}

static inline float dequantize_per_channel(int8_t q, float scale)
{
    return (float)q * scale;
}

static void dense_layer_per_channel(
    const int8_t *w,        /* [N_in, N_out] */
    const int8_t *b,        /* [N_out] */
    const float *sw,        /* [N_out] per-output scale */
    float sb,               /* scalar bias scale */
    const float *x,         /* [N_in] dequantized input */
    int N_in,
    int N_out,
    float *y)               /* [N_out] output */
{
    for (int j = 0; j < N_out; j++) {
        float acc = 0.0f;
        for (int i = 0; i < N_in; i++) {
            float w_ij = (float)w[i * N_out + j] * sw[j];
            acc += x[i] * w_ij;
        }
        acc += (float)b[j] * sb;
        y[j] = acc;
    }
}

static void requantize_to_int8(const float *x, int n, float *out_scale, int8_t *x_q)
{
    float max_abs = 1e-8f;
    for (int i = 0; i < n; i++) {
        float a = fabsf(x[i]);
        if (a > max_abs) max_abs = a;
    }
    float scale = max_abs / 127.0f;
    *out_scale = scale;
    for (int i = 0; i < n; i++) {
        float q = x[i] / scale;
        if (q > 127.0f) q = 127.0f;
        if (q < -128.0f) q = -128.0f;
        x_q[i] = (int8_t)q;
    }
}

float tinyml_predict(const float x[9])
{
    /* Buffers estáticos (no malloc, bare-metal) */
    static int8_t x_q[9];
    static float x_q_f[9];
    static float h1[TINYML_N_HIDDEN_1];
    static int8_t h1_q[TINYML_N_HIDDEN_1];
    static float h1_q_f[TINYML_N_HIDDEN_1];
    static float h2[TINYML_N_HIDDEN_2];
    static int8_t h2_q[TINYML_N_HIDDEN_2];
    static float h2_q_f[TINYML_N_HIDDEN_2];

    const float x_scale = TINYML_X_MAX / 127.0f;

    /* 1) Normalizar y cuantizar entrada */
    for (int i = 0; i < TINYML_N_FEATURES; i++) {
        float xn = (x[i] - tinyml_x_mean[i]) / tinyml_x_std[i];
        if (xn > TINYML_X_MAX) xn = TINYML_X_MAX;
        if (xn < -TINYML_X_MAX) xn = -TINYML_X_MAX;
        x_q[i] = quantize_input(xn, x_scale);
        x_q_f[i] = (float)x_q[i] * x_scale;
    }

    /* 2) Capa densa 1: 9 -> 32 (per-channel) */
    dense_layer_per_channel(
        tinyml_w0, tinyml_b0, tinyml_sw0, tinyml_sb0,
        x_q_f, TINYML_N_FEATURES, TINYML_N_HIDDEN_1, h1);

    /* ReLU */
    for (int j = 0; j < TINYML_N_HIDDEN_1; j++) {
        if (h1[j] < 0.0f) h1[j] = 0.0f;
    }

    /* Re-cuantizar activaciones capa 1 */
    float h1_scale;
    requantize_to_int8(h1, TINYML_N_HIDDEN_1, &h1_scale, h1_q);
    for (int j = 0; j < TINYML_N_HIDDEN_1; j++) {
        h1_q_f[j] = (float)h1_q[j] * h1_scale;
    }

    /* 3) Capa densa 2: 32 -> 16 (per-channel) */
    dense_layer_per_channel(
        tinyml_w1, tinyml_b1, tinyml_sw1, tinyml_sb1,
        h1_q_f, TINYML_N_HIDDEN_1, TINYML_N_HIDDEN_2, h2);

    /* ReLU */
    for (int j = 0; j < TINYML_N_HIDDEN_2; j++) {
        if (h2[j] < 0.0f) h2[j] = 0.0f;
    }

    /* Re-cuantizar activaciones capa 2 */
    float h2_scale;
    requantize_to_int8(h2, TINYML_N_HIDDEN_2, &h2_scale, h2_q);
    for (int j = 0; j < TINYML_N_HIDDEN_2; j++) {
        h2_q_f[j] = (float)h2_q[j] * h2_scale;
    }

    /* 4) Capa densa 3: 16 -> 1 */
    float out = 0.0f;
    for (int i = 0; i < TINYML_N_HIDDEN_2; i++) {
        out += h2_q_f[i] * (float)tinyml_w2[i] * tinyml_sw2[0];
    }
    out += (float)tinyml_b2[0] * tinyml_sb2;

    /* 5) Desnormalizar salida */
    return out * tinyml_y_std + tinyml_y_mean;
}
