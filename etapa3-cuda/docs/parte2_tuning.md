# Etapa 3 — Parte 2: Otimização / Tuning (Integrante 2)

## 1. Arquivos desta parte

| Arquivo | Função |
| :--- | :--- |
| `src/mandelbrot_bench.cu` | Harness único de benchmark + todas as variantes de kernel |
| `scripts/run_tuning.sh` | Varreduras (bloco/grade, variantes, `chunk`, modos de transferência) → `output/tuning/tuning.csv` |
| `scripts/plot_tuning.py` | CSV → tabelas Markdown e gráficos PNG |
| `scripts/profile.sh` | Profiling `nsys` / `ncu` (ocupação, divergência, banda) |
| `tests/cpu_emulation/` | Teste da **lógica** dos kernels em CPU (sem GPU), comparando com uma serial independente |

O kernel do Integrante 1 (`src/mandelbrot_cuda.cu`) **não foi alterado**; uma cópia fiel dele roda dentro do harness como variante `base`.

## 2. Compilar

### 2.1. Compilação
```bash
make clean && make all && make bench
```

Comandos invocados pelo `Makefile` (com o `ARCH` padrão):
```bash
nvcc -O3 -arch=sm_89 -lineinfo -Isrc src/mandelbrot_bench.cu -o bin/mandelbrot_bench
nvcc -O3 -arch=sm_89 -lineinfo -Isrc -DUSE_CONST_PARAMS src/mandelbrot_bench.cu -o bin/mandelbrot_bench_const
```
- `bin/mandelbrot_bench`: harness com todas as variantes (parâmetros do kernel como argumento).
- `bin/mandelbrot_bench_const`: o mesmo código com os parâmetros em `__constant__` (`-DUSE_CONST_PARAMS`), usado só na comparação do `run_tuning.sh`.
- `-Isrc` permite ao `nvcc` encontrar `common.h`; `-lineinfo` não altera o código gerado, só permite ao `ncu` mapear métricas para linhas do fonte.

### 2.2. Execução rápida de conferência (Seção 5.2 — Vista Completa: 4096×4096, `Re ∈ [-2.0, 1.0]`, `Im ∈ [-1.5, 1.5]`, `MAX_ITER = 1000`)
```bash
./bin/mandelbrot_serial                                    # gera output/serial_base.bin (o `make clean` apaga output/)
./bin/mandelbrot_bench --variant naive --out-bin output/bench_base.bin
./bin/compare output/serial_base.bin output/bench_base.bin
```
Além do `bin/compare` contra a serial, o próprio harness compara a saída com a do kernel `base` (linha `Verificacao` na saída).

## 3. Executar

```bash
./bin/mandelbrot_bench --variant naive --block 32x8 # uma configuração
./bin/mandelbrot_bench --width 4096 --height 4096 --preset seahorse \
        --variant compact --block 16x16 --chunk 64 --csv output/tuning/tuning.csv

QUICK=1 bash scripts/run_tuning.sh                  # testa o pipeline inteiro (1024x1024)
bash scripts/run_tuning.sh                          # completo (4096x4096)
python3 scripts/plot_tuning.py output/tuning/tuning.csv
bash scripts/profile.sh
```

Opções do harness: `--variant base|naive|warp|compact`, `--block BXxBY`, `--layout 2d|1d`, `--ctab`, `--mode sync|pinned|streams`, `--streams N`,
`--chunk K`, `--warmup N` (padrão 2), `--reps N` (padrão 7, mínimo 5), `--csv`, `--group`,
`--scenario`, `--no-verify`, e as de `common.h` (`--width`, `--height`, `--preset`, `--max-iter`, `--out-bin`, ...).
**`--preset seahorse` deve vir depois de `--width/--height`** (o preset usa a proporção da imagem).

## 4. Metodologia de medição (Seção 9)

- **Warm-up** (padrão 2 execuções, não medidas) + **≥ 5 repetições** medidas; reporta-se a **mediana** (e mín./máx.).
  O warm-up absorve a compilação JIT do PTX (relevante: o alvo é `sm_89` rodando numa GPU `sm_120`) e o 1º `cudaMemcpy`.
- O contexto CUDA é criado (`cudaFree(0)`) **antes** de qualquer medição.
- **Kernel:** `cudaEvent` (tempo de GPU, sem incluir o *launch* do host).
- **H→D** (tabelas de `c` / `__constant__`) e **D→H:** relógio de parede em torno de `cudaMemcpy` (bloqueante).
- **Total do pipeline:** relógio de parede de H→D + kernel + D→H. No modo `streams` kernel e D→H se sobrepõem,
  então só o total é comparável (as colunas separadas ficam `-1`).
- **Escrita em disco** (`.bin`/`.pgm`): **uma única vez**, depois das repetições, cronometrada à parte (`write_ms`).
  O harness só escreve se `--out-bin`/`--out-pgm` forem passados.

## 5. Variantes e hipóteses a testar

As hipóteses vêm de como a GPU funciona; **os números só existem depois de rodar `run_tuning.sh`**.

| Variante / opção | Ideia | O que esperar (a confirmar) |
| :--- | :--- | :--- |
| `base` | Kernel do Integrante 1 | Referência |
| `naive` | `__restrict__`, `zr²`/`zi²` em registrador | Pequeno ganho (menos multiplicações `double`); pode ser ≈ 0 se o compilador já fazia CSE |
| `naive --ctab` | `c` vindo de tabelas `cr[px]`, `ci[py]` calculadas no host | ≈ `naive`: `c` é calculado 1 vez por thread, desprezível frente a centenas/milhares de iterações; custa 2 cópias H→D |
| build `-DUSE_CONST_PARAMS` | Parâmetros em `__constant__` | ≈ `naive`: argumentos de kernel **já** ficam no banco de constantes |
| `--layout 1d` | Índice linear | Muda quais pixels formam um warp (1 linha × 32 colunas) → altera a divergência |
| `warp` | `__any_sync`: warp sai quando todos os lanes escapam | ≈ `naive`: o hardware já mascara lanes que saíram do laço; vale como medição |
| `compact` | Tile + compactação de pixels ativos | Ganha onde pixels lentos estão **espalhados** (Seahorse); perde onde quase nada escapa (overhead de barreiras por rodada) |

Early-exit no nível do **bloco** (`__syncthreads_or`) não foi implementado: faria warps rápidos esperarem o mais lento
do bloco, então só pode ser pior que o `warp`.

### Decisão sobre `c` (host × device)
Critério: ficar com a variante **mais simples** que não seja claramente mais lenta (mediana **e** intervalo mín.–máx.).
Se `naive`, `naive --ctab` e o build `__constant__` empatarem (como esperado), manter `c` no device é a escolha natural.

### Variante `compact`
Cada bloco é um *tile*. O trabalho é feito em **rodadas de `chunk` iterações**: cada thread avança seu pixel; quem
terminou grava `out[pix]`; os ainda ativos são **compactados** em memória compartilhada (`__ballot_sync` + `__popc` +
soma de contagens por warp) e as threads `0..total-1` assumem esses pixels. `chunk` pequeno compacta mais cedo mas paga mais
barreiras; `chunk` grande se aproxima do `naive`. Memória compartilhada dinâmica por bloco: `T·40 + 128` bytes.

### Streams
No modo `streams` a imagem é dividida em `N` faixas de linhas; cada faixa roda numa stream (kernel + `cudaMemcpyAsync`
D→H para memória *pinned*). O ganho máximo é limitado ao tempo de D→H (que costuma ser pequeno frente ao kernel em
`double`). Comparar `sync` × `pinned` × `streams` para separar o efeito da memória *pinned* do efeito da sobreposição.

## 6. Corretude e toolchain

- **Todas as variantes preservam a aritmética do baseline** (mesmos intrinsecos `_rn`, mesma ordem de operações) →
  saída **bit a bit idêntica**. O harness compara com o kernel `base` (`Verificacao vs base: identical`) e retorna código 3 se
  houver diferença. Necessário validar também com o `bin/compare` contra a serial:
  `./bin/mandelbrot_bench ... --out-bin output/bench.bin && ./bin/compare output/serial_base.bin output/bench.bin`.
- **Toolchain (atenção):** o README registra GPU `sm_120` (Blackwell), `nvcc 12.0`, `nsys 2022.4` e `ncu 2022.4`.
  O `nvcc 12.0` não gera código nativo para `sm_120` (roda por JIT do PTX `sm_89`, o que funciona, mas o 1º lançamento é
  lento). Ferramentas de profiling dessa época **tendem a não suportar GPUs Blackwell**; se `ncu`/`nsys` recusarem a GPU,
  instale um CUDA Toolkit mais recente (12.8+) e compile com `ARCH=sm_120`.

## 7. Resultados (saída de `plot_tuning.py`)

As tabelas ficam em `output/tuning/tuning_tables.md`. 
(a) varredura de bloco/grade; (b) naive × variantes × compactada; (c) efeito do `chunk`; (d) custo host-device;
(e) métricas do `ncu` (ocupação, `smsp__thread_inst_executed_per_inst_executed.ratio` = threads ativas por warp, banda DRAM).
