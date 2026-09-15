#include "mandelbrot.h"
#include "io_utils.h"
#include <stdio.h>
#include <stdlib.h>
#ifdef _OPENMP
#include <omp.h>
#endif

int main(void) {
    printf("====================================================\n");
    printf(" Gerador do Conjunto de Mandelbrot (OpenMP) \n");
    printf("====================================================\n");
    printf("Configuracoes:\n");
    printf("  - Dimensoes: %d x %d pixels\n", WIDTH, HEIGHT);
    printf("  - Memoria da Matriz: %.2f MB\n", (double)(WIDTH * HEIGHT * sizeof(int32_t)) / (1024.0 * 1024.0));
    printf("  - Dominio Real (Re): [%.2f, %.2f]\n", RE_MIN, RE_MAX);
    printf("  - Dominio Imaginario (Im): [%.2f, %.2f]\n", IM_MIN, IM_MAX);
    printf("  - Maximo de Iteracoes: %d\n", MAX_ITER);
#ifdef _OPENMP
    printf("  - Threads OpenMP disponiveis: %d\n", omp_get_max_threads());
#else
    printf("  - AVISO: binario compilado sem suporte a OpenMP (-fopenmp ausente).\n");
#endif

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

    #ifdef _OPENMP
        double start_time = omp_get_wtime();

        compute_mandelbrot(img);

        double end_time = omp_get_wtime();
        double elapsed_time = end_time - start_time;
    #else 
        double start_time = get_wtime();

        compute_mandelbrot(img);

        double end_time = get_wtime();
        double elapsed_time = end_time - start_time;
    #endif
    /* 3. Exibicao do tempo decorrido com 4 casas decimais */
    printf("Tempo de calculo: %.4f segundos\n", elapsed_time);

    /* 4. Exportação dos dados (fora da medição de tempo) */
    printf("\nExportando resultados...\n");

    if (export_binary(img, "mandelbrot_omp.bin") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar matriz binaria.\n");
    }

    if (export_pgm(img, "mandelbrot_omp.pgm") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PGM.\n");
    }

    if (export_ppm(img, "mandelbrot_omp.ppm") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PPM.\n");
    }

    printf("\nExportacao concluida.\n");

    /* 5. Desalocacao de recursos */
    free_image_buffer(img);

    return EXIT_SUCCESS;
}
