#include "mandelbrot.h"
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
 */
void compute_mandelbrot(ImageBuffer *img, const MandelbrotParams *params) {
    if (img == NULL || img->data == NULL || params == NULL) {
        return;
    }

    #pragma omp parallel for schedule(runtime)
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
}
