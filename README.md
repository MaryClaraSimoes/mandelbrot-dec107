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
├── common/                    # Código compartilhado entre as versões serial e OpenMP
│   ├── common.c               # Buffer, mapeamento, temporização e parser da CLI
│   ├── io_utils.c             # Exportação PGM/PPM e matriz binária int32 (row-major)
│   ├── io_utils.h             # Interface do módulo de Entrada/Saída
│   └── mandelbrot.h           # Constantes globais, ImageBuffer, MandelbrotParams, LoadBalanceStats
├── openmp/                    # Versão paralela do cálculo do Mandelbrot
│   ├── main.c                 # Ponto de entrada OpenMP: CLI, I/O, tempo de parede e fator de carga
│   ├── Makefile               # Regras de build específicas da versão OpenMP (gcc -O3 -fopenmp)
│   └── mandelbrot_compute.c   # Cálculo paralelizado (schedule(runtime)) e tempo por thread
├── serial/                    # Versão sequencial do cálculo do Mandelbrot
│   ├── main.c                 # Ponto de entrada da versão serial
│   ├── Makefile               # Regras de build específicas da versão serial (gcc -O3)
│   └── mandelbrot_compute.c   # Rotina de cálculo serial (loop simples, sem paralelismo)
├── .gitignore                 # Arquivos/pastas ignorados pelo Git (binários, *.o, saídas)
├── Makefile                   # Makefile raiz: orquestra build das duas versões + testes + limpeza
├── README.md                  # Documentação técnica e arquitetural do projeto
└── validate.py                # Comparação pixel a pixel entre matrizes binárias (serial vs OpenMP)

```

### Organização Modular e Reaproveitamento de Código

A estrutura em diretórios distingue explicitamente os componentes invariantes do projeto daqueles cuja implementação é específica de cada paradigma de execução.

#### Componentes Comuns (`common/`)

Residem em `common/` os módulos cujo comportamento independe do modelo de paralelismo adotado, compilados e ligados a ambos os executáveis a partir de uma única cópia física dos arquivos:

| Arquivo | Componentes | Responsabilidade |
| :--- | :--- | :--- |
| `mandelbrot.h` | Macros do caso base e do seahorse, `ImageBuffer`, `MandelbrotParams`, `LoadBalanceStats`, protótipos | Contrato compartilhado: defaults oficiais, parâmetros por execução e estatísticas de carga |
| `common.c` | `create_image_buffer()`, `free_image_buffer()` | Alocação e liberação do buffer contíguo de `int32_t` |
| `common.c` | `mandelbrot_params_init_default()`, `mandelbrot_params_parse_args()` | Defaults do caso base e CLI (`--width`, `--preset`, domínio, `MAX_ITER`) |
| `common.c` | `pixel_to_complex()` | Mapeamento linear `(px, py)` → `(cr, ci)` a partir de `MandelbrotParams` |
| `common.c` | `get_wtime()` | Temporização monotônica via `CLOCK_MONOTONIC` (serial e I/O) |
| `io_utils.c` / `io_utils.h` | `export_binary()`, `export_pgm()`, `export_ppm()`, `load_binary()` | Serialização da matriz; PGM/PPM usam `max_iter` da execução |

A centralização desses módulos garante que as constantes de domínio, o mapeamento de coordenadas e o formato de serialização sejam rigorosamente idênticos entre as versões, condição necessária para que a comparação de corretude descrita adiante seja válida, uma vez que elimina divergências originadas fora da rotina de cálculo.

#### Componentes Específicos (`serial/` e `openmp/`)

Cada diretório de implementação contém dois arquivos próprios, cujas diferenças estão delimitadas a seguir:

**`mandelbrot_compute.c` — rotina de cálculo**

| Aspecto | `serial/` | `openmp/` |
| :--- | :--- | :--- |
| Diretiva de paralelização | Ausente | `#pragma omp parallel` + `#pragma omp for schedule(runtime) nowait` sobre o laço `py` |
| Instrumentação de carga | Ignora `LoadBalanceStats` (`NULL`) | Tempo de trabalho por thread; fator `t_max / t_mean` |
| Inclusão de cabeçalhos | Apenas `mandelbrot.h` | `mandelbrot.h` e, condicionalmente, `<omp.h>` sob `#ifdef _OPENMP` |
| Corpo do laço, aritmética e ordem *row-major* | Idênticos entre as duas versões | Idênticos entre as duas versões |

**`main.c` — ponto de entrada**

| Aspecto | `serial/` | `openmp/` |
| :--- | :--- | :--- |
| Parâmetros | CLI compartilhada; sem flags usa o caso base (4096×4096, vista completa) | Idêntica |
| Função de temporização | `get_wtime()` (`CLOCK_MONOTONIC`) | `omp_get_wtime()`, com fallback para `get_wtime()` sob `#ifndef _OPENMP` |
| Diagnóstico de ambiente | Não aplicável | Reporta `omp_get_max_threads()` e emite alerta caso `_OPENMP` não esteja definida |
| Fator de balanceamento | Não imprime | Imprime min/médio/máximo por thread e a linha `BALANCE ...` |
| Prefixo dos artefatos de saída | `mandelbrot_serial.*` | `mandelbrot_omp.*` |
| Sequência de operações | Parse da CLI → alocação → cálculo cronometrado → exportação → liberação | Idêntica |

**`Makefile` — regras de construção**

| Aspecto | `serial/` | `openmp/` |
| :--- | :--- | :--- |
| Flags de compilação e linkagem | `-std=c99 -O3 -Wall -Wextra` | Acrescenta `-fopenmp` em ambas as etapas |
| Executável gerado | `mandelbrot_seq` | `mandelbrot_omp` |
| Alvos de execução | `run` | `run`, `run-static`, `run-dynamic`, `run-guided` |
| Localização dos fontes comuns | `vpath %.c ../common` | `vpath %.c ../common` |

Essa delimitação assegura que o algoritmo de escape-time seja expresso uma única vez em termos semânticos: as versões diferem quanto à distribuição do trabalho entre unidades de execução e quanto à instrumentação de medição, mas não quanto à definição do que é computado para cada pixel.

---

## Arquitetura da Paralelização (OpenMP)

### Estratégia de Decomposição

A paralelização é aplicada sobre o **laço externo** (`py`), de modo que cada thread processa linhas inteiras da imagem. O laço interno (`px`) permanece serial dentro de cada thread, preservando a localidade espacial de acesso à memória: como o buffer é contíguo em ordem *row-major*, o percurso de uma linha completa maximiza o aproveitamento das linhas de cache carregadas.

```c
#pragma omp parallel
{
    /* t0 = omp_get_wtime(); */
    #pragma omp for schedule(runtime) nowait
    for (int py = 0; py < img->height; py++) {
        for (int px = 0; px < img->width; px++) {
            /* ... cálculo escape-time do pixel (px, py) ... */
        }
    }
    /* t1 = omp_get_wtime();  grava tempo desta thread */
}
```

O `nowait` no `for` evita que o tempo por thread inclua a espera na barreira: cada thread registra `t1 - t0` ao terminar as próprias linhas. Sem isso, todos os tempos coincidiriam com o da thread mais lenta e o fator de carga ficaria artificialmente 1.

### Gerenciamento de Escopo das Variáveis

As variáveis de estado da recorrência (`zr`, `zi`, `cr`, `ci`, `iter`) são declaradas **no interior do corpo do laço**, e não em escopo externo. Essa decisão é deliberada: variáveis declaradas dentro do bloco paralelo são automaticamente privadas a cada iteração pela semântica do OpenMP, dispensando a cláusula `private()` explícita e eliminando por construção qualquer possibilidade de condição de corrida sobre o estado da iteração.

### Ausência de Região Crítica

A escrita em `img->data[py * width + px]` dispensa qualquer primitiva de sincronização (`critical`, `atomic` ou bloqueios explícitos). Cada iteração do espaço de índices escreve em uma posição unicamente determinada por `(px, py)`, de forma que não existe sobreposição de endereços entre threads distintas. O problema é, nesse aspecto, *embaraçosamente paralelo*: não há dependência de dados nem redução a ser coordenada.

### Justificativa do `schedule(runtime)`

A adoção de `schedule(runtime)`, em detrimento da fixação de uma política específica em tempo de compilação, atende diretamente ao objetivo experimental da Etapa 1. O desbalanceamento intrínseco de carga implica que linhas atravessando regiões de fronteira do fractal demandam substancialmente mais tempo que linhas situadas em regiões de escape rápido.

Com `schedule(runtime)`, a totalidade dessas configurações é avaliável a partir de um **único binário**, mediante variação exclusiva da variável de ambiente `OMP_SCHEDULE`, garantindo que as medições comparativas não sejam contaminadas por diferenças de compilação entre execuções.

### Fator de Balanceamento de Carga

A versão OpenMP mede o tempo de **trabalho** de cada thread e resume:

- `t_min`, `t_mean`, `t_max`
- **fator** = `t_max / t_mean` (1,0 = carga uniforme; valores maiores = desbalanceamento)

A linha parseável `BALANCE nthreads=... factor=...` destina-se ao registro no relatório da Etapa 1. A serial não calcula essa métrica.

---

## Especificações Técnicas e Parâmetros

A tabela a seguir consolida os parâmetros do caso base (vista completa). Sem argumentos na CLI, estes são os valores usados:

| Parâmetro | Configuração Base | Descrição Técnica |
| :--- | :--- | :--- |
| **Resolução da Grade** | 4096 x 4096 pixels | Discretização bidimensional do espaço amostrado (16.777.216 pixels) |
| **Região Real (Re)** | `[-2.0, 1.0]` | Intervalo do eixo real no plano complexo |
| **Região Imaginária (Im)** | `[-1.5, 1.5]` | Intervalo do eixo imaginário no plano complexo |
| **Limite de Iterações** | 1000 (`MAX_ITER`) | Critério de corte temporal para pontos não divergentes |
| **Critério de Escape** | $\|z\|^2 > 4.0$ | Limite euclidiano de divergência em dupla precisão |
| **Aritmética** | Ponto flutuante duplo | Precisão de 64 bits (`double`, padrão IEEE 754) |
| **Representação em Memória** | `int32_t` contíguo | Vetor unidimensional organizado em ordem estrita *Row-Major* (64 MB) |
| **Temporização (serial)** | `CLOCK_MONOTONIC` | Resolução em nanossegundos isolando a fase de cálculo das rotinas de I/O |
| **Temporização (OpenMP)** | `omp_get_wtime()` | Relógio de parede da especificação OpenMP, portátil entre implementações e monotônico por definição |
| **Formatos de Saída** | Binário (`.bin`) / PGM / PPM | Matriz bruta de contagens e mapas visuais em escala de cinza e RGB |

O caso de desbalanceamento acentuado é o preset `--preset seahorse`: centro `(−0,743643887, 0,131825904)`, largura real `3,0×10⁻³` (eixo imaginário com a mesma extensão) e `MAX_ITER = 5000`. A resolução permanece 4096×4096, salvo `--width` / `--height`.

---

## Compilação e Execução

### Requisitos de Ambiente
- Compilador C em conformidade com o padrão C99 ou superior (`gcc`).
- Utilitário de compilação `make`.
- Sistema operacional compatível com padrões POSIX (com suporte a `<time.h>` e `clock_gettime`).
- Suporte a **OpenMP 3.0 ou superior** (`-fopenmp`), necessário apenas para a versão paralela. O GCC oferece suporte nativo; não requer instalação de bibliotecas adicionais.
- Interpretador Python 3 (apenas a biblioteca padrão) para o validador de corretude.

### Instruções de Compilação

O projeto adota um esquema de compilação hierárquico composto por três `Makefile`s: um na raiz, responsável pela orquestração, e um em cada diretório de implementação (`serial/` e `openmp/`), responsável pelas regras específicas daquele paradigma. Todos aplicam otimizações agressivas via `-O3` e habilitam avisos rigorosos do compilador (`-Wall -Wextra`).

Os módulos compartilhados (`common/common.c` e `common/io_utils.c`) **não são duplicados fisicamente**: cada `Makefile` de implementação os localiza via diretiva `vpath` apontando para `../common`, de modo que uma correção nesses arquivos se propaga automaticamente para ambas as versões.

#### Compilação de Ambas as Versões

A partir do diretório raiz, o alvo padrão delega a construção para os dois subdiretórios:

```bash
make
```

Para remover todos os artefatos compilados (objetos, binários e saídas geradas) e realizar uma compilação limpa:

```bash
make clean && make
```

#### Compilação Individual — Versão Serial

```bash
cd serial
make
```

Gera o executável `serial/mandelbrot_seq`. Flags aplicadas:

```
gcc -std=c99 -O3 -Wall -Wextra -I../common
```

#### Compilação Individual — Versão OpenMP

```bash
cd openmp
make
```

Gera o executável `openmp/mandelbrot_omp`. Flags aplicadas:

```
gcc -std=c99 -O3 -Wall -Wextra -fopenmp -I../common
```

> **Atenção:** a flag `-fopenmp` é obrigatória tanto na etapa de compilação quanto na de *linkagem*. Na sua ausência, o compilador **ignora silenciosamente** as diretivas `#pragma omp`, o binário compila e executa normalmente, porém de forma estritamente sequencial, sem emitir erro ou aviso. Por essa razão, `main.c` da versão paralela emite em tempo de execução um alerta explícito caso a macro `_OPENMP` não esteja definida.

#### Compilação Manual (sem `make`)

Caso seja necessário compilar sem o auxílio do `make`, a partir do diretório raiz do projeto:

```bash
# Versão serial
gcc -std=c99 -O3 -Wall -Wextra -Icommon \
    serial/main.c serial/mandelbrot_compute.c \
    common/common.c common/io_utils.c \
    -o mandelbrot_seq -lm

# Versão OpenMP
gcc -std=c99 -O3 -Wall -Wextra -fopenmp -Icommon \
    openmp/main.c openmp/mandelbrot_compute.c \
    common/common.c common/io_utils.c \
    -o mandelbrot_omp -lm
```


### Instruções de Execução

Resolução, domínio e `MAX_ITER` são definidos em `MandelbrotParams` e podem ser alterados na linha de comando. Sem flags, o comportamento é o caso base (`make validate` permanece válido).

| Flag | Padrão | Função |
| :--- | :--- | :--- |
| `--width` / `--height` | 4096 | Resolução em pixels |
| `--max-iter` | 1000 | Teto de iterações |
| `--re-min` / `--re-max` | −2,0 / 1,0 | Intervalo do eixo real |
| `--im-min` / `--im-max` | −1,5 / 1,5 | Intervalo do eixo imaginário |
| `--preset full` | (implícito) | Restaura domínio e `MAX_ITER` da vista completa |
| `--preset seahorse` | — | Zoom no vale dos cavalos-marinhos e `MAX_ITER = 5000` |
| `-h` / `--help` | — | Ajuda e encerra |

Flags posteriores sobrescrevem as anteriores (`--preset seahorse --width 256` gera o zoom em 256×256).

```bash
./serial/mandelbrot_seq --help
./serial/mandelbrot_seq --width 256 --height 256 --max-iter 200
./openmp/mandelbrot_omp --preset seahorse
```

#### Versão Serial

A execução do binário pode ser realizada diretamente via terminal:

```bash
cd serial
./mandelbrot_seq
```

Ou através do alvo configurado no `Makefile`:

```bash
make run              # a partir de serial/
make run-serial       # a partir da raiz
```

#### Versão OpenMP

```bash
cd openmp
./mandelbrot_omp
```

Ou pelos alvos do `Makefile`:

```bash
make run              # a partir de openmp/
make run-openmp       # a partir da raiz
```

#### Configuração do Escalonamento e do Grau de Paralelismo

A rotina paralela emprega a cláusula `schedule(runtime)`, o que significa que **a política de escalonamento e o tamanho do bloco (*chunk*) não são fixados em tempo de compilação**. Ambos são resolvidos no instante em que o laço paralelo inicia a execução, a partir da variável de ambiente `OMP_SCHEDULE`. Essa decisão arquitetural permite conduzir toda a bateria experimental de comparação entre políticas **sem exigir recompilação** a cada configuração testada.

| Variável de Ambiente | Função | Exemplos de Valores |
| :--- | :--- | :--- |
| `OMP_SCHEDULE` | Define a política de escalonamento e o *chunk size* | `static`, `static,8`, `dynamic,16`, `guided,4`, `auto` |
| `OMP_NUM_THREADS` | Define o número de threads do time paralelo | `1`, `2`, `4`, `8`, `16` |

Exemplos de execução parametrizada:

```bash
cd openmp

# Escalonamento estático com particionamento padrão
OMP_SCHEDULE="static" ./mandelbrot_omp

# Escalonamento dinâmico, blocos de 16 linhas
OMP_SCHEDULE="dynamic,16" ./mandelbrot_omp

# Escalonamento guiado, bloco mínimo de 4 linhas, restrito a 8 threads
OMP_SCHEDULE="guided,4" OMP_NUM_THREADS=8 ./mandelbrot_omp

# Execução sequencial de controle (linha de base para cálculo de Speedup)
OMP_NUM_THREADS=1 ./mandelbrot_omp

# Caso seahorse (desbalanceamento acentuado) com 8 threads e schedule dinâmico
OMP_NUM_THREADS=8 OMP_SCHEDULE="dynamic,16" ./mandelbrot_omp --preset seahorse
```

O `Makefile` da versão paralela disponibiliza ainda alvos de conveniência que encapsulam as três políticas de interesse principal:

```bash
make run-static       # OMP_SCHEDULE="static"
make run-dynamic      # OMP_SCHEDULE="dynamic,16"
make run-guided       # OMP_SCHEDULE="guided,16"
```

---

## Formato dos Dados de Saída

O pipeline do projeto contempla duas representações distintas para os dados processados:

A versão serial grava três artefatos (fora da medição de tempo): `mandelbrot_serial.bin`, `mandelbrot_serial.pgm` e `mandelbrot_serial.ppm`.

A versão OpenMP grava os três artefatos equivalentes, sob o prefixo `mandelbrot_omp` (`mandelbrot_omp.bin`, `mandelbrot_omp.pgm` e `mandelbrot_omp.ppm`), também fora da janela de medição de tempo. A nomenclatura distinta previne sobrescrita acidental da referência canônica serial e permite que ambas as saídas coexistam para fins de comparação direta. Cada versão grava seus artefatos no respectivo diretório de origem (`serial/` e `openmp/`).

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
# Fluxo completo a partir da raiz: compila, executa ambas as versões e compara
make validate

# Comparação manual, após gerar as duas saídas:
python3 validate.py serial/mandelbrot_serial.bin openmp/mandelbrot_omp.bin

# Dimensões customizadas, modo verboso e tolerância explícita:
python3 validate.py serial/mandelbrot_serial.bin openmp/mandelbrot_omp.bin --width 4096 --height 4096 --verbose
```

---

## Próximas Etapas (Roadmap do Projeto)

O cronograma do projeto está organizado em três fases de evolução arquitetural:

- **Etapa 1: Versão Serial e Paralelismo em Memória Compartilhada (OpenMP)**
  - Rotina serial de referência, OpenMP com `schedule(runtime)`, CLI, preset seahorse e fator de balanceamento de carga.
  - Experimentos e relatório técnico da etapa (tempos, Speedup, Eficiência, carga) ainda a registrar.
- **Etapa 2: Paralelismo em Memória Distribuída (MPI)**
  - Decomposição de domínio bidimensional e balanceamento de carga entre múltiplos nós de computação independentes.
  - Avaliação de estratégias de divisão estática por faixas de linhas contra arquiteturas dinâmicas mestre-trabalhador (*master-worker*).
- **Etapa 3: Paralelismo Massivo em GPU (CUDA)**
  - Implementação de *kernels* dedicados para execução massivamente paralela em arquiteturas many-core NVIDIA.
  - Otimização do padrão de coalescência na memória global, ajuste na volumetria de blocos/threads e minimização dos tempos de transferência de memória entre *host* e *device*.
