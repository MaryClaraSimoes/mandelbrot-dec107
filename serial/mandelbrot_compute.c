#include "mandelbrot.h"

/**
 * Ver mandelbrot.h para documentação da interface.
 *
 * Implementação SEQUENCIAL de referência: percorre a matriz estritamente
 * em ordem row-major, sem qualquer paralelismo. Esta é a versão usada
 * para gerar a saída binária canônica de validação de corretude.
 */
void compute_mandelbrot(ImageBuffer *img) {
    if (img == NULL || img->data == NULL) {
        return;
    }

    int max_iter = img->max_iter;

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
}
