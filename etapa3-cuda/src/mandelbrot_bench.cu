/* ========================================================================== */
/* mandelbrot_bench.cu -- Etapa 3 - Parte 2: benchmark + tuning */
/*                                                                            */
/* Variantes (--variant):                                                     */
/*   base     kernel base (referencia)                                        */
/*   naive    __restrict__, z^2 em registrador, layout 1D/2D, c opcional host */
/*   warp     early-exit por warp (__any_sync)                                */
/*   compact  tile + compactacao de pixels ativos (rodadas de --chunk)        */
/* Opcoes: --block BXxBY  --layout 2d|1d  --ctab (c = tabelas do host)        */
/*         --mode sync|pinned|streams  --streams N  --chunk K                 */
/*         --warmup N  --reps N (>=5)  --csv F  --group G  --scenario S       */
/*         --no-verify   (+ as de common.h; --preset depois de --width/--height)*/
/* Compile com -DUSE_CONST_PARAMS para colocar os parametros em __constant__. */
/*                                                                            */
/* Todas as variantes usam a MESMA aritmetica IEEE (intrinsecos _rn, sem FMA, */
/* mesma ordem de operacoes) => saida bit a bit igual ao baseline/serial.     */
/* ========================================================================== */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 199309L
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <cuda_runtime.h>
#include "common.h"

#define CUDA_CHECK(call) do { cudaError_t e_ = (call); if (e_ != cudaSuccess) {      \
    fprintf(stderr, "Erro CUDA %s:%d: %s\n", __FILE__, __LINE__, cudaGetErrorString(e_)); \
    exit(EXIT_FAILURE); } } while (0)
#define FULL 0xffffffffu
#define MAX_STREAMS 64

typedef struct {
    int width, height, max_iter, oneD;
    double xmin, xmax, ymin, ymax, range_x, range_y, denom_x, denom_y;
    const double *cr_tab, *ci_tab;      /* != NULL => c vem de tabelas calculadas no host */
} KParams;

#ifdef USE_CONST_PARAMS
__constant__ KParams c_kp;              /* parametros em memoria constante */
#define KP(p) c_kp
#else
#define KP(p) (p)                       /* parametros como argumento (ja vao ao banco de constantes) */
#endif

/* -- device -- */
/* Thread -> pixel. 2D: (x,y) do bloco. 1D: indice linear -> (lin % W, lin / W). */
__device__ __forceinline__ int get_pixel(const KParams &K, int row0, int row1, int *px, int *py) {
    if (K.oneD) {
        int lin = row0 * K.width + (int)(blockIdx.x * blockDim.x + threadIdx.x);
        *px = lin % K.width;
        *py = lin / K.width;
        return lin < row1 * K.width;
    }
    *px = blockIdx.x * blockDim.x + threadIdx.x;
    *py = row0 + blockIdx.y * blockDim.y + threadIdx.y;
    return *px < K.width && *py < row1;
}

__device__ __forceinline__ void get_c(const KParams &K, int px, int py, double *cr, double *ci) {
    if (K.cr_tab) { *cr = K.cr_tab[px]; *ci = K.ci_tab[py]; return; }
    *cr = __dadd_rn(K.xmin, __dmul_rn(__ddiv_rn((double)px, K.denom_x), K.range_x));
    *ci = __dadd_rn(K.ymin, __dmul_rn(__ddiv_rn((double)py, K.denom_y), K.range_y));
}

/* Um passo z <- z^2 + c; zr2/zi2 ficam em registrador (o baseline os recalcula).
 * Mesmas operacoes na mesma ordem => mesmo resultado, menos multiplicacoes double. */
#define STEP(zr, zi, zr2, zi2, cr, ci) do {                                 \
    double nzi_ = __dadd_rn(__dmul_rn(2.0, __dmul_rn(zr, zi)), ci);         \
    double nzr_ = __dadd_rn(__dsub_rn(zr2, zi2), cr);                       \
    zr = nzr_; zi = nzi_; zr2 = __dmul_rn(zr, zr); zi2 = __dmul_rn(zi, zi); \
} while (0)
#define INSIDE(zr2, zi2) (__dadd_rn(zr2, zi2) <= 4.0)

/* base: copia fiel do kernel da Parte 1 */
__global__ void k_base(int *out, int width, int height, double xmin, double xmax,
                       double ymin, double ymax, int max_iter) {
    int px = blockIdx.x * blockDim.x + threadIdx.x;
    int py = blockIdx.y * blockDim.y + threadIdx.y;
    if (px >= width || py >= height) return;
    double dx = (width > 1) ? (double)(width - 1) : 1.0, dy = (height > 1) ? (double)(height - 1) : 1.0;
    double cr = __dadd_rn(xmin, __dmul_rn(__ddiv_rn((double)px, dx), __dsub_rn(xmax, xmin)));
    double ci = __dadd_rn(ymin, __dmul_rn(__ddiv_rn((double)py, dy), __dsub_rn(ymax, ymin)));
    double zr = 0.0, zi = 0.0;
    int iter = 0;
    while (iter < max_iter && __dadd_rn(__dmul_rn(zr, zr), __dmul_rn(zi, zi)) <= 4.0) {
        double zr2 = __dmul_rn(zr, zr), zi2 = __dmul_rn(zi, zi);
        double nzr = __dadd_rn(__dsub_rn(zr2, zi2), cr);
        double nzi = __dadd_rn(__dmul_rn(2.0, __dmul_rn(zr, zi)), ci);
        zr = nzr; zi = nzi; iter++;
    }
    out[py * width + px] = iter;
}

/* naive: o laco de cada thread termina sozinho (o hardware mascara os lanes que escaparam) */
__global__ void k_naive(int *__restrict__ out, KParams p, int row0, int row1) {
    const KParams &K = KP(p);
    int px, py;
    if (!get_pixel(K, row0, row1, &px, &py)) return;
    double cr, ci, zr = 0.0, zi = 0.0, zr2 = 0.0, zi2 = 0.0;
    int iter = 0;
    get_c(K, px, py, &cr, &ci);
    while (iter < K.max_iter && INSIDE(zr2, zi2)) { STEP(zr, zi, zr2, zi2, cr, ci); iter++; }
    out[py * K.width + px] = iter;
}

/* warp: early-exit por warp. O warp inteiro sai quando NENHUM lane esta ativo
 * (__any_sync). Todos os 32 lanes devem executar o __any_sync, entao threads fora
 * da imagem NAO retornam cedo: participam com active=0. Bloco multiplo de 32. */
__global__ void k_warp(int *__restrict__ out, KParams p, int row0, int row1) {
    const KParams &K = KP(p);
    int px = 0, py = 0;
    int in = get_pixel(K, row0, row1, &px, &py);
    double cr = 0.0, ci = 0.0, zr = 0.0, zi = 0.0, zr2 = 0.0, zi2 = 0.0;
    int iter = 0, active = in;
    if (in) get_c(K, px, py, &cr, &ci);
    while (__any_sync(FULL, active)) {
        if (active) {
            STEP(zr, zi, zr2, zi2, cr, ci);
            iter++;
            active = (iter < K.max_iter) && INSIDE(zr2, zi2);
        }
    }
    if (in) out[py * K.width + px] = iter;
}

/* compact: cada bloco e um tile. Trabalho em RODADAS de `chunk` iteracoes:
 *  (1) cada thread avanca seu pixel ate `chunk` iteracoes ou ate escapar;
 *  (2) quem terminou grava out[pix];
 *  (3) os pixels ainda ativos sao compactados na memoria compartilhada
 *      (__ballot_sync + __popc + soma das contagens por warp) e as threads
 *      0..total-1 assumem esses pixels => warps densos nas rodadas seguintes.
 * Estado (zr,zi,iter) preservado entre rodadas => mesmo resultado do laco serial.
 * smem dinamica por bloco: T*(4 double + 2 int) + 32 int. Bloco multiplo de 32. */
extern __shared__ __align__(16) unsigned char smem_raw[];

__global__ void k_compact(int *__restrict__ out, KParams p, int row0, int row1, int chunk) {
    const KParams &K = KP(p);
    const int T = blockDim.x * blockDim.y, tid = threadIdx.y * blockDim.x + threadIdx.x;
    const int lane = tid & 31, wid = tid >> 5, nwarps = T >> 5;
    double *s_zr = (double *)smem_raw, *s_zi = s_zr + T, *s_cr = s_zi + T, *s_ci = s_cr + T;
    int *s_it = (int *)(s_ci + T), *s_pix = s_it + T, *s_wc = s_pix + T;

    int px = 0, py = 0, iter = 0, pix = 0;
    int have = get_pixel(K, row0, row1, &px, &py);
    double cr = 0.0, ci = 0.0, zr = 0.0, zi = 0.0;
    if (have) { get_c(K, px, py, &cr, &ci); pix = py * K.width + px; }

    for (;;) {
        int alive = 0;
        if (have) {                                           /* (1) rodada */
            int stop = iter + chunk < K.max_iter ? iter + chunk : K.max_iter;
            double zr2 = __dmul_rn(zr, zr), zi2 = __dmul_rn(zi, zi);
            while (iter < stop && INSIDE(zr2, zi2)) { STEP(zr, zi, zr2, zi2, cr, ci); iter++; }
            alive = (iter < K.max_iter) && INSIDE(zr2, zi2);  /* o laco serial continuaria? */
            if (!alive) out[pix] = iter;                      /* (2) concluido */
        }
        unsigned m = __ballot_sync(FULL, alive);              /* (3) compactacao */
        int wrank = __popc(m & ((1u << lane) - 1u));
        if (lane == 0) s_wc[wid] = __popc(m);
        __syncthreads();
        int base = 0, total = 0;
        for (int w = 0; w < nwarps; w++) { int c = s_wc[w]; if (w < wid) base += c; total += c; }
        if (total == 0) break;                                /* uniforme no bloco */
        if (alive) {
            int s = base + wrank;
            s_zr[s] = zr; s_zi[s] = zi; s_cr[s] = cr; s_ci[s] = ci; s_it[s] = iter; s_pix[s] = pix;
        }
        __syncthreads();
        have = (tid < total);
        if (have) { zr = s_zr[tid]; zi = s_zi[tid]; cr = s_cr[tid]; ci = s_ci[tid]; iter = s_it[tid]; pix = s_pix[tid]; }
    }
}

/* -- host -- */
enum { V_BASE, V_NAIVE, V_WARP, V_COMPACT };
enum { M_SYNC, M_PINNED, M_STREAMS };
static const char *VNAME[] = {"base", "naive", "warp", "compact"};
static const char *MNAME[] = {"sync", "pinned", "streams"};

typedef struct {
    int variant, bx, by, oneD, ctab, mode, streams, chunk, warmup, reps, verify;
    const char *csv, *group, *scenario;
} Opt;

static KParams kp;                       /* parametros do problema */
static int *d_out;                       /* matriz no device */
static double *d_cr, *d_ci;              /* tabelas de c (--ctab) */
static double *h_cr, *h_ci;
static size_t bytes;
static cudaEvent_t ev0, ev1;
static cudaStream_t strm[MAX_STREAMS];
static int nstreams;

typedef struct { double h2d, kernel, d2h, total; } Timing;     /* ms */

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
static int cmp_d(const void *a, const void *b) { double x = *(const double *)a, y = *(const double *)b; return (x > y) - (x < y); }
static void stats(const double *v, int n, double *med, double *mn, double *mx) {
    double *s = (double *)malloc((size_t)n * sizeof(double));
    memcpy(s, v, (size_t)n * sizeof(double));
    qsort(s, (size_t)n, sizeof(double), cmp_d);
    *med = (n % 2) ? s[n / 2] : 0.5 * (s[n / 2 - 1] + s[n / 2]);
    *mn = s[0]; *mx = s[n - 1];
    free(s);
}

/* c(i) = min + (i/denom)*range com os mesmos passos IEEE do device; `volatile`
 * impede o compilador do host de fundir em FMA (o que mudaria os bits). */
static double host_c(int i, double minv, double denom, double range) {
    volatile double q = (double)i / denom;
    volatile double m = q * range;
    return minv + m;
}

static void launch(int v, int bx, int by, int r0, int r1, int chunk, cudaStream_t s) {
    int rows = r1 - r0, T = bx * by;
    dim3 b = kp.oneD ? dim3(T, 1, 1) : dim3(bx, by, 1);
    dim3 g = kp.oneD ? dim3((rows * kp.width + T - 1) / T, 1, 1)
                     : dim3((kp.width + bx - 1) / bx, (rows + by - 1) / by, 1);
    size_t smem = (v == V_COMPACT) ? (size_t)T * (4 * sizeof(double) + 2 * sizeof(int)) + 32 * sizeof(int) : 0;
    if (v == V_BASE) {
        dim3 b2(bx, by, 1), g2((kp.width + bx - 1) / bx, (kp.height + by - 1) / by, 1);
        k_base<<<g2, b2, 0, s>>>(d_out, kp.width, kp.height, kp.xmin, kp.xmax, kp.ymin, kp.ymax, kp.max_iter);
    } else if (v == V_NAIVE) {
        k_naive<<<g, b, 0, s>>>(d_out, kp, r0, r1);
    } else if (v == V_WARP) {
        k_warp<<<g, b, 0, s>>>(d_out, kp, r0, r1);
    } else {
        k_compact<<<g, b, smem, s>>>(d_out, kp, r0, r1, chunk);
    }
}

/* Uma repeticao do pipeline (SEM escrita em disco). */
static Timing run_rep(const Opt *o, int variant, int bx, int by, int mode, int *h_out) {
    Timing t = {0, 0, 0, 0};
    double t0 = now_sec();
    if (kp.cr_tab && variant != V_BASE) {                     /* H->D das tabelas de c */
        CUDA_CHECK(cudaMemcpy(d_cr, h_cr, (size_t)kp.width * sizeof(double), cudaMemcpyHostToDevice));
        CUDA_CHECK(cudaMemcpy(d_ci, h_ci, (size_t)kp.height * sizeof(double), cudaMemcpyHostToDevice));
    }
    double t1 = now_sec();
    if (mode != M_STREAMS) {
        CUDA_CHECK(cudaEventRecord(ev0, 0));
        launch(variant, bx, by, 0, kp.height, o->chunk, 0);
        CUDA_CHECK(cudaEventRecord(ev1, 0));
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaEventSynchronize(ev1));
        double t2 = now_sec();
        CUDA_CHECK(cudaMemcpy(h_out, d_out, bytes, cudaMemcpyDeviceToHost));
        double t3 = now_sec();
        float ms = 0.0f;
        CUDA_CHECK(cudaEventElapsedTime(&ms, ev0, ev1));
        t.h2d = (t1 - t0) * 1e3; t.kernel = ms; t.d2h = (t3 - t2) * 1e3; t.total = (t3 - t0) * 1e3;
    } else {                                                  /* N faixas de linhas, 1 stream cada */
        for (int s = 0; s < nstreams; s++) {
            int r0 = (int)((long long)kp.height * s / nstreams), r1 = (int)((long long)kp.height * (s + 1) / nstreams);
            if (r1 <= r0) continue;
            launch(variant, bx, by, r0, r1, o->chunk, strm[s]);
            CUDA_CHECK(cudaMemcpyAsync(h_out + (size_t)r0 * kp.width, d_out + (size_t)r0 * kp.width,
                                       (size_t)(r1 - r0) * kp.width * sizeof(int), cudaMemcpyDeviceToHost, strm[s]));
        }
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaDeviceSynchronize());
        t.h2d = (t1 - t0) * 1e3; t.kernel = t.d2h = -1.0;     /* kernel e D->H se sobrepoem */
        t.total = (now_sec() - t0) * 1e3;
    }
    return t;
}

static void die(const char *msg) { fprintf(stderr, "Erro: %s\n", msg); exit(EXIT_FAILURE); }
static int index_of(const char **names, int n, const char *s) {
    for (int i = 0; i < n; i++) if (strcmp(names[i], s) == 0) return i;
    die("valor invalido de --variant/--mode");
    return -1;
}

int main(int argc, char **argv) {
    Opt o = {V_NAIVE, 16, 16, 0, 0, M_SYNC, 4, 64, 2, 7, 1, NULL, "adhoc", "adhoc"};
    char **rest = (char **)malloc((size_t)argc * sizeof(char *));
    int nrest = 0;
    rest[nrest++] = argv[0];
    for (int i = 1; i < argc; i++) {                          /* opcoes proprias; o resto vai a parse_args */
        const char *a = argv[i], *v = (i + 1 < argc) ? argv[i + 1] : NULL;
        if (!strcmp(a, "--variant") && v)       { o.variant = index_of(VNAME, 4, v); i++; }
        else if (!strcmp(a, "--mode") && v)     { o.mode = index_of(MNAME, 3, v); i++; }
        else if (!strcmp(a, "--block") && v)    { if (sscanf(v, "%dx%d", &o.bx, &o.by) != 2) die("--block espera BXxBY"); i++; }
        else if (!strcmp(a, "--layout") && v)   { o.oneD = !strcmp(v, "1d"); i++; }
        else if (!strcmp(a, "--streams") && v)  { o.streams = atoi(v); i++; }
        else if (!strcmp(a, "--chunk") && v)    { o.chunk = atoi(v); i++; }
        else if (!strcmp(a, "--warmup") && v)   { o.warmup = atoi(v); i++; }
        else if (!strcmp(a, "--reps") && v)     { o.reps = atoi(v); i++; }
        else if (!strcmp(a, "--csv") && v)      { o.csv = v; i++; }
        else if (!strcmp(a, "--group") && v)    { o.group = v; i++; }
        else if (!strcmp(a, "--scenario") && v) { o.scenario = v; i++; }
        else if (!strcmp(a, "--ctab"))          o.ctab = 1;
        else if (!strcmp(a, "--no-verify"))     o.verify = 0;
        else rest[nrest++] = argv[i];
    }
    MandelbrotParams mp;
    init_default_params(&mp, NULL, NULL);                     /* sem caminhos: so escreve se pedido */
    int rc = parse_args(nrest, rest, &mp);
    if (rc != 0) return rc == 1 ? EXIT_SUCCESS : EXIT_FAILURE;

    if (o.reps < 5) { fprintf(stderr, "Aviso: --reps < 5; usando 5 (Secao 9).\n"); o.reps = 5; }
    if (o.warmup < 1) o.warmup = 1;
    int T = o.bx * o.by;
    if (o.bx <= 0 || o.by <= 0 || T > 1024 || o.chunk <= 0 || o.streams <= 0) die("--block/--chunk/--streams invalidos");
    if ((o.variant == V_WARP || o.variant == V_COMPACT) && T % 32) die("warp/compact exigem bloco multiplo de 32");
    if (o.variant == V_BASE && (o.mode == M_STREAMS || o.oneD || o.ctab)) die("base nao suporta streams/1d/ctab");

    CUDA_CHECK(cudaFree(0));                                  /* cria o contexto fora das medicoes */
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    int W = mp.width, H = mp.height;
    memset(&kp, 0, sizeof kp);
    kp.width = W; kp.height = H; kp.max_iter = mp.max_iter; kp.oneD = o.oneD;
    kp.xmin = mp.xmin; kp.xmax = mp.xmax; kp.ymin = mp.ymin; kp.ymax = mp.ymax;
    kp.range_x = mp.xmax - mp.xmin; kp.range_y = mp.ymax - mp.ymin;
    kp.denom_x = (W > 1) ? (double)(W - 1) : 1.0; kp.denom_y = (H > 1) ? (double)(H - 1) : 1.0;
    bytes = (size_t)W * (size_t)H * sizeof(int);

    CUDA_CHECK(cudaMalloc((void **)&d_out, bytes));
    if (o.ctab) {
        CUDA_CHECK(cudaMalloc((void **)&d_cr, (size_t)W * sizeof(double)));
        CUDA_CHECK(cudaMalloc((void **)&d_ci, (size_t)H * sizeof(double)));
        h_cr = (double *)malloc((size_t)W * sizeof(double));
        h_ci = (double *)malloc((size_t)H * sizeof(double));
        for (int i = 0; i < W; i++) h_cr[i] = host_c(i, kp.xmin, kp.denom_x, kp.range_x);
        for (int j = 0; j < H; j++) h_ci[j] = host_c(j, kp.ymin, kp.denom_y, kp.range_y);
        kp.cr_tab = d_cr; kp.ci_tab = d_ci;
    }
#ifdef USE_CONST_PARAMS
    CUDA_CHECK(cudaMemcpyToSymbol(c_kp, &kp, sizeof kp));    /* 1 vez; kernels leem c_kp */
    const char *params_s = "const";
#else
    const char *params_s = "arg";
#endif
    CUDA_CHECK(cudaEventCreate(&ev0));
    CUDA_CHECK(cudaEventCreate(&ev1));
    nstreams = (o.streams > MAX_STREAMS) ? MAX_STREAMS : (o.streams > H ? H : o.streams);
    if (o.mode == M_STREAMS) for (int s = 0; s < nstreams; s++) CUDA_CHECK(cudaStreamCreate(&strm[s]));

    int *h_out;
    if (o.mode == M_SYNC) h_out = (int *)malloc(bytes);                   /* pageable */
    else CUDA_CHECK(cudaMallocHost((void **)&h_out, bytes));              /* pinned */
    memset(h_out, 0, bytes);                                              /* evita page-fault no 1o D->H */

    printf("=== Mandelbrot CUDA — benchmark (Parte 2) ===\n");
    printf("GPU        : %s (CC %d.%d, %d SMs, %.1f GiB)\n", prop.name, prop.major, prop.minor,
           prop.multiProcessorCount, (double)prop.totalGlobalMem / (1024.0 * 1024.0 * 1024.0));
    printf("Resolucao  : %d x %d  MAX_ITER=%d\n", W, H, mp.max_iter);
    printf("Regiao Re  : [%.10f, %.10f]\n", mp.xmin, mp.xmax);
    printf("Regiao Im  : [%.10f, %.10f]\n", mp.ymin, mp.ymax);
    printf("Variante   : %s  (%s; layout %s; c no %s; parametros: %s)\n", VNAME[o.variant],
           o.variant == V_BASE ? "kernel do Integrante 1" : o.variant == V_NAIVE ? "restrict, z^2 em registrador"
           : o.variant == V_WARP ? "early-exit por warp (__any_sync)" : "tile + compactacao de pixels ativos",
           o.oneD ? "1D" : "2D", o.ctab ? "host (tabelas)" : "device", params_s);
    printf("Bloco      : %dx%d (%d threads)\n", o.bx, o.by, T);
    printf("Modo       : %s", MNAME[o.mode]);
    if (o.mode == M_STREAMS) printf("  (%d streams)", nstreams);
    if (o.variant == V_COMPACT) printf("  chunk=%d", o.chunk);
    printf("\nRepeticoes : %d aquecimento + %d medidas (mediana)\n", o.warmup, o.reps);


    /* referencia do --verify: kernel base, 16x16, modo sync */
    int *h_ref = NULL;
    if (o.verify && o.variant != V_BASE) {
        h_ref = (int *)malloc(bytes);
        run_rep(&o, V_BASE, 16, 16, M_SYNC, h_ref);
    }

    for (int i = 0; i < o.warmup; i++) run_rep(&o, o.variant, o.bx, o.by, o.mode, h_out);
    double *vh = (double *)malloc((size_t)o.reps * sizeof(double)), *vk = (double *)malloc((size_t)o.reps * sizeof(double));
    double *vd = (double *)malloc((size_t)o.reps * sizeof(double)), *vt = (double *)malloc((size_t)o.reps * sizeof(double));
    for (int i = 0; i < o.reps; i++) {
        Timing t = run_rep(&o, o.variant, o.bx, o.by, o.mode, h_out);
        vh[i] = t.h2d; vk[i] = t.kernel; vd[i] = t.d2h; vt[i] = t.total;
    }
    double h2d, k, k0, k1, d2h, d0, d1, tot, t0, t1, junk;
    stats(vh, o.reps, &h2d, &junk, &junk);
    stats(vk, o.reps, &k, &k0, &k1);
    stats(vd, o.reps, &d2h, &d0, &d1);
    stats(vt, o.reps, &tot, &t0, &t1);

    const char *verify = "skipped";
    if (h_ref) {
        size_t bad = 0, n = (size_t)W * H;
        for (size_t i = 0; i < n; i++) bad += (h_out[i] != h_ref[i]);
        verify = bad ? "MISMATCH" : "identical";
        printf("Verificacao vs base: %s (%zu pixels diferentes)\n", verify, bad);
    }

    double write_ms = 0.0;                                    /* escrita em disco: 1 vez, fora das medicoes */
    if (mp.out_bin || mp.out_pgm) {
        double w0 = now_sec();
        if (mp.out_bin && write_matrix_bin(mp.out_bin, h_out, W, H)) return EXIT_FAILURE;
        if (mp.out_pgm && write_pgm(mp.out_pgm, h_out, W, H, mp.max_iter)) return EXIT_FAILURE;
        write_ms = (now_sec() - w0) * 1e3;
    }

    printf("\n--- Resultados (mediana de %d repeticoes) ---\n", o.reps);
    printf("H->D (tabelas/const)  : %10.3f ms\n", h2d);
    if (o.mode != M_STREAMS) {
        printf("Kernel (cudaEvent)    : %10.3f ms   [min %.3f, max %.3f]   %.2f Mpixel/s\n",
               k, k0, k1, ((double)W * (double)H) / (k * 1e-3) / 1e6);
        printf("D->H                  : %10.3f ms\n", d2h);
    } else {
        printf("Kernel + D->H         : (sobrepostos em %d streams; ver total)\n", nstreams);
    }
    printf("TOTAL pipeline (wall) : %10.3f ms   [min %.3f, max %.3f]\n", tot, t0, t1);
    printf("Escrita em disco      : %10.3f ms   (fora das medicoes acima)\n", write_ms);

    if (o.csv) {
        ensure_parent_dir(o.csv);
        FILE *f = fopen(o.csv, "a");
        if (!f) die("nao foi possivel abrir o CSV");
        fseek(f, 0, SEEK_END);
        if (ftell(f) == 0)
            fprintf(f, "group,scenario,variant,layout,ctab,params,mode,bx,by,streams,chunk,width,height,max_iter,"
                       "reps,h2d_ms,kernel_ms,kernel_min_ms,kernel_max_ms,d2h_ms,total_ms,total_min_ms,total_max_ms,"
                       "write_ms,verify,gpu\n");
        fprintf(f, "%s,%s,%s,%s,%d,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%s,%s\n",
                o.group, o.scenario, VNAME[o.variant], o.oneD ? "1d" : "2d", o.ctab, params_s, MNAME[o.mode],
                o.bx, o.by, o.mode == M_STREAMS ? nstreams : 0, o.variant == V_COMPACT ? o.chunk : 0, W, H,
                mp.max_iter, o.reps, h2d, k, k0, k1, d2h, tot, t0, t1, write_ms, verify, prop.name);
        fclose(f);
    }
    return strcmp(verify, "MISMATCH") ? EXIT_SUCCESS : 3;
}
