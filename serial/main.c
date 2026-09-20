#include "mandelbrot.h"
#include "io_utils.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    MandelbrotParams params;
    int parse_rc;

    mandelbrot_params_init_default(&params);
    parse_rc = mandelbrot_params_parse_args(argc, argv, &params);
    if (parse_rc == 1) {
        return EXIT_SUCCESS;
    }
    if (parse_rc != 0) {
        return EXIT_FAILURE;
    }

    printf("====================================================\n");
    printf(" Gerador do Conjunto de Mandelbrot (Infraestrutura) \n");
    printf("====================================================\n");
    printf("Configuracoes:\n");
    printf("  - Dimensoes: %d x %d pixels\n", params.width, params.height);
    printf("  - Memoria da Matriz: %.2f MB\n", (double)(params.width * params.height * sizeof(int32_t)) / (1024.0 * 1024.0));
    printf("  - Dominio Real (Re): [%.9f, %.9f]\n", params.re_min, params.re_max);
    printf("  - Dominio Imaginario (Im): [%.9f, %.9f]\n", params.im_min, params.im_max);
    printf("  - Maximo de Iteracoes: %d\n", params.max_iter);

    /* Teste de sanidade do mapeamento de coordenadas nos vertices */
    double cr_min, ci_min, cr_max, ci_max;
    pixel_to_complex(0, 0, &params, &cr_min, &ci_min);
    pixel_to_complex(params.width - 1, params.height - 1, &params, &cr_max, &ci_max);
    printf("  - Mapeamento Vertice (0,0): (%.9f, %.9f)\n", cr_min, ci_min);
    printf("  - Mapeamento Vertice (%d,%d): (%.9f, %.9f)\n", params.width - 1, params.height - 1, cr_max, ci_max);
    printf("====================================================\n\n");

    /* 1. Alocacao da estrutura e do buffer de imagem */
    ImageBuffer *img = create_image_buffer(params.width, params.height);
    if (img == NULL) {
        fprintf(stderr, "Erro: Falha na alocacao do buffer da imagem.\n");
        return EXIT_FAILURE;
    }

    /* 2. Medicao isolada do tempo de calculo */
    printf("Iniciando computacao...\n");
    double start_time = get_wtime();

    compute_mandelbrot(img, &params, NULL);

    double end_time = get_wtime();
    double elapsed_time = end_time - start_time;

    /* 3. Exibicao do tempo decorrido com 4 casas decimais */
    printf("Tempo de calculo: %.4f segundos\n", elapsed_time);

    /* 4. Exportação dos dados (fora da medição de tempo) */
    printf("\nExportando resultados...\n");

    if (export_binary(img, "mandelbrot_serial.bin") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar matriz binaria.\n");
    }

    if (export_pgm(img, "mandelbrot_serial.pgm", params.max_iter) != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PGM.\n");
    }

    if (export_ppm(img, "mandelbrot_serial.ppm", params.max_iter) != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PPM.\n");
    }

    printf("\nExportacao concluida.\n");

    /* 5. Desalocacao de recursos */
    free_image_buffer(img);

    return EXIT_SUCCESS;
}
