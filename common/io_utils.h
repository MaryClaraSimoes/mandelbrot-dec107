#ifndef IO_UTILS_H
#define IO_UTILS_H

#include "mandelbrot.h"

/* ========================================================================== */
/* Módulo de Entrada/Saída (I/O) para o Conjunto de Mandelbrot                */
/* ========================================================================== */

/**
 * @brief Exporta a matriz de iterações como imagem PGM (Portable Graymap).
 *
 * Gera um arquivo no formato Netpbm P5 (binário, escala de cinza) com
 * intensidades linearmente mapeadas do intervalo [0, MAX_ITER] para [0, 255].
 * Pixels com valor MAX_ITER (interior do conjunto) são mapeados para preto (0).
 *
 * @param img      Ponteiro para o ImageBuffer com os dados de iteração.
 * @param filename Caminho do arquivo de saída (e.g., "mandelbrot.pgm").
 * @return 0 em caso de sucesso, -1 em caso de erro.
 */
int export_pgm(const ImageBuffer *img, const char *filename);

/**
 * @brief Exporta a matriz de iterações como imagem PPM (Portable Pixmap).
 *
 * Gera um arquivo no formato Netpbm P6 (binário, RGB) utilizando uma paleta
 * de cores baseada em mapeamento cíclico HSV para realçar as faixas de
 * iteração. Pixels com valor MAX_ITER são mapeados para preto (0, 0, 0).
 *
 * @param img      Ponteiro para o ImageBuffer com os dados de iteração.
 * @param filename Caminho do arquivo de saída (e.g., "mandelbrot.ppm").
 * @return 0 em caso de sucesso, -1 em caso de erro.
 */
int export_ppm(const ImageBuffer *img, const char *filename);

/**
 * @brief Exporta a matriz de iterações em formato binário bruto.
 *
 * Grava os dados do ImageBuffer como uma sequência contígua de inteiros de
 * 32 bits com sinal (int32_t), em ordem Row-Major (py * width + px), sem
 * cabeçalho. O arquivo resultante tem tamanho exato de
 * width * height * sizeof(int32_t) bytes.
 *
 * Este formato é utilizado como referência canônica para validação de
 * corretude entre diferentes implementações (serial, OpenMP, MPI, CUDA).
 *
 * @param img      Ponteiro para o ImageBuffer com os dados de iteração.
 * @param filename Caminho do arquivo de saída (e.g., "mandelbrot.bin").
 * @return 0 em caso de sucesso, -1 em caso de erro.
 */
int export_binary(const ImageBuffer *img, const char *filename);

/**
 * @brief Carrega uma matriz de iterações de um arquivo binário bruto.
 *
 * Lê uma sequência contígua de int32_t em ordem Row-Major e aloca um
 * ImageBuffer com as dimensões especificadas. O chamador é responsável
 * por liberar o buffer retornado com free_image_buffer().
 *
 * @param filename Caminho do arquivo binário de entrada.
 * @param width    Largura esperada da matriz.
 * @param height   Altura esperada da matriz.
 * @return Ponteiro para ImageBuffer alocado ou NULL em caso de erro.
 */
ImageBuffer* load_binary(const char *filename, int width, int height);

#endif /* IO_UTILS_H */
