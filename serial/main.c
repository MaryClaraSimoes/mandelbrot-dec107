#include "mandelbrot.h"
#include "io_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    const char *cenario = "padrao";
    int width = DEFAULT_WIDTH;
    int height = DEFAULT_HEIGHT;

    /* Leitura simples de argumentos posicionais ou variaveis de ambiente (sem argparse) */
    if (argc > 1 && strlen(argv[1]) > 0) {
        cenario = argv[1];
    } else if (getenv("MANDELBROT_SCENARIO") != NULL) {
        cenario = getenv("MANDELBROT_SCENARIO");
    }

    if (argc > 2) {
        int sz = atoi(argv[2]);
        if (sz > 0) {
            width = sz;
            height = sz;
        }
    } else if (getenv("MANDELBROT_SIZE") != NULL) {
        int sz = atoi(getenv("MANDELBROT_SIZE"));
        if (sz > 0) {
            width = sz;
            height = sz;
        }
    }

    /* 1. Alocacao da estrutura e do buffer de imagem */
    ImageBuffer *img = create_image_buffer(width, height);
    if (img == NULL) {
        fprintf(stderr, "Erro: Falha na alocacao do buffer da imagem.\n");
        return EXIT_FAILURE;
    }

    configure_scenario(img, cenario);

    /* 2. Medicao isolada do tempo de geracao (computacao pura) */
    double start_gen = get_wtime();
    compute_mandelbrot(img);
    double end_gen = get_wtime();
    double tempo_geracao_s = end_gen - start_gen;

    /* 3. Medicao isolada do tempo de escrita em disco (I/O) */
    double start_io = get_wtime();
    if (export_binary(img, "mandelbrot_serial.bin") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar matriz binaria.\n");
    }
    if (export_pgm(img, "mandelbrot_serial.pgm") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PGM.\n");
    }
    if (export_ppm(img, "mandelbrot_serial.ppm") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PPM.\n");
    }
    double end_io = get_wtime();
    double tempo_io_s = end_io - start_io;
    double tempo_total_s = tempo_geracao_s + tempo_io_s;

    /* 4. Exibicao formatada e parseavel (chave=valor, conforme Secao 9) */
    printf("versao=serial\n");
    printf("cenario=%s\n", cenario);
    printf("resolucao=%dx%d\n", img->width, img->height);
    printf("max_iter=%d\n", img->max_iter);
    printf("tempo_geracao_s=%.6f\n", tempo_geracao_s);
    printf("tempo_io_s=%.6f\n", tempo_io_s);
    printf("tempo_total_s=%.6f\n", tempo_total_s);

    /* 5. Desalocacao de recursos */
    free_image_buffer(img);

    return EXIT_SUCCESS;
}
