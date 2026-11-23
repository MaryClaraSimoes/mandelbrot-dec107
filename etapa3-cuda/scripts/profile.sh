#!/usr/bin/env bash
# ============================================================================
# profile.sh — profiling com Nsight Systems (nsys) e Nsight Compute (ncu).
#
# Objetivo (Parte 2): registrar ocupacao (occupancy), divergencia de warps e
# banda de memoria, comparando kernel ingenuo x compactado, nos dois cenarios.
#
#   nsys : linha do tempo — tempo de kernel, cudaMemcpy H<->D, cudaMalloc, e
#          sobreposicao copia/computacao no modo streams.
#   ncu  : metricas por kernel (ocupacao alcancada, threads ativas por warp,
#          uso da unidade FP64, banda DRAM).
#
# Saidas em output/prof/. Uso:
#   bash scripts/profile.sh            # N=1024 (ncu repete o kernel varias vezes; 4096 e lento)
#   N=2048 bash scripts/profile.sh
#
# IMPORTANTE (compatibilidade): ncu/nsys antigos nao suportam GPUs novas. Se o
# ncu reclamar que a arquitetura (ex.: Blackwell / sm_120) nao e suportada,
# instale um CUDA Toolkit mais recente (ver docs/parte2_tuning.md, secao 6).
# Nomes de metricas podem mudar entre versoes: `ncu --query-metrics` lista os
# validos na sua instalacao.
# ============================================================================
set -uo pipefail

BIN="${BIN:-./bin/mandelbrot_bench}"
N="${N:-1024}"
BB="${BEST_BLOCK:-16x16}"
OUTD="${OUTD:-output/prof}"
mkdir -p "$OUTD"

[ -x "$BIN" ] || { echo "Compile antes: make bench" >&2; exit 2; }

# Metricas pedidas no enunciado -> nomes de metricas do ncu
#  occupancy ........ sm__warps_active.avg.pct_of_peak_sustained_active
#  divergencia ...... smsp__thread_inst_executed_per_inst_executed.ratio
#                     (media de threads ativas por instrucao de warp; ideal = 32)
#                     smsp__sass_average_branch_targets_threads_uniform.pct
#  unidade FP64 ..... sm__inst_executed_pipe_fp64.avg.pct_of_peak_sustained_active
#  banda DRAM ....... dram__throughput.avg.pct_of_peak_sustained_elapsed
#                     dram__bytes_read.sum, dram__bytes_write.sum
#  duracao .......... gpu__time_duration.sum
METRICS="gpu__time_duration.sum,\
sm__warps_active.avg.pct_of_peak_sustained_active,\
sm__maximum_warps_per_active_cycle_pct,\
smsp__thread_inst_executed_per_inst_executed.ratio,\
smsp__sass_average_branch_targets_threads_uniform.pct,\
sm__inst_executed_pipe_fp64.avg.pct_of_peak_sustained_active,\
dram__throughput.avg.pct_of_peak_sustained_elapsed,\
dram__bytes_read.sum,dram__bytes_write.sum"

declare -a CASES=(
  "naive   full     --variant naive   --preset full"
  "compact full     --variant compact --preset full     --chunk 64"
  "naive   seahorse --variant naive   --preset seahorse"
  "compact seahorse --variant compact --preset seahorse --chunk 64"
)

for entry in "${CASES[@]}"; do
  read -r name scen rest <<<"$entry"
  tag="${name}_${scen}"
  # --width/--height antes de --preset (o preset usa a proporcao)
  ARGS="--width $N --height $N $rest --block $BB --reps 5 --warmup 1 --no-verify"

  echo "=== nsys: $tag"
  nsys profile --trace=cuda --stats=true --force-overwrite=true \
       -o "$OUTD/nsys_${tag}" "$BIN" $ARGS > "$OUTD/nsys_${tag}.txt" 2>&1 \
       || echo "   (nsys falhou; veja $OUTD/nsys_${tag}.txt)"

  echo "=== ncu : $tag (1 lancamento, apos o aquecimento)"
  # --launch-skip 1 pula o lancamento de aquecimento; --launch-count 1 mede um so.
  ncu --launch-skip 1 --launch-count 1 --metrics "$METRICS" \
      --csv --log-file "$OUTD/ncu_${tag}.csv" \
      "$BIN" $ARGS > "$OUTD/ncu_${tag}.stdout.txt" 2>&1 \
      || echo "   (ncu falhou; veja $OUTD/ncu_${tag}.stdout.txt)"
done

echo
echo "Relatorio completo (secoes de occupancy/warp state) de UM caso, para anexar ao relatorio:"
echo "  ncu --set full --launch-skip 1 --launch-count 1 -o $OUTD/ncu_full_compact_seahorse \\"
echo "      $BIN --width $N --height $N --variant compact --preset seahorse --block $BB --reps 5 --warmup 1 --no-verify"
echo "Resultados em $OUTD/"
