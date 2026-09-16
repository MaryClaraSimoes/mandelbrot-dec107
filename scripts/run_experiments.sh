#!/bin/bash
set -e

# ==============================================================================
# run_experiments.sh — Coleta Experimental da Etapa 1 (DEC107)
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

CSV_FILE="experiments.csv"
ENV_FILE="environment_info.txt"

echo "=================================================================="
echo " Iniciando Coleta Experimental — Mandelbrot DEC107 (Etapa 1)"
echo "=================================================================="

# 1. Registro do Ambiente de Execução
echo "--> Registrando informacoes de hardware, SO e compilador..."
cat << 'EOF' > "$ENV_FILE"
=== AMBIENTE DE EXECUÇÃO ===
EOF
uname -a >> "$ENV_FILE"
cat /etc/os-release | grep PRETTY_NAME >> "$ENV_FILE"
gcc --version | head -n 1 >> "$ENV_FILE"
lscpu >> "$ENV_FILE"
free -h >> "$ENV_FILE"

# 2. Inicialização do CSV
cat << 'EOF' > "$CSV_FILE"
cenario,resolucao,threads,schedule,chunk,repeticao,tempo_geracao_s,tempo_io_s,tempo_total_s,t_max_s,t_avg_s,lambda
EOF

# Função auxiliar para executar e parsear OpenMP
run_omp() {
    local cenario="$1"
    local res="$2"
    local threads="$3"
    local sched="$4"
    local chunk="$5"
    local rep="$6"

    local sched_env="$sched"
    if [ -n "$chunk" ] && [ "$chunk" != "0" ] && [ "$chunk" != "default" ]; then
        sched_env="${sched},${chunk}"
    fi

    echo "  [OMP] cenario=$cenario res=$res threads=$threads sched=$sched_env rep=$rep"
    
    local out
    out=$(OMP_NUM_THREADS="$threads" OMP_SCHEDULE="$sched_env" ./openmp/mandelbrot_omp "$cenario" "$res")
    
    local t_gen t_io t_tot t_max t_avg lam
    t_gen=$(echo "$out" | grep '^tempo_geracao_s=' | cut -d= -f2)
    t_io=$(echo "$out" | grep '^tempo_io_s=' | cut -d= -f2)
    t_tot=$(echo "$out" | grep '^tempo_total_s=' | cut -d= -f2)
    t_max=$(echo "$out" | grep '^t_max_s=' | cut -d= -f2)
    t_avg=$(echo "$out" | grep '^t_avg_s=' | cut -d= -f2)
    lam=$(echo "$out" | grep '^lambda=' | cut -d= -f2)

    echo "$cenario,$res,$threads,$sched,$chunk,$rep,$t_gen,$t_io,$t_tot,$t_max,$t_avg,$lam" >> "$CSV_FILE"
}

# Função auxiliar para executar e parsear Serial
run_serial() {
    local cenario="$1"
    local res="$2"
    local rep="$3"

    echo "  [SERIAL] cenario=$cenario res=$res rep=$rep"
    
    local out
    out=$(./serial/mandelbrot_seq "$cenario" "$res")
    
    local t_gen t_io t_tot
    t_gen=$(echo "$out" | grep '^tempo_geracao_s=' | cut -d= -f2)
    t_io=$(echo "$out" | grep '^tempo_io_s=' | cut -d= -f2)
    t_tot=$(echo "$out" | grep '^tempo_total_s=' | cut -d= -f2)

    echo "$cenario,$res,1,serial,0,$rep,$t_gen,$t_io,$t_tot,$t_gen,$t_gen,1.000000" >> "$CSV_FILE"
}

# ------------------------------------------------------------------------------
# BLOCO 0: Baseline Serial
# ------------------------------------------------------------------------------
echo "=================================================================="
echo " BLOCO 0: Baseline Serial (T1 de referência)"
echo "=================================================================="
for rep in 1 2 3; do
    run_serial "padrao" 4096 "$rep"
    run_serial "seahorse" 4096 "$rep"
done

for rep in 1 2 3; do
    run_serial "padrao" 8192 "$rep"
done

# Baseline Serial 16384 (1 repetição de validação e baseline)
run_serial "padrao" 16384 1

# ------------------------------------------------------------------------------
# BLOCO 1: Strong Scaling — Input Padrão (threads = 1, 2, 4, 8, 16, static)
# ------------------------------------------------------------------------------
echo "=================================================================="
echo " BLOCO 1: Strong Scaling (Input Padrão, static)"
echo "=================================================================="
for th in 1 2 4 8 16; do
    for rep in 1 2 3; do
        run_omp "padrao" 4096 "$th" "static" "default" "$rep"
    done
done

# ------------------------------------------------------------------------------
# BLOCO 2: Políticas e Chunks — Input Padrão (threads = 8)
# ------------------------------------------------------------------------------
echo "=================================================================="
echo " BLOCO 2: Politicas e Chunks (Input Padrao, threads=8)"
echo "=================================================================="
for sched in "dynamic" "guided"; do
    for chunk in 1 8 16 32 64; do
        for rep in 1 2 3; do
            run_omp "padrao" 4096 8 "$sched" "$chunk" "$rep"
        done
    done
done

for chunk in 1 8 16 32 64; do
    for rep in 1 2 3; do
        run_omp "padrao" 4096 8 "static" "$chunk" "$rep"
    done
done

# ------------------------------------------------------------------------------
# BLOCO 3: Caso de Estresse Seahorse (Strong Scaling + Politicas)
# ------------------------------------------------------------------------------
echo "=================================================================="
echo " BLOCO 3: Caso de Estresse Seahorse (Desbalanceamento)"
echo "=================================================================="
# Strong scaling com static
for th in 1 2 4 8 16; do
    for rep in 1 2 3; do
        run_omp "seahorse" 4096 "$th" "static" "default" "$rep"
    done
done

# Comparação de políticas em threads=8
for sched in "dynamic" "guided"; do
    for chunk in 1 8 16 32 64; do
        for rep in 1 2 3; do
            run_omp "seahorse" 4096 8 "$sched" "$chunk" "$rep"
        done
    done
done

for chunk in 1 8 16 32 64; do
    for rep in 1 2 3; do
        run_omp "seahorse" 4096 8 "static" "$chunk" "$rep"
    done
done

# ------------------------------------------------------------------------------
# BLOCO 4: Weak Scaling (4096² @ 1 thread, 8192² @ 4 threads, 16384² @ 16 threads)
# ------------------------------------------------------------------------------
echo "=================================================================="
echo " BLOCO 4: Weak Scaling (Carga constante por thread: 16M pixels/thread)"
echo "=================================================================="
# 4096² @ 1 thread (já rodado no bloco 1, mas registramos com tag de schedule dynamic,16 para consistência)
for rep in 1 2 3; do
    run_omp "padrao" 4096 1 "dynamic" 16 "$rep"
    run_omp "padrao" 8192 4 "dynamic" 16 "$rep"
    run_omp "padrao" 16384 16 "dynamic" 16 "$rep"
done

echo "=================================================================="
echo " Coleta experimental finalizada com sucesso! Dados em $CSV_FILE"
echo "=================================================================="
