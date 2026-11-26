#!/usr/bin/env bash
# ==============================================================================
# run_experiments.sh — Automacao Experimental Completa (Etapa 3 — CUDA)
# ==============================================================================
# Executa:
#   1. Validacao de corretude (base e seahorse) via ./bin/compare
#   2. Varredura de tuning (blocksweep, variants, chunk, modes) via run_tuning.sh
#   3. Escalabilidade forte (4096^2 variando blocos grid-stride: 1..224 e grade cheia)
#   4. Escalabilidade fraca (4096^2, 8192^2, 16384^2 proporcionais + grade cheia)
#   5. Profiling oficial nsys / ncu via profile.sh (quando executado como root)
#   6. Medicao de escrita em disco (.bin + .pgm) isolada
#   7. Consolidacao de tabelas (Speedup, Eficiencia, FBC, Amdahl/Gustafson)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

BIN_DIR="${ROOT_DIR}/bin"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/output}"
TUN_DIR="${OUT_DIR}/tuning"
mkdir -p "${OUT_DIR}" "${TUN_DIR}"

REPS="${REPS:-5}"
WARMUP="${WARMUP:-1}"

echo "=== 1. Validacao de Corretude (Secao 5.5) ==="
"${BIN_DIR}/mandelbrot_serial" --out-bin "${OUT_DIR}/serial_base.bin" --out-pgm "${OUT_DIR}/serial_base.pgm"
"${BIN_DIR}/mandelbrot_cuda"   --out-bin "${OUT_DIR}/cuda_base.bin"   --out-pgm "${OUT_DIR}/cuda_base.pgm"
"${BIN_DIR}/compare" "${OUT_DIR}/serial_base.bin" "${OUT_DIR}/cuda_base.bin"

"${BIN_DIR}/mandelbrot_serial" --preset seahorse --out-bin "${OUT_DIR}/serial_zoom.bin" --out-pgm "${OUT_DIR}/serial_zoom.pgm"
"${BIN_DIR}/mandelbrot_cuda"   --preset seahorse --out-bin "${OUT_DIR}/cuda_zoom.bin"   --out-pgm "${OUT_DIR}/cuda_zoom.pgm"
"${BIN_DIR}/compare" "${OUT_DIR}/serial_zoom.bin" "${OUT_DIR}/cuda_zoom.bin"

if [ "${SKIP_TUNING:-0}" != "1" ]; then
  echo "=== 2. Varredura de Tuning (4096x4096) ==="
  rm -f "${TUN_DIR}/tuning.csv"
  OUT="${TUN_DIR}/tuning.csv" bash "${SCRIPT_DIR}/run_tuning.sh"
fi

echo "=== 3. Escalabilidade Forte (4096x4096, grid-stride 1..320 blocos, 20 SMs) ==="
STRIDE_CSV="${TUN_DIR}/stride_scaling.csv"
rm -f "${STRIDE_CSV}"
for scen in full seahorse; do
  for B in 1 2 4 5 10 20 40 80 160 320; do
    echo ">>> [strong_stride/${scen}] blocks=${B} (16x16=256 threads/bloco)"
    "${BIN_DIR}/mandelbrot_bench" --width 4096 --height 4096 --preset "${scen}" \
      --variant naive --block 16x16 --grid-blocks "${B}" \
      --reps "${REPS}" --warmup "${WARMUP}" \
      --csv "${STRIDE_CSV}" --group "strong_stride" --scenario "${scen}_B${B}" \
      | grep -E "^Verificacao|^Kernel|^TOTAL"
  done
done

echo "=== 4. Escalabilidade Fraca (4096^2, 8192^2, 16384^2 proporcionais) ==="
# Proporcional por blocos (1 -> 4 -> 16 blocos de 256 threads = 16M pixels/bloco)
"${BIN_DIR}/mandelbrot_bench" --width 4096  --height 4096  --preset full --variant naive --block 16x16 --grid-blocks 1  --reps "${REPS}" --warmup "${WARMUP}" --csv "${STRIDE_CSV}" --group "weak_stride" --scenario "4096_B1"  | grep -E "^Verificacao|^Kernel|^TOTAL"
"${BIN_DIR}/mandelbrot_bench" --width 8192  --height 8192  --preset full --variant naive --block 16x16 --grid-blocks 4  --reps "${REPS}" --warmup "${WARMUP}" --csv "${STRIDE_CSV}" --group "weak_stride" --scenario "8192_B4"  | grep -E "^Verificacao|^Kernel|^TOTAL"
"${BIN_DIR}/mandelbrot_bench" --width 16384 --height 16384 --preset full --variant naive --block 16x16 --grid-blocks 16 --no-verify --reps "${REPS}" --warmup "${WARMUP}" --csv "${STRIDE_CSV}" --group "weak_stride" --scenario "16384_B16" | grep -E "^Kernel|^TOTAL"

echo "=== 4b. Escalabilidade por Resolucao (1024^2..16384^2, grade completa 8x8) ==="
SCALING_CSV="${TUN_DIR}/scaling.csv"
rm -f "${SCALING_CSV}"
for N in 1024 2048 4096 8192 16384; do
  VFLAG=""
  R=7; W=2
  if [ "${N}" -eq 16384 ]; then VFLAG="--no-verify"; R=5; W=1; fi
  "${BIN_DIR}/mandelbrot_bench" --width "${N}" --height "${N}" --preset full --variant naive --block 8x8 --mode sync ${VFLAG} --reps "${R}" --warmup "${W}" --csv "${SCALING_CSV}" --group scaling --scenario "N${N}" | grep -E "^Verificacao|^Kernel|^TOTAL"
  "${BIN_DIR}/mandelbrot_bench" --width "${N}" --height "${N}" --preset full --variant naive --block 8x8 --ctab --mode sync ${VFLAG} --reps "${R}" --warmup "${W}" --csv "${SCALING_CSV}" --group scaling --scenario "N${N}_ctab" | grep -E "^Verificacao|^Kernel|^TOTAL"
  "${BIN_DIR}/mandelbrot_bench" --width "${N}" --height "${N}" --preset full --variant naive --block 8x8 --mode streams --streams 16 ${VFLAG} --reps "${R}" --warmup "${W}" --csv "${SCALING_CSV}" --group scaling --scenario "N${N}_streams16" | grep -E "^Verificacao|^TOTAL"
done

echo "=== 5. Profiling nsys / ncu (requer root se RmProfilingAdminOnly=1) ==="
if [ "$(id -u)" -eq 0 ]; then
  BEST_BLOCK=8x8 bash "${SCRIPT_DIR}/profile.sh"
else
  echo "[INFO] Pulei ncu (sem root). Rode: sudo BEST_BLOCK=8x8 bash scripts/profile.sh"
fi

echo "=== 6. Medicao de I/O em Disco (4096^2, 8192^2, 16384^2) ==="
for N in 4096 8192 16384; do
  "${BIN_DIR}/mandelbrot_bench" --width "${N}" --height "${N}" --preset full --variant naive --block 8x8 \
    --reps 5 --warmup 1 --no-verify --out-bin "/tmp/io_${N}.bin" --out-pgm "/tmp/io_${N}.pgm" \
    | grep -E "^Resolucao|^Kernel|^D->H|^TOTAL|^Escrita"
  rm -f "/tmp/io_${N}.bin" "/tmp/io_${N}.pgm"
done

echo "=== 7. Consolidacao de Metricas e Graficos ==="
python3 "${SCRIPT_DIR}/summarize_results.py"
python3 "${SCRIPT_DIR}/generate_report_plots.py"

echo "[OK] Experimentos da Etapa 3 concluidos."
