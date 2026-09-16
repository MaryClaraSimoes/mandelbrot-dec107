#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_plots_and_tables.py — Processamento de Métricas e Gráficos da Etapa 1
=============================================================================

Lê 'experiments.csv', calcula médias, desvios padrão, Speedup, Eficiência,
ajuste de Amdahl/Gustafson, e gera gráficos em 'docs/plots/' e tabelas formatadas.
"""

import os
import csv
import math
import collections
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT_ROOT, "experiments.csv")
PLOTS_DIR = os.path.join(PROJECT_ROOT, "docs", "plots")
SUMMARY_TABLES_PATH = os.path.join(PROJECT_ROOT, "docs", "summary_tables.md")

os.makedirs(PLOTS_DIR, exist_ok=True)

def mean(values):
    return sum(values) / len(values) if values else 0.0

def stddev(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)

def load_data(filepath):
    """Carrega dados brutos e agrupa por configuração."""
    # chave: (cenario, resolucao, threads, schedule, chunk) -> lista de dicts
    data = collections.defaultdict(list)
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cenario = row["cenario"]
            res = int(row["resolucao"])
            th = int(row["threads"])
            sched = row["schedule"]
            chunk = row["chunk"]
            key = (cenario, res, th, sched, chunk)
            data[key].append({
                "t_gen": float(row["tempo_geracao_s"]),
                "t_io": float(row["tempo_io_s"]),
                "t_tot": float(row["tempo_total_s"]),
                "t_max": float(row["t_max_s"]),
                "t_avg": float(row["t_avg_s"]),
                "lambda": float(row["lambda"]),
            })
    return data

def aggregate_data(raw_data):
    """Calcula médias e desvios."""
    agg = {}
    for key, runs in raw_data.items():
        t_gens = [r["t_gen"] for r in runs]
        t_ios = [r["t_io"] for r in runs]
        t_tots = [r["t_tot"] for r in runs]
        lambdas = [r["lambda"] for r in runs]
        t_maxs = [r["t_max"] for r in runs]
        t_avgs = [r["t_avg"] for r in runs]

        agg[key] = {
            "n": len(runs),
            "t_gen_mean": mean(t_gens),
            "t_gen_std": stddev(t_gens),
            "t_io_mean": mean(t_ios),
            "t_io_std": stddev(t_ios),
            "t_tot_mean": mean(t_tots),
            "t_tot_std": stddev(t_tots),
            "lambda_mean": mean(lambdas),
            "lambda_std": stddev(lambdas),
            "t_max_mean": mean(t_maxs),
            "t_avg_mean": mean(t_avgs),
        }
    return agg

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Erro: {CSV_PATH} não encontrado.")
        return

    raw = load_data(CSV_PATH)
    agg = aggregate_data(raw)

    # Identifica baselines seriais T1
    # ("padrao", 4096, 1, "serial", "0")
    t1_padrao = agg.get(("padrao", 4096, 1, "serial", "0"), {}).get("t_gen_mean", None)
    t1_seahorse = agg.get(("seahorse", 4096, 1, "serial", "0"), {}).get("t_gen_mean", None)
    t1_8192 = agg.get(("padrao", 8192, 1, "serial", "0"), {}).get("t_gen_mean", None)
    t1_16384 = agg.get(("padrao", 16384, 1, "serial", "0"), {}).get("t_gen_mean", None)

    print("Baselines seriais detectados:")
    print(f"  - Padrao 4096: {t1_padrao:.4f} s" if t1_padrao else "  - Padrao 4096: N/A")
    print(f"  - Seahorse 4096: {t1_seahorse:.4f} s" if t1_seahorse else "  - Seahorse 4096: N/A")
    print(f"  - Padrao 8192: {t1_8192:.4f} s" if t1_8192 else "  - Padrao 8192: N/A")
    print(f"  - Padrao 16384: {t1_16384:.4f} s" if t1_16384 else "  - Padrao 16384: N/A")

    # =========================================================================
    # 1. Gráfico de Strong Scaling (Speedup vs Threads)
    # =========================================================================
    threads_list = [1, 2, 4, 8, 16]
    speedup_padrao = []
    speedup_seahorse = []

    for p in threads_list:
        val_p = agg.get(("padrao", 4096, p, "static", "default"))
        if val_p and t1_padrao:
            speedup_padrao.append(t1_padrao / val_p["t_gen_mean"])
        else:
            speedup_padrao.append(None)

        val_s = agg.get(("seahorse", 4096, p, "static", "default"))
        if val_s and t1_seahorse:
            speedup_seahorse.append(t1_seahorse / val_s["t_gen_mean"])
        else:
            speedup_seahorse.append(None)

    # Ajuste de Amdahl para o caso padrão: S(p) = 1 / ((1-f) + f/p)
    # Estima f usando p=16
    f_padrao = 0.95
    if speedup_padrao[-1] is not None:
        s16 = speedup_padrao[-1]
        p_ref = 16
        # s16 = 1 / ( (1-f) + f/p_ref ) => (1-f) + f/p_ref = 1/s16 => 1 - f*(1 - 1/p_ref) = 1/s16
        # f = (1 - 1/s16) / (1 - 1/p_ref)
        if s16 > 1:
            f_padrao = (1.0 - (1.0 / s16)) / (1.0 - (1.0 / p_ref))
            f_padrao = min(max(f_padrao, 0.5), 0.999)

    amdahl_padrao = [1.0 / ((1.0 - f_padrao) + (f_padrao / p)) for p in threads_list]

    plt.figure(figsize=(9, 6), dpi=300)
    plt.plot(threads_list, threads_list, 'k--', label="Speedup Linear Ideal ($S_p = p$)", linewidth=1.8)
    if any(s is not None for s in speedup_padrao):
        plt.plot(threads_list, speedup_padrao, 'o-', color='#1f77b4', label="Input Padrão (Obs. estático)", linewidth=2.2, markersize=7)
    if any(s is not None for s in speedup_seahorse):
        plt.plot(threads_list, speedup_seahorse, 's-', color='#d62728', label="Caso Seahorse (Obs. estático)", linewidth=2.2, markersize=7)
    plt.plot(threads_list, amdahl_padrao, ':', color='#2ca02c', label=f"Modelo de Amdahl ($f = {f_padrao*100:.1f}\\%$)", linewidth=2.0)

    plt.title("Escalabilidade Forte: Speedup vs Número de Threads ($4096 \\times 4096$)", fontsize=13, pad=12, fontweight='bold')
    plt.xlabel("Número de Threads ($p$)", fontsize=11)
    plt.ylabel("Speedup ($S_p = T_1 / T_p$)", fontsize=11)
    plt.xticks(threads_list)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=10, loc="upper left")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "speedup_strong_scaling.png"))
    plt.close()

    # =========================================================================
    # 2. Gráfico de Eficiência vs Threads
    # =========================================================================
    eff_padrao = [(sp / p) * 100.0 if sp is not None else None for p, sp in zip(threads_list, speedup_padrao)]
    eff_seahorse = [(ss / p) * 100.0 if ss is not None else None for p, ss in zip(threads_list, speedup_seahorse)]

    plt.figure(figsize=(9, 6), dpi=300)
    plt.axhline(100.0, color='k', linestyle='--', linewidth=1.8, label="Eficiência Ideal ($100\\%$)")
    if any(e is not None for e in eff_padrao):
        plt.plot(threads_list, eff_padrao, 'o-', color='#1f77b4', label="Input Padrão (Estático)", linewidth=2.2, markersize=7)
    if any(e is not None for e in eff_seahorse):
        plt.plot(threads_list, eff_seahorse, 's-', color='#d62728', label="Caso Seahorse (Estático)", linewidth=2.2, markersize=7)

    plt.title("Eficiência Paralela vs Número de Threads ($4096 \\times 4096$)", fontsize=13, pad=12, fontweight='bold')
    plt.xlabel("Número de Threads ($p$)", fontsize=11)
    plt.ylabel("Eficiência Paralela ($E_p = S_p / p$ [\\%])", fontsize=11)
    plt.xticks(threads_list)
    plt.ylim(0, 110)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=10, loc="lower left")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "efficiency_strong_scaling.png"))
    plt.close()

    # =========================================================================
    # 3. Comparativo de Políticas e Chunks (Input Padrão, 8 threads)
    # =========================================================================
    chunks = [1, 8, 16, 32, 64]
    
    def get_sched_times(cenario, sched_name):
        res_list = []
        for c in chunks:
            row = agg.get((cenario, 4096, 8, sched_name, str(c)))
            if row:
                res_list.append(row["t_gen_mean"])
            else:
                res_list.append(None)
        return res_list

    t_padrao_dyn = get_sched_times("padrao", "dynamic")
    t_padrao_gui = get_sched_times("padrao", "guided")
    t_padrao_sta = get_sched_times("padrao", "static")

    plt.figure(figsize=(9, 5.5), dpi=300)
    plt.plot(chunks, t_padrao_dyn, 'o-', color='#1f77b4', label="dynamic", linewidth=2.0, markersize=6)
    plt.plot(chunks, t_padrao_gui, 's-', color='#ff7f0e', label="guided", linewidth=2.0, markersize=6)
    plt.plot(chunks, t_padrao_sta, '^--', color='#2ca02c', label="static", linewidth=2.0, markersize=6)

    plt.title("Comparação de Políticas e Chunks: Input Padrão ($p = 8$, $4096^2$)", fontsize=13, pad=12, fontweight='bold')
    plt.xlabel("Tamanho de Chunk", fontsize=11)
    plt.ylabel("Tempo de Geração (segundos)", fontsize=11)
    plt.xticks(chunks)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "schedule_comparison_padrao.png"))
    plt.close()

    # =========================================================================
    # 4. Comparativo de Políticas e Chunks (Caso Seahorse, 8 threads)
    # =========================================================================
    t_sea_dyn = get_sched_times("seahorse", "dynamic")
    t_sea_gui = get_sched_times("seahorse", "guided")
    t_sea_sta = get_sched_times("seahorse", "static")

    plt.figure(figsize=(9, 5.5), dpi=300)
    plt.plot(chunks, t_sea_dyn, 'o-', color='#1f77b4', label="dynamic", linewidth=2.0, markersize=6)
    plt.plot(chunks, t_sea_gui, 's-', color='#ff7f0e', label="guided", linewidth=2.0, markersize=6)
    plt.plot(chunks, t_sea_sta, '^--', color='#2ca02c', label="static", linewidth=2.0, markersize=6)

    plt.title("Comparação de Políticas e Chunks: Caso Seahorse ($p = 8$, $4096^2$)", fontsize=13, pad=12, fontweight='bold')
    plt.xlabel("Tamanho de Chunk", fontsize=11)
    plt.ylabel("Tempo de Geração (segundos)", fontsize=11)
    plt.xticks(chunks)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "schedule_comparison_seahorse.png"))
    plt.close()

    # =========================================================================
    # 5. Fator de Balanceamento de Carga (lambda) vs Configuração (Seahorse)
    # =========================================================================
    def get_lambdas(cenario, sched_name):
        return [agg.get((cenario, 4096, 8, sched_name, str(c)), {}).get("lambda_mean", None) for c in chunks]

    lam_sea_dyn = get_lambdas("seahorse", "dynamic")
    lam_sea_gui = get_lambdas("seahorse", "guided")
    lam_sea_sta = get_lambdas("seahorse", "static")

    plt.figure(figsize=(9, 5.5), dpi=300)
    plt.plot(chunks, lam_sea_dyn, 'o-', color='#1f77b4', label="dynamic", linewidth=2.0, markersize=6)
    plt.plot(chunks, lam_sea_gui, 's-', color='#ff7f0e', label="guided", linewidth=2.0, markersize=6)
    plt.plot(chunks, lam_sea_sta, '^--', color='#2ca02c', label="static", linewidth=2.0, markersize=6)
    plt.axhline(1.0, color='gray', linestyle=':', label="Balanceamento Perfeito ($\lambda = 1.0$)")

    plt.title("Fator de Balanceamento de Carga ($\\lambda = T_{avg} / T_{max}$) no Seahorse ($p = 8$)", fontsize=13, pad=12, fontweight='bold')
    plt.xlabel("Tamanho de Chunk", fontsize=11)
    plt.ylabel("Fator de Balanceamento $\\lambda$", fontsize=11)
    plt.xticks(chunks)
    plt.ylim(0.5, 1.05)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=10, loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "load_balance_lambda.png"))
    plt.close()

    # =========================================================================
    # 6. Weak Scaling (4096²@1, 8192²@4, 16384²@16)
    # =========================================================================
    # Carga constante: 16.777.216 pixels / thread
    ws_configs = [(4096, 1), (8192, 4), (16384, 16)]
    ws_times = []
    ws_effs = []
    t_base_ws = None

    for res, p in ws_configs:
        entry = agg.get(("padrao", res, p, "dynamic", "16"))
        if not entry:
            entry = agg.get(("padrao", res, p, "static", "default"))
        if entry:
            t = entry["t_gen_mean"]
            ws_times.append(t)
            if t_base_ws is None:
                t_base_ws = t
            # Gustafson Efficiency: E_weak = T(1) / T(p)
            eff_w = (t_base_ws / t) * 100.0 if t > 0 else 0.0
            ws_effs.append(eff_w)
        else:
            ws_times.append(None)
            ws_effs.append(None)

    labels = ["$4096^2$ (p=1)", "$8192^2$ (p=4)", "$16384^2$ (p=16)"]

    fig, ax1 = plt.subplots(figsize=(9, 5.5), dpi=300)
    ax2 = ax1.twinx()

    x = range(len(labels))
    ax1.plot(x, ws_times, 'o-', color='#1f77b4', linewidth=2.2, markersize=8, label="Tempo de Geração (s)")
    ax2.plot(x, ws_effs, 's--', color='#d62728', linewidth=2.2, markersize=8, label="Eficiência de Gustafson (%)")

    ax1.set_xlabel("Escala do Problema e Recursos Alocados", fontsize=11)
    ax1.set_ylabel("Tempo de Geração (s)", color='#1f77b4', fontsize=11)
    ax2.set_ylabel("Eficiência de Escalabilidade Fraca (%)", color='#d62728', fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=10)
    ax2.set_ylim(0, 110)
    ax1.grid(True, linestyle="--", alpha=0.6)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower left", fontsize=10)

    plt.title("Escalabilidade Fraca (Weak Scaling): Carga Constante ($16\\text{M pixels/thread}$)", fontsize=13, pad=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "weak_scaling.png"))
    plt.close()

    # =========================================================================
    # 7. Separação Tempo de Geração vs Tempo de I/O
    # =========================================================================
    resolutions = [4096, 8192, 16384]
    gen_times_res = []
    io_times_res = []

    for r in resolutions:
        # Pega a melhor configuração com 16 threads
        entry = agg.get(("padrao", r, 16, "dynamic", "16"))
        if not entry:
            entry = agg.get(("padrao", r, 16, "static", "default"))
        if not entry:
            entry = agg.get(("padrao", r, 1, "serial", "0"))
        if entry:
            gen_times_res.append(entry["t_gen_mean"])
            io_times_res.append(entry["t_io_mean"])
        else:
            gen_times_res.append(0.0)
            io_times_res.append(0.0)

    plt.figure(figsize=(9, 5.5), dpi=300)
    width_bar = 0.35
    x_pos = range(len(resolutions))

    plt.bar([p - width_bar/2 for p in x_pos], gen_times_res, width=width_bar, color='#1f77b4', label="Tempo de Geração (Computação)")
    plt.bar([p + width_bar/2 for p in x_pos], io_times_res, width=width_bar, color='#ff7f0e', label="Tempo de I/O (Escrita em Disco)")

    plt.title("Separação Obrigatória: Tempo de Geração vs Tempo de I/O (Seção 9)", fontsize=13, pad=12, fontweight='bold')
    plt.xlabel("Resolução da Matriz", fontsize=11)
    plt.ylabel("Tempo (segundos)", fontsize=11)
    plt.xticks(x_pos, [f"{r}x{r}" for r in resolutions])
    plt.grid(True, linestyle="--", alpha=0.6, axis='y')
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, "io_vs_compute.png"))
    plt.close()

    # =========================================================================
    # 8. Geração de Tabelas Markdown para o Relatório
    # =========================================================================
    with open(SUMMARY_TABLES_PATH, "w", encoding="utf-8") as f:
        f.write("# Tabelas de Métricas Experimentais da Etapa 1\n\n")

        # Tabela 1: Strong Scaling (Input Padrão)
        f.write("### Tabela 1: Escalabilidade Forte — Input Padrão (4096×4096, MAX_ITER=1000, static)\n\n")
        f.write("| Threads (p) | Tempo Geração (Tₚ) [s] | Desvio Padrão [s] | Speedup (Sₚ) | Eficiência (Eₚ) [%] | Fator λ | Tempo I/O [s] |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        if t1_padrao:
            f.write(f"| Serial (1) | {t1_padrao:.4f} | - | 1.0000 | 100.00% | 1.0000 | {agg.get(('padrao', 4096, 1, 'serial', '0'), {}).get('t_io_mean', 0.0):.4f} |\n")
        for p, sp, ep in zip(threads_list, speedup_padrao, eff_padrao):
            row = agg.get(("padrao", 4096, p, "static", "default"))
            if row and sp is not None:
                f.write(f"| {p} | {row['t_gen_mean']:.4f} | ±{row['t_gen_std']:.4f} | {sp:.4f} | {ep:.2f}% | {row['lambda_mean']:.4f} | {row['t_io_mean']:.4f} |\n")
        f.write("\n\n")

        # Tabela 2: Strong Scaling (Seahorse)
        f.write("### Tabela 2: Escalabilidade Forte — Caso de Estresse Seahorse (4096×4096, MAX_ITER=5000, static)\n\n")
        f.write("| Threads (p) | Tempo Geração (Tₚ) [s] | Desvio Padrão [s] | Speedup (Sₚ) | Eficiência (Eₚ) [%] | Fator λ | Tempo I/O [s] |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        if t1_seahorse:
            f.write(f"| Serial (1) | {t1_seahorse:.4f} | - | 1.0000 | 100.00% | 1.0000 | {agg.get(('seahorse', 4096, 1, 'serial', '0'), {}).get('t_io_mean', 0.0):.4f} |\n")
        for p, ss, es in zip(threads_list, speedup_seahorse, eff_seahorse):
            row = agg.get(("seahorse", 4096, p, "static", "default"))
            if row and ss is not None:
                f.write(f"| {p} | {row['t_gen_mean']:.4f} | ±{row['t_gen_std']:.4f} | {ss:.4f} | {es:.2f}% | {row['lambda_mean']:.4f} | {row['t_io_mean']:.4f} |\n")
        f.write("\n\n")

        # Tabela 3: Políticas e Chunks (Seahorse, threads=8)
        f.write("### Tabela 3: Avaliação de Políticas e Chunks — Caso Seahorse (p = 8 threads)\n\n")
        f.write("| Política | Chunk | Tempo Geração [s] | Desvio Padrão [s] | Speedup (S₈) | Fator de Balanceamento (λ) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
        for sched in ["static", "dynamic", "guided"]:
            for c in chunks:
                row = agg.get(("seahorse", 4096, 8, sched, str(c)))
                if row and t1_seahorse:
                    sp = t1_seahorse / row["t_gen_mean"]
                    f.write(f"| `{sched}` | {c} | {row['t_gen_mean']:.4f} | ±{row['t_gen_std']:.4f} | {sp:.4f} | {row['lambda_mean']:.4f} |\n")
        f.write("\n\n")

        # Tabela 4: Weak Scaling
        f.write("### Tabela 4: Escalabilidade Fraca (Weak Scaling — Carga Fixa: 16M pixels/thread)\n\n")
        f.write("| Resolução | Pixels Totais | Threads (p) | Tempo Geração [s] | Eficiência de Gustafson [%] | Tempo I/O [s] |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for (r, p), tw, ew in zip(ws_configs, ws_times, ws_effs):
            entry = agg.get(("padrao", r, p, "dynamic", "16"))
            if not entry:
                entry = agg.get(("padrao", r, p, "static", "default"))
            if entry and tw is not None:
                tot_pix = r * r
                f.write(f"| {r}×{r} | {tot_pix:,} | {p} | {tw:.4f} | {ew:.2f}% | {entry['t_io_mean']:.4f} |\n")
        f.write("\n")

    print(f"Gráficos gerados em: {PLOTS_DIR}")
    print(f"Tabelas de sumário geradas em: {SUMMARY_TABLES_PATH}")

if __name__ == "__main__":
    main()
