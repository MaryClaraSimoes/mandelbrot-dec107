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
├── Makefile        # Regras de compilação automatizada com gcc (-O3), execução e limpeza
├── README.md       # Documentação técnica e arquitetural do projeto
├── main.c          # Ponto de entrada, medição de tempo de alta precisão e orquestração
├── mandelbrot.c    # Implementação da alocação contígua, mapeamento complexo e rotina de cálculo
└── mandelbrot.h    # Definição de constantes globais, estrutura ImageBuffer e protótipos
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
| **Formatos de Saída** | Binário (`.bin`) / PGM | Matriz bruta de contagens de iterações e mapa visual em escala de cinza |

---

## Compilação e Execução

### Requisitos de Ambiente
- Compilador C em conformidade com o padrão C99 ou superior (`gcc`).
- Utilitário de compilação `make`.
- Sistema operacional compatível com padrões POSIX (com suporte a `<time.h>` e `clock_gettime`).

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
gcc -std=c99 -O3 -Wall -Wextra main.c mandelbrot.c -o mandelbrot
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

1. **Matriz Binária de Contagens (`.bin` / Raw Binary):**
   - Vetor unidimensional contíguo composto por elementos inteiros de 32 bits com sinal (`int32_t`), indexados estritamente na convenção *Row-Major* (`indice = y * width + x`).
   - Cada posição armazena o número exato de iterações necessárias para atingir o critério de escape ou o valor `MAX_ITER` caso o ponto pertença ao conjunto.
   - Otimizado para máxima largura de banda de I/O em disco, evitando a sobrecarga de serialização textual e facilitando a ingestão direta em scripts analíticos.

2. **Arquivo de Inspeção Visual (Netpbm - PGM/PPM):**
   - Formato gráfico simples sem compressão (*Portable Graymap* ou *Portable Pixmap*), permitindo inspeção visual imediata da geometria fractal por visualizadores nativos do sistema operacional.
   - Os valores inteiros de escape são mapeados para intensidades de luminosidade ou paletas de cores perceptualmente lineares.

---

## Validação de Corretude

Para certificar que as versões paralelas e otimizadas preservem a integridade numérica em relação à implementação serial de referência, aplica-se o seguinte protocolo de verificação:

- **Concordância Global:** Espera-se igualdade exata na quase totalidade dos pontos amostrados da matriz de contagens.
- **Tolerância de Fronteira:** Admite-se uma discrepância de no máximo **1 iteração** em até **0,01% dos pixels totais**, restrita estritamente às regiões limítrofes do fractal. Essa tolerância acomoda variações legítimas de arredondamento numérico decorrentes de fusão de operações (*Fused Multiply-Add* - FMA), vetorização SIMD, reordenação aritmética pelo compilador ou diferenças de precisão em unidades de execução de ponto flutuante em GPUs.

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
