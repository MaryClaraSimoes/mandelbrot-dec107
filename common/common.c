#define _POSIX_C_SOURCE 199309L

#include "mandelbrot.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/**
 * @brief Aloca dinamicamente a estrutura ImageBuffer e o vetor contíguo de pixels.
 *
 * Aloca a estrutura controladora e um bloco contíguo de memória para armazenar
 * `width * height` elementos do tipo int32_t, garantindo contiguidade espacial.
 * Em caso de falha de alocação de qualquer um dos blocos, garante a liberação
 * adequada e retorna NULL.
 */
ImageBuffer* create_image_buffer(int width, int height) {
    if (width <= 0 || height <= 0) {
        return NULL;
    }

    ImageBuffer *img = (ImageBuffer *)malloc(sizeof(ImageBuffer));
    if (img == NULL) {
        perror("Erro ao alocar estrutura ImageBuffer");
        return NULL;
    }

    size_t total_pixels = (size_t)width * (size_t)height;
    img->data = (int32_t *)malloc(total_pixels * sizeof(int32_t));
    if (img->data == NULL) {
        perror("Erro ao alocar buffer de dados da imagem");
        free(img);
        return NULL;
    }

    img->width = width;
    img->height = height;

    return img;
}

/**
 * @brief Libera a memória do vetor contíguo de dados e da estrutura ImageBuffer.
 */
void free_image_buffer(ImageBuffer *img) {
    if (img != NULL) {
        if (img->data != NULL) {
            free(img->data);
            img->data = NULL;
        }
        free(img);
    }
}

/**
 * @brief Mapeamento linear de coordenadas de tela (px, py) para o plano complexo (cr, ci).
 *
 * Fórmulas aplicadas:
 *   cr = RE_MIN + ((double)px / (width - 1)) * (RE_MAX - RE_MIN)
 *   ci = IM_MIN + ((double)py / (height - 1)) * (IM_MAX - IM_MIN)
 */
void pixel_to_complex(int px, int py, int width, int height, double *cr, double *ci) {
    if (cr != NULL) {
        double factor_x = (width > 1) ? ((double)px / (double)(width - 1)) : 0.0;
        *cr = RE_MIN + factor_x * (RE_MAX - RE_MIN);
    }
    if (ci != NULL) {
        double factor_y = (height > 1) ? ((double)py / (double)(height - 1)) : 0.0;
        *ci = IM_MIN + factor_y * (IM_MAX - IM_MIN);
    }
}

/**
 * @brief Retorna o tempo decorrido com alta precisão usando CLOCK_MONOTONIC.
 */
double get_wtime(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
