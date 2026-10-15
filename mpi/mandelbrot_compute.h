#ifndef MANDELBROT_COMPUTE_H
#define MANDELBROT_COMPUTE_H

#include "mandelbrot.h"

/**
 * @brief Calcula o Conjunto de Mandelbrot em paralelo usando MPI.
 *
 * Distribui as linhas do plano complexo entre os processos de MPI_COMM_WORLD
 * conforme params->strategy:
 *   - MANDELBROT_STRATEGY_BLOCK: blocos contíguos de linhas (Estratégia A);
 *     MPI_Gatherv escreve diretamente nas posições corretas de img->data.
 *   - MANDELBROT_STRATEGY_CYCLIC: linhas intercaladas py = rank; py += size
 *     (Estratégia B); MPI_Gatherv coleta segmentos empacotados e o rank 0
 *     remonta a imagem na ordem global.
 *
 * Cada processo aloca e computa localmente sua fatia. Ao término, as
 * estatísticas de tempo são agregadas via reduções MPI (λ = t_max / t_mean)
 * e a matriz completa de iterações fica disponível no processo raiz.
 *
 * @param img     Buffer da imagem. OBSERVAÇÃO: img->data só é preenchido no
 *                rank 0. Nos demais processos (rank > 0), img pode ser NULL ou
 *                ter img->data não alocado.
 * @param params  Parâmetros da execução (largura, altura, max_iter, limites
 *                re_min, re_max, im_min, im_max, strategy).
 * @param balance Estrutura para retorno das métricas de balanceamento de carga.
 *                Preenchida apenas no rank 0 se o ponteiro for não-nulo.
 */
void compute_mandelbrot_mpi(ImageBuffer *img,
                            const MandelbrotParams *params,
                            LoadBalanceStats *balance);

#endif /* MANDELBROT_COMPUTE_H */
