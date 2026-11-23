#!/usr/bin/env python3
"""
plot_tuning.py — tabelas Markdown e graficos a partir do CSV do mandelbrot_bench.

Saidas (em --outdir, padrao = pasta do CSV):
  tuning_tables.md                tabelas por grupo/cenario (mediana, min, max)
  blocksweep_<cenario>.png        kernel x configuracao de bloco/grade (2D e 1D)
  variants_<cenario>.png          base x naive x ctab x warp x compact (x __constant__)
  chunk_<cenario>.png             compact: kernel x chunk (com a linha do naive)
  modes_<cenario>.png             sync x pinned x streams (custo host-device)
Requer apenas matplotlib.  Uso: python3 scripts/plot_tuning.py output/tuning/tuning.csv
"""
import argparse
import csv
import os
import sys
from collections import OrderedDict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FLOATS = ["h2d_ms", "kernel_ms", "kernel_min_ms", "kernel_max_ms", "d2h_ms",
          "total_ms", "total_min_ms", "total_max_ms", "write_ms"]
INTS = ["ctab", "bx", "by", "streams", "chunk", "width", "height", "max_iter", "reps"]


def load(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            for c in FLOATS:
                r[c] = float(r[c])
            for c in INTS:
                r[c] = int(r[c])
            rows.append(r)
    return rows


def vlabel(r):
    return r["variant"] + ("+ctab" if r["ctab"] else "") + ("[__constant__]" if r["params"] == "const" else "")


def blabel(r):
    return f"1D {r['bx'] * r['by']}" if r["layout"] == "1d" else f"2D {r['bx']}x{r['by']}"


def uniq(rows, key):
    d = OrderedDict()
    for r in rows:
        d[key(r)] = r          # a ultima execucao de cada configuracao vale
    return list(d.values())


def sel(rows, group, scen):
    return [r for r in rows if r["group"] == group and r["scenario"] == scen]


def f3(x):
    return "-" if x < 0 else f"{x:.3f}"


def table(md, head, body):
    md.append("| " + " | ".join(head) + " |")
    md.append("|" + "|".join(["---"] * len(head)) + "|")
    md.extend("| " + " | ".join(str(c) for c in b) + " |" for b in body)
    md.append("")


def bar(labels, vals, title, ylabel, path, ref=None):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, vals, color="tab:blue")
    if ref is not None:
        ax.axhline(ref, ls="--", color="gray", label="naive")
        ax.legend()
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--outdir")
    a = ap.parse_args()
    outdir = a.outdir or os.path.dirname(os.path.abspath(a.csv))
    os.makedirs(outdir, exist_ok=True)
    out = lambda n: os.path.join(outdir, n)  # noqa: E731
    rows = load(a.csv)
    if not rows:
        sys.exit("CSV vazio")

    md = ["# Tabelas de tuning (Parte 2)", "",
          f"GPU: {rows[0]['gpu']}. Mediana de {rows[0]['reps']} repeticoes (apos aquecimento); tempos em ms.", ""]
    if any(r["verify"] == "MISMATCH" for r in rows):
        md += ["**ATENCAO: ha configuracao com saida diferente do kernel base!**", ""]

    for scen in OrderedDict.fromkeys(r["scenario"] for r in rows):
        s0 = next(r for r in rows if r["scenario"] == scen)
        md += [f"## Cenario `{scen}` ({s0['width']}x{s0['height']}, MAX_ITER={s0['max_iter']})", ""]

        bs = uniq(sel(rows, "blocksweep", scen), lambda r: (r["variant"], r["layout"], r["bx"], r["by"]))
        if bs:
            md += ["### Bloco/grade", ""]
            table(md, ["Config", "Kernel (ms)", "min", "max"],
                  [[blabel(r), f3(r["kernel_ms"]), f3(r["kernel_min_ms"]), f3(r["kernel_max_ms"])] for r in bs])
            bar([blabel(r) for r in bs], [r["kernel_ms"] for r in bs],
                f"Bloco/grade, kernel naive ({scen})", "kernel (ms, mediana)", out(f"blocksweep_{scen}.png"))

        vs = uniq(sel(rows, "variants", scen), vlabel)
        nv = next((r for r in vs if vlabel(r) == "naive"), None)
        if vs:
            md += ["### Variantes (ingenua x otimizadas x compactada)", ""]
            table(md, ["Variante", "Bloco", "Chunk", "Kernel (ms)", "H->D (ms)", "Ganho vs naive", "Verificacao"],
                  [[vlabel(r), blabel(r), r["chunk"] or "-", f3(r["kernel_ms"]), f3(r["h2d_ms"]),
                    f"{nv['kernel_ms'] / r['kernel_ms']:.3f}x" if nv and r["kernel_ms"] > 0 else "-",
                    r["verify"]] for r in vs])
            bar([vlabel(r) for r in vs], [r["kernel_ms"] for r in vs], f"Variantes de kernel ({scen})",
                "kernel (ms, mediana)", out(f"variants_{scen}.png"), ref=nv["kernel_ms"] if nv else None)

        ck = sorted(uniq(sel(rows, "chunk", scen), lambda r: r["chunk"]), key=lambda r: r["chunk"])
        if ck:
            md += ["### compact: kernel x chunk", ""]
            table(md, ["Chunk", "Bloco", "Smem/bloco", "Kernel (ms)", "Ganho vs naive"],
                  [[r["chunk"], blabel(r), f"{r['bx'] * r['by'] * 40 + 128} B", f3(r["kernel_ms"]),
                    f"{nv['kernel_ms'] / r['kernel_ms']:.3f}x" if nv and r["kernel_ms"] > 0 else "-"] for r in ck])
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.plot([r["chunk"] for r in ck], [r["kernel_ms"] for r in ck], "o-", label="compact")
            if nv:
                ax.axhline(nv["kernel_ms"], ls="--", color="gray", label="naive")
            ax.set_xscale("log", base=2)
            ax.set_xlabel("chunk (iteracoes por rodada)")
            ax.set_ylabel("kernel (ms, mediana)")
            ax.set_title(f"Compactacao: efeito do chunk ({scen})")
            ax.legend()
            fig.tight_layout()
            fig.savefig(out(f"chunk_{scen}.png"), dpi=150)
            plt.close(fig)

        ms = uniq(sel(rows, "modes", scen), lambda r: (r["mode"], r["streams"]))
        if ms:
            base = next((r for r in ms if r["mode"] == "sync"), ms[0])
            md += ["### Custo host-device (sync x pinned x streams)", ""]
            table(md, ["Modo", "Streams", "Kernel (ms)", "D->H (ms)", "Total wall (ms)", "Ganho vs sync"],
                  [[r["mode"], r["streams"] or "-", f3(r["kernel_ms"]), f3(r["d2h_ms"]), f3(r["total_ms"]),
                    f"{base['total_ms'] / r['total_ms']:.3f}x"] for r in ms])
            labels = [r["mode"] + (f" S={r['streams']}" if r["streams"] else "") for r in ms]
            ker = [max(r["kernel_ms"], 0) for r in ms]
            d2h = [max(r["d2h_ms"], 0) for r in ms]
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.bar(labels, ker, label="kernel")
            ax.bar(labels, d2h, bottom=ker, label="D->H")
            ax.plot(labels, [r["total_ms"] for r in ms], "k_", markersize=18, label="total (wall)")
            ax.set_ylabel("ms (mediana)")
            ax.set_title(f"Host-device ({scen}); em streams kernel e D->H se sobrepoem")
            ax.legend()
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
            fig.tight_layout()
            fig.savefig(out(f"modes_{scen}.png"), dpi=150)
            plt.close(fig)

    open(out("tuning_tables.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("tabelas e graficos em", outdir)


if __name__ == "__main__":
    main()
