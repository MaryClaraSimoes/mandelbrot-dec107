#ifndef MANDELBROT_COMPUTE_H
#define MANDELBROT_COMPUTE_H

#include "mandelbrot.h"

/**
 * @brief Calcula o Conjunto de Mandelbrot em paralelo usando MPI.
 *
 * Distribui as linhas do plano complexo em blocos contíguos de linhas entre os
 * processos do comunicador MPI_COMM_WORLD. Cada processo aloca e computa
 * localmente sua respectiva fatia de linhas. Ao término da computação local,
 * as estatísticas de tempo são agregadas via reduções MPI e a matriz completa
 * de iterações é reunida no processo raiz (rank 0) via MPI_Gatherv.
 *
 * @param img     Buffer da imagem. OBSERVAÇÃO: img->data só é preenchido no
 *                rank 0. Nos demais processos (rank > 0), img pode ser NULL ou
 *                ter img->data não alocado.
 * @param params  Parâmetros da execução (largura, altura, max_iter, limites
 *                re_min, re_max, im_min, im_max).
 * @param balance Estrutura para retorno das métricas de balanceamento de carga.
 *                Preenchida apenas no rank 0 se o ponteiro for não-nulo.
 */
void compute_mandelbrot_mpi(ImageBuffer *img,
                            const MandelbrotParams *params,
                            LoadBalanceStats *balance);

#endif /* MANDELBROT_COMPUTE_H */
