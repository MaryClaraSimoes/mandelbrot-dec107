#include "mandelbrot.h"
#include "io_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _OPENMP
#include <omp.h>
#endif

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

    int num_threads = 1;
#ifdef _OPENMP
    num_threads = omp_get_max_threads();
#endif

    const char *sched_env = getenv("OMP_SCHEDULE");
    if (sched_env == NULL || strlen(sched_env) == 0) {
        sched_env = "default";
    }

    /* 2. Medicao isolada do tempo de geracao (computacao pura) */
#ifdef _OPENMP
    double start_gen = omp_get_wtime();
#else
    double start_gen = get_wtime();
#endif

    compute_mandelbrot(img);

#ifdef _OPENMP
    double end_gen = omp_get_wtime();
#else
    double end_gen = get_wtime();
#endif
    double tempo_geracao_s = end_gen - start_gen;

    /* 3. Medicao isolada do tempo de escrita em disco (I/O) */
#ifdef _OPENMP
    double start_io = omp_get_wtime();
#else
    double start_io = get_wtime();
#endif

    if (export_binary(img, "mandelbrot_omp.bin") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar matriz binaria.\n");
    }
    if (export_pgm(img, "mandelbrot_omp.pgm") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PGM.\n");
    }
    if (export_ppm(img, "mandelbrot_omp.ppm") != 0) {
        fprintf(stderr, "Aviso: falha ao exportar imagem PPM.\n");
    }

#ifdef _OPENMP
    double end_io = omp_get_wtime();
#else
    double end_io = get_wtime();
#endif
    double tempo_io_s = end_io - start_io;
    double tempo_total_s = tempo_geracao_s + tempo_io_s;

    /* 4. Exibicao formatada e parseavel (chave=valor, conforme Secao 9) */
    printf("versao=openmp\n");
    printf("cenario=%s\n", cenario);
    printf("resolucao=%dx%d\n", img->width, img->height);
    printf("max_iter=%d\n", img->max_iter);
    printf("threads=%d\n", num_threads);
    printf("schedule=%s\n", sched_env);
    printf("tempo_geracao_s=%.6f\n", tempo_geracao_s);
    printf("tempo_io_s=%.6f\n", tempo_io_s);
    printf("tempo_total_s=%.6f\n", tempo_total_s);

    /* 5. Desalocacao de recursos */
    free_image_buffer(img);

    return EXIT_SUCCESS;
}
