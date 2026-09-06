# Benchmark de Geração do Conjunto de Mandelbrot (Escape-Time)

**Disciplina:** DEC107 — Processamento Paralelo  
**Desenvolvedores:**
- Breno Arouca Nascimento
- Emyle Santana da Silva
- Maria Clara Simões de Jesus

---

## Descrição Geral

Este projeto consiste na implementação, otimização e análise de desempenho computacional da geração do Conjunto de Mandelbrot utilizando o algoritmo de *escape-time* em linguagem C. O cálculo desse fractal apresenta uma propriedade central para investigações em High-Performance Computing (HPC): o **desbalanceamento intrínseco de carga**.

Pontos localizados no interior do conjunto convergem lentamente, demandando invariavelmente o número máximo de iterações (`MAX_ITER`). Em contrapartida, pontos exteriores divergem rapidamente em poucas iterações. Essa assimetria espacial no custo computacional por pixel torna o problema um caso de estudo representativo para avaliação de diferentes modelos de programação paralela e estratégias de particionamento e escalonamento de tarefas.

---

## Estrutura do Repositório

```text
.
├── Makefile        # Regras de compilação (gcc -O3), execução, validação e limpeza
├── README.md       # Documentação técnica e arquitetural do projeto
├── main.c          # Ponto de entrada, medição de tempo e orquestração de I/O
├── mandelbrot.c    # Alocação contígua, mapeamento complexo e rotina de cálculo serial
├── mandelbrot.h    # Constantes globais, estrutura ImageBuffer e protótipos
├── io_utils.c      # Exportação PGM/PPM e matriz binária int32 (row-major)
├── io_utils.h      # Interface do módulo de Entrada/Saída
└── validate.py     # Comparação pixel a pixel entre matrizes binárias
```

---

## Especificações Técnicas e Parâmetros

A tabela a seguir consolida os parâmetros adotados para o caso base de referência:

| Parâmetro | Configuração Base | Descrição Técnica |
| :--- | :--- | :--- |
| **Resolução da Grade** | 4096 x 4096 pixels | Discretização bidimensional do espaço amostrado (16.777.216 pixels) |
| **Região Real (Re)** | `[-2.0, 1.0]` | Intervalo do eixo real no plano complexo |
| **Região Imaginária (Im)** | `[-1.5, 1.5]` | Intervalo do eixo imaginário no plano complexo |
| **Limite de Iterações** | 1000 (`MAX_ITER`) | Critério de corte temporal para pontos não divergentes |
| **Critério de Escape** | $\|z\|^2 > 4.0$ | Limite euclidiano de divergência em dupla precisão |
| **Aritmética** | Ponto flutuante duplo | Precisão de 64 bits (`double`, padrão IEEE 754) |
| **Representação em Memória** | `int32_t` contíguo | Vetor unidimensional organizado em ordem estrita *Row-Major* (64 MB) |
| **Temporização** | `CLOCK_MONOTONIC` | Resolução em nanossegundos isolando a fase de cálculo das rotinas de I/O |
| **Formatos de Saída** | Binário (`.bin`) / PGM / PPM | Matriz bruta de contagens e mapas visuais em escala de cinza e RGB |

---

## Compilação e Execução

### Requisitos de Ambiente
- Compilador C em conformidade com o padrão C99 ou superior (`gcc`).
- Utilitário de compilação `make`.
- Sistema operacional compatível com padrões POSIX (com suporte a `<time.h>` e `clock_gettime`).
- Interpretador Python 3 (apenas a biblioteca padrão) para o validador de corretude.

### Instruções de Compilação

O projeto conta com um `Makefile` configurado para aplicar otimizações agressivas via `-O3` e habilitar avisos rigorosos do compilador (`-Wall -Wextra`):

```bash
make
```

Para remover os artefatos compilados e realizar uma compilação limpa:

```bash
make clean && make
```

Caso seja necessário compilar manualmente sem o auxílio do `make`:

```bash
gcc -std=c99 -O3 -Wall -Wextra main.c mandelbrot.c io_utils.c -o mandelbrot -lm
```

### Instruções de Execução

A execução do binário pode ser realizada diretamente via terminal:

```bash
./mandelbrot
```

Ou através do alvo configurado no `Makefile`:

```bash
make run
```

---

## Formato dos Dados de Saída

O pipeline do projeto contempla duas representações distintas para os dados processados:

A versão serial grava três artefatos (fora da medição de tempo): `mandelbrot_serial.bin`, `mandelbrot_serial.pgm` e `mandelbrot_serial.ppm`.

1. **Matriz Binária de Contagens (`.bin` / Raw Binary):**
   - Vetor unidimensional contíguo composto por elementos inteiros de 32 bits com sinal (`int32_t`), indexados estritamente na convenção *Row-Major* (`indice = y * width + x`), sem cabeçalho.
   - Cada posição armazena o número exato de iterações necessárias para atingir o critério de escape ou o valor `MAX_ITER` caso o ponto pertença ao conjunto.
   - Tamanho do arquivo: `WIDTH * HEIGHT * 4` bytes (64 MiB no caso base 4096×4096).
   - Referência canônica para o validador `validate.py`.

2. **Arquivo de Inspeção Visual (Netpbm - PGM/PPM):**
   - PGM P5 (escala de cinza) e PPM P6 (RGB com paleta HSV cíclica), sem compressão, para conferência visual da geometria fractal.
   - Pixels no interior do conjunto (`MAX_ITER`) são mapeados para preto; os demais recebem intensidade/cor proporcional ao número de iterações.

---

## Validação de Corretude

Para certificar que as versões paralelas e otimizadas preservem a integridade numérica em relação à implementação serial de referência, aplica-se o seguinte protocolo de verificação:

- **Concordância Global:** Espera-se igualdade exata na quase totalidade dos pontos amostrados da matriz de contagens.
- **Tolerância de Fronteira:** Admite-se uma discrepância de no máximo **1 iteração** em até **0,01% dos pixels totais**, restrita estritamente às regiões limítrofes do fractal. Essa tolerância acomoda variações legítimas de arredondamento numérico decorrentes de fusão de operações (*Fused Multiply-Add* - FMA), vetorização SIMD, reordenação aritmética pelo compilador ou diferenças de precisão em unidades de execução de ponto flutuante em GPUs.

O script `validate.py` lê duas matrizes `.bin` (int32, row-major, sem cabeçalho) e aplica esses critérios. Código de saída: `0` se aprovado, `1` se reprovado, `2` em erro de leitura.

```bash
# Após gerar mandelbrot_serial.bin (make run) e a saída da versão paralela:
python3 validate.py mandelbrot_serial.bin mandelbrot_omp.bin

# Dimensões customizadas, modo verboso e tolerância explícita:
python3 validate.py mandelbrot_serial.bin mandelbrot_cuda.bin --width 4096 --height 4096 --verbose

# Sanidade: comparar a referência serial consigo mesma
make validate
```

---

## Próximas Etapas (Roadmap do Projeto)

O cronograma do projeto está organizado em três fases de evolução arquitetural:

- **Etapa 1: Versão Serial e Paralelismo em Memória Compartilhada (OpenMP)**
  - Conclusão da rotina de cálculo serial de referência.
  - Implementação de laços paralelos OpenMP, investigando políticas de escalonamento estático (`schedule(static)`) e dinâmico (`schedule(dynamic)` ou `guided`) para compensar a distribuição irregular de carga.
- **Etapa 2: Paralelismo em Memória Distribuída (MPI)**
  - Decomposição de domínio bidimensional e balanceamento de carga entre múltiplos nós de computação independentes.
  - Avaliação de estratégias de divisão estática por faixas de linhas contra arquiteturas dinâmicas mestre-trabalhador (*master-worker*).
- **Etapa 3: Paralelismo Massivo em GPU (CUDA)**
  - Implementação de *kernels* dedicados para execução massivamente paralela em arquiteturas many-core NVIDIA.
  - Otimização do padrão de coalescência na memória global, ajuste na volumetria de blocos/threads e minimização dos tempos de transferência de memória entre *host* e *device*.
