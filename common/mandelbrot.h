#ifndef MANDELBROT_H
#define MANDELBROT_H

#include <stdint.h>
#include <stddef.h>

/* ========================================================================== */
/* Constantes Globais Padrão (Input Padrão - Seção 5.2)                       */
/* ========================================================================== */
#define DEFAULT_WIDTH      4096
#define DEFAULT_HEIGHT     4096
#define DEFAULT_MAX_ITER   1000

#define DEFAULT_RE_MIN    -2.0
#define DEFAULT_RE_MAX     1.0
#define DEFAULT_IM_MIN    -1.5
#define DEFAULT_IM_MAX     1.5

/* Compatibilidade com código legado */
#define WIDTH      DEFAULT_WIDTH
#define HEIGHT     DEFAULT_HEIGHT
#define MAX_ITER   DEFAULT_MAX_ITER
#define RE_MIN     DEFAULT_RE_MIN
#define RE_MAX     DEFAULT_RE_MAX
#define IM_MIN     DEFAULT_IM_MIN
#define IM_MAX     DEFAULT_IM_MAX

/* ========================================================================== */
/* Estrutura de Armazenamento da Imagem e Configuração do Cenário             */
/* ========================================================================== */
typedef struct {
    int width;
    int height;
    int max_iter;
    double re_min;
    double re_max;
    double im_min;
    double im_max;
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
 * @brief Configura o cenário de execução no ImageBuffer (Seções 5.2 e 5.3).
 *
 * Suporta:
 *   - "padrao" ou "default": [-2.0, 1.0] x [-1.5, 1.5], max_iter = 1000
 *   - "seahorse": centro (-0.743643887, 0.131825904), largura 0.003, max_iter = 5000
 *
 * @param img           Ponteiro para a estrutura ImageBuffer já alocada.
 * @param scenario_name Nome do cenário ("padrao" ou "seahorse").
 * @return 0 em caso de sucesso, -1 se cenário desconhecido.
 */
int configure_scenario(ImageBuffer *img, const char *scenario_name);

/**
 * @brief Realiza o mapeamento linear das coordenadas de tela (pixels) para o plano complexo.
 *
 * @param px     Coordenada X na imagem (coluna, 0 <= px < width).
 * @param py     Coordenada Y na imagem (linha, 0 <= py < height).
 * @param img    Ponteiro para a estrutura ImageBuffer com os parâmetros de domínio.
 * @param cr     Ponteiro para armazenar a parte real correspondente.
 * @param ci     Ponteiro para armazenar a parte imaginária correspondente.
 */
void pixel_to_complex(int px, int py, const ImageBuffer *img, double *cr, double *ci);

/**
 * @brief Obtém o tempo atual com precisão de nanossegundos via CLOCK_MONOTONIC.
 *
 * @return double Tempo em segundos.
 */
double get_wtime(void);

/**
 * @brief Calcula o Conjunto de Mandelbrot para todos os pixels da imagem.
 *
 * @param img Buffer de imagem já alocado e configurado.
 */
void compute_mandelbrot(ImageBuffer *img);

#endif /* MANDELBROT_H */
