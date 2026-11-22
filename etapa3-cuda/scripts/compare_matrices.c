#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

/* Garante que int possui 32 bits */
typedef int compare_int_check[(sizeof(int) == 4) ? 1 : -1];

static int *read_matrix_file(const char *path, size_t *out_count) {
    FILE *fp = fopen(path, "rb");
    if (fp == NULL) {
        perror("Erro ao abrir arquivo de matriz");
        fprintf(stderr, "Caminho: %s\n", path);
        return NULL;
    }

    if (fseek(fp, 0, SEEK_END) != 0) {
        perror("Erro em fseek");
        fclose(fp);
        return NULL;
    }

    long file_bytes = ftell(fp);
    if (file_bytes <= 0 || (file_bytes % (long)sizeof(int)) != 0) {
        fprintf(stderr, "Erro: tamanho de arquivo invalido em '%s' (%ld bytes).\n",
                path, file_bytes);
        fclose(fp);
        return NULL;
    }
    rewind(fp);

    size_t count = (size_t)file_bytes / sizeof(int);
    int *buf = (int *)malloc(count * sizeof(int));
    if (buf == NULL) {
        perror("Erro ao alocar memoria para matriz");
        fclose(fp);
        return NULL;
    }

    size_t nread = fread(buf, sizeof(int), count, fp);
    fclose(fp);

    if (nread != count) {
        fprintf(stderr, "Erro: leitura incompleta de '%s' (%zu de %zu elementos).\n",
                path, nread, count);
        free(buf);
        return NULL;
    }

    *out_count = count;
    return buf;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "Uso: %s <matriz_referencia.bin> <matriz_teste.bin>\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char *ref_path  = argv[1];
    const char *test_path = argv[2];

    size_t ref_count  = 0;
    size_t test_count = 0;

    int *ref_mat = read_matrix_file(ref_path, &ref_count);
    if (ref_mat == NULL) {
        return EXIT_FAILURE;
    }

    int *test_mat = read_matrix_file(test_path, &test_count);
    if (test_mat == NULL) {
        free(ref_mat);
        return EXIT_FAILURE;
    }

    if (ref_count != test_count) {
        fprintf(stderr,
                "Erro: matrizes possuem tamanhos diferentes (%zu vs %zu pixels).\n"
                "Veredito: FAIL\n",
                ref_count, test_count);
        free(ref_mat);
        free(test_mat);
        return EXIT_FAILURE;
    }

    size_t diff_pixels = 0;
    int max_diff = 0;

    for (size_t i = 0; i < ref_count; i++) {
        int a = ref_mat[i];
        int b = test_mat[i];
        if (a != b) {
            diff_pixels++;
            int d = (a > b) ? (a - b) : (b - a);
            if (d > max_diff) {
                max_diff = d;
            }
        }
    }

    free(ref_mat);
    free(test_mat);

    double frac_diff = (double)diff_pixels / (double)ref_count;
    double pct_diff  = frac_diff * 100.0;

    /* Criterio da Secao 5.5:
     * - Igualdade exata (diff_pixels == 0), OU
     * - Fracao de divergentes <= 0.01% (pct_diff <= 0.01) E max_diff <= 1
     */
    int pass = 0;
    if (diff_pixels == 0) {
        pass = 1;
    } else if (frac_diff <= 0.0001 && max_diff <= 1) {
        pass = 1;
    }

    printf("=== Relatorio de Validacao de Matrizes (Secao 5.5) ===\n");
    printf("Arquivo referencia : %s\n", ref_path);
    printf("Arquivo teste      : %s\n", test_path);
    printf("Total de pixels    : %zu\n", ref_count);
    printf("Pixels divergentes : %zu\n", diff_pixels);
    printf("Percentual diverg. : %.6f%% (limite: 0.010000%%)\n", pct_diff);
    printf("Maior diferenca    : %d iteracao(oes) (limite: 1)\n", max_diff);
    printf("Veredito           : %s\n", pass ? "PASS" : "FAIL");

    return pass ? EXIT_SUCCESS : EXIT_FAILURE;
}
