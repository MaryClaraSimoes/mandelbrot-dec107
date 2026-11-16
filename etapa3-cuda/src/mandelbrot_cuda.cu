#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 199309L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <cuda_runtime.h>
#include "common.h"

/* Macro de verificacao de erros em chamadas da API CUDA Runtime */
#define CUDA_CHECK(call)                                                        \
    do {                                                                        \
        cudaError_t err__ = (call);                                             \
        if (err__ != cudaSuccess) {                                             \
            fprintf(stderr, "Erro CUDA em %s:%d (%s): %s\n",                    \
                    __FILE__, __LINE__, #call, cudaGetErrorString(err__));      \
            exit(EXIT_FAILURE);                                                 \
        }                                                                       \
    } while (0)

/* ========================================================================== */
/* Kernel CUDA Baseline: 1 thread = 1 pixel (aritmética estrita em double)    */
/* Usa intrínsecos IEEE-754 (__dadd_rn, __dsub_rn, __dmul_rn, __ddiv_rn)      */
/* para impedir fusão automática de FMA (DFMA) pelo ptxas e preservar a       */
/* mesma ordem de arredondamento da versão serial compilada com gcc -O3.      */
/* ========================================================================== */
__global__ void mandelbrot_kernel(int *out_matrix,
                                  int width,
                                  int height,
                                  double xmin,
                                  double xmax,
                                  double ymin,
                                  double ymax,
                                  int max_iter) {
    int px = blockIdx.x * blockDim.x + threadIdx.x;
    int py = blockIdx.y * blockDim.y + threadIdx.y;

    if (px >= width || py >= height) {
        return;
    }

    int idx = py * width + px;

    double denom_x = (width > 1)  ? (double)(width - 1)  : 1.0;
    double denom_y = (height > 1) ? (double)(height - 1) : 1.0;

    double range_x = __dsub_rn(xmax, xmin);
    double range_y = __dsub_rn(ymax, ymin);

    double cr = __dadd_rn(xmin, __dmul_rn(__ddiv_rn((double)px, denom_x), range_x));
    double ci = __dadd_rn(ymin, __dmul_rn(__ddiv_rn((double)py, denom_y), range_y));

    double zr = 0.0;
    double zi = 0.0;
    int iter  = 0;

    while (iter < max_iter && __dadd_rn(__dmul_rn(zr, zr), __dmul_rn(zi, zi)) <= 4.0) {
        double zr2     = __dmul_rn(zr, zr);
        double zi2     = __dmul_rn(zi, zi);
        double next_zr = __dadd_rn(__dsub_rn(zr2, zi2), cr);
        double next_zi = __dadd_rn(__dmul_rn(2.0, __dmul_rn(zr, zi)), ci);
        zr = next_zr;
        zi = next_zi;
        iter++;
    }

    out_matrix[idx] = iter;
}

static double get_monotonic_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

int main(int argc, char **argv) {
    MandelbrotParams params;
    init_default_params(&params, "output/cuda_base.bin", "output/cuda_base.pgm");

    int rc = parse_args(argc, argv, &params);
    if (rc == 1) {
        return EXIT_SUCCESS;
    }
    if (rc != 0) {
        return EXIT_FAILURE;
    }

    const int W = params.width;
    const int H = params.height;
    const size_t total_pixels = (size_t)W * (size_t)H;
    const size_t bytes        = total_pixels * sizeof(int);

    int *h_matrix = (int *)malloc(bytes);
    if (h_matrix == NULL) {
        perror("Erro ao alocar matriz no host");
        return EXIT_FAILURE;
    }

    printf("=== Mandelbrot CUDA Baseline (1 thread = 1 pixel) ===\n");
    printf("Resolucao : %d x %d (%zu pixels)\n", W, H, total_pixels);
    printf("Regiao Re : [%.10f, %.10f]\n", params.xmin, params.xmax);
    printf("Regiao Im : [%.10f, %.10f]\n", params.ymin, params.ymax);
    printf("MAX_ITER  : %d\n", params.max_iter);

    /* Passo 1: Alocacao de memoria no device (cudaMalloc) */
    int *d_matrix = NULL;
    CUDA_CHECK(cudaMalloc((void **)&d_matrix, bytes));

    /* Passo 2: Transferencia H->D (nao necessaria para matriz de entrada,
     * pois (cr, ci) e calculado diretamente no kernel a partir dos escalares) */

    /* Configuracao inicial de execucao: bloco 16x16 e grade 2D */
    dim3 block(16, 16);
    dim3 grid((W + 15) / 16, (H + 15) / 16);

    printf("Grid/Block: grid(%u, %u, %u), block(%u, %u, %u)\n",
           grid.x, grid.y, grid.z, block.x, block.y, block.z);

    /* Sincroniza antes de iniciar a medicao do kernel */
    CUDA_CHECK(cudaDeviceSynchronize());
    double t_kernel_start = get_monotonic_sec();

    /* Passo 3: Lancamento do kernel */
    mandelbrot_kernel<<<grid, block>>>(d_matrix,
                                       W, H,
                                       params.xmin, params.xmax,
                                       params.ymin, params.ymax,
                                       params.max_iter);

    /* Verifica erros de lancamento e sincroniza para medir o tempo do kernel */
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    double t_kernel_end = get_monotonic_sec();
    double kernel_sec   = t_kernel_end - t_kernel_start;

    /* Passo 4: Copia do resultado D->H (cudaMemcpyDeviceToHost) medida separadamente */
    double t_d2h_start = get_monotonic_sec();
    CUDA_CHECK(cudaMemcpy(h_matrix, d_matrix, bytes, cudaMemcpyDeviceToHost));
    double t_d2h_end = get_monotonic_sec();
    double d2h_sec   = t_d2h_end - t_d2h_start;

    /* Passo 5: Liberacao de memoria no device (cudaFree) */
    CUDA_CHECK(cudaFree(d_matrix));

    double total_gpu_sec = kernel_sec + d2h_sec;
    printf("Tempo do kernel          : %.6f s (%.3f ms)\n", kernel_sec, kernel_sec * 1000.0);
    printf("Tempo de copia D->H      : %.6f s (%.3f ms)\n", d2h_sec, d2h_sec * 1000.0);
    printf("Tempo total (kernel+D2H) : %.6f s (%.3f ms)\n", total_gpu_sec, total_gpu_sec * 1000.0);

    /* Escrita dos arquivos de saida (fora da medicao de tempo) */
    if (params.out_bin != NULL) {
        if (write_matrix_bin(params.out_bin, h_matrix, W, H) != 0) {
            free(h_matrix);
            return EXIT_FAILURE;
        }
        printf("Matriz binaria salva em  : %s\n", params.out_bin);
    }

    if (params.out_pgm != NULL) {
        if (write_pgm(params.out_pgm, h_matrix, W, H, params.max_iter) != 0) {
            free(h_matrix);
            return EXIT_FAILURE;
        }
        printf("Imagem PGM salva em      : %s\n", params.out_pgm);
    }

    free(h_matrix);
    return EXIT_SUCCESS;
}
