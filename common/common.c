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
 * @brief Preenche params com os valores padrão do input oficial (seção 5.2).
 */
void mandelbrot_params_init_default(MandelbrotParams *params) {
    if (params == NULL) {
        return;
    }

    params->width = WIDTH;
    params->height = HEIGHT;
    params->max_iter = MAX_ITER;
    params->re_min = RE_MIN;
    params->re_max = RE_MAX;
    params->im_min = IM_MIN;
    params->im_max = IM_MAX;
}

static void print_usage(FILE *fp, const char *prog) {
    const char *name = (prog != NULL && prog[0] != '\0') ? prog : "mandelbrot";
    fprintf(fp,
        "Uso: %s [opcoes]\n"
        "\n"
        "  --width N       Largura em pixels          (padrao: %d)\n"
        "  --height N      Altura em pixels           (padrao: %d)\n"
        "  --max-iter N    Teto de iteracoes          (padrao: %d)\n"
        "  --re-min X      Minimo do eixo real        (padrao: %.1f)\n"
        "  --re-max X      Maximo do eixo real        (padrao: %.1f)\n"
        "  --im-min Y      Minimo do eixo imaginario  (padrao: %.1f)\n"
        "  --im-max Y      Maximo do eixo imaginario  (padrao: %.1f)\n"
        "  --preset NAME   full (secao 5.2) ou seahorse (secao 5.3)\n"
        "  -h, --help      Exibe esta ajuda e encerra\n"
        "\n"
        "Sem opcoes, usa o input oficial da secao 5.2.\n"
        "O preset seahorse centra o zoom em (%.9f, %.9f), largura real %.1e,\n"
        "MAX_ITER=%d; a resolucao permanece a corrente (--width/--height).\n",
        name, WIDTH, HEIGHT, MAX_ITER, RE_MIN, RE_MAX, IM_MIN, IM_MAX,
        SEAHORSE_RE_CENTER, SEAHORSE_IM_CENTER, SEAHORSE_RE_WIDTH, SEAHORSE_MAX_ITER);
}

static int parse_int_arg(const char *flag, const char *text, int *out) {
    char *end = NULL;
    long value;

    if (text == NULL || text[0] == '\0') {
        fprintf(stderr, "Erro: %s requer um valor inteiro.\n", flag);
        return -1;
    }

    value = strtol(text, &end, 10);
    if (end == text || *end != '\0') {
        fprintf(stderr, "Erro: valor invalido para %s: '%s'\n", flag, text);
        return -1;
    }

    *out = (int)value;
    return 0;
}

static int parse_double_arg(const char *flag, const char *text, double *out) {
    char *end = NULL;
    double value;

    if (text == NULL || text[0] == '\0') {
        fprintf(stderr, "Erro: %s requer um numero real.\n", flag);
        return -1;
    }

    value = strtod(text, &end);
    if (end == text || *end != '\0') {
        fprintf(stderr, "Erro: valor invalido para %s: '%s'\n", flag, text);
        return -1;
    }

    *out = value;
    return 0;
}

static void apply_preset_full(MandelbrotParams *params) {
    params->max_iter = MAX_ITER;
    params->re_min = RE_MIN;
    params->re_max = RE_MAX;
    params->im_min = IM_MIN;
    params->im_max = IM_MAX;
}

static void apply_preset_seahorse(MandelbrotParams *params) {
    double half = SEAHORSE_RE_WIDTH / 2.0;
    params->max_iter = SEAHORSE_MAX_ITER;
    params->re_min = SEAHORSE_RE_CENTER - half;
    params->re_max = SEAHORSE_RE_CENTER + half;
    params->im_min = SEAHORSE_IM_CENTER - half;
    params->im_max = SEAHORSE_IM_CENTER + half;
}

static int require_value(int i, int argc, const char *flag) {
    if (i + 1 >= argc) {
        fprintf(stderr, "Erro: %s requer um valor.\n", flag);
        return -1;
    }
    return 0;
}

/**
 * @brief Interpreta argc/argv e sobrescreve os campos correspondentes em params.
 *
 * @return  0 sucesso; 1 ajuda; -1 erro.
 */
int mandelbrot_params_parse_args(int argc, char **argv, MandelbrotParams *params) {
    int i;

    if (params == NULL) {
        return -1;
    }

    for (i = 1; i < argc; i++) {
        const char *arg = argv[i];

        if (strcmp(arg, "-h") == 0 || strcmp(arg, "--help") == 0) {
            print_usage(stdout, argv[0]);
            return 1;
        }

        if (strcmp(arg, "--width") == 0) {
            if (require_value(i, argc, arg) != 0 ||
                parse_int_arg(arg, argv[++i], &params->width) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--height") == 0) {
            if (require_value(i, argc, arg) != 0 ||
                parse_int_arg(arg, argv[++i], &params->height) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--max-iter") == 0) {
            if (require_value(i, argc, arg) != 0 ||
                parse_int_arg(arg, argv[++i], &params->max_iter) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--re-min") == 0) {
            if (require_value(i, argc, arg) != 0 ||
                parse_double_arg(arg, argv[++i], &params->re_min) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--re-max") == 0) {
            if (require_value(i, argc, arg) != 0 ||
                parse_double_arg(arg, argv[++i], &params->re_max) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--im-min") == 0) {
            if (require_value(i, argc, arg) != 0 ||
                parse_double_arg(arg, argv[++i], &params->im_min) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--im-max") == 0) {
            if (require_value(i, argc, arg) != 0 ||
                parse_double_arg(arg, argv[++i], &params->im_max) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--preset") == 0) {
            const char *name;
            if (require_value(i, argc, arg) != 0) {
                return -1;
            }
            name = argv[++i];
            if (strcmp(name, "full") == 0) {
                apply_preset_full(params);
            } else if (strcmp(name, "seahorse") == 0) {
                apply_preset_seahorse(params);
            } else {
                fprintf(stderr, "Erro: --preset desconhecido: '%s' (use full ou seahorse)\n", name);
                return -1;
            }
        } else {
            fprintf(stderr, "Erro: opcao desconhecida: '%s'\n", arg);
            print_usage(stderr, argv[0]);
            return -1;
        }
    }

    if (params->width <= 0 || params->height <= 0) {
        fprintf(stderr, "Erro: --width e --height devem ser inteiros positivos.\n");
        return -1;
    }
    if (params->max_iter <= 0) {
        fprintf(stderr, "Erro: --max-iter deve ser um inteiro positivo.\n");
        return -1;
    }
    if (!(params->re_min < params->re_max) || !(params->im_min < params->im_max)) {
        fprintf(stderr, "Erro: o dominio exige re_min < re_max e im_min < im_max.\n");
        return -1;
    }

    return 0;
}

/**
 * @brief Mapeamento linear de coordenadas de tela (px, py) para o plano complexo (cr, ci).
 *
 * Fórmulas aplicadas:
 *   cr = re_min + ((double)px / (width - 1)) * (re_max - re_min)
 *   ci = im_min + ((double)py / (height - 1)) * (im_max - im_min)
 */
void pixel_to_complex(int px, int py, const MandelbrotParams *params, double *cr, double *ci) {
    if (params == NULL) {
        return;
    }

    if (cr != NULL) {
        double factor_x = (params->width > 1) ? ((double)px / (double)(params->width - 1)) : 0.0;
        *cr = params->re_min + factor_x * (params->re_max - params->re_min);
    }
    if (ci != NULL) {
        double factor_y = (params->height > 1) ? ((double)py / (double)(params->height - 1)) : 0.0;
        *ci = params->im_min + factor_y * (params->im_max - params->im_min);
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
