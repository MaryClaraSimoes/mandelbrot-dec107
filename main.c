#include "mandelbrot.h"
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    printf("====================================================\n");
    printf(" Gerador do Conjunto de Mandelbrot (Infraestrutura) \n");
    printf("====================================================\n");
    printf("Configuracoes:\n");
    printf("  - Dimensoes: %d x %d pixels\n", WIDTH, HEIGHT);
    printf("  - Memoria da Matriz: %.2f MB\n", (double)(WIDTH * HEIGHT * sizeof(int32_t)) / (1024.0 * 1024.0));
    printf("  - Dominio Real (Re): [%.2f, %.2f]\n", RE_MIN, RE_MAX);
    printf("  - Dominio Imaginario (Im): [%.2f, %.2f]\n", IM_MIN, IM_MAX);
    printf("  - Maximo de Iteracoes: %d\n", MAX_ITER);

    /* Teste de sanidade do mapeamento de coordenadas nos vertices */
    double cr_min, ci_min, cr_max, ci_max;
    pixel_to_complex(0, 0, WIDTH, HEIGHT, &cr_min, &ci_min);
    pixel_to_complex(WIDTH - 1, HEIGHT - 1, WIDTH, HEIGHT, &cr_max, &ci_max);
    printf("  - Mapeamento Vertice (0,0): (%.2f, %.2f)\n", cr_min, ci_min);
    printf("  - Mapeamento Vertice (%d,%d): (%.2f, %.2f)\n", WIDTH - 1, HEIGHT - 1, cr_max, ci_max);
    printf("====================================================\n\n");

    /* 1. Alocacao da estrutura e do buffer de imagem */
    ImageBuffer *img = create_image_buffer(WIDTH, HEIGHT);
    if (img == NULL) {
        fprintf(stderr, "Erro: Falha na alocacao do buffer da imagem.\n");
        return EXIT_FAILURE;
    }

    /* 2. Medicao isolada do tempo de calculo */
    printf("Iniciando computacao...\n");
    double start_time = get_wtime();

    compute_mandelbrot(img);

    double end_time = get_wtime();
    double elapsed_time = end_time - start_time;

    /* 3. Exibicao do tempo decorrido com 4 casas decimais */
    printf("Tempo de calculo: %.4f segundos\n", elapsed_time);

    /* 4. Desalocacao de recursos */
    free_image_buffer(img);

    return EXIT_SUCCESS;
}
