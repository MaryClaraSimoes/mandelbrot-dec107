# Relatório de Validação — Etapa 3 (CUDA Baseline)

**Disciplina:** DEC107 — Processamento Paralelo (UESC, Semestre 2026-2)  
**Papel:** Integrante 1 — Arquiteto CUDA / Núcleo do Kernel (Parte 1)

---

## 1. Ambiente de Execução

| Componente | Especificação / Versão |
| :--- | :--- |
| **Sistema Operacional** | Ubuntu 24.04.5 LTS (Kernel Linux `7.0.0-42-generic` x86_64) |
| **CPU** | Intel(R) Core(TM) 7 240H (16 threads lógicas, 2 threads/núcleo) |
| **GPU** | NVIDIA GeForce RTX 5050 Laptop GPU (8151 MiB VRAM, Arquitetura Blackwell `sm_120`) |
| **Driver NVIDIA** | `595.99.02` (suporte até CUDA Runtime `13.2`) |
| **CUDA Toolkit (`nvcc`)** | `12.0.140` (`Build cuda_12.0.r12.0/compiler.32267302_0`, flag `-arch=sm_89` com JIT PTX compatível para `sm_120`) |
| **Compilador C (`gcc`)** | `gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0` |
| **GNU Make** | `GNU Make 4.3` |
| **Ferramentas de Profiling** | NVIDIA Nsight Systems `2022.4.2.50` (`nsys`) / Nsight Compute `2022.4.1.0` (`ncu`) |
| **Valgrind** | `valgrind-3.22.0` |
| **Python / Bibliotecas** | Python `3.12.3`, NumPy `1.26.4`, Matplotlib `3.6.3` |

---

## 2. Comandos Executados

A partir do diretório `etapa3-cuda/`:

### 2.1. Compilação
```bash
make clean && make all
```
Comandos invocados pelo `Makefile`:
```bash
gcc -O3 -Wall -Wextra -std=c11 src/mandelbrot_serial.c -o bin/mandelbrot_serial -lm
nvcc -O3 -arch=sm_89 src/mandelbrot_cuda.cu -o bin/mandelbrot_cuda
gcc -O3 -Wall -Wextra -std=c11 scripts/compare_matrices.c -o bin/compare
```
*(Compilação concluída com zero warnings em todos os alvos).*

### 2.2. Caso Base (Seção 5.2 — Vista Completa: 4096×4096, `Re ∈ [-2.0, 1.0]`, `Im ∈ [-1.5, 1.5]`, `MAX_ITER = 1000`)
```bash
./bin/mandelbrot_serial
./bin/mandelbrot_cuda
./bin/compare output/serial_base.bin output/cuda_base.bin
```

### 2.3. Caso de Desbalanceamento Acentuado (Seção 5.3 — Vale dos Cavalos-Marinhos: centro `-0.743643887 + 0.131825904i`, largura `3.0e-3`, `MAX_ITER = 5000`)
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

./bin/compare output/serial_zoom.bin output/cuda_zoom.bin
```

### 2.4. Verificação de Memória com Valgrind (Versão Serial)
```bash
valgrind --leak-check=full --error-exitcode=1 \
  ./bin/mandelbrot_serial --width 256 --height 256 \
  --out-bin /tmp/test_valgrind.bin --out-pgm /tmp/test_valgrind.pgm
```
Resultado: `0 bytes in 0 blocks` em uso na saída (`All heap blocks were freed -- no leaks are possible`, `ERROR SUMMARY: 0 errors from 0 contexts`).

---

## 3. Resultados da Validação (`compare_matrices`)

### 3.1. Resumo Comparativo

| Cenário | Resolução | `MAX_ITER` | Total de Pixels | Pixels Divergentes | % Divergente | Maior Diferença | Veredito |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Caso Base (Seção 5.2)** | 4096 × 4096 | 1000 | 16.777.216 | **0** | **0,000000%** | **0** | **PASS** |
| **Caso Zoom / Seahorse (Seção 5.3)** | 4096 × 4096 | 5000 | 16.777.216 | **0** | **0,000000%** | **0** | **PASS** |

### 3.2. Saída Literal do Validador — Caso Base
```text
=== Relatorio de Validacao de Matrizes (Secao 5.5) ===
Arquivo referencia : output/serial_base.bin
Arquivo teste      : output/cuda_base.bin
Total de pixels    : 16777216
Pixels divergentes : 0
Percentual diverg. : 0.000000% (limite: 0.010000%)
Maior diferenca    : 0 iteracao(oes) (limite: 1)
Veredito           : PASS
```

### 3.3. Saída Literal do Validador — Caso de Desbalanceamento (Zoom Seahorse)
```text
=== Relatorio de Validacao de Matrizes (Secao 5.5) ===
Arquivo referencia : output/serial_zoom.bin
Arquivo teste      : output/cuda_zoom.bin
Total de pixels    : 16777216
Pixels divergentes : 0
Percentual diverg. : 0.000000% (limite: 0.010000%)
Maior diferenca    : 0 iteracao(oes) (limite: 1)
Veredito           : PASS
```

### 3.4. Tempos Observados na Validação Preliminar (Bloco 16×16)

- **Caso Base (4096×4096, `MAX_ITER = 1000`):**
  - Tempo Serial (CPU): `5,987262 s` (`5987,262 ms`)
  - Tempo do Kernel CUDA: `0,373778 s` (`373,778 ms`)
  - Tempo de Cópia D→H: `0,019661 s` (`19,661 ms`)
  - Tempo Total GPU (Kernel + D→H): `0,393439 s` (`393,439 ms`)
- **Caso de Desbalanceamento / Zoom (4096×4096, `MAX_ITER = 5000`):**
  - Tempo Serial (CPU): `3,758215 s` (`3758,215 ms`)
  - Tempo do Kernel CUDA: `0,312176 s` (`312,176 ms`)
  - Tempo de Cópia D→H: `0,019289 s` (`19,289 ms`)
  - Tempo Total GPU (Kernel + D→H): `0,331465 s` (`331,465 ms`)

---

## 4. Nota Técnica sobre Ponto Flutuante (`double`) e Igualdade Exata

Por padrão, o compilador `nvcc -O3` habilita a contração automática de multiplicação e adição em instruções *Fused Multiply-Add* (`fma.rn.f64` / `DFMA`), que realizam `a * b + c` com um único arredondamento IEEE-754, enquanto o `gcc -O3` em x86_64 (sem `-mfma`) emite instruções SSE2 separadas (`mulsd` seguida de `addsd`/`subsd`), realizando dois arredondamentos consecutivos.

Para garantir **igualdade exata bit a bit (0 pixels divergentes)** entre a referência serial em CPU e o kernel CUDA em GPU sem alterar as flags de otimização `-O3` do `Makefile`, o kernel `mandelbrot_kernel` utiliza os intrínsecos IEEE-754 de dupla precisão com arredondamento *round-to-nearest-even* do CUDA (`__dadd_rn`, `__dsub_rn`, `__dmul_rn`, `__ddiv_rn`). Isso instrui o montador PTX (`ptxas`) a preservar estritamente cada operação individual em `double` na mesma ordem algébrica da versão serial.
