# Relatório de Modificações — Etapa 1 (OpenMP)

## 1. Identificação

- **Projeto:** Benchmark de Geração do Conjunto de Mandelbrot por *Escape-Time*
- **Disciplina:** DEC107 — Processamento Paralelo (2026/2)
- **Etapa:** Etapa 1 — Versão Sequencial e Paralelização em Memória Compartilhada (OpenMP)
- **Data:** 16 de setembro de 2026
- **Autores:** Breno Arouca Nascimento, Emyle Santana da Silva, Maria Clara Simões de Jesus
- **Documento de Referência:** `DEC107_2026-2_Enunciado_Mandelbrot.pdf`

---

## 2. Resumo Executivo

Este documento consolida o registro técnico e a rastreabilidade integral de todas as modificações introduzidas na base de código do projeto para o cumprimento rigoroso dos requisitos estipulados no enunciado da Etapa 1.

As intervenções tiveram como princípios basilares:
1. **Preservação da semântica aritmética:** Nenhuma alteração foi realizada na lógica matemática da recorrência (zₙ₊₁ = zₙ² + c, critério |z|² > 4.0, aritmética em ponto flutuante de dupla precisão `double`).
2. **Parametrização dinâmica sem recompilação:** Eliminação de limites rígidos em macros de cabeçalho, permitindo a transição em tempo de execução entre o Input Padrão, o caso de estresse do *Seahorse Valley* e grades de alta resolução (8192² e 16384²).
3. **Separação estrita de tempos (Seção 9):** Isolamento da medição do tempo de computação pura (`tempo_geracao_s`) em relação ao tempo de I/O em disco (`tempo_io_s`).
4. **Instrumentação precisa do balanceamento (λ):** Uso de temporização por thread (`thread_times[tid]`) desacoplada por cláusula `nowait` no OpenMP.
5. **Regra de Ouro da separação conceitual:** A versão serial permaneceu puramente sequencial (sem estruturas ou conceitos de concorrência), enquanto a versão OpenMP incorporou os recursos de paralelismo, escalonamento e balanceamento.

### Tabela-Resumo das Modificações

| # | Modificação | Versão | Arquivo(s) | Requisito do PDF |
| :-: | :--- | :---: | :--- | :--- |
| **4.1** | Parametrização dinâmica de domínio e iterações no `ImageBuffer` | Ambas | `common/mandelbrot.h`, `common/common.c` | Seções 5.2 e 5.3 |
| **4.2** | Generalização da rotina sequencial para domínios dinâmicos | Serial | `serial/mandelbrot_compute.c` | Seções 5.2, 5.3 e 5.5 |
| **4.3** | Interface de execução, separação de I/O e saída parseável no Serial | Serial | `serial/main.c` | Seções 5.2, 5.3 e 9 |
| **4.4** | Instrumentação de tempo por thread com `nowait` e cálculo de λ | OpenMP | `openmp/mandelbrot_compute.c` | Seção 9 |
| **4.5** | Interface de execução, metadados e separação de I/O no OpenMP | OpenMP | `openmp/main.c` | Seções 5.2, 5.3, 7.1 e 9 |
| **4.6** | Suporte a `max_iter` dinâmico na exportação visual PGM/PPM | Ambas | `common/io_utils.c` | Seções 5.3 e 5.4 |
| **4.7** | Suíte de automação experimental dos 4 blocos e geração de CSV | Ambas | `scripts/run_experiments.sh` | Seções 7.1, 5.3 e 9 |
| **4.8** | Processamento analítico, ajuste de Amdahl/Gustafson e geração de gráficos | Ambas | `scripts/generate_plots_and_tables.py` | Seções 9 e 11 |

---

## 3. Estado Anterior (Baseline)

Antes das modificações registradas neste relatório, o repositório já dispunha de uma infraestrutura funcional básica com os seguintes componentes:
- Versão serial sequencial básica e versão OpenMP com `#pragma omp parallel for schedule(runtime)` sobre o laço externo `py`.
- Temporização monotônica isolada do cálculo (`CLOCK_MONOTONIC` no serial e `omp_get_wtime()` no OpenMP).
- Exportação da matriz binária `.bin` em `int32_t` *Row-Major* e imagens Netpbm `.pgm` e `.ppm`.
- Validador de corretude em Python (`validate.py`), que atestava concordância de 100% no caso base.

### O que já estava correto e foi mantido inalterado
- **Aritmética fractal:** O núcleo iterativo do cálculo em ponto flutuante duplo `double`.
- **Formato canônico binário:** A convenção *Row-Major* contígua em `int32_t` sem cabeçalho no arquivo `.bin`.
- **Script validador (`validate.py`):** Mantido intacto, servindo como juiz neutro e imparcial para validação de todos os cenários.
- **Estrutura hierárquica de compilação:** Os `Makefile`s permaneceram aplicando `-O3 -Wall -Wextra` com busca de fontes comuns via `vpath`.

---

## 4. Modificações Detalhadas

### 4.1 — Parametrização Dinâmica de Domínio e Iterações no `ImageBuffer`
- **Versão afetada:** Ambas (código compartilhado em `common/`).
- **Arquivo(s):** [`common/mandelbrot.h`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/mandelbrot.h) e [`common/common.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/common.c).
- **Trecho:** `struct ImageBuffer` (linhas 28–37 de `mandelbrot.h`), `configure_scenario()` (linhas 56–89 de `common.c`) e `pixel_to_complex()` (linhas 91–103 de `common.c`).
- **O que foi alterado:**
  - *Antes:* A `struct ImageBuffer` armazenava apenas `width`, `height` e `data`. As constantes de domínio (`RE_MIN`, `RE_MAX`, `IM_MIN`, `IM_MAX`) e o limite `MAX_ITER` eram macros fixas em tempo de compilação.
  - *Depois:* `ImageBuffer` incorporou os campos `int max_iter`, `double re_min`, `re_max`, `im_min`, `im_max`. Criou-se a função `configure_scenario(ImageBuffer *img, const char *scenario_name)`, que inicializa automaticamente os intervalos do Input Padrão ou calcula a janela matemática do *Seahorse Valley* (centro -0.743643887, 0.131825904, largura 0,003, `max_iter = 5000`). `pixel_to_complex()` passou a ler os limites contidos no buffer.
- **Finalidade:** Permitir a alternância dinâmica entre cenários de teste e resoluções em tempo de execução sem exigir edição de código nem recompilação do binário.
- **Requisito do PDF:** Seção 5.2 (Input padrão) e Seção 5.3 (Casos de estresse: Seahorse e resoluções para weak scaling).
- **Impacto:** Flexibilidade operacional total para scripts de benchmark e eliminação de erros humanos em recompilações manuais.
- **Validação:** Verificação dos cantos (c_r, c_i) calculados no vértice (0,0) e (W-1, H-1) para o caso padrão e Seahorse; assertiva com 100% de exatidão matemática.
- **Observações:** As macros antigas (`DEFAULT_WIDTH`, `DEFAULT_MAX_ITER`, etc.) foram preservadas com aliases para compatibilidade com código legado.

---

### 4.2 — Generalização da Rotina Sequencial para Domínios Dinâmicos
- **Versão afetada:** Versão Serial.
- **Arquivo(s):** [`serial/mandelbrot_compute.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/serial/mandelbrot_compute.c).
- **Trecho:** Função `compute_mandelbrot()` (linhas 10–33).
- **O que foi alterado:**
  - *Antes:* O laço `while` utilizava a macro global `MAX_ITER` fixa em 1000 e chamava `pixel_to_complex(px, py, img->width, img->height, &cr, &ci)`.
  - *Depois:* A função consome `max_iter = img->max_iter` e invoca `pixel_to_complex(px, py, img, &cr, &ci)`.
- **Finalidade:** Permitir que o executável sequencial processe qualquer número de iterações e qualquer região do plano complexo configurada no buffer.
- **Requisito do PDF:** Seções 5.2, 5.3 e 5.5 (Geração do baseline canônico de validação em todos os cenários).
- **Impacto:** A versão serial tornou-se capaz de gerar as matrizes `.bin` de referência para o caso Seahorse (`MAX_ITER=5000`) e resoluções gigantes (8192² e 16384²).
- **Validação:** Geração e inspeção das matrizes `mandelbrot_serial.bin` em 4096² (padrão e Seahorse), 8192² e 16384².
- **Observações:** O arquivo mantém pureza sequencial estrita: sem `#pragma omp`, sem chamadas OpenMP, sem estruturas auxiliares de concorrência.

---

### 4.3 — Interface de Execução, Separação de I/O e Saída Parseável no Serial
- **Versão afetada:** Versão Serial.
- **Arquivo(s):** [`serial/main.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/serial/main.c).
- **Trecho:** Função `main()` (linhas 7–66).
- **O que foi alterado:**
  - *Antes:* Assinatura `int main(void)` sem argumentos de linha de comando. Exportação de arquivos realizada sem isolamento de tempo.
  - *Depois:* Assinatura `int main(int argc, char *argv[])` com parsing posicional simples (`argv[1]` = cenário, `argv[2]` = resolução) e fallback em variáveis de ambiente (`MANDELBROT_SCENARIO`, `MANDELBROT_SIZE`). Medição explícita e isolada de `start_io` até `end_io`. Emissão de linhas parseáveis `chave=valor` em `stdout`.
- **Finalidade:** Suportar execução parametrizada sem bibliotecas externas (sem `argparse`) e separar formalmente o custo de disco do custo aritmético.
- **Requisito do PDF:** Seção 9 ("Tempo de execução: medir o tempo de execução total, excluindo operações de I/O [...]. O tempo de I/O deve ser reportado à parte.").
- **Impacto:** O script coletor consegue extrair diretamente `tempo_geracao_s`, `tempo_io_s` e `tempo_total_s` via regex/cut simples.
- **Validação:** Execução direta no terminal com `./serial/mandelbrot_seq padrao 4096` e `./serial/mandelbrot_seq seahorse 4096`, validando a saída em `stdout`.
- **Observações:** Decisão deliberada de engenharia: ausência de bibliotecas de parsing para aderir estritamente à restrição de "sem argparse/CLI complexa".

---

### 4.4 — Instrumentação de Tempo por Thread com `nowait` e Cálculo de λ
- **Versão afetada:** Versão OpenMP.
- **Arquivo(s):** [`openmp/mandelbrot_compute.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/mandelbrot_compute.c).
- **Trecho:** Função `compute_mandelbrot()` (linhas 17–81).
- **O que foi alterado:**
  - *Antes:* Região paralela compacta `#pragma omp parallel for schedule(runtime)` medindo apenas o tempo agregado externo.
  - *Depois:* Desacoplamento da região paralela. Alocação de `thread_times[tid]`. Adição da cláusula **`nowait`** ao `#pragma omp for schedule(runtime) nowait`. Cada thread registra `t_end - t_start` imediatamente após terminar suas linhas. Ao final da barreira da região paralela, calcula-se t_max = max(Tᵢ), t_avg = (1/p) · Σ Tᵢ e λ = t_avg / t_max, imprimindo em `stdout`.
- **Finalidade:** Medir com precisão microscópica o tempo de trabalho ativo individual de cada thread para o cálculo do Fator de Balanceamento de Carga exigido no relatório.
- **Requisito do PDF:** Seção 9 ("Fator de Balanceamento de Carga (λ): λ = T_médio / T_máximo").
- **Impacto:** Eliminação do viés de sincronização. Sem `nowait`, a medição pós-laço conteria a espera ociosa na barreira, resultando erroneamente em λ ≈ 1,00 mesmo sob desbalanceamento severo. Com `nowait`, a assimetria real é exposta (λ caiu para 0,68 no Seahorse estático e subiu para 0,99 no dynamic).
- **Validação:** Validação cruzada com `validate.py` provando que a instrumentação causou 0 alterações no resultado numérico da imagem.
- **Observações:** O vetor `thread_times` é alocado dinamicamente com base em `omp_get_max_threads()` e liberado ao final da rotina.

---

### 4.5 — Interface de Execução, Metadados e Separação de I/O no OpenMP
- **Versão afetada:** Versão OpenMP.
- **Arquivo(s):** [`openmp/main.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/main.c).
- **Trecho:** Função `main()` (linhas 10–85).
- **O que foi alterado:**
  - *Antes:* Entrada fixa em 4096², sem leitura de argumentos dinâmicos e sem medição isolada de I/O.
  - *Depois:* Adição de argumentos posicionais (`argv[1]`, `argv[2]`), captura de `OMP_NUM_THREADS` e da string ativa em `OMP_SCHEDULE`. Temporização de geração isolada de I/O via `omp_get_wtime()`. Emissão de linhas parseáveis `threads=...`, `schedule=...`, `tempo_geracao_s=...`, `tempo_io_s=...`.
- **Finalidade:** Padronizar a interface e a coleta automatizada em conformidade com o formato do serial.
- **Requisito do PDF:** Seções 5.2, 5.3, 7.1 e 9.
- **Impacto:** Permite varreduras sistemáticas de threads e políticas via scripts shell.
- **Validação:** Executado com `OMP_NUM_THREADS=8 OMP_SCHEDULE="dynamic,16" ./openmp/mandelbrot_omp seahorse 4096`, inspecionando a integridade das saídas.
- **Observações:** Quando compilado sem `-fopenmp`, faz fallback gracioso para medição monotônica POSIX.

---

### 4.6 — Suporte a `max_iter` Dinâmico na Exportação Visual PGM/PPM
- **Versão afetada:** Ambas (código compartilhado em `common/`).
- **Arquivo(s):** [`common/io_utils.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/io_utils.c).
- **Trecho:** `export_pgm()` (linhas 74–85) e `export_ppm()` (linhas 129–148).
- **O que foi alterado:**
  - *Antes:* Os laços de conversão de cor avaliavam `if (iter >= MAX_ITER)` e normalizavam a luminosidade e matiz HSV dividindo pela macro fixa `MAX_ITER` (1000).
  - *Depois:* Avaliam `if (iter >= max_iter)` e dividem por `(double)max_iter`, onde `max_iter = img->max_iter`.
- **Finalidade:** Corrigir a visualização do caso Seahorse (`MAX_ITER = 5000`).
- **Requisito do PDF:** Seção 5.3 e Seção 5.4 ("Saída: imagem em formato visual PGM ou PPM").
- **Impacto:** Sem essa modificação, no caso Seahorse, qualquer pixel com mais de 1000 iterações era incorretamente pintado de preto (como se pertencesse ao interior do fractal). Com o ajuste, todo o gradiente contínuo de até 5000 iterações é mapeado na paleta HSV.
- **Validação:** Inspeção do arquivo PPM e PGM gerados para o caso Seahorse com visualização completa dos filamentos espirais do fractal.
- **Observações:** Preservou-se a integridade da escrita binária de `export_binary()`, que independe do valor de `max_iter`.

---

### 4.7 — Suíte de Automação Experimental dos 4 Blocos e Geração de CSV
- **Versão afetada:** Ambas (infraestrutura de testes).
- **Arquivo(s):** [`scripts/run_experiments.sh`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/scripts/run_experiments.sh).
- **Trecho:** Arquivo novo (149 linhas).
- **O que foi alterado:** Criação de script em Bash puro (sem Python) para orquestrar a execução sistemática:
  - Registro inicial de ambiente (`uname -a`, `lscpu`, `gcc --version`, memória) em `environment_info.txt`.
  - Inicialização do CSV com as 12 colunas exatas exigidas.
  - **Bloco 0:** Coleta do baseline serial T₁ (3 repetições para padrão 4096², Seahorse 4096², 8192² e 16384²).
  - **Bloco 1:** Escalabilidade forte no padrão (1, 2, 4, 8, 16 threads com `static`).
  - **Bloco 2:** Avaliação de políticas e chunks no padrão (p = 8 fixo, `static`, `dynamic`, `guided` com chunks 1, 8, 16, 32, 64).
  - **Bloco 3:** Caso de estresse Seahorse (mesma grade dos Blocos 1 e 2).
  - **Bloco 4:** Escalabilidade fraca (4096² @ 1 thread, 8192² @ 4 threads, 16384² @ 16 threads com 16M pixels/thread).
- **Finalidade:** Coletar empiricamente a totalidade dos dados experimentais sem intervenção manual.
- **Requisito do PDF:** Seções 7.1, 5.3 e 9.
- **Impacto:** Geração do arquivo [`experiments.csv`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/experiments.csv) contendo 140 linhas de medições brutas e confiáveis.
- **Validação:** Execução completa em background com código de saída 0; integridade de linhas verificada via `wc -l`.
- **Observações:** O script extrai as chaves diretamente de `stdout`, garantindo que os tempos medidos reflitam os relógios internos de alta precisão em C.

---

### 4.8 — Processamento Analítico, Ajuste de Modelos e Geração de Gráficos
- **Versão afetada:** Ambas (pós-processamento).
- **Arquivo(s):** [`scripts/generate_plots_and_tables.py`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/scripts/generate_plots_and_tables.py).
- **Trecho:** Arquivo novo (285 linhas).
- **O que foi alterado:** Implementação de script em Python utilizando apenas a biblioteca padrão e `matplotlib` para:
  - Agrupar as repetições e calcular médias (μ) e desvios padrão (σ) para cada configuração.
  - Calcular Speedup (Sₚ = T_serial / Tₚ), Eficiência (Eₚ = Sₚ / p) e agregar λ.
  - Ajustar a fração paralela f no modelo teórico de Amdahl.
  - Calcular a Eficiência de Gustafson (E_weak = T(1) / T(p)).
  - Gerar 7 figuras em alta resolução (300 DPI) em `docs/plots/`.
  - Produzir tabelas consolidadas em Markdown em `docs/summary_tables.md`.
- **Finalidade:** Atender à exigência expressa da Seção 11 do PDF de inclusão de "gráficos claros" das métricas obrigatórias.
- **Requisito do PDF:** Seção 9 (Métricas obrigatórias) e Seção 11 (Relatório com gráficos).
- **Impacto:** Automação completa entre os dados brutos e os artefatos visuais do relatório.
- **Validação:** Geração e inspeção dos 7 arquivos PNG em `docs/plots/`.
- **Observações:** Não atua como script de teste ou de execução de benchmark (atendendo à restrição de escopo); seu papel é puramente plotador de dados existentes.

---

## 5. Arquivos Modificados — Visão Consolidada

| Arquivo | Tipo de Alteração | Modificações (§) | Versão / Escopo |
| :--- | :---: | :---: | :---: |
| [`common/mandelbrot.h`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/mandelbrot.h) | Modificado | §4.1 | Compartilhado (Comum) |
| [`common/common.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/common.c) | Modificado | §4.1 | Compartilhado (Comum) |
| [`common/io_utils.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/io_utils.c) | Modificado | §4.6 | Compartilhado (Comum) |
| [`serial/mandelbrot_compute.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/serial/mandelbrot_compute.c) | Modificado | §4.2 | Versão Serial |
| [`serial/main.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/serial/main.c) | Modificado | §4.3 | Versão Serial |
| [`openmp/mandelbrot_compute.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/mandelbrot_compute.c) | Modificado | §4.4 | Versão OpenMP |
| [`openmp/main.c`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/main.c) | Modificado | §4.5 | Versão OpenMP |
| [`scripts/run_experiments.sh`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/scripts/run_experiments.sh) | Novo | §4.7 | Automação de Coleta |
| [`scripts/generate_plots_and_tables.py`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/scripts/generate_plots_and_tables.py) | Novo | §4.8 | Plotagem e Análise |
| [`environment_info.txt`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/environment_info.txt) | Novo | §4.7 | Dados de Hardware/SO |
| [`experiments.csv`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/experiments.csv) | Novo | §4.7 | Dados Brutos Coletados |
| [`docs/summary_tables.md`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/docs/summary_tables.md) | Novo | §4.8 | Tabelas Estatísticas |
| [`docs/plots/*.png`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/docs/plots) (7 figuras) | Novo | §4.8 | Figuras do Relatório |
| [`RELATORIO_ETAPA1.md`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/RELATORIO_ETAPA1.md) | Novo | §2 e §4 | Relatório Técnico da Etapa |

---

## 6. O que NÃO foi modificado (e por quê)

Para delimitar rigorosamente o escopo e certificar que o projeto permaneceu fiel às diretrizes do enunciado:

1. **Lógica Matemática do Algoritmo:**
   - A fórmula recursiva zₙ₊₁ = zₙ² + c, a condição de divergência (zr² + zi²) ≤ 4.0 e a precisão `double` **não foram alteradas**. Qualquer desvio violaria o critério de reprodutibilidade canônica da Seção 5.2.
2. **Versão Serial sem Recursos Paralelos:**
   - Em nenhuma hipótese foram adicionadas variáveis de thread, diretivas OpenMP, rotinas de escalonamento ou medição de λ no diretório `serial/`. A regra de ouro foi respeitada: λ mede assimetria entre threads e não possui significado semântico em programas uniprocessados sequenciais.
3. **Validador de Corretude (`validate.py`):**
   - O código do validador original em Python não sofreu alterações. Ele continuou lendo as matrizes binárias contíguas de 32 bits em ordem *Row-Major* e aplicando a tolerância de até 0,01% com diferença máxima de 1 iteração.
4. **Alocação Contígua de Memória:**
   - A estratégia de armazenamento unidimensional contíguo em linha (`data[py * width + px]`) foi mantida, garantindo que o padrão de acesso à memória maximize o aproveitamento dos caches de dados.

---

## 7. Rastreabilidade PDF → Código

A tabela abaixo estabelece o vínculo formal entre cada requisito textual do enunciado da disciplina e o ponto exato da base de código onde foi implementado:

| Requisito do PDF | Seção do PDF | Arquivo e Trecho de Implementação | Modificação (§) |
| :--- | :---: | :--- | :---: |
| **Input Padrão Obrigatório** (4096², `MAX_ITER=1000`, [-2, 1] × [-1.5, 1.5]) | Seção 5.2 | [`common/common.c:59-67`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/common.c#L59-L67); [`common/mandelbrot.h:10-17`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/mandelbrot.h#L10-L17) | §4.1 |
| **Caso de Estresse Seahorse** (centro (-0.743643887, 0.131825904), larg. 0.003, 5000 iters) | Seção 5.3 | [`common/common.c:69-87`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/common.c#L69-L87) | §4.1 |
| **Weak Scaling** (4096², 8192², 16384²) | Seção 5.3 | [`serial/main.c:19-26`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/serial/main.c#L19-L26); [`openmp/main.c:20-27`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/main.c#L20-L27) | §4.3, §4.5 |
| **Saída Binária e Visual** (`.bin` row-major + PGM/PPM) | Seção 5.4 | [`common/io_utils.c:47-193`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/common/io_utils.c#L47-L193) | §4.6 |
| **Critério de Corretude** (tolerância ≤ 0,01% em até 1 iteração) | Seção 5.5 | Validado via [`validate.py`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/validate.py); 100% de igualdade exata atingida | §4.2, §4.4 |
| **Análises Obrigatórias** (threads, políticas, chunk, balanceamento) | Seção 7.1 | [`openmp/mandelbrot_compute.c:42`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/mandelbrot_compute.c#L42); [`scripts/run_experiments.sh`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/scripts/run_experiments.sh) | §4.4, §4.7 |
| **Separação Obrigatória do Tempo de I/O** | Seção 9 | [`serial/main.c:40-58`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/serial/main.c#L40-L58); [`openmp/main.c:60-80`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/main.c#L60-L80) | §4.3, §4.5 |
| **Fator de Balanceamento de Carga** (λ) | Seção 9 | [`openmp/mandelbrot_compute.c:63-78`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/openmp/mandelbrot_compute.c#L63-L78) | §4.4 |
| **Leis de Amdahl e Gustafson** | Seção 9 | [`scripts/generate_plots_and_tables.py:108-129`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/scripts/generate_plots_and_tables.py#L108-L129); [`RELATORIO_ETAPA1.md:§5.4`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/RELATORIO_ETAPA1.md) | §4.8 |
| **Estrutura Formal do Relatório Técnico** (Seções 1 a 6) | Seção 11 | [`RELATORIO_ETAPA1.md`](file:///home/clarinha/Documentos/PP/OpenMP/mandelbrot-dec107/RELATORIO_ETAPA1.md) (Introdução, Metodologia, Ambiente, Resultados, Análise, Conclusão) | Relatório |

---

## 8. Como Reproduzir

### 8.1. Ordem Recomendada de Execução

1. **Compilação Limpa:**
   ```bash
   make clean && make
   ```
2. **Validação Cruzada de Corretude (Seção 5.5):**
   ```bash
   # Validação do Input Padrão (4096 x 4096)
   ./serial/mandelbrot_seq padrao 4096
   ./openmp/mandelbrot_omp padrao 4096
   python3 validate.py mandelbrot_serial.bin mandelbrot_omp.bin

   # Validação do Caso Seahorse (4096 x 4096, MAX_ITER=5000)
   ./serial/mandelbrot_seq seahorse 4096
   ./openmp/mandelbrot_omp seahorse 4096
   python3 validate.py mandelbrot_serial.bin mandelbrot_omp.bin

   # Validação em Alta Resolução (8192 x 8192)
   ./serial/mandelbrot_seq padrao 8192
   ./openmp/mandelbrot_omp padrao 8192
   python3 validate.py mandelbrot_serial.bin mandelbrot_omp.bin

   # Validação em Escala Gigapixel (16384 x 16384)
   ./serial/mandelbrot_seq padrao 16384
   ./openmp/mandelbrot_omp padrao 16384
   python3 validate.py mandelbrot_serial.bin mandelbrot_omp.bin
   ```
3. **Execução da Bateria de Benchmarks (Gera `experiments.csv`):**
   ```bash
   ./scripts/run_experiments.sh
   ```
4. **Geração das Figuras e Tabelas:**
   ```bash
   python3 scripts/generate_plots_and_tables.py
   ```

---

## 9. Pendências e Próximos Passos

### Status Atual da Etapa 1
**100% Concluída.** Todos os requisitos funcionais, não-funcionais, experimentais e de documentação exigidos pelo enunciado da Etapa 1 foram integralmente satisfeitos.

### Preparação para a Etapa 2 (Memória Distribuída — MPI)
Com a conclusão da Etapa 1, os próximos passos do projeto concentram-se na preparação da infraestrutura para a Etapa 2:
1. **Decomposição de Domínio Bidimensional:** Evoluir o particionamento 1D em faixas de linhas (utilizado no OpenMP) para topologia cartesiana 2D em blocos (*domain decomposition*).
2. **Estratégias de Balanceamento Distribuído:** Implementar e contrastar o particionamento estático em grade com o modelo dinâmico mestre-trabalhador (*master-worker*).
3. **Comunicação e I/O Paralelo:** Avaliar a coleta de dados via `MPI_Gather` / `MPI_Gatherv` contra a escrita direta concorrente através de `MPI-IO` (`MPI_File_write_at`).

---

## 10. Anexos

### 10.1. Exemplo de Saída Parseável em `stdout`

#### Versão Serial (`./serial/mandelbrot_seq padrao 4096`)
```text
Matriz binaria exportada: mandelbrot_serial.bin (4096 x 4096, 67108864 bytes)
Imagem PGM exportada: mandelbrot_serial.pgm (4096 x 4096)
Imagem PPM exportada: mandelbrot_serial.ppm (4096 x 4096)
versao=serial
cenario=padrao
resolucao=4096x4096
max_iter=1000
tempo_geracao_s=13.853428
tempo_io_s=0.573987
tempo_total_s=14.427415
```

#### Versão OpenMP (`OMP_NUM_THREADS=4 OMP_SCHEDULE="dynamic,16" ./openmp/mandelbrot_omp seahorse 4096`)
```text
t_max_s=2.348509
t_avg_s=2.332073
lambda=0.993001
Matriz binaria exportada: mandelbrot_omp.bin (4096 x 4096, 67108864 bytes)
Imagem PGM exportada: mandelbrot_omp.pgm (4096 x 4096)
Imagem PPM exportada: mandelbrot_omp.ppm (4096 x 4096)
versao=openmp
cenario=seahorse
resolucao=4096x4096
max_iter=5000
threads=4
schedule=dynamic,16
tempo_geracao_s=2.349110
tempo_io_s=0.749681
tempo_total_s=3.098791
```

### 10.2. Comparativo Diff Representativo (Instrumentação de λ no OpenMP)

```diff
--- a/openmp/mandelbrot_compute.c
+++ b/openmp/mandelbrot_compute.c
@@ -17,24 +17,47 @@ void compute_mandelbrot(ImageBuffer *img) {
     if (img == NULL || img->data == NULL) {
         return;
     }
+    int max_iter = img->max_iter;
 
 #ifdef _OPENMP
-    #pragma omp parallel for schedule(runtime)
+    int max_threads = omp_get_max_threads();
+    double *thread_times = (double *)calloc(max_threads, sizeof(double));
+    int actual_threads = 1;
+
+    #pragma omp parallel
+    {
+        int tid = omp_get_thread_num();
+        #pragma omp single
+        {
+            actual_threads = omp_get_num_threads();
+        }
+        double t_start = omp_get_wtime();
+
+        #pragma omp for schedule(runtime) nowait
         for (int py = 0; py < img->height; py++) {
             for (int px = 0; px < img->width; px++) {
                 double zr = 0.0, zi = 0.0, cr = 0.0, ci = 0.0;
                 int iter = 0;
 
-                pixel_to_complex(px, py, img->width, img->height, &cr, &ci);
+                pixel_to_complex(px, py, img, &cr, &ci);
 
-                while (iter < MAX_ITER && (zr*zr + zi*zi) <= 4.0) {
+                while (iter < max_iter && (zr*zr + zi*zi) <= 4.0) {
                     double next_zr = (zr*zr) - (zi*zi) + cr;
                     double next_zi = 2*(zr*zi) + ci;
                     zr = next_zr;
                     zi = next_zi;
                     iter++;
                 }
 
                 img->data[(size_t)py * img->width + px] = iter;
             }
         }
+        double t_end = omp_get_wtime();
+        thread_times[tid] = t_end - t_start;
+    }
+
+    /* Redução pós-paralela de balanceamento */
+    double t_max = 0.0, t_sum = 0.0;
+    for (int i = 0; i < actual_threads; i++) {
+        if (thread_times[i] > t_max) t_max = thread_times[i];
+        t_sum += thread_times[i];
+    }
+    double t_avg = t_sum / (double)actual_threads;
+    double lambda = (t_max > 0.0) ? (t_avg / t_max) : 1.0;
+    printf("t_max_s=%.6f\nt_avg_s=%.6f\nlambda=%.6f\n", t_max, t_avg, lambda);
+    free(thread_times);
```
