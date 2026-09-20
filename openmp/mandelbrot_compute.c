#include "mandelbrot.h"
#include <stdlib.h>
#ifdef _OPENMP
#include <omp.h>
#endif

/**
 * Ver mandelbrot.h para documentação da interface.
 *
 * Implementação OPENMP: mesma lógica sequencial de base, mas paralelizada
 * sobre o loop externo (py). zr/zi/cr/ci/iter já estão declaradas dentro
 * do loop de px, portanto já são privadas por iteração por padrão do OpenMP.
 *
 * Usando schedule(runtime), a política e o chunk size podem ser trocados
 * sem recompilar, via variável de ambiente, por exemplo:
 *   OMP_SCHEDULE="dynamic,16" ./mandelbrot_omp
 *
 * O laço é `omp for nowait` dentro de `omp parallel` para registrar o tempo
 * de trabalho de cada thread *antes* da barreira implícita do fim da região
 * paralela. Sem nowait, todos os tempos de parede coincidiriam com o da
 * thread mais lenta e o fator de balanceamento ficaria artificialmente 1.
 */
static void fill_balance_stats(LoadBalanceStats *balance, const double *times, int nthreads) {
    double t_min, t_max, sum;
    int i;

    if (balance == NULL || times == NULL || nthreads <= 0) {
        return;
    }

    t_min = times[0];
    t_max = times[0];
    sum = times[0];
    for (i = 1; i < nthreads; i++) {
        if (times[i] < t_min) {
            t_min = times[i];
        }
        if (times[i] > t_max) {
            t_max = times[i];
        }
        sum += times[i];
    }

    balance->nthreads = nthreads;
    balance->t_min = t_min;
    balance->t_max = t_max;
    balance->t_mean = sum / (double)nthreads;
    balance->factor = (balance->t_mean > 0.0) ? (t_max / balance->t_mean) : 1.0;
}

void compute_mandelbrot(ImageBuffer *img, const MandelbrotParams *params,
                        LoadBalanceStats *balance) {
    double *thread_time = NULL;
    int nthreads_used = 1;
    int max_threads = 1;

    if (img == NULL || img->data == NULL || params == NULL) {
        return;
    }

#ifdef _OPENMP
    max_threads = omp_get_max_threads();
#endif
    if (balance != NULL && max_threads > 0) {
        thread_time = (double *)calloc((size_t)max_threads, sizeof(double));
    }

#ifdef _OPENMP
    #pragma omp parallel
#endif
    {
        int tid = 0;
#ifdef _OPENMP
        tid = omp_get_thread_num();
        #pragma omp single
        {
            nthreads_used = omp_get_num_threads();
        }
#endif

#ifdef _OPENMP
        double t0 = omp_get_wtime();
#else
        double t0 = get_wtime();
#endif

#ifdef _OPENMP
        #pragma omp for schedule(runtime) nowait
#endif
        for (int py = 0; py < img->height; py++) {
            for (int px = 0; px < img->width; px++) {
                double zr = 0.0, zi = 0.0, cr = 0.0, ci = 0.0;
                int iter = 0;

                pixel_to_complex(px, py, params, &cr, &ci);

                while (iter < params->max_iter && (zr*zr + zi*zi) <= 4.0) {
                    double next_zr = (zr*zr) - (zi*zi) + cr;
                    double next_zi = 2*(zr*zi) + ci;
                    zr = next_zr;
                    zi = next_zi;
                    iter++;
                }

                img->data[(size_t)py * img->width + px] = iter;
            }
        }

#ifdef _OPENMP
        double t1 = omp_get_wtime();
#else
        double t1 = get_wtime();
#endif
        if (thread_time != NULL) {
            thread_time[tid] = t1 - t0;
        }
    }

    if (balance != NULL && thread_time != NULL) {
        fill_balance_stats(balance, thread_time, nthreads_used);
        free(thread_time);
    }
}
