#!/usr/bin/env python3
"""
summarize_results.py — Consolida metricas obrigatorias da Etapa 3 (Secao 9):
  - Tempo sem e com escrita em disco
  - Speedup e Eficiencia (RTX 5050 Laptop GPU: 20 SMs, 40 unidades FP64, 2560 nucleos CUDA)
  - Fator de Balanceamento de Carga (FBC) via clock64()
  - Escalabilidade forte (grid-stride 1..320 + grade cheia) e fraca (4096^2, 8192^2, 16384^2)
  - Analise quantitativa pelas Leis de Amdahl e Gustafson
  - Tabela unica consolidada: OpenMP (Etapa 1), MPI (Etapa 2) e CUDA (Etapa 3)
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUN_DIR = os.environ.get("TUN_DIR", os.path.join(ROOT, "output", "tuning"))
STRIDE_CSV = os.path.join(TUN_DIR, "stride_scaling.csv")
SCALING_CSV = os.path.join(TUN_DIR, "scaling.csv")
OUT_MD = os.path.join(TUN_DIR, "consolidated_summary.md")
GPU_SMS = int(os.environ.get("GPU_SMS", "20"))


def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    stride_rows = load_csv(STRIDE_CSV)
    scaling_rows = load_csv(SCALING_CSV)

    lines = ["# Resumo Consolidado — Etapa 3 (CUDA — RTX 5050 Laptop GPU)", ""]

    if stride_rows:
        lines += [f"## Escalabilidade Forte (Grid-Stride 16x16 = 256 threads/bloco, 4096x4096, {GPU_SMS} SMs)", ""]
        for scen_prefix, t_ser in [("full_B", 12431.057), ("seahorse_B", 5603.407)]:
            rows = [r for r in stride_rows if r["group"] == "strong_stride" and r["scenario"].startswith(scen_prefix)]
            if not rows:
                continue
            t_b1 = float(rows[0]["kernel_ms"])
            lines.append(f"### Cenario `{scen_prefix[:-2]}` (T_serial = {t_ser:.3f} ms, T_1bloco = {t_b1:.3f} ms)")
            lines.append("")
            lines.append("| Blocos | Threads | Kernel (ms) | Total (ms) | Speedup vs 1 blk | Speedup vs Serial | Eficiencia vs 1 blk |")
            lines.append("|---:|---:|---:|---:|---:|---:|---:|")
            for r in rows:
                b = int(r["scenario"].split("_B")[1])
                t = b * 256
                km = float(r["kernel_ms"])
                tm = float(r["total_ms"])
                sb = t_b1 / km
                ss = t_ser / tm
                eb = sb / min(b, GPU_SMS) * 100.0
                lines.append(f"| {b} | {t} | {km:.3f} | {tm:.3f} | {sb:.2f}x | {ss:.2f}x | {eb:.1f}% |")
            lines.append("")

        wrows = [r for r in stride_rows if r["group"] == "weak_stride"]
        if wrows:
            t_base = float(wrows[0]["total_ms"])
            lines += ["## Escalabilidade Fraca Proporcional (Grid-Stride: 16M pixels/bloco)", ""]
            lines.append("| Resolucao | Blocos | Pixels/bloco | Kernel (ms) | D->H (ms) | Total (ms) | Eficiencia Fraca (T1/Tp) |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|")
            for r in wrows:
                w = int(r["width"])
                b = int(r["scenario"].split("_B")[1])
                ppb = (w * w) // b
                km = float(r["kernel_ms"])
                dm = float(r["d2h_ms"])
                tm = float(r["total_ms"])
                eff = t_base / tm * 100.0
                lines.append(f"| {w}x{w} | {b} | {ppb:,} | {km:.3f} | {dm:.3f} | {tm:.3f} | {eff:.2f}% |")
            lines.append("")

    if scaling_rows:
        lines += ["## Escalabilidade por Resolucao (Grade Completa: 1 pixel/thread, 8x8)", ""]
        lines.append("| Resolucao | Variante | Kernel (ms) | D->H (ms) | Total (ms) | % D->H |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for r in scaling_rows:
            if r["variant"] == "naive" and r["ctab"] == "0" and r["mode"] == "sync":
                w = int(r["width"])
                km = float(r["kernel_ms"])
                dm = float(r["d2h_ms"])
                tm = float(r["total_ms"])
                lines.append(f"| {w}x{w} | naive sync | {km:.3f} | {dm:.3f} | {tm:.3f} | {100.0*dm/tm:.2f}% |")
        lines.append("")

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote", OUT_MD)


if __name__ == "__main__":
    main()
