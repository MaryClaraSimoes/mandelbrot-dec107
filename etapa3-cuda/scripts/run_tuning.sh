#!/usr/bin/env bash
# ============================================================================
# run_tuning.sh — varreduras de tuning da Parte 2 (Integrante 2).
#
# Executa bin/mandelbrot_bench varias vezes e acumula UMA linha por
# configuracao (mediana de >= 5 repeticoes) em output/tuning/tuning.csv.
#
# Grupos (coluna `group` do CSV):
#   blocksweep  kernel naive: 8x8, 16x16, 32x8, 32x16, 32x32 (2D) e 1D (128..1024)
#   variants    base, naive, naive --ctab, warp, compact (+ naive com __constant__ se
#               existir o binario BIN_CONST, compilado com -DUSE_CONST_PARAMS)
#   chunk       compact variando --chunk (16..1024)
#   modes       sync x pinned x streams (2,4,8,16) com o melhor bloco
#
# Cenarios: full (Secao 5.2, MAX_ITER=1000) e seahorse (Secao 5.3, MAX_ITER=5000).
#
# Uso:
#   bash scripts/run_tuning.sh                 # completo (4096x4096)
#   QUICK=1 bash scripts/run_tuning.sh         # teste rapido do pipeline (1024x1024)
#   GROUPS_TO_RUN="blocksweep chunk" bash scripts/run_tuning.sh
#   BEST_BLOCK=32x8 bash scripts/run_tuning.sh # forca o bloco usado em variants/chunk/modes
#
# Observacao: o tempo total depende da GPU (double precision e lento em GPUs de
# consumo). Rode primeiro com QUICK=1 para estimar.
# ============================================================================
set -euo pipefail

BIN="${BIN:-./bin/mandelbrot_bench}"
BIN_CONST="${BIN_CONST:-./bin/mandelbrot_bench_const}"
OUT="${OUT:-output/tuning/tuning.csv}"
N="${N:-4096}"
REPS="${REPS:-7}"
WARMUP="${WARMUP:-2}"
GROUPS_TO_RUN="${GROUPS_TO_RUN:-blocksweep variants chunk modes}"
SCENARIOS="${SCENARIOS:-full seahorse}"

if [ "${QUICK:-0}" = "1" ]; then
  N=1024; REPS=5; WARMUP=1
fi

if [ ! -x "$BIN" ]; then
  echo "Executavel $BIN nao encontrado. Compile com: make bench" >&2
  exit 2
fi
mkdir -p "$(dirname "$OUT")"

scenario_args() {  # --width/--height ANTES de --preset (o preset usa a proporcao)
  case "$1" in
    full)     echo "--width $N --height $N --preset full" ;;
    seahorse) echo "--width $N --height $N --preset seahorse" ;;
    *) echo "cenario desconhecido: $1" >&2; exit 2 ;;
  esac
}

run() {  # run <group> <scenario> <args do harness...>
  local group="$1" scen="$2"; shift 2
  echo ">>> [$group/$scen] $*"
  # shellcheck disable=SC2046
  "$BIN" $(scenario_args "$scen") "$@" \
      --reps "$REPS" --warmup "$WARMUP" --csv "$OUT" --group "$group" --scenario "$scen" \
      | grep -E "^Verificacao|^Kernel|^D->H|^TOTAL pipeline|^Escrita"
}

best_block() {  # escolhe o bloco 2D de menor mediana do kernel naive no grupo blocksweep
  local scen="$1"
  if [ -n "${BEST_BLOCK:-}" ]; then echo "$BEST_BLOCK"; return; fi
  python3 - "$OUT" "$scen" <<'PY'
import csv, sys
path, scen = sys.argv[1], sys.argv[2]
best = None
try:
    for r in csv.DictReader(open(path)):
        if r["group"] == "blocksweep" and r["scenario"] == scen and r["variant"] == "naive" \
           and r["layout"] == "2d":
            t = float(r["kernel_ms"])
            if best is None or t < best[0]:
                best = (t, f'{r["bx"]}x{r["by"]}')
except FileNotFoundError:
    pass
print(best[1] if best else "16x16")
PY
}

want() { [[ " $GROUPS_TO_RUN " == *" $1 "* ]]; }

for scen in $SCENARIOS; do
  if want blocksweep; then
    for blk in 8x8 16x16 32x8 32x16 32x32; do
      run blocksweep "$scen" --variant naive --block "$blk"
    done
    for n in 128 256 512 1024; do          # 1D: BXxBY = n x 1
      run blocksweep "$scen" --variant naive --layout 1d --block "${n}x1"
    done
  fi

  BB="$(best_block "$scen")"
  echo "=== [$scen] melhor bloco 2D (naive) para os proximos grupos: $BB"

  if want variants; then
    run variants "$scen" --variant base --block 16x16
    run variants "$scen" --variant naive   --block "$BB"
    run variants "$scen" --variant naive   --block "$BB" --ctab        # c calculado no host
    run variants "$scen" --variant warp    --block "$BB"
    run variants "$scen" --variant compact --block "$BB"
    if [ -x "$BIN_CONST" ]; then                                       # parametros em __constant__
      BIN="$BIN_CONST" run variants "$scen" --variant naive --block "$BB"
    fi
  fi

  if want chunk; then
    for ch in 16 32 64 128 256 512 1024; do
      run chunk "$scen" --variant compact --block "$BB" --chunk "$ch"
    done
  fi

  if want modes; then
    run modes "$scen" --variant naive --block "$BB" --mode sync
    run modes "$scen" --variant naive --block "$BB" --mode pinned
    for s in 2 4 8 16; do
      run modes "$scen" --variant naive --block "$BB" --mode streams --streams "$s"
    done
  fi
done

echo
echo "Concluido. CSV em $OUT"
echo "Gere tabelas e graficos com: python3 scripts/plot_tuning.py $OUT"
