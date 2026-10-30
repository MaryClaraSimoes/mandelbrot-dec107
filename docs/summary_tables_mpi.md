# Tabelas Resumo — Etapa 2 (MPI)

Geradas a partir de `experiments_mpi.csv` (comparações com `experiments.csv`, Etapa 1 — OpenMP).

## Tabela 1 — Strong scaling MPI, input padrão (4096x4096, 1000 iterações)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

T_serial = 12.686733 s.

| Estratégia | Processos | Tempo (s) | Speedup | Eficiência | f_lb | Corretude |
|:---|:-:|:-:|:-:|:-:|:-:|:---|
| block | 1 | 12.703137 ± 0.042951 | 0.9987 ± 0.0034 | 0.9987 ± 0.0034 | 0.0000 ± 0.0000 | idêntica (3/3) |
| block | 2 | 7.427058 ± 0.035944 | 1.7082 ± 0.0082 | 0.8541 ± 0.0041 | 0.0016 ± 0.0001 | idêntica (3/3) |
| block | 4 | 9.276649 ± 0.047436 | 1.3676 ± 0.0070 | 0.3419 ± 0.0017 | 0.9702 ± 0.0003 | idêntica (3/3) |
| block | 8 | 8.144117 ± 0.217866 | 1.5585 ± 0.0423 | 0.1948 ± 0.0053 | 0.9952 ± 0.0011 | idêntica (3/3) |
| cyclic | 1 | 12.709290 ± 0.030399 | 0.9982 ± 0.0024 | 0.9982 ± 0.0024 | 0.0000 ± 0.0000 | idêntica (3/3) |
| cyclic | 2 | 7.408484 ± 0.021949 | 1.7125 ± 0.0051 | 0.8562 ± 0.0025 | 0.0022 ± 0.0006 | idêntica (3/3) |
| cyclic | 4 | 4.836015 ± 0.001591 | 2.6234 ± 0.0009 | 0.6558 ± 0.0002 | 0.0020 ± 0.0007 | idêntica (3/3) |
| cyclic | 8 | 3.261153 ± 0.127765 | 3.8942 ± 0.1492 | 0.4868 ± 0.0186 | 0.0553 ± 0.0044 | idêntica (3/3) |

## Tabela 2 — Strong scaling MPI, Seahorse (4096x4096, 5000 iterações)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

T_serial = 5.670867 s.

| Estratégia | Processos | Tempo (s) | Speedup | Eficiência | f_lb | Corretude |
|:---|:-:|:-:|:-:|:-:|:-:|:---|
| block | 1 | 6.110460 ± 0.009083 | 0.9281 ± 0.0014 | 0.9281 ± 0.0014 | 0.0000 ± 0.0000 | idêntica (3/3) |
| block | 2 | 4.102024 ± 0.012568 | 1.3825 ± 0.0042 | 0.6912 ± 0.0021 | 0.2857 ± 0.0013 | idêntica (3/3) |
| block | 4 | 2.796761 ± 0.002653 | 2.0277 ± 0.0019 | 0.5069 ± 0.0005 | 0.4239 ± 0.0011 | idêntica (3/3) |
| block | 8 | 1.860724 ± 0.005750 | 3.0477 ± 0.0094 | 0.3810 ± 0.0012 | 0.5804 ± 0.0060 | idêntica (3/3) |
| cyclic | 1 | 5.695332 ± 0.017791 | 0.9957 ± 0.0031 | 0.9957 ± 0.0031 | 0.0000 ± 0.0000 | idêntica (3/3) |
| cyclic | 2 | 3.352206 ± 0.036942 | 1.6918 ± 0.0186 | 0.8459 ± 0.0093 | 0.0094 ± 0.0019 | idêntica (3/3) |
| cyclic | 4 | 2.211711 ± 0.004914 | 2.5640 ± 0.0057 | 0.6410 ± 0.0014 | 0.0081 ± 0.0009 | idêntica (3/3) |
| cyclic | 8 | 1.551044 ± 0.057485 | 3.6594 ± 0.1328 | 0.4574 ± 0.0166 | 0.0863 ± 0.0149 | idêntica (3/3) |

## Tabela 3 — Weak scaling MPI

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

Eficiência fraca = T(p=1) / T(p). Speedup é relativo ao serial da respectiva resolução.

| Estratégia | Processos | Resolução | Pixels/proc | T_serial (s) | Tempo (s) | Speedup vs serial | Eficiência fraca | f_lb | Corretude |
|:---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:---|
| block | 1 | 4096x4096 | 16,777,216 | 12.686733 | 12.750656 ± 0.052336 | 0.9950 ± 0.0041 | 1.0000 ± 0.0041 | 0.0000 ± 0.0000 | idêntica (3/3) |
| block | 4 | 8192x8192 | 16,777,216 | 50.528933 | 37.038328 ± 0.065042 | 1.3642 ± 0.0024 | 0.3443 ± 0.0006 | 0.9701 ± 0.0001 | idêntica (3/3) |
| block | 9 | 12288x12288 | 16,777,216 | 113.804200 | 81.679943 ± 2.307430 | 1.3940 ± 0.0400 | 0.1562 ± 0.0045 | 0.9957 ± 0.0011 | idêntica (3/3) |
| cyclic | 1 | 4096x4096 | 16,777,216 | 12.686733 | 12.771270 ± 0.075864 | 0.9934 ± 0.0059 | 1.0000 ± 0.0060 | 0.0000 ± 0.0000 | idêntica (3/3) |
| cyclic | 4 | 8192x8192 | 16,777,216 | 50.528933 | 19.326869 ± 0.033492 | 2.6144 ± 0.0045 | 0.6608 ± 0.0011 | 0.0012 ± 0.0008 | idêntica (3/3) |
| cyclic | 9 | 12288x12288 | 16,777,216 | 113.804200 | 27.799297 ± 0.185397 | 4.0939 ± 0.0272 | 0.4594 ± 0.0031 | 0.0524 ± 0.0003 | idêntica (3/3) |

## Tabela 4 — Comparação OpenMP × MPI, Input padrão (strong scaling)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

| Implementação | p | Resolução | Tempo (s) | Speedup | Eficiência | λ / f_lb |
|:---|:-:|:-:|:-:|:-:|:-:|:-:|
| OpenMP static | 1 | 4096x4096 | 5.8646 ± 0.0162 | 1.0020 ± 0.0028 | 1.0020 ± 0.0028 | 1.0000 ± 0.0000 |
| MPI block | 1 | 4096x4096 | 12.703137 ± 0.042951 | 0.9987 ± 0.0034 | 0.9987 ± 0.0034 | 0.0000 ± 0.0000 |
| MPI cyclic | 1 | 4096x4096 | 12.709290 ± 0.030399 | 0.9982 ± 0.0024 | 0.9982 ± 0.0024 | 0.0000 ± 0.0000 |
| OpenMP static | 2 | 4096x4096 | 2.9474 ± 0.0129 | 1.9938 ± 0.0087 | 0.9969 ± 0.0043 | 1.0032 ± 0.0021 |
| MPI block | 2 | 4096x4096 | 7.427058 ± 0.035944 | 1.7082 ± 0.0082 | 0.8541 ± 0.0041 | 0.0016 ± 0.0001 |
| MPI cyclic | 2 | 4096x4096 | 7.408484 ± 0.021949 | 1.7125 ± 0.0051 | 0.8562 ± 0.0025 | 0.0022 ± 0.0006 |
| OpenMP static | 4 | 4096x4096 | 2.8701 ± 0.0031 | 2.0475 ± 0.0022 | 0.5119 ± 0.0006 | 1.9396 ± 0.0037 |
| MPI block | 4 | 4096x4096 | 9.276649 ± 0.047436 | 1.3676 ± 0.0070 | 0.3419 ± 0.0017 | 0.9702 ± 0.0003 |
| MPI cyclic | 4 | 4096x4096 | 4.836015 ± 0.001591 | 2.6234 ± 0.0009 | 0.6558 ± 0.0002 | 0.0020 ± 0.0007 |
| OpenMP static | 8 | 4096x4096 | 2.0283 ± 0.0091 | 2.8972 ± 0.0130 | 0.3622 ± 0.0016 | 2.6488 ± 0.0110 |
| MPI block | 8 | 4096x4096 | 8.144117 ± 0.217866 | 1.5585 ± 0.0423 | 0.1948 ± 0.0053 | 0.9952 ± 0.0011 |
| MPI cyclic | 8 | 4096x4096 | 3.261153 ± 0.127765 | 3.8942 ± 0.1492 | 0.4868 ± 0.0186 | 0.0553 ± 0.0044 |
| OpenMP static,1 | 8 | 4096x4096 | 0.9628 ± 0.0270 | 6.1068 ± 0.1690 | 0.7634 ± 0.0211 | 1.1331 ± 0.0079 |
| OpenMP dynamic,1 | 8 | 4096x4096 | 0.8323 ± 0.0010 | 7.0607 ± 0.0087 | 0.8826 ± 0.0011 | 1.0000 ± 0.0001 |

## Tabela 5 — Comparação OpenMP × MPI, Seahorse (strong scaling)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

| Implementação | p | Resolução | Tempo (s) | Speedup | Eficiência | λ / f_lb |
|:---|:-:|:-:|:-:|:-:|:-:|:-:|
| OpenMP static | 1 | 4096x4096 | 2.6290 ± 0.0132 | 0.9970 ± 0.0050 | 0.9970 ± 0.0050 | 1.0000 ± 0.0000 |
| MPI block | 1 | 4096x4096 | 6.110460 ± 0.009083 | 0.9281 ± 0.0014 | 0.9281 ± 0.0014 | 0.0000 ± 0.0000 |
| MPI cyclic | 1 | 4096x4096 | 5.695332 ± 0.017791 | 0.9957 ± 0.0031 | 0.9957 ± 0.0031 | 0.0000 ± 0.0000 |
| OpenMP static | 2 | 4096x4096 | 1.5486 ± 0.0042 | 1.6927 ± 0.0046 | 0.8463 ± 0.0023 | 1.1838 ± 0.0017 |
| MPI block | 2 | 4096x4096 | 4.102024 ± 0.012568 | 1.3825 ± 0.0042 | 0.6912 ± 0.0021 | 0.2857 ± 0.0013 |
| MPI cyclic | 2 | 4096x4096 | 3.352206 ± 0.036942 | 1.6918 ± 0.0186 | 0.8459 ± 0.0093 | 0.0094 ± 0.0019 |
| OpenMP static | 4 | 4096x4096 | 0.8399 ± 0.0045 | 3.1208 ± 0.0166 | 0.7802 ± 0.0042 | 1.2304 ± 0.0017 |
| MPI block | 4 | 4096x4096 | 2.796761 ± 0.002653 | 2.0277 ± 0.0019 | 0.5069 ± 0.0005 | 0.4239 ± 0.0011 |
| MPI cyclic | 4 | 4096x4096 | 2.211711 ± 0.004914 | 2.5640 ± 0.0057 | 0.6410 ± 0.0014 | 0.0081 ± 0.0009 |
| OpenMP static | 8 | 4096x4096 | 0.4879 ± 0.0011 | 5.3728 ± 0.0122 | 0.6716 ± 0.0015 | 1.3586 ± 0.0035 |
| MPI block | 8 | 4096x4096 | 1.860724 ± 0.005750 | 3.0477 ± 0.0094 | 0.3810 ± 0.0012 | 0.5804 ± 0.0060 |
| MPI cyclic | 8 | 4096x4096 | 1.551044 ± 0.057485 | 3.6594 ± 0.1328 | 0.4574 ± 0.0166 | 0.0863 ± 0.0149 |
| OpenMP static,1 | 8 | 4096x4096 | 0.4258 ± 0.0011 | 6.1560 ± 0.0163 | 0.7695 ± 0.0020 | 1.1476 ± 0.0060 |
| OpenMP dynamic,1 | 8 | 4096x4096 | 0.3728 ± 0.0016 | 7.0312 ± 0.0295 | 0.8789 ± 0.0037 | 1.0016 ± 0.0004 |

## Tabela 6 — Comparação OpenMP × MPI (weak scaling)

Valores: **média ± desvio padrão amostral** (n = 3 no MPI). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

Eficiência fraca = T(p=1) / T(p). A carga por unidade de execução difere entre as etapas (16M pixels/thread no OpenMP; 262.144 pixels/processo no MPI), então compare a **eficiência**, não o tempo. No OpenMP, o bloco 4 tem apenas 1 repetição por configuração (`n=1`: desvio padrão não definido).

| Implementação | p | Resolução | Pixels/unidade | Tempo (s) | Eficiência fraca |
|:---|:-:|:-:|:-:|:-:|:-:|
| OpenMP static | 1 | 4096x4096 | 16,777,216 | 5.8800 (n=1) | 1.0000 (n=1) |
| OpenMP static | 4 | 8192x8192 | 16,777,216 | 6.1968 (n=1) | 0.9489 (n=1) |
| OpenMP static | 16 | 16384x16384 | 16,777,216 | 7.4871 (n=1) | 0.7854 (n=1) |
| OpenMP dynamic,1 | 1 | 4096x4096 | 16,777,216 | 5.8761 (n=1) | 1.0000 (n=1) |
| OpenMP dynamic,1 | 4 | 8192x8192 | 16,777,216 | 6.1891 (n=1) | 0.9494 (n=1) |
| OpenMP dynamic,1 | 16 | 16384x16384 | 16,777,216 | 7.6364 (n=1) | 0.7695 (n=1) |
| MPI block | 1 | 4096x4096 | 16,777,216 | 12.750656 ± 0.052336 | 1.0000 ± 0.0041 |
| MPI block | 4 | 8192x8192 | 16,777,216 | 37.038328 ± 0.065042 | 0.3443 ± 0.0006 |
| MPI block | 9 | 12288x12288 | 16,777,216 | 81.679943 ± 2.307430 | 0.1562 ± 0.0045 |
| MPI cyclic | 1 | 4096x4096 | 16,777,216 | 12.771270 ± 0.075864 | 1.0000 ± 0.0060 |
| MPI cyclic | 4 | 8192x8192 | 16,777,216 | 19.326869 ± 0.033492 | 0.6608 ± 0.0011 |
| MPI cyclic | 9 | 12288x12288 | 16,777,216 | 27.799297 ± 0.185397 | 0.4594 ± 0.0031 |

## Tabela 7 — Verificação de corretude (todas as execuções MPI)

| Execuções | Idênticas ao serial | Máx. px divergentes | Máx. diff |
|:-:|:-:|:-:|:-:|
| 66 | 66 | 0 | 0 |

