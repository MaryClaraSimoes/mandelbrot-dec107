# Tabelas Resumo — Etapa 2 (MPI)

Geradas a partir de `experiments_mpi.csv` (comparações com `experiments.csv`, Etapa 1 — OpenMP).

## Tabela 1 — Strong scaling MPI, input padrão (4096x4096, 1000 iterações)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

T_serial = 16.655433 s.

| Estratégia | Processos | Tempo (s) | Speedup | Eficiência | f_lb | Corretude |
|:---|:-:|:-:|:-:|:-:|:-:|:---|
| block | 1 | 16.517162 ± 2.386648 | 1.0238 ± 0.1604 | 1.0238 ± 0.1604 | 1.0000 ± 0.0000 | idêntica (3/3) |
| block | 2 | 8.420078 ± 0.874455 | 1.9916 ± 0.1952 | 0.9958 ± 0.0976 | 1.0011 ± 0.0008 | idêntica (3/3) |
| block | 4 | 10.355572 ± 0.757996 | 1.6140 ± 0.1165 | 0.4035 ± 0.0291 | 1.9129 ± 0.0113 | idêntica (3/3) |
| block | 8 | 9.151242 ± 0.478537 | 1.8233 ± 0.0954 | 0.2279 ± 0.0119 | 2.7310 ± 0.0986 | idêntica (3/3) |
| cyclic | 1 | 13.985228 ± 0.856518 | 1.1938 ± 0.0707 | 1.1938 ± 0.0707 | 1.0000 ± 0.0000 | idêntica (3/3) |
| cyclic | 2 | 9.029600 ± 0.265018 | 1.8456 ± 0.0539 | 0.9228 ± 0.0270 | 1.0019 ± 0.0008 | idêntica (3/3) |
| cyclic | 4 | 5.266584 ± 0.042490 | 3.1626 ± 0.0254 | 0.7907 ± 0.0063 | 1.0013 ± 0.0004 | idêntica (3/3) |
| cyclic | 8 | 3.417286 ± 0.021641 | 4.8740 ± 0.0308 | 0.6093 ± 0.0039 | 1.0353 ± 0.0007 | idêntica (3/3) |

## Tabela 2 — Strong scaling MPI, Seahorse (4096x4096, 5000 iterações)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

T_serial = 5.925033 s.

| Estratégia | Processos | Tempo (s) | Speedup | Eficiência | f_lb | Corretude |
|:---|:-:|:-:|:-:|:-:|:-:|:---|
| block | 1 | 6.512467 ± 0.219998 | 0.9105 ± 0.0314 | 0.9105 ± 0.0314 | 1.0000 ± 0.0000 | idêntica (3/3) |
| block | 2 | 4.610490 ± 0.021616 | 1.2851 ± 0.0060 | 0.6426 ± 0.0030 | 1.1516 ± 0.0017 | idêntica (3/3) |
| block | 4 | 3.108156 ± 0.004136 | 1.9063 ± 0.0025 | 0.4766 ± 0.0006 | 1.1913 ± 0.0017 | idêntica (3/3) |
| block | 8 | 1.995781 ± 0.016075 | 2.9689 ± 0.0239 | 0.3711 ± 0.0030 | 1.2584 ± 0.0041 | idêntica (3/3) |
| cyclic | 1 | 6.243431 ± 0.035451 | 0.9490 ± 0.0054 | 0.9490 ± 0.0054 | 1.0000 ± 0.0000 | idêntica (3/3) |
| cyclic | 2 | 3.848581 ± 0.031858 | 1.5396 ± 0.0127 | 0.7698 ± 0.0064 | 1.0043 ± 0.0007 | idêntica (3/3) |
| cyclic | 4 | 2.502078 ± 0.025712 | 2.3682 ± 0.0245 | 0.5921 ± 0.0061 | 1.0016 ± 0.0012 | idêntica (3/3) |
| cyclic | 8 | 1.693561 ± 0.022434 | 3.4990 ± 0.0464 | 0.4374 ± 0.0058 | 1.0457 ± 0.0006 | idêntica (3/3) |

## Tabela 3 — Weak scaling MPI

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

Eficiência fraca = T(p=1) / T(p). Speedup é relativo ao serial da respectiva resolução.

| Estratégia | Processos | Resolução | Pixels/proc | T_serial (s) | Tempo (s) | Speedup vs serial | Eficiência fraca | f_lb | Corretude |
|:---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:---|
| block | 1 | 4096x4096 | 16,777,216 | 16.655433 | 13.476912 ± 0.076413 | 1.2359 ± 0.0070 | 1.0000 ± 0.0057 | 1.0000 ± 0.0000 | idêntica (3/3) |
| block | 4 | 8192x8192 | 16,777,216 | 52.110067 | 40.083100 ± 1.914670 | 1.3021 ± 0.0640 | 0.3368 ± 0.0165 | 1.9464 ± 0.0044 | idêntica (3/3) |
| block | 9 | 12288x12288 | 16,777,216 | 127.904267 | 82.714398 ± 0.961912 | 1.5465 ± 0.0180 | 0.1629 ± 0.0019 | 3.0830 ± 0.0289 | idêntica (3/3) |
| cyclic | 1 | 4096x4096 | 16,777,216 | 16.655433 | 15.554859 ± 1.951843 | 1.0830 ± 0.1465 | 1.0114 ± 0.1368 | 1.0000 ± 0.0000 | idêntica (3/3) |
| cyclic | 4 | 8192x8192 | 16,777,216 | 52.110067 | 20.658994 ± 1.063862 | 2.5270 ± 0.1330 | 0.7543 ± 0.0397 | 1.0131 ± 0.0105 | idêntica (3/3) |
| cyclic | 9 | 12288x12288 | 16,777,216 | 127.904267 | 28.791104 ± 0.580000 | 4.4437 ± 0.0890 | 0.5404 ± 0.0108 | 1.0408 ± 0.0227 | idêntica (3/3) |

## Tabela 4 — Comparação OpenMP × MPI, Input padrão (strong scaling)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

| Implementação | p | Resolução | Tempo (s) | Speedup | Eficiência | λ / f_lb |
|:---|:-:|:-:|:-:|:-:|:-:|:-:|
| OpenMP static | 1 | 4096x4096 | 5.8646 ± 0.0162 | 1.0020 ± 0.0028 | 1.0020 ± 0.0028 | 1.0000 ± 0.0000 |
| MPI block | 1 | 4096x4096 | 16.517162 ± 2.386648 | 1.0238 ± 0.1604 | 1.0238 ± 0.1604 | 1.0000 ± 0.0000 |
| MPI cyclic | 1 | 4096x4096 | 13.985228 ± 0.856518 | 1.1938 ± 0.0707 | 1.1938 ± 0.0707 | 1.0000 ± 0.0000 |
| OpenMP static | 2 | 4096x4096 | 2.9474 ± 0.0129 | 1.9938 ± 0.0087 | 0.9969 ± 0.0043 | 1.0032 ± 0.0021 |
| MPI block | 2 | 4096x4096 | 8.420078 ± 0.874455 | 1.9916 ± 0.1952 | 0.9958 ± 0.0976 | 1.0011 ± 0.0008 |
| MPI cyclic | 2 | 4096x4096 | 9.029600 ± 0.265018 | 1.8456 ± 0.0539 | 0.9228 ± 0.0270 | 1.0019 ± 0.0008 |
| OpenMP static | 4 | 4096x4096 | 2.8701 ± 0.0031 | 2.0475 ± 0.0022 | 0.5119 ± 0.0006 | 1.9396 ± 0.0037 |
| MPI block | 4 | 4096x4096 | 10.355572 ± 0.757996 | 1.6140 ± 0.1165 | 0.4035 ± 0.0291 | 1.9129 ± 0.0113 |
| MPI cyclic | 4 | 4096x4096 | 5.266584 ± 0.042490 | 3.1626 ± 0.0254 | 0.7907 ± 0.0063 | 1.0013 ± 0.0004 |
| OpenMP static | 8 | 4096x4096 | 2.0283 ± 0.0091 | 2.8972 ± 0.0130 | 0.3622 ± 0.0016 | 2.6488 ± 0.0110 |
| MPI block | 8 | 4096x4096 | 9.151242 ± 0.478537 | 1.8233 ± 0.0954 | 0.2279 ± 0.0119 | 2.7310 ± 0.0986 |
| MPI cyclic | 8 | 4096x4096 | 3.417286 ± 0.021641 | 4.8740 ± 0.0308 | 0.6093 ± 0.0039 | 1.0353 ± 0.0007 |
| OpenMP static,1 | 8 | 4096x4096 | 0.9628 ± 0.0270 | 6.1068 ± 0.1690 | 0.7634 ± 0.0211 | 1.1331 ± 0.0079 |
| OpenMP dynamic,1 | 8 | 4096x4096 | 0.8323 ± 0.0010 | 7.0607 ± 0.0087 | 0.8826 ± 0.0011 | 1.0000 ± 0.0001 |

## Tabela 5 — Comparação OpenMP × MPI, Seahorse (strong scaling)

Valores: **média ± desvio padrão amostral** (n = 3 repetições). Speedup, eficiência e f_lb calculados por repetição e depois agregados.

| Implementação | p | Resolução | Tempo (s) | Speedup | Eficiência | λ / f_lb |
|:---|:-:|:-:|:-:|:-:|:-:|:-:|
| OpenMP static | 1 | 4096x4096 | 2.6290 ± 0.0132 | 0.9970 ± 0.0050 | 0.9970 ± 0.0050 | 1.0000 ± 0.0000 |
| MPI block | 1 | 4096x4096 | 6.512467 ± 0.219998 | 0.9105 ± 0.0314 | 0.9105 ± 0.0314 | 1.0000 ± 0.0000 |
| MPI cyclic | 1 | 4096x4096 | 6.243431 ± 0.035451 | 0.9490 ± 0.0054 | 0.9490 ± 0.0054 | 1.0000 ± 0.0000 |
| OpenMP static | 2 | 4096x4096 | 1.5486 ± 0.0042 | 1.6927 ± 0.0046 | 0.8463 ± 0.0023 | 1.1838 ± 0.0017 |
| MPI block | 2 | 4096x4096 | 4.610490 ± 0.021616 | 1.2851 ± 0.0060 | 0.6426 ± 0.0030 | 1.1516 ± 0.0017 |
| MPI cyclic | 2 | 4096x4096 | 3.848581 ± 0.031858 | 1.5396 ± 0.0127 | 0.7698 ± 0.0064 | 1.0043 ± 0.0007 |
| OpenMP static | 4 | 4096x4096 | 0.8399 ± 0.0045 | 3.1208 ± 0.0166 | 0.7802 ± 0.0042 | 1.2304 ± 0.0017 |
| MPI block | 4 | 4096x4096 | 3.108156 ± 0.004136 | 1.9063 ± 0.0025 | 0.4766 ± 0.0006 | 1.1913 ± 0.0017 |
| MPI cyclic | 4 | 4096x4096 | 2.502078 ± 0.025712 | 2.3682 ± 0.0245 | 0.5921 ± 0.0061 | 1.0016 ± 0.0012 |
| OpenMP static | 8 | 4096x4096 | 0.4879 ± 0.0011 | 5.3728 ± 0.0122 | 0.6716 ± 0.0015 | 1.3586 ± 0.0035 |
| MPI block | 8 | 4096x4096 | 1.995781 ± 0.016075 | 2.9689 ± 0.0239 | 0.3711 ± 0.0030 | 1.2584 ± 0.0041 |
| MPI cyclic | 8 | 4096x4096 | 1.693561 ± 0.022434 | 3.4990 ± 0.0464 | 0.4374 ± 0.0058 | 1.0457 ± 0.0006 |
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
| MPI block | 1 | 4096x4096 | 16,777,216 | 13.476912 ± 0.076413 | 1.0000 ± 0.0057 |
| MPI block | 4 | 8192x8192 | 16,777,216 | 40.083100 ± 1.914670 | 0.3368 ± 0.0165 |
| MPI block | 9 | 12288x12288 | 16,777,216 | 82.714398 ± 0.961912 | 0.1629 ± 0.0019 |
| MPI cyclic | 1 | 4096x4096 | 16,777,216 | 15.554859 ± 1.951843 | 1.0114 ± 0.1368 |
| MPI cyclic | 4 | 8192x8192 | 16,777,216 | 20.658994 ± 1.063862 | 0.7543 ± 0.0397 |
| MPI cyclic | 9 | 12288x12288 | 16,777,216 | 28.791104 ± 0.580000 | 0.5404 ± 0.0108 |

## Tabela 7 — Verificação de corretude (todas as execuções MPI)

| Execuções | Idênticas ao serial | Máx. px divergentes | Máx. diff |
|:-:|:-:|:-:|:-:|
| 66 | 66 | 0 | 0 |

