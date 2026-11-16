# Etapa 3 — Geração do Conjunto de Mandelbrot em CUDA

**Disciplina:** DEC107 — Processamento Paralelo (UESC, Semestre 2026-2)  
**Etapa:** 3 (Paralelismo Massivo em GPU com NVIDIA CUDA)

---

## 1. Sobre a Etapa 3

Esta pasta contém a implementação da **Etapa 3 (CUDA)** do projeto de geração do Conjunto de Mandelbrot pelo algoritmo de *escape-time* em precisão dupla (`double`).

Na **Parte 1 (Base Funcional e Validação)** são entregues:
- A versão serial de referência (`src/mandelbrot_serial.c`) seguindo estritamente a especificação da Seção 5.1 do enunciado;
- O kernel CUDA *baseline* (`src/mandelbrot_cuda.cu`) com mapeamento **1 thread = 1 pixel**, blocos iniciais `16×16` e medição separada do tempo de execução do kernel e do tempo de transferência `Device -> Host` (`D->H`);
- O cabeçalho compartilhado (`src/common.h`) com a estrutura `MandelbrotParams`, parser de argumentos de linha de comando e funções de exportação em formato binário (`int32` *row-major*) e imagem PGM (`P5`);
- O verificador de corretude (`scripts/compare_matrices.c`) que implementa os critérios da Seção 5.5 (igualdade exata ou no máximo `0,01%` de pixels divergindo em até `1` iteração);
- O esqueleto de automação experimental (`scripts/run_experiments.sh`) para a Parte 2.

---

## 2. Estrutura de Pastas

```text
etapa3-cuda/
├── README.md                  # Instruções de instalação, compilação, execução e validação
├── Makefile                   # Alvos: all, serial, cuda, compare, clean
├── .gitignore                 # Ignora bin/, output/ e artefatos gerados
├── src/
│   ├── common.h               # Struct MandelbrotParams, CLI parser, write_matrix_bin, write_pgm
│   ├── mandelbrot_serial.c    # Implementação serial de referência (CLOCK_MONOTONIC)
│   └── mandelbrot_cuda.cu     # Implementação CUDA baseline (1 thread = 1 pixel, bloco 16x16)
├── scripts/
│   ├── compare_matrices.c     # Validador de corretude (Seção 5.5)
│   └── run_experiments.sh     # Esqueleto de experimentos (será preenchido na Parte 2)
├── bin/                       # Executáveis gerados pelo Makefile (ignorado pelo Git)
├── output/                    # Matrizes .bin e imagens .pgm geradas (ignorado pelo Git)
└── docs/
    └── validacao.md           # Relatório de validação da Parte 1 (ambiente e resultados)
```

---

## 3. Dependências e Instalação

### 3.1. Como Instalar (Ubuntu / Debian)

1. **Compilador C e ferramentas de build:**
   ```bash
   sudo apt update && sudo apt install -y build-essential
   gcc --version
   make --version
   ```

2. **CUDA Toolkit (inclui `nvcc`, `nsys`, `ncu`):**
   ```bash
   sudo apt install -y nvidia-cuda-toolkit
   nvcc --version
   nvidia-smi
   ```

3. **Ferramentas de profiling (para a Parte 2):**
   ```bash
   nsys --version
   ncu --version
   ```

4. **Valgrind (verificação de vazamentos de memória na versão serial):**
   ```bash
   sudo apt install -y valgrind
   valgrind --version
   ```

5. **Python 3 + Matplotlib + NumPy (opcional, para conferência visual de imagens PGM):**
   ```bash
   sudo apt install -y python3 python3-matplotlib python3-numpy
   ```

### 3.2. Versões Registradas no Ambiente de Validação

- **Sistema Operacional:** Ubuntu 24.04.5 LTS (`Linux 7.0.0-42-generic x86_64`)
- **CPU:** Intel(R) Core(TM) 7 240H (16 threads)
- **GPU:** NVIDIA GeForce RTX 5050 Laptop GPU (8151 MiB, Arquitetura Blackwell, Compute Capability `12.0` / `sm_120`)
- **Driver NVIDIA / CUDA Driver:** Driver `595.99.02` / CUDA `13.2`
- **NVCC (CUDA Toolkit):** `Cuda compilation tools, release 12.0, V12.0.140` (`-arch=sm_89` com compatibilidade PTX JIT para `sm_120`)
- **GCC:** `gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`
- **Make:** `GNU Make 4.3`
- **Nsight Systems (`nsys`):** `2022.4.2.50-32196742v0`
- **Nsight Compute (`ncu`):** `2022.4.1.0 (build 32308335)`
- **Valgrind:** `valgrind-3.22.0`
- **Python / NumPy / Matplotlib:** Python `3.12.3`, NumPy `1.26.4`, Matplotlib `3.6.3`

---

## 4. Como Compilar

A partir do diretório `etapa3-cuda/`:

```bash
# Compila todos os alvos (serial, cuda e compare)
make all
```

Ou individualmente:

```bash
make serial    # Gera bin/mandelbrot_serial
make cuda      # Gera bin/mandelbrot_cuda
make compare   # Gera bin/compare
```

Para ajustar a arquitetura da GPU (padrão `ARCH=sm_89` no topo do `Makefile`):

```bash
make cuda ARCH=sm_86
```

Para limpar os diretórios `bin/` e `output/`:

```bash
make clean
```

---

## 5. Como Executar

Tanto `./bin/mandelbrot_serial` quanto `./bin/mandelbrot_cuda` aceitam exatamente as mesmas flags de linha de comando:

| Flag | Padrão | Descrição |
| :--- | :--- | :--- |
| `--width N` | `4096` | Largura da imagem em pixels |
| `--height N` | `4096` | Altura da imagem em pixels |
| `--xmin X` | `-2.0` | Limite inferior do eixo real ($\text{Re}_{\min}$) |
| `--xmax X` | `1.0` | Limite superior do eixo real ($\text{Re}_{\max}$) |
| `--ymin Y` | `-1.5` | Limite inferior do eixo imaginário ($\text{Im}_{\min}$) |
| `--ymax Y` | `1.5` | Limite superior do eixo imaginário ($\text{Im}_{\max}$) |
| `--max-iter N` | `1000` | Número máximo de iterações (`MAX_ITER`) |
| `--out-bin PATH` | `output/{serial,cuda}_base.bin` | Caminho de saída da matriz binária (`int32` *row-major*) |
| `--out-pgm PATH` | `output/{serial,cuda}_base.pgm` | Caminho de saída da imagem PGM (`P5`) |
| `--preset NAME` | `full` | Preset de região: `full` (Seção 5.2) ou `seahorse`/`zoom` (Seção 5.3) |

### 5.1. Caso Base (Seção 5.2 — 4096×4096, `MAX_ITER = 1000`)

```bash
./bin/mandelbrot_serial
./bin/mandelbrot_cuda
```
Gera `output/serial_base.bin`, `output/serial_base.pgm`, `output/cuda_base.bin` e `output/cuda_base.pgm`.

### 5.2. Caso de Desbalanceamento Acentuado (Seção 5.3 — Vale dos Cavalos-Marinhos, `MAX_ITER = 5000`)

Centro `(-0.743643887, 0.131825904)` e largura `3.0e-3` em ambos os eixos:

```bash
./bin/mandelbrot_serial \
  --xmin -0.745143887 --xmax -0.742143887 \
  --ymin 0.130325904 --ymax 0.133325904 \
  --max-iter 5000 \
  --out-bin output/serial_zoom.bin \
  --out-pgm output/serial_zoom.pgm

./bin/mandelbrot_cuda \
  --xmin -0.745143887 --xmax -0.742143887 \
  --ymin 0.130325904 --ymax 0.133325904 \
  --max-iter 5000 \
  --out-bin output/cuda_zoom.bin \
  --out-pgm output/cuda_zoom.pgm
```

*(Alternativamente, pode-se usar `--preset seahorse --out-bin ... --out-pgm ...`).*

---

## 6. Como Validar a Corretude

Utilize o binário `./bin/compare` passando a matriz serial de referência e a matriz gerada pelo CUDA:

```bash
# Validação no Caso Base (Seção 5.2)
./bin/compare output/serial_base.bin output/cuda_base.bin

# Validação no Caso de Desbalanceamento / Zoom (Seção 5.3)
./bin/compare output/serial_zoom.bin output/cuda_zoom.bin
```

O programa imprime o total de pixels, o número e o percentual de pixels divergentes, a maior diferença absoluta em iterações e o veredito (`PASS` com código de retorno `0`, ou `FAIL` com código `1`). Os resultados detalhados da validação encontram-se em [`docs/validacao.md`](docs/validacao.md).
