# ==============================================================================
# Makefile — Etapa 3 (CUDA) — Conjunto de Mandelbrot (DEC107)
# ==============================================================================

# Arquitetura alvo da GPU (ajuste conforme sua GPU e versao do nvcc):
#   Exemplos: sm_75 (Turing), sm_86 (Ampere), sm_89 (Ada), sm_120 (Blackwell,
#   RTX 5050 Laptop GPU com CUDA Toolkit >= 12.8 / 13.2).
ARCH ?= sm_120

CC      = gcc
NVCC    = nvcc
CFLAGS  = -O3 -Wall -Wextra -std=c11
NVFLAGS = -O3 -arch=$(ARCH)
LDFLAGS = -lm

BIN_DIR = bin
OUT_DIR = output

SERIAL_BIN  = $(BIN_DIR)/mandelbrot_serial
CUDA_BIN    = $(BIN_DIR)/mandelbrot_cuda
COMPARE_BIN = $(BIN_DIR)/compare
BENCH_BIN   = $(BIN_DIR)/mandelbrot_bench

.PHONY: all serial cuda compare bench clean

all: serial cuda compare 

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

serial: $(BIN_DIR)
	$(CC) $(CFLAGS) src/mandelbrot_serial.c -o $(SERIAL_BIN) $(LDFLAGS)

cuda: $(BIN_DIR)
	$(NVCC) $(NVFLAGS) src/mandelbrot_cuda.cu -o $(CUDA_BIN)

compare: $(BIN_DIR)
	$(CC) $(CFLAGS) scripts/compare_matrices.c -o $(COMPARE_BIN)

# ---------------------------------------------------------------------------
# Harness de benchmark + variantes de otimizacao (Parte 2, Integrante 2).
# -lineinfo  : apenas debug-info; nao altera o codigo gerado, so permite ao
#              ncu/nsys mapear metricas para linhas do fonte.
# -Isrc      : garante que "common.h" seja encontrado mesmo se o arquivo for
#              compilado de outro diretorio.
# ---------------------------------------------------------------------------
bench: $(BIN_DIR) src/mandelbrot_bench.cu src/common.h
	$(NVCC) $(NVFLAGS) -lineinfo -Isrc src/mandelbrot_bench.cu -o $(BENCH_BIN)
	$(NVCC) $(NVFLAGS) -lineinfo -Isrc -DUSE_CONST_PARAMS src/mandelbrot_bench.cu -o $(BIN_DIR)/mandelbrot_bench_const

clean:
	rm -rf $(BIN_DIR) $(OUT_DIR)
