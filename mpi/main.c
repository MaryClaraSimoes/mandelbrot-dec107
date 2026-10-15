#include "mandelbrot.h"
#include "mandelbrot_compute.h"
#include "io_utils.h"
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *strategy_name(int strategy) {
    return (strategy == MANDELBROT_STRATEGY_CYCLIC) ? "cyclic" : "block";
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank = 0;
    int size = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    MandelbrotParams params;
    mandelbrot_params_init_default(&params);

    int parse_rc = 0;
    if (rank == 0) {
        parse_rc = mandelbrot_params_parse_args(argc, argv, &params);
        if (parse_rc == -1) {
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }

    /* Propaga status do parsing para que todos os ranks finalizem se -h/--help foi solicitado */
    MPI_Bcast(&parse_rc, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (parse_rc == 1) {
        MPI_Finalize();
        return 0;
    }

    /* Transmissão dos parâmetros validados do rank 0 para os demais processos */
    MPI_Bcast(&params.width, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&params.height, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&params.max_iter, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&params.re_min, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Bcast(&params.re_max, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Bcast(&params.im_min, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Bcast(&params.im_max, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Bcast(&params.strategy, 1, MPI_INT, 0, MPI_COMM_WORLD);

    const char *strat = strategy_name(params.strategy);

    ImageBuffer *img = NULL;
    if (rank == 0) {
        img = create_image_buffer(params.width, params.height);
        if (img == NULL) {
            fprintf(stderr, "Erro: Falha na alocacao do buffer da imagem no rank 0.\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        printf("====================================================\n");
        printf(" Gerador do Conjunto de Mandelbrot (MPI - %s)\n",
               (params.strategy == MANDELBROT_STRATEGY_CYCLIC) ? "Ciclico" : "Blocos");
        printf("====================================================\n");
        printf("Configuracoes:\n");
        printf("  - Dimensoes: %d x %d pixels\n", params.width, params.height);
        printf("  - Memoria da Matriz: %.2f MB\n", (double)(params.width * params.height * sizeof(int32_t)) / (1024.0 * 1024.0));
        printf("  - Dominio Real (Re): [%.9f, %.9f]\n", params.re_min, params.re_max);
        printf("  - Dominio Imaginario (Im): [%.9f, %.9f]\n", params.im_min, params.im_max);
        printf("  - Maximo de Iteracoes: %d\n", params.max_iter);
        printf("  - Numero de Processos: %d\n", size);
        printf("  - Estrategia: %s\n", strat);

        /* Teste de sanidade do mapeamento de coordenadas nos vértices */
        double cr_min, ci_min, cr_max, ci_max;
        pixel_to_complex(0, 0, &params, &cr_min, &ci_min);
        pixel_to_complex(params.width - 1, params.height - 1, &params, &cr_max, &ci_max);
        printf("  - Mapeamento Vertice (0,0): (%.9f, %.9f)\n", cr_min, ci_min);
        printf("  - Mapeamento Vertice (%d,%d): (%.9f, %.9f)\n", params.width - 1, params.height - 1, cr_max, ci_max);
        printf("====================================================\n\n");
        printf("Iniciando computacao...\n");
        fflush(stdout);
    }

    LoadBalanceStats balance;
    memset(&balance, 0, sizeof(LoadBalanceStats));

    /* Medição estrita do tempo total de computação paralela (inclui cálculo e comunicação) */
    MPI_Barrier(MPI_COMM_WORLD);
    double t_total_start = MPI_Wtime();

    compute_mandelbrot_mpi(img, &params, &balance);

    MPI_Barrier(MPI_COMM_WORLD);
    double t_total_end = MPI_Wtime();
    double t_total = t_total_end - t_total_start;

    if (rank == 0) {
        char bin_path[64];
        char pgm_path[64];
        char ppm_path[64];
        snprintf(bin_path, sizeof(bin_path), "mandelbrot_mpi_%s.bin", strat);
        snprintf(pgm_path, sizeof(pgm_path), "mandelbrot_mpi_%s.pgm", strat);
        snprintf(ppm_path, sizeof(ppm_path), "mandelbrot_mpi_%s.ppm", strat);

        printf("\nExportando resultados...\n");

        if (export_binary(img, bin_path) != 0) {
            fprintf(stderr, "Aviso: falha ao exportar matriz binaria.\n");
        }

        if (export_pgm(img, pgm_path, params.max_iter) != 0) {
            fprintf(stderr, "Aviso: falha ao exportar imagem PGM.\n");
        }

        if (export_ppm(img, ppm_path, params.max_iter) != 0) {
            fprintf(stderr, "Aviso: falha ao exportar imagem PPM.\n");
        }

        printf("Exportacao concluida.\n\n");

        /* Saída de métricas em formato chave=valor parseável */
        printf("versao=mpi\n");
        printf("estrategia=%s\n", strat);
        printf("resolucao=%dx%d\n", params.width, params.height);
        printf("max_iter=%d\n", params.max_iter);
        printf("processos=%d\n", size);
        printf("tempo_total_s=%.6f\n", t_total);
        printf("t_min_s=%.6f\n", balance.t_min);
        printf("t_max_s=%.6f\n", balance.t_max);
        printf("t_mean_s=%.6f\n", balance.t_mean);
        printf("f_lb=%.6f\n", balance.factor);

        free_image_buffer(img);
    }

    MPI_Finalize();
    return 0;
}
