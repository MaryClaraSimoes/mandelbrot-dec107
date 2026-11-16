#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "common.h"

/* ========================================================================== */
/* Cálculo Serial de Referência — Conjunto de Mandelbrot (Seção 5.1)          */
/* ========================================================================== */
static void compute_mandelbrot_serial(int *matrix, const MandelbrotParams *params) {
    const int width    = params->width;
    const int height   = params->height;
    const int max_iter = params->max_iter;
    const double xmin  = params->xmin;
    const double xmax  = params->xmax;
    const double ymin  = params->ymin;
    const double ymax  = params->ymax;

    const double range_x = xmax - xmin;
    const double range_y = ymax - ymin;
    const double denom_x = (width > 1)  ? (double)(width - 1)  : 1.0;
    const double denom_y = (height > 1) ? (double)(height - 1) : 1.0;

    for (int py = 0; py < height; py++) {
        const double ci = ymin + ((double)py / denom_y) * range_y;

        for (int px = 0; px < width; px++) {
            const double cr = xmin + ((double)px / denom_x) * range_x;

            double zr = 0.0;
            double zi = 0.0;
            int iter  = 0;

            while (iter < max_iter && (zr * zr + zi * zi) <= 4.0) {
                double next_zr = (zr * zr) - (zi * zi) + cr;
                double next_zi = 2.0 * (zr * zi) + ci;
                zr = next_zr;
                zi = next_zi;
                iter++;
            }

            matrix[(size_t)py * (size_t)width + (size_t)px] = iter;
        }
    }
}

int main(int argc, char **argv) {
    MandelbrotParams params;
    init_default_params(&params, "output/serial_base.bin", "output/serial_base.pgm");

    int rc = parse_args(argc, argv, &params);
    if (rc == 1) {
        return EXIT_SUCCESS;
    }
    if (rc != 0) {
        return EXIT_FAILURE;
    }

    size_t total_pixels = (size_t)params.width * (size_t)params.height;
    int *matrix = (int *)malloc(total_pixels * sizeof(int));
    if (matrix == NULL) {
        perror("Erro ao alocar matriz no host");
        return EXIT_FAILURE;
    }

    printf("=== Mandelbrot Serial (Referencia) ===\n");
    printf("Resolucao : %d x %d (%zu pixels)\n", params.width, params.height, total_pixels);
    printf("Regiao Re : [%.10f, %.10f]\n", params.xmin, params.xmax);
    printf("Regiao Im : [%.10f, %.10f]\n", params.ymin, params.ymax);
    printf("MAX_ITER  : %d\n", params.max_iter);

    struct timespec t_start, t_end;
    clock_gettime(CLOCK_MONOTONIC, &t_start);

    compute_mandelbrot_serial(matrix, &params);

    clock_gettime(CLOCK_MONOTONIC, &t_end);
    double elapsed_sec = (double)(t_end.tv_sec - t_start.tv_sec) +
                         (double)(t_end.tv_nsec - t_start.tv_nsec) * 1e-9;

    printf("Tempo de calculo (serial): %.6f s (%.3f ms)\n", elapsed_sec, elapsed_sec * 1000.0);

    if (params.out_bin != NULL) {
        if (write_matrix_bin(params.out_bin, matrix, params.width, params.height) != 0) {
            free(matrix);
            return EXIT_FAILURE;
        }
        printf("Matriz binaria salva em : %s\n", params.out_bin);
    }

    if (params.out_pgm != NULL) {
        if (write_pgm(params.out_pgm, matrix, params.width, params.height, params.max_iter) != 0) {
            free(matrix);
            return EXIT_FAILURE;
        }
        printf("Imagem PGM salva em     : %s\n", params.out_pgm);
    }

    free(matrix);
    return EXIT_SUCCESS;
}
