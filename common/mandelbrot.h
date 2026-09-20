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

/* Caso de desbalanceamento acentuado (enunciado, seção 5.3): vale dos cavalos-marinhos. */
#define SEAHORSE_RE_CENTER  -0.743643887
#define SEAHORSE_IM_CENTER   0.131825904
#define SEAHORSE_RE_WIDTH     3.0e-3
#define SEAHORSE_MAX_ITER     5000

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

/**
 * @brief Parâmetros de uma execução do benchmark (resolução, domínio e MAX_ITER).
 *
 * Os macros WIDTH, HEIGHT, MAX_ITER, RE_MIN/RE_MAX e IM_MIN/IM_MAX permanecem
 * como valores padrão do input oficial (seção 5.2). Esta estrutura permite
 * que o mapeamento, o kernel e a coloração usem um conjunto de valores por
 * execução, em vez de ler as macros globais.
 */
typedef struct {
    int width;
    int height;
    int max_iter;
    double re_min;
    double re_max;
    double im_min;
    double im_max;
} MandelbrotParams;

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
 * @brief Preenche params com os valores padrão do input oficial (seção 5.2).
 *
 * @param params Ponteiro para a estrutura a ser inicializada. Não faz nada se for NULL.
 */
void mandelbrot_params_init_default(MandelbrotParams *params);

/**
 * @brief Interpreta argumentos de linha de comando sobre params já inicializado.
 *
 * Flags reconhecidas: --width, --height, --max-iter, --re-min, --re-max,
 * --im-min, --im-max, --preset {full|seahorse}, --help / -h. Valores omitidos
 * preservam o conteúdo prévio de params (em geral, os defaults da seção 5.2).
 * Flags posteriores sobrescrevem as anteriores (ex.: --preset seahorse --width 256).
 *
 * @return  0 em sucesso; 1 se --help foi pedido; -1 em erro de sintaxe/validação.
 */
int mandelbrot_params_parse_args(int argc, char **argv, MandelbrotParams *params);

/**
 * @brief Realiza o mapeamento linear das coordenadas de tela (pixels) para o plano complexo.
 *
 * Fórmulas:
 *   cr = re_min + (px / (width - 1)) * (re_max - re_min)
 *   ci = im_min + (py / (height - 1)) * (im_max - im_min)
 *
 * @param px     Coordenada X na imagem (coluna, 0 <= px < width).
 * @param py     Coordenada Y na imagem (linha, 0 <= py < height).
 * @param params Resolução e domínio do plano complexo (não pode ser NULL).
 * @param cr     Ponteiro para armazenar a parte real correspondente.
 * @param ci     Ponteiro para armazenar a parte imaginária correspondente.
 */
void pixel_to_complex(int px, int py, const MandelbrotParams *params, double *cr, double *ci);

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
 * até que |Z|² > 4 (escape) ou até atingir params->max_iter iterações.
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
 * O resultado (número de iterações até o escape, ou params->max_iter se o
 * ponto nunca escapar) é armazenado em img->data, percorrido em ordem
 * row-major (linha por linha, py externo e px interno).
 *
 * @param params Resolução, domínio e teto de iterações desta execução.
 *               Função não faz nada se params for NULL.
 */
void compute_mandelbrot(ImageBuffer *img, const MandelbrotParams *params);

#endif /* MANDELBROT_H */
