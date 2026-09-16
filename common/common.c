#define _POSIX_C_SOURCE 199309L

#include "mandelbrot.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/**
 * @brief Aloca dinamicamente a estrutura ImageBuffer e o vetor contíguo de pixels.
 *
 * Aloca a estrutura controladora e um bloco contíguo de memória para armazenar
 * `width * height` elementos do tipo int32_t, garantindo contiguidade espacial.
 * Inicializa os parâmetros com os valores padrão (Input Padrão, Seção 5.2).
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
    img->max_iter = DEFAULT_MAX_ITER;
    img->re_min = DEFAULT_RE_MIN;
    img->re_max = DEFAULT_RE_MAX;
    img->im_min = DEFAULT_IM_MIN;
    img->im_max = DEFAULT_IM_MAX;

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
 * @brief Configura o cenário de execução no ImageBuffer (Seções 5.2 e 5.3).
 */
int configure_scenario(ImageBuffer *img, const char *scenario_name) {
    if (img == NULL) {
        return -1;
    }

    if (scenario_name == NULL || strcmp(scenario_name, "padrao") == 0 ||
        strcmp(scenario_name, "default") == 0 || strlen(scenario_name) == 0) {
        /* Input Padrão (Seção 5.2): Re in [-2.0, 1.0], Im in [-1.5, 1.5], MAX_ITER = 1000 */
        img->re_min = DEFAULT_RE_MIN;
        img->re_max = DEFAULT_RE_MAX;
        img->im_min = DEFAULT_IM_MIN;
        img->im_max = DEFAULT_IM_MAX;
        img->max_iter = DEFAULT_MAX_ITER;
        return 0;
    }

    if (strcmp(scenario_name, "seahorse") == 0) {
        /*
         * Caso de estresse: Vale dos Cavalos-Marinhos (Seção 5.3)
         * Centro: (-0.743643887, 0.131825904), largura = 0.003, MAX_ITER = 5000
         */
        double center_r = -0.743643887;
        double center_i = 0.131825904;
        double width_domain = 0.003;
        double aspect = (double)img->height / (double)img->width;
        double height_domain = width_domain * aspect;

        img->re_min = center_r - (width_domain / 2.0);
        img->re_max = center_r + (width_domain / 2.0);
        img->im_min = center_i - (height_domain / 2.0);
        img->im_max = center_i + (height_domain / 2.0);
        img->max_iter = 5000;
        return 0;
    }

    fprintf(stderr, "Aviso: cenario desconhecido '%s', utilizando 'padrao'.\n", scenario_name);
    return -1;
}

/**
 * @brief Mapeamento linear de coordenadas de tela (px, py) para o plano complexo (cr, ci).
 *
 * Utiliza os parâmetros do domínio (re_min, re_max, im_min, im_max) contidos no ImageBuffer.
 */
void pixel_to_complex(int px, int py, const ImageBuffer *img, double *cr, double *ci) {
    if (cr != NULL && img != NULL) {
        double factor_x = (img->width > 1) ? ((double)px / (double)(img->width - 1)) : 0.0;
        *cr = img->re_min + factor_x * (img->re_max - img->re_min);
    }
    if (ci != NULL && img != NULL) {
        double factor_y = (img->height > 1) ? ((double)py / (double)(img->height - 1)) : 0.0;
        *ci = img->im_min + factor_y * (img->im_max - img->im_min);
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
