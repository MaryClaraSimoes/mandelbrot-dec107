#include "mandelbrot_compute.h"
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

/**
 * Escolha do tipo de dados MPI para transmissão dos pixels (int32_t):
 * - De acordo com o padrão MPI-3.0 (C99 bindings), MPI_INT32_T corresponde
 *   diretamente ao tipo int32_t de <stdint.h>, garantindo correspondência de
 *   tamanho e representação binária da matriz data.
 * - Caso a biblioteca MPI utilizada não defina MPI_INT32_T (MPI pré-3.0),
 *   utiliza-se MPI_INT como fallback seguro em arquiteturas x86_64 onde
 *   sizeof(int) == sizeof(int32_t) == 4 bytes.
 */
#if defined(MPI_INT32_T)
#define MANDELBROT_MPI_TYPE MPI_INT32_T
#else
#define MANDELBROT_MPI_TYPE MPI_INT
#endif

/**
 * @brief Computa o tempo de escape do Conjunto de Mandelbrot para um ponto (px, py).
 *
 * Lógica aritmética estritamente idêntica à referência serial:
 *   Z0 = 0
 *   Z{n+1} = Z{n}² + c, com c = cr + ci*I
 * Critério de escape: |Z|² > 4.0 ou atingir params->max_iter.
 */
static inline int32_t escape_time(int px, int py, const MandelbrotParams *params) {
    double zr = 0.0, zi = 0.0, cr = 0.0, ci = 0.0;
    int iter = 0;

    pixel_to_complex(px, py, params, &cr, &ci);

    while (iter < params->max_iter && (zr * zr + zi * zi) <= 4.0) {
        double next_zr = (zr * zr) - (zi * zi) + cr;
        double next_zi = 2.0 * (zr * zi) + ci;
        zr = next_zr;
        zi = next_zi;
        iter++;
    }

    return (int32_t)iter;
}

/**
 * @brief Divide o intervalo [0, height) em `size` blocos contíguos de linhas.
 *
 * Caso a divisão não seja exata, os primeiros (height % size) processos
 * recebem exatamente 1 linha adicional, distribuindo o resto uniformemente.
 */
static void compute_range(int height, int size, int rank, int *start, int *count) {
    int base = height / size;
    int rem = height % size;

    if (rank < rem) {
        if (count != NULL) *count = base + 1;
        if (start != NULL) *start = rank * (base + 1);
    } else {
        if (count != NULL) *count = base;
        if (start != NULL) *start = rank * base + rem;
    }
}

/**
 * @brief Número de linhas atribuídas ao rank na distribuição cíclica.
 *
 * Linhas: rank, rank+size, rank+2*size, ... enquanto < height.
 */
static int cyclic_row_count(int height, int size, int rank) {
    if (height <= rank || size <= 0) {
        return 0;
    }
    return ((height - 1 - rank) / size) + 1;
}

/**
 * @brief Agrega tempos locais e preenche LoadBalanceStats no rank 0.
 *
 * Fator λ = t_max / t_mean (mesmo critério da versão OpenMP).
 */
static void reduce_balance_stats(int rank, int size, double t_local, LoadBalanceStats *balance) {
    double t_max = 0.0;
    double t_min = 0.0;
    double t_sum = 0.0;

    MPI_Reduce(&t_local, &t_max, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_local, &t_min, 1, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_local, &t_sum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    if (rank == 0 && balance != NULL) {
        balance->nthreads = size;
        balance->t_min = t_min;
        balance->t_max = t_max;
        balance->t_mean = t_sum / (double)size;
        balance->factor = (balance->t_mean > 0.0) ? (t_max / balance->t_mean) : 1.0;
        printf("BALANCE_MPI ranks=%d t_min=%.6f t_max=%.6f t_mean=%.6f F_LB=%.6f\n",
               size, t_min, t_max, balance->t_mean, balance->factor);
        fflush(stdout);
    }
}

/**
 * @brief Estratégia A: faixas contíguas de linhas + MPI_Gatherv direto na imagem.
 */
static void compute_mpi_block(ImageBuffer *img,
                              const MandelbrotParams *params,
                              LoadBalanceStats *balance,
                              int rank, int size) {
    int start_row = 0;
    int n_rows = 0;
    compute_range(params->height, size, rank, &start_row, &n_rows);

    size_t local_pixels = (size_t)n_rows * (size_t)params->width;
    int32_t *local_data = NULL;
    if (local_pixels > 0) {
        local_data = (int32_t *)malloc(local_pixels * sizeof(int32_t));
        if (local_data == NULL) {
            fprintf(stderr, "[Rank %d] Erro ao alocar buffer local de pixels (%zu pixels).\n",
                    rank, local_pixels);
            MPI_Abort(MPI_COMM_WORLD, 1);
            return;
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double t_start = MPI_Wtime();

    for (int r = 0; r < n_rows; r++) {
        int py = start_row + r;
        for (int px = 0; px < params->width; px++) {
            local_data[(size_t)r * (size_t)params->width + (size_t)px] = escape_time(px, py, params);
        }
    }

    double t_local = MPI_Wtime() - t_start;
    reduce_balance_stats(rank, size, t_local, balance);

    int *recvcounts = NULL;
    int *displs = NULL;
    void *recvbuf = NULL;

    if (rank == 0) {
        recvbuf = img->data;
        recvcounts = (int *)malloc((size_t)size * sizeof(int));
        displs = (int *)malloc((size_t)size * sizeof(int));
        if (recvcounts == NULL || displs == NULL) {
            fprintf(stderr, "[Rank 0] Erro ao alocar vetores de contagem para MPI_Gatherv.\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return;
        }

        for (int p = 0; p < size; p++) {
            int p_start = 0;
            int p_rows = 0;
            compute_range(params->height, size, p, &p_start, &p_rows);
            recvcounts[p] = p_rows * params->width;
            displs[p] = p_start * params->width;
        }
    }

    int sendcount = n_rows * params->width;
    int32_t dummy = 0;
    void *sendbuf = (local_data != NULL) ? (void *)local_data : (void *)&dummy;

    MPI_Gatherv(sendbuf, sendcount, MANDELBROT_MPI_TYPE,
                recvbuf, recvcounts, displs, MANDELBROT_MPI_TYPE,
                0, MPI_COMM_WORLD);

    if (rank == 0) {
        free(recvcounts);
        free(displs);
    }

    if (local_data != NULL) {
        free(local_data);
    }
}

/**
 * @brief Estratégia B: linhas cíclicas (py = rank; py += size) + Gatherv empacotado.
 *
 * Cada rank empacota suas linhas em ordem de índice local. O rank 0 recebe
 * segmentos contíguos via MPI_Gatherv e remonta a imagem global na ordem
 * correta (py = p + k * size).
 */
static void compute_mpi_cyclic(ImageBuffer *img,
                               const MandelbrotParams *params,
                               LoadBalanceStats *balance,
                               int rank, int size) {
    int n_rows = cyclic_row_count(params->height, size, rank);

    size_t local_pixels = (size_t)n_rows * (size_t)params->width;
    int32_t *local_data = NULL;
    if (local_pixels > 0) {
        local_data = (int32_t *)malloc(local_pixels * sizeof(int32_t));
        if (local_data == NULL) {
            fprintf(stderr, "[Rank %d] Erro ao alocar buffer local de pixels (%zu pixels).\n",
                    rank, local_pixels);
            MPI_Abort(MPI_COMM_WORLD, 1);
            return;
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double t_start = MPI_Wtime();

    int r = 0;
    for (int py = rank; py < params->height; py += size, r++) {
        for (int px = 0; px < params->width; px++) {
            local_data[(size_t)r * (size_t)params->width + (size_t)px] = escape_time(px, py, params);
        }
    }

    double t_local = MPI_Wtime() - t_start;
    reduce_balance_stats(rank, size, t_local, balance);

    int *recvcounts = NULL;
    int *displs = NULL;
    int32_t *gather_buf = NULL;
    int total_pixels = params->width * params->height;

    if (rank == 0) {
        recvcounts = (int *)malloc((size_t)size * sizeof(int));
        displs = (int *)malloc((size_t)size * sizeof(int));
        gather_buf = (int32_t *)malloc((size_t)total_pixels * sizeof(int32_t));
        if (recvcounts == NULL || displs == NULL || gather_buf == NULL) {
            fprintf(stderr, "[Rank 0] Erro ao alocar buffers para MPI_Gatherv ciclico.\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
            return;
        }

        int offset = 0;
        for (int p = 0; p < size; p++) {
            int p_rows = cyclic_row_count(params->height, size, p);
            recvcounts[p] = p_rows * params->width;
            displs[p] = offset;
            offset += recvcounts[p];
        }
    }

    int sendcount = n_rows * params->width;
    int32_t dummy = 0;
    void *sendbuf = (local_data != NULL) ? (void *)local_data : (void *)&dummy;

    MPI_Gatherv(sendbuf, sendcount, MANDELBROT_MPI_TYPE,
                gather_buf, recvcounts, displs, MANDELBROT_MPI_TYPE,
                0, MPI_COMM_WORLD);

    if (rank == 0) {
        for (int p = 0; p < size; p++) {
            int p_rows = cyclic_row_count(params->height, size, p);
            for (int k = 0; k < p_rows; k++) {
                int py = p + k * size;
                const int32_t *src = gather_buf + displs[p] + k * params->width;
                int32_t *dst = img->data + (size_t)py * (size_t)params->width;
                memcpy(dst, src, (size_t)params->width * sizeof(int32_t));
            }
        }

        free(recvcounts);
        free(displs);
        free(gather_buf);
    }

    if (local_data != NULL) {
        free(local_data);
    }
}

/**
 * @brief Executa o cálculo paralelo do Mandelbrot e reúne o resultado no rank 0.
 */
void compute_mandelbrot_mpi(ImageBuffer *img,
                            const MandelbrotParams *params,
                            LoadBalanceStats *balance) {
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (params == NULL) {
        return;
    }
    if (rank == 0 && (img == NULL || img->data == NULL)) {
        fprintf(stderr, "[Rank 0] Erro: buffer de imagem nulo fornecido a compute_mandelbrot_mpi.\n");
        MPI_Abort(MPI_COMM_WORLD, 1);
        return;
    }

    if (params->strategy == MANDELBROT_STRATEGY_CYCLIC) {
        compute_mpi_cyclic(img, params, balance, rank, size);
    } else {
        compute_mpi_block(img, params, balance, rank, size);
    }
}
