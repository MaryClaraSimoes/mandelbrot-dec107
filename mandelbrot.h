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
 * @brief Calcula o Conjunto de Mandelbrot para todos os pixels da imagem.
 *
 * @param img Buffer de imagem já alocado (data, width, height inicializados).
 *            Função não faz nada se img ou img->data forem NULL.
 *
 * Para cada pixel (px, py), obtém o número complexo c = cr + ci*I
 * correspondente via discretização linear do plano complexo (ver
 * pixel_to_complex), e itera a recorrência:
 *
 *   Z0 = 0
 *   Z{n+1} = Z{n}² + c
 *
 * até que |Z|² > 4 (escape) ou até atingir MAX_ITER iterações.
 *
 * Dedução da recorrência em termos de partes real/imaginária
 * (Z{n}² == (zr + ziI)², c == (cr + ciI)):
 *
 *   (zr + ziI)² = zr² + 2(zr·zi)I + zi²I²   {I² = -1}
 *              => (zr² - zi²) + 2(zr·zi)I
 *
 *   Portanto:
 *     zr{n+1} = zr² - zi² + cr
 *     zi{n+1} = 2(zr·zi) + ci
 *
 * O resultado (número de iterações até o escape, ou MAX_ITER se o ponto
 * nunca escapar) é armazenado em img->data, percorrido em ordem row-major
 * (linha por linha, py externo e px interno).
 */
void compute_mandelbrot(ImageBuffer *img);

#endif /* MANDELBROT_H */
