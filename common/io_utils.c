#include "io_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/* ========================================================================== */
/* Funções Auxiliares Internas                                                 */
/* ========================================================================== */

/**
 * @brief Converte componentes HSV para RGB (intervalo 0–255 cada canal).
 *
 * Utilizada internamente para gerar a paleta de cores do PPM.
 *
 * @param h  Matiz (hue), intervalo [0, 360).
 * @param s  Saturação, intervalo [0, 1].
 * @param v  Valor (brilho), intervalo [0, 1].
 * @param r  Ponteiro para componente vermelho de saída [0, 255].
 * @param g  Ponteiro para componente verde de saída [0, 255].
 * @param b  Ponteiro para componente azul de saída [0, 255].
 */
static void hsv_to_rgb(double h, double s, double v,
                        unsigned char *r, unsigned char *g, unsigned char *b)
{
    double c = v * s;
    double x = c * (1.0 - fabs(fmod(h / 60.0, 2.0) - 1.0));
    double m = v - c;

    double rp = 0.0, gp = 0.0, bp = 0.0;

    if (h < 60.0)       { rp = c; gp = x; bp = 0; }
    else if (h < 120.0) { rp = x; gp = c; bp = 0; }
    else if (h < 180.0) { rp = 0; gp = c; bp = x; }
    else if (h < 240.0) { rp = 0; gp = x; bp = c; }
    else if (h < 300.0) { rp = x; gp = 0; bp = c; }
    else                { rp = c; gp = 0; bp = x; }

    *r = (unsigned char)((rp + m) * 255.0 + 0.5);
    *g = (unsigned char)((gp + m) * 255.0 + 0.5);
    *b = (unsigned char)((bp + m) * 255.0 + 0.5);
}

/* ========================================================================== */
/* Exportação PGM (Escala de Cinza)                                           */
/* ========================================================================== */

int export_pgm(const ImageBuffer *img, const char *filename) {
    if (img == NULL || img->data == NULL || filename == NULL) {
        fprintf(stderr, "Erro: parametros invalidos para export_pgm.\n");
        return -1;
    }

    FILE *fp = fopen(filename, "wb");
    if (fp == NULL) {
        perror("Erro ao abrir arquivo PGM para escrita");
        return -1;
    }

    /* Cabeçalho P5 (PGM binário) */
    fprintf(fp, "P5\n%d %d\n255\n", img->width, img->height);

    /* Alocação do buffer de pixels em escala de cinza */
    size_t total_pixels = (size_t)img->width * (size_t)img->height;
    unsigned char *pixels = (unsigned char *)malloc(total_pixels);
    if (pixels == NULL) {
        perror("Erro ao alocar buffer de pixels PGM");
        fclose(fp);
        return -1;
    }

    /*
     * Mapeamento linear: iterações [0, max_iter) -> luminosidade [0, 255).
     * Pixels no interior do conjunto (iter == max_iter) recebem preto (0).
     */
    int max_iter = (img->max_iter > 0) ? img->max_iter : DEFAULT_MAX_ITER;
    for (size_t i = 0; i < total_pixels; i++) {
        int32_t iter = img->data[i];
        if (iter >= max_iter) {
            pixels[i] = 0;
        } else {
            pixels[i] = (unsigned char)(255.0 * (double)iter / (double)max_iter);
        }
    }

    size_t written = fwrite(pixels, 1, total_pixels, fp);
    free(pixels);
    fclose(fp);

    if (written != total_pixels) {
        fprintf(stderr, "Erro: escrita incompleta no arquivo PGM (%zu de %zu bytes).\n",
                written, total_pixels);
        return -1;
    }

    printf("Imagem PGM exportada: %s (%d x %d)\n", filename, img->width, img->height);
    return 0;
}

/* ========================================================================== */
/* Exportação PPM (Colorido com Paleta HSV)                                   */
/* ========================================================================== */

int export_ppm(const ImageBuffer *img, const char *filename) {
    if (img == NULL || img->data == NULL || filename == NULL) {
        fprintf(stderr, "Erro: parametros invalidos para export_ppm.\n");
        return -1;
    }

    FILE *fp = fopen(filename, "wb");
    if (fp == NULL) {
        perror("Erro ao abrir arquivo PPM para escrita");
        return -1;
    }

    /* Cabeçalho P6 (PPM binário) */
    fprintf(fp, "P6\n%d %d\n255\n", img->width, img->height);

    size_t total_pixels = (size_t)img->width * (size_t)img->height;
    unsigned char *pixels = (unsigned char *)malloc(total_pixels * 3);
    if (pixels == NULL) {
        perror("Erro ao alocar buffer de pixels PPM");
        fclose(fp);
        return -1;
    }

    /*
     * Paleta HSV cíclica: a matiz (hue) varia ciclicamente com o número
     * de iterações, produzindo bandas cromáticas distintas que evidenciam
     * a velocidade de escape em cada região do fractal.
     */
    int max_iter = (img->max_iter > 0) ? img->max_iter : DEFAULT_MAX_ITER;
    for (size_t i = 0; i < total_pixels; i++) {
        int32_t iter = img->data[i];
        if (iter >= max_iter) {
            /* Interior do conjunto: preto */
            pixels[i * 3 + 0] = 0;
            pixels[i * 3 + 1] = 0;
            pixels[i * 3 + 2] = 0;
        } else {
            double t = (double)iter / (double)max_iter;
            double hue = fmod(360.0 * t * 5.0, 360.0);  /* ciclos de matiz */
            double sat = 0.85;
            double val = 0.6 + 0.4 * t;                  /* brilho crescente */
            hsv_to_rgb(hue, sat, val,
                       &pixels[i * 3 + 0],
                       &pixels[i * 3 + 1],
                       &pixels[i * 3 + 2]);
        }
    }

    size_t total_bytes = total_pixels * 3;
    size_t written = fwrite(pixels, 1, total_bytes, fp);
    free(pixels);
    fclose(fp);

    if (written != total_bytes) {
        fprintf(stderr, "Erro: escrita incompleta no arquivo PPM (%zu de %zu bytes).\n",
                written, total_bytes);
        return -1;
    }

    printf("Imagem PPM exportada: %s (%d x %d)\n", filename, img->width, img->height);
    return 0;
}

/* ========================================================================== */
/* Exportação Binária (int32_t Row-Major)                                     */
/* ========================================================================== */

int export_binary(const ImageBuffer *img, const char *filename) {
    if (img == NULL || img->data == NULL || filename == NULL) {
        fprintf(stderr, "Erro: parametros invalidos para export_binary.\n");
        return -1;
    }

    FILE *fp = fopen(filename, "wb");
    if (fp == NULL) {
        perror("Erro ao abrir arquivo binario para escrita");
        return -1;
    }

    size_t total_pixels = (size_t)img->width * (size_t)img->height;
    size_t written = fwrite(img->data, sizeof(int32_t), total_pixels, fp);
    fclose(fp);

    if (written != total_pixels) {
        fprintf(stderr, "Erro: escrita incompleta no arquivo binario (%zu de %zu elementos).\n",
                written, total_pixels);
        return -1;
    }

    printf("Matriz binaria exportada: %s (%d x %d, %zu bytes)\n",
           filename, img->width, img->height, total_pixels * sizeof(int32_t));
    return 0;
}

/* ========================================================================== */
/* Carregamento de Matriz Binária                                             */
/* ========================================================================== */

ImageBuffer* load_binary(const char *filename, int width, int height) {
    if (filename == NULL || width <= 0 || height <= 0) {
        fprintf(stderr, "Erro: parametros invalidos para load_binary.\n");
        return NULL;
    }

    FILE *fp = fopen(filename, "rb");
    if (fp == NULL) {
        perror("Erro ao abrir arquivo binario para leitura");
        return NULL;
    }

    ImageBuffer *img = create_image_buffer(width, height);
    if (img == NULL) {
        fclose(fp);
        return NULL;
    }

    size_t total_pixels = (size_t)width * (size_t)height;
    size_t read_count = fread(img->data, sizeof(int32_t), total_pixels, fp);
    fclose(fp);

    if (read_count != total_pixels) {
        fprintf(stderr, "Erro: leitura incompleta do arquivo binario (%zu de %zu elementos).\n",
                read_count, total_pixels);
        free_image_buffer(img);
        return NULL;
    }

    return img;
}
