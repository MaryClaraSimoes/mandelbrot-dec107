#ifndef COMMON_H
#define COMMON_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>

/* ========================================================================== */
/* Constantes Padrão — Seção 5.2 (Caso Base) e Seção 5.3 (Desbalanceamento)   */
/* ========================================================================== */
#define DEFAULT_WIDTH      4096
#define DEFAULT_HEIGHT     4096
#define DEFAULT_XMIN      -2.0
#define DEFAULT_XMAX       1.0
#define DEFAULT_YMIN      -1.5
#define DEFAULT_YMAX       1.5
#define DEFAULT_MAX_ITER   1000

/* Caso de desbalanceamento acentuado (Seção 5.3 — Vale dos Cavalos-Marinhos) */
#define ZOOM_CENTER_X     -0.743643887
#define ZOOM_CENTER_Y      0.131825904
#define ZOOM_WIDTH         3.0e-3
#define ZOOM_MAX_ITER      5000

/* Garante que int possui 32 bits (int32 row-major conforme Seção 5.4) */
typedef int mandelbrot_int_check[(sizeof(int) == 4) ? 1 : -1];

/* ========================================================================== */
/* Estrutura de Parâmetros                                                    */
/* ========================================================================== */
typedef struct {
    int width;
    int height;
    double xmin;
    double xmax;
    double ymin;
    double ymax;
    int max_iter;
    const char *out_bin;
    const char *out_pgm;
} MandelbrotParams;

/* ========================================================================== */
/* Protótipos das Funções Utilitárias e de Escrita                            */
/* ========================================================================== */
static inline void init_default_params(MandelbrotParams *params,
                                       const char *default_bin,
                                       const char *default_pgm);

static inline int parse_args(int argc, char **argv, MandelbrotParams *params);

static inline int write_matrix_bin(const char *path, const int *matrix,
                                   int width, int height);

static inline int write_pgm(const char *path, const int *matrix,
                            int width, int height, int max_iter);

/* ========================================================================== */
/* Implementações Inline (compartilhadas entre serial C11 e CUDA C++)         */
/* ========================================================================== */

static inline void ensure_parent_dir(const char *filepath) {
    if (filepath == NULL) {
        return;
    }
    const char *slash = strrchr(filepath, '/');
    if (slash != NULL && slash != filepath) {
        size_t len = (size_t)(slash - filepath);
        char *dir = (char *)malloc(len + 1);
        if (dir != NULL) {
            memcpy(dir, filepath, len);
            dir[len] = '\0';
            mkdir(dir, 0775);
            free(dir);
        }
    }
}

static inline void init_default_params(MandelbrotParams *params,
                                       const char *default_bin,
                                       const char *default_pgm) {
    if (params == NULL) {
        return;
    }
    params->width    = DEFAULT_WIDTH;
    params->height   = DEFAULT_HEIGHT;
    params->xmin     = DEFAULT_XMIN;
    params->xmax     = DEFAULT_XMAX;
    params->ymin     = DEFAULT_YMIN;
    params->ymax     = DEFAULT_YMAX;
    params->max_iter = DEFAULT_MAX_ITER;
    params->out_bin  = default_bin;
    params->out_pgm  = default_pgm;
}

static inline void print_cli_usage(FILE *fp, const char *prog) {
    fprintf(fp,
        "Uso: %s [opcoes]\n\n"
        "Opcoes:\n"
        "  --width N         Largura da imagem em pixels (padrao: %d)\n"
        "  --height N        Altura da imagem em pixels (padrao: %d)\n"
        "  --xmin X          Limite inferior do eixo real (padrao: %.1f)\n"
        "  --xmax X          Limite superior do eixo real (padrao: %.1f)\n"
        "  --ymin Y          Limite inferior do eixo imaginario (padrao: %.1f)\n"
        "  --ymax Y          Limite superior do eixo imaginario (padrao: %.1f)\n"
        "  --max-iter N      Numero maximo de iteracoes (padrao: %d)\n"
        "  --out-bin PATH    Caminho do arquivo binario de saida\n"
        "  --out-pgm PATH    Caminho da imagem PGM de saida\n"
        "  --preset NAME     Preset de regiao: 'full' (Secao 5.2) ou 'seahorse'/'zoom' (Secao 5.3)\n"
        "  -h, --help        Exibe esta mensagem de ajuda\n",
        prog ? prog : "mandelbrot",
        DEFAULT_WIDTH, DEFAULT_HEIGHT,
        DEFAULT_XMIN, DEFAULT_XMAX,
        DEFAULT_YMIN, DEFAULT_YMAX,
        DEFAULT_MAX_ITER);
}

static inline int parse_int_option(const char *flag, const char *val_str, int *out_val) {
    if (val_str == NULL || val_str[0] == '\0') {
        fprintf(stderr, "Erro: a opcao %s requer um valor inteiro.\n", flag);
        return -1;
    }
    char *endptr = NULL;
    long v = strtol(val_str, &endptr, 10);
    if (endptr == val_str || *endptr != '\0') {
        fprintf(stderr, "Erro: valor inteiro invalido para %s: '%s'\n", flag, val_str);
        return -1;
    }
    *out_val = (int)v;
    return 0;
}

static inline int parse_double_option(const char *flag, const char *val_str, double *out_val) {
    if (val_str == NULL || val_str[0] == '\0') {
        fprintf(stderr, "Erro: a opcao %s requer um valor real (double).\n", flag);
        return -1;
    }
    char *endptr = NULL;
    double v = strtod(val_str, &endptr);
    if (endptr == val_str || *endptr != '\0') {
        fprintf(stderr, "Erro: valor real invalido para %s: '%s'\n", flag, val_str);
        return -1;
    }
    *out_val = v;
    return 0;
}

static inline int parse_args(int argc, char **argv, MandelbrotParams *params) {
    if (params == NULL) {
        return -1;
    }

    for (int i = 1; i < argc; i++) {
        const char *arg = argv[i];

        if (strcmp(arg, "-h") == 0 || strcmp(arg, "--help") == 0) {
            print_cli_usage(stdout, argv[0]);
            return 1;
        } else if (strcmp(arg, "--width") == 0) {
            if (i + 1 >= argc || parse_int_option(arg, argv[++i], &params->width) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--height") == 0) {
            if (i + 1 >= argc || parse_int_option(arg, argv[++i], &params->height) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--xmin") == 0 || strcmp(arg, "--re-min") == 0) {
            if (i + 1 >= argc || parse_double_option(arg, argv[++i], &params->xmin) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--xmax") == 0 || strcmp(arg, "--re-max") == 0) {
            if (i + 1 >= argc || parse_double_option(arg, argv[++i], &params->xmax) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--ymin") == 0 || strcmp(arg, "--im-min") == 0) {
            if (i + 1 >= argc || parse_double_option(arg, argv[++i], &params->ymin) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--ymax") == 0 || strcmp(arg, "--im-max") == 0) {
            if (i + 1 >= argc || parse_double_option(arg, argv[++i], &params->ymax) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--max-iter") == 0) {
            if (i + 1 >= argc || parse_int_option(arg, argv[++i], &params->max_iter) != 0) {
                return -1;
            }
        } else if (strcmp(arg, "--out-bin") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Erro: --out-bin requer um caminho de arquivo.\n");
                return -1;
            }
            params->out_bin = argv[++i];
        } else if (strcmp(arg, "--out-pgm") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Erro: --out-pgm requer um caminho de arquivo.\n");
                return -1;
            }
            params->out_pgm = argv[++i];
        } else if (strcmp(arg, "--preset") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Erro: --preset requer 'full' ou 'seahorse'/'zoom'.\n");
                return -1;
            }
            const char *preset = argv[++i];
            if (strcmp(preset, "full") == 0) {
                params->xmin     = DEFAULT_XMIN;
                params->xmax     = DEFAULT_XMAX;
                params->ymin     = DEFAULT_YMIN;
                params->ymax     = DEFAULT_YMAX;
                params->max_iter = DEFAULT_MAX_ITER;
            } else if (strcmp(preset, "seahorse") == 0 || strcmp(preset, "zoom") == 0) {
                double half_w = ZOOM_WIDTH / 2.0;
                double aspect = (params->width > 0) ? ((double)params->height / (double)params->width) : 1.0;
                double half_h = half_w * aspect;
                params->xmin     = ZOOM_CENTER_X - half_w;
                params->xmax     = ZOOM_CENTER_X + half_w;
                params->ymin     = ZOOM_CENTER_Y - half_h;
                params->ymax     = ZOOM_CENTER_Y + half_h;
                params->max_iter = ZOOM_MAX_ITER;
            } else {
                fprintf(stderr, "Erro: preset desconhecido '%s'. Use 'full' ou 'seahorse'.\n", preset);
                return -1;
            }
        } else {
            fprintf(stderr, "Erro: opcao desconhecida '%s'\n", arg);
            print_cli_usage(stderr, argv[0]);
            return -1;
        }
    }

    if (params->width <= 0 || params->height <= 0) {
        fprintf(stderr, "Erro: width e height devem ser maiores que zero.\n");
        return -1;
    }
    if (params->max_iter <= 0) {
        fprintf(stderr, "Erro: max-iter deve ser maior que zero.\n");
        return -1;
    }
    if (!(params->xmin < params->xmax) || !(params->ymin < params->ymax)) {
        fprintf(stderr, "Erro: intervalo invalido (requer xmin < xmax e ymin < ymax).\n");
        return -1;
    }

    return 0;
}

static inline int write_matrix_bin(const char *path, const int *matrix,
                                   int width, int height) {
    if (path == NULL || matrix == NULL || width <= 0 || height <= 0) {
        fprintf(stderr, "Erro: parametros invalidos em write_matrix_bin.\n");
        return -1;
    }

    ensure_parent_dir(path);

    FILE *fp = fopen(path, "wb");
    if (fp == NULL) {
        perror("Erro ao abrir arquivo binario para escrita");
        return -1;
    }

    size_t total = (size_t)width * (size_t)height;
    size_t written = fwrite(matrix, sizeof(int), total, fp);
    fclose(fp);

    if (written != total) {
        fprintf(stderr, "Erro: escrita incompleta em '%s' (%zu de %zu elementos).\n",
                path, written, total);
        return -1;
    }

    return 0;
}

static inline int write_pgm(const char *path, const int *matrix,
                            int width, int height, int max_iter) {
    if (path == NULL || matrix == NULL || width <= 0 || height <= 0 || max_iter <= 0) {
        fprintf(stderr, "Erro: parametros invalidos em write_pgm.\n");
        return -1;
    }

    ensure_parent_dir(path);

    FILE *fp = fopen(path, "wb");
    if (fp == NULL) {
        perror("Erro ao abrir arquivo PGM para escrita");
        return -1;
    }

    fprintf(fp, "P5\n%d %d\n255\n", width, height);

    size_t total = (size_t)width * (size_t)height;
    unsigned char *buf = (unsigned char *)malloc(total);
    if (buf == NULL) {
        perror("Erro ao alocar buffer para imagem PGM");
        fclose(fp);
        return -1;
    }

    for (size_t i = 0; i < total; i++) {
        int iter = matrix[i];
        if (iter >= max_iter) {
            buf[i] = 0;
        } else {
            buf[i] = (unsigned char)(255.0 * (double)iter / (double)max_iter);
        }
    }

    size_t written = fwrite(buf, 1, total, fp);
    free(buf);
    fclose(fp);

    if (written != total) {
        fprintf(stderr, "Erro: escrita incompleta no PGM '%s' (%zu de %zu bytes).\n",
                path, written, total);
        return -1;
    }

    return 0;
}

#endif /* COMMON_H */
