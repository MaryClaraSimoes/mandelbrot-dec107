#include "mandelbrot.h"
#include <stdio.h>
#include <stdlib.h>
#ifdef _OPENMP
#include <omp.h>
#endif

/**
 * Ver mandelbrot.h para documentação da interface.
 *
 * Implementação OPENMP: paralelizada sobre o laço externo (py) com
 * schedule(runtime). Instrumenta o tempo computacional individual de cada
 * thread para calcular as métricas de balanceamento de carga (t_max, t_avg,
 * e lambda = t_avg / t_max), conforme exigido pela Seção 9 do PDF.
 */
void compute_mandelbrot(ImageBuffer *img) {
    if (img == NULL || img->data == NULL) {
        return;
    }

    int max_iter = img->max_iter;

#ifdef _OPENMP
    int max_threads = omp_get_max_threads();
    double *thread_times = (double *)calloc(max_threads, sizeof(double));
    int actual_threads = 1;

    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        #pragma omp single
        {
            actual_threads = omp_get_num_threads();
        }

        double t_start = omp_get_wtime();

        /*
         * Cláusula nowait: permite que cada thread registre seu tempo
         * imediatamente ao concluir suas iterações atribuídas, medindo
         * exclusivamente o tempo de trabalho sem incluir tempo de espera
         * na barreira implícita do for. A barreira da região paralela
         * garante que todas tenham gravado antes da redução externa.
         */
        #pragma omp for schedule(runtime) nowait
        for (int py = 0; py < img->height; py++) {
            for (int px = 0; px < img->width; px++) {
                double zr = 0.0, zi = 0.0, cr = 0.0, ci = 0.0;
                int iter = 0;

                pixel_to_complex(px, py, img, &cr, &ci);

                while (iter < max_iter && (zr*zr + zi*zi) <= 4.0) {
                    double next_zr = (zr*zr) - (zi*zi) + cr;
                    double next_zi = 2.0*(zr*zi) + ci;
                    zr = next_zr;
                    zi = next_zi;
                    iter++;
                }

                img->data[(size_t)py * img->width + px] = iter;
            }
        }

        double t_end = omp_get_wtime();
        thread_times[tid] = t_end - t_start;
    }

    /* Cálculo das métricas de balanceamento de carga (Seção 9) */
    double t_max = 0.0;
    double t_sum = 0.0;
    for (int i = 0; i < actual_threads; i++) {
        if (thread_times[i] > t_max) {
            t_max = thread_times[i];
        }
        t_sum += thread_times[i];
    }
    double t_avg = (actual_threads > 0) ? (t_sum / (double)actual_threads) : 0.0;
    double lambda = (t_max > 0.0) ? (t_avg / t_max) : 1.0;

    printf("t_max_s=%.6f\n", t_max);
    printf("t_avg_s=%.6f\n", t_avg);
    printf("lambda=%.6f\n", lambda);

    free(thread_times);
#else
    for (int py = 0; py < img->height; py++) {
        for (int px = 0; px < img->width; px++) {
            double zr = 0.0, zi = 0.0, cr = 0.0, ci = 0.0;
            int iter = 0;

            pixel_to_complex(px, py, img, &cr, &ci);

            while (iter < max_iter && (zr*zr + zi*zi) <= 4.0) {
                double next_zr = (zr*zr) - (zi*zi) + cr;
                double next_zi = 2.0*(zr*zi) + ci;
                zr = next_zr;
                zi = next_zi;
                iter++;
            }

            img->data[(size_t)py * img->width + px] = iter;
        }
    }
#endif
}
