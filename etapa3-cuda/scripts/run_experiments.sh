#!/usr/bin/env bash
# ==============================================================================
# run_experiments.sh — Esqueleto de Automação Experimental (Etapa 3 — CUDA)
# ==============================================================================
# NOTA: Este arquivo é um esqueleto entregue na Parte 1 (Integrante 1).
# A implementação completa dos experimentos será preenchida na Parte 2
# (Integrante 2) e utilizada para coleta de métricas na Parte 3 (Integrante 3).
# ==============================================================================

set -euo pipefail

# Diretórios base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_DIR="${ROOT_DIR}/bin"
OUT_DIR="${ROOT_DIR}/output"

mkdir -p "${OUT_DIR}"

# ------------------------------------------------------------------------------
# TODO (Parte 2 — Integrante 2):
# 1. Definir configurações de blocos de threads a avaliar:
#    Ex.: (8x8), (16x16), (32x8), (32x16), (32x32), (256x1), (512x1)
# ------------------------------------------------------------------------------
# BLOCK_CONFIGS=("8x8" "16x16" "32x8" "32x16" "32x32")

# ------------------------------------------------------------------------------
# TODO (Parte 2 — Integrante 2):
# 2. Executar o Caso Base (Seção 5.2: 4096x4096, Re[-2,1], Im[-1.5,1.5], MAX_ITER=1000)
#    para múltiplas repetições e coletar tempo do kernel e tempo de cópia D->H.
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# TODO (Parte 2 — Integrante 2):
# 3. Executar o Caso de Desbalanceamento Acentuado (Seção 5.3 — Vale dos
#    Cavalos-Marinhos: centro -0.743643887 + 0.131825904i, largura 3.0e-3,
#    MAX_ITER=5000) e validar cada saída com ${BIN_DIR}/compare.
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# TODO (Parte 2 / Parte 3):
# 4. Executar escalabilidade fraca/forte (resoluções 2048^2, 4096^2, 8192^2)
#    e consolidar resultados em CSV para análise de Speedup e Eficiência.
# ------------------------------------------------------------------------------

echo "[INFO] Esqueleto run_experiments.sh pronto para preenchimento na Parte 2."
