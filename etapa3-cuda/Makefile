# ==============================================================================
# Makefile — Etapa 3 (CUDA) — Conjunto de Mandelbrot (DEC107)
# ==============================================================================

# Arquitetura alvo da GPU (ajuste conforme sua GPU e versao do nvcc):
#   Exemplos: sm_75 (Turing), sm_86 (Ampere), sm_89 (Ada / compatibilidade PTX
#   no CUDA 12.0 para GPUs Blackwell sm_120 como a RTX 5050 Laptop GPU).
ARCH ?= sm_89

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

.PHONY: all serial cuda compare clean

all: serial cuda compare

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

serial: $(BIN_DIR)
	$(CC) $(CFLAGS) src/mandelbrot_serial.c -o $(SERIAL_BIN) $(LDFLAGS)

cuda: $(BIN_DIR)
	$(NVCC) $(NVFLAGS) src/mandelbrot_cuda.cu -o $(CUDA_BIN)

compare: $(BIN_DIR)
	$(CC) $(CFLAGS) scripts/compare_matrices.c -o $(COMPARE_BIN)

clean:
	rm -rf $(BIN_DIR) $(OUT_DIR)
