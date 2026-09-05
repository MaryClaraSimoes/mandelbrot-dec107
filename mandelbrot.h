#ifndef MANDELBROT_H
#define MANDELBROT_H

#include <stdint.h>
#include <stddef.h>

/* ========================================================================== */
/* Constantes Globais de Configuração e Domínio do Plano Complexo             */
/* ========================================================================== */
#define WIDTH      4096
#define HEIGHT     4096
#define MAX_ITER   1000

#define RE_MIN    -2.0
#define RE_MAX     1.0
#define IM_MIN    -1.5
#define IM_MAX     1.5

/* ========================================================================== */
/* Estrutura de Armazenamento da Imagem                                       */
/* ========================================================================== */
/**
 * @brief Estrutura que encapsula as dimensões e o buffer contínuo de contagens.
 * 
 * O buffer `data` armazena a matriz em ordem Row-Major (linha por linha),
 * garantindo contiguidade espacial e otimização de localidade de cache.
 */
typedef struct {
    int width;
    int height;
    int32_t *data;
} ImageBuffer;

/* ========================================================================== */
/* Protótipos das Funções do Módulo                                           */
/* ========================================================================== */

/**
 * @brief Aloca dinamicamente a estrutura ImageBuffer e seu array contínuo de dados.
 * 
 * @param width  Largura da imagem em pixels.
 * @param height Altura da imagem em pixels.
 * @return ImageBuffer* Ponteiro para o buffer alocado ou NULL em caso de erro.
 */
ImageBuffer* create_image_buffer(int width, int height);

/**
 * @brief Libera a memória alocada para o buffer de dados e para a estrutura ImageBuffer.
 * 
 * @param img Ponteiro para a estrutura a ser desalocada.
 */
void free_image_buffer(ImageBuffer *img);

/**
 * @brief Realiza o mapeamento linear das coordenadas de tela (pixels) para o plano complexo.
 * 
 * @param px     Coordenada X na imagem (coluna, 0 <= px < width).
 * @param py     Coordenada Y na imagem (linha, 0 <= py < height).
 * @param width  Largura total da imagem.
 * @param height Altura total da imagem.
 * @param cr     Ponteiro para armazenar a parte real correspondente.
 * @param ci     Ponteiro para armazenar a parte imaginária correspondente.
 */
void pixel_to_complex(int px, int py, int width, int height, double *cr, double *ci);

/**
 * @brief Obtém o tempo atual com precisão de nanossegundos via CLOCK_MONOTONIC.
 * 
 * @return double Tempo em segundos.
 */
double get_wtime(void);

/**
 * @brief Função responsável pelo cálculo do Conjunto de Mandelbrot.
 *        Neste módulo de infraestrutura, atua como stub/mock preenchendo a matriz.
 * 
 * @param img Ponteiro para o ImageBuffer a ser processado.
 */
void compute_mandelbrot(ImageBuffer *img);

#endif /* MANDELBROT_H */
