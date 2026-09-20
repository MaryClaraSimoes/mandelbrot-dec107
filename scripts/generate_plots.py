#!/usr/bin/env python3
"""
Gera gráficos e tabelas resumo a partir de experiments.csv.
Entrada:  experiments.csv (na raiz do projeto)
Saída:    docs/plots/*.png
          docs/summary_tables.md
"""

import csv
import os
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "experiments.csv")
PLOTS_DIR = os.path.join(ROOT, "docs", "plots")
TABLES_PATH = os.path.join(ROOT, "docs", "summary_tables.md")

os.makedirs(PLOTS_DIR, exist_ok=True)

# ---------------------------------------------------------------
# Baselines seriais (T1) por cenário — extraídos do CSV
# ---------------------------------------------------------------
BASELINE_SERIAL = {}
with open(CSV_PATH, newline="") as f:
    for row in csv.DictReader(f):
        if row["bloco"] == "baseline":
            BASELINE_SERIAL[row["cenario"]] = float(row["tempo_s"])

print("Baselines seriais:", BASELINE_SERIAL)

# ---------------------------------------------------------------
# Leitura e agrupamento
# ---------------------------------------------------------------
# chave: (bloco, cenario, resolucao, threads, schedule, chunk)
# valor: lista de tempos (3 repetições)
grupos = defaultdict(list)
lambda_por_grupo = defaultdict(list)

with open(CSV_PATH, newline="") as f:
    for row in csv.DictReader(f):
        if row["bloco"] == "baseline":
            continue
        key = (
            row["bloco"],
            row["cenario"],
            row["resolucao"],
            int(row["threads"]),
            row["schedule"],
            row["chunk"] if row["chunk"] else "-",
        )
        grupos[key].append(float(row["tempo_s"]))
        if row["lambda"]:
            try:
                lambda_por_grupo[key].append(float(row["lambda"]))
            except ValueError:
                pass

# ---------------------------------------------------------------
# Estatísticas agregadas
# ---------------------------------------------------------------
def stats(tempos):
    if len(tempos) == 1:
        return tempos[0], 0.0
    return statistics.mean(tempos), statistics.stdev(tempos)

resumo = []  # lista de dicts
for key, tempos in sorted(grupos.items()):
    bloco, cenario, resolucao, threads, schedule, chunk = key
    media, desvio = stats(tempos)
    t1 = BASELINE_SERIAL.get(cenario, None)
    speedup = t1 / media if t1 else None
    eficiencia = speedup / threads if speedup else None
    lambdas = lambda_por_grupo.get(key, [])
    lambda_med = statistics.mean(lambdas) if lambdas else None
    resumo.append({
        "bloco": bloco,
        "cenario": cenario,
        "resolucao": resolucao,
        "threads": threads,
        "schedule": schedule,
        "chunk": chunk,
        "tempo_medio": media,
        "desvio": desvio,
        "speedup": speedup,
        "eficiencia": eficiencia,
        "lambda": lambda_med,
    })

# ---------------------------------------------------------------
# Tabelas resumo em Markdown
# ---------------------------------------------------------------
def fmt(v, casas=4):
    if v is None:
        return "—"
    return f"{v:.{casas}f}"

with open(TABLES_PATH, "w") as f:
    f.write("# Tabelas Resumo — Etapa 1 (OpenMP)\n\n")
    f.write("Geradas a partir de `experiments.csv`.\n\n")

    # Tabela 1 — Strong scaling padrão (bloco 1)
    f.write("## Tabela 1 — Strong scaling no input padrão (bloco 1)\n\n")
    f.write("| Threads | Tempo (s) | Speedup | Eficiência | λ |\n")
    f.write("|:-:|:-:|:-:|:-:|:-:|\n")
    for r in resumo:
        if r["bloco"] == "1":
            f.write(f"| {r['threads']} | {fmt(r['tempo_medio'])} ± {fmt(r['desvio'])} | "
                    f"{fmt(r['speedup'])} | {fmt(r['eficiencia'])} | {fmt(r['lambda'])} |\n")
    f.write("\n")

    # Tabela 2 — Políticas e chunks padrão (bloco 2)
    f.write("## Tabela 2 — Políticas e chunks no input padrão (bloco 2, p=8)\n\n")
    f.write("| Política | Chunk | Tempo (s) | Speedup | Eficiência | λ |\n")
    f.write("|:---|:-:|:-:|:-:|:-:|:-:|\n")
    for r in resumo:
        if r["bloco"] == "2":
            f.write(f"| {r['schedule']} | {r['chunk']} | {fmt(r['tempo_medio'])} ± {fmt(r['desvio'])} | "
                    f"{fmt(r['speedup'])} | {fmt(r['eficiencia'])} | {fmt(r['lambda'])} |\n")
    f.write("\n")

    # Tabela 3 — Strong scaling Seahorse (bloco 3)
    f.write("## Tabela 3 — Strong scaling no Seahorse (bloco 3)\n\n")
    f.write("| Threads | Tempo (s) | Speedup | Eficiência | λ |\n")
    f.write("|:-:|:-:|:-:|:-:|:-:|\n")
    for r in resumo:
        if r["bloco"] == "3":
            f.write(f"| {r['threads']} | {fmt(r['tempo_medio'])} ± {fmt(r['desvio'])} | "
                    f"{fmt(r['speedup'])} | {fmt(r['eficiencia'])} | {fmt(r['lambda'])} |\n")
    f.write("\n")

    # Tabela 4 — Políticas e chunks Seahorse (bloco 3b)
    f.write("## Tabela 4 — Políticas e chunks no Seahorse (bloco 3b, p=8)\n\n")
    f.write("| Política | Chunk | Tempo (s) | Speedup | Eficiência | λ |\n")
    f.write("|:---|:-:|:-:|:-:|:-:|:-:|\n")
    for r in resumo:
        if r["bloco"] == "3b":
            f.write(f"| {r['schedule']} | {r['chunk']} | {fmt(r['tempo_medio'])} ± {fmt(r['desvio'])} | "
                    f"{fmt(r['speedup'])} | {fmt(r['eficiencia'])} | {fmt(r['lambda'])} |\n")
    f.write("\n")

    # Tabela 5 — Weak scaling (bloco 4)
    f.write("## Tabela 5 — Weak scaling (bloco 4)\n\n")
    f.write("| Resolução | Threads | Política | Tempo (s) |\n")
    f.write("|:-:|:-:|:---|:-:|\n")
    for r in resumo:
        if r["bloco"] == "4":
            f.write(f"| {r['resolucao']} | {r['threads']} | {r['schedule']},1 | {fmt(r['tempo_medio'])} |\n")
    f.write("\n")

print("Tabelas salvas em", TABLES_PATH)

# ---------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------
def filtrar(bloco=None, cenario=None, schedule=None, chunk=None):
    out = []
    for r in resumo:
        if bloco is not None and r["bloco"] != bloco: continue
        if cenario is not None and r["cenario"] != cenario: continue
        if schedule is not None and r["schedule"] != schedule: continue
        if chunk is not None and r["chunk"] != chunk: continue
        out.append(r)
    return out

# --- Gráfico 1: Speedup vs threads (padrão e Seahorse) ---
fig, ax = plt.subplots(figsize=(8, 5))
for cenario, bloco in [("full", "1"), ("seahorse", "3")]:
    dados = sorted(filtrar(bloco=bloco, cenario=cenario), key=lambda r: r["threads"])
    threads = [r["threads"] for r in dados]
    speedup = [r["speedup"] for r in dados]
    ax.plot(threads, speedup, marker="o", label=f"{cenario} (static)")
ax.plot([1, 16], [1, 16], "--", color="gray", label="ideal (linear)")
ax.set_xlabel("Número de threads")
ax.set_ylabel("Speedup")
ax.set_title("Speedup vs Threads — Input Padrão e Seahorse")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PLOTS_DIR, "speedup_strong.png"), dpi=150)
plt.close(fig)

# --- Gráfico 2: Eficiência vs threads ---
fig, ax = plt.subplots(figsize=(8, 5))
for cenario, bloco in [("full", "1"), ("seahorse", "3")]:
    dados = sorted(filtrar(bloco=bloco, cenario=cenario), key=lambda r: r["threads"])
    threads = [r["threads"] for r in dados]
    efic = [r["eficiencia"] for r in dados]
    ax.plot(threads, efic, marker="s", label=f"{cenario} (static)")
ax.axhline(1.0, linestyle="--", color="gray", label="ideal (100%)")
ax.set_xlabel("Número de threads")
ax.set_ylabel("Eficiência")
ax.set_title("Eficiência vs Threads — Input Padrão e Seahorse")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PLOTS_DIR, "efficiency_strong.png"), dpi=150)
plt.close(fig)

# --- Gráfico 3: Tempo vs política × chunk (input padrão, p=8) ---
fig, ax = plt.subplots(figsize=(8, 5))
for sched in ["static", "dynamic", "guided"]:
    dados = sorted([r for r in filtrar(bloco="2", cenario="full", schedule=sched) if r["chunk"] != "-"],
                   key=lambda r: int(r["chunk"]))
    chunks = [int(r["chunk"]) for r in dados]
    tempos = [r["tempo_medio"] for r in dados]
    ax.plot(chunks, tempos, marker="o", label=sched)
ax.set_xlabel("Chunk size")
ax.set_ylabel("Tempo médio (s)")
ax.set_title("Tempo vs Política e Chunk — Input Padrão (p=8)")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PLOTS_DIR, "time_vs_schedule_full.png"), dpi=150)
plt.close(fig)

# --- Gráfico 4: Tempo vs política × chunk (Seahorse, p=8) ---
fig, ax = plt.subplots(figsize=(8, 5))
for sched in ["static", "dynamic", "guided"]:
    dados = sorted([r for r in filtrar(bloco="3b", cenario="seahorse", schedule=sched) if r["chunk"] != "-"],
                   key=lambda r: int(r["chunk"]))
    chunks = [int(r["chunk"]) for r in dados]
    tempos = [r["tempo_medio"] for r in dados]
    ax.plot(chunks, tempos, marker="o", label=sched)
ax.set_xlabel("Chunk size")
ax.set_ylabel("Tempo médio (s)")
ax.set_title("Tempo vs Política e Chunk — Seahorse (p=8)")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PLOTS_DIR, "time_vs_schedule_seahorse.png"), dpi=150)
plt.close(fig)

# --- Gráfico 5: λ vs política × chunk (padrão e Seahorse, p=8) ---
fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
for ax, (bloco, cenario, titulo) in zip(axes, [("2", "full", "Input Padrão"),
                                                ("3b", "seahorse", "Seahorse")]):
    for sched in ["static", "dynamic", "guided"]:
        dados = sorted([r for r in filtrar(bloco=bloco, cenario=cenario, schedule=sched) if r["chunk"] != "-"],
                       key=lambda r: int(r["chunk"]))
        chunks = [int(r["chunk"]) for r in dados]
        lambdas = [r["lambda"] for r in dados]
        ax.plot(chunks, lambdas, marker="^", label=sched)
    ax.axhline(1.0, linestyle="--", color="gray", label="ideal (1.0)")
    ax.set_xlabel("Chunk size")
    ax.set_title(titulo)
    ax.grid(True, alpha=0.3)
    ax.legend()
axes[0].set_ylabel("λ (t_max / t_mean)")
fig.suptitle("Fator de Balanceamento λ vs Política e Chunk (p=8)")
fig.tight_layout()
fig.savefig(os.path.join(PLOTS_DIR, "lambda_vs_schedule.png"), dpi=150)
plt.close(fig)

# --- Gráfico 6: Weak scaling ---
fig, ax = plt.subplots(figsize=(8, 5))
for sched in ["static", "dynamic"]:
    dados = [r for r in filtrar(bloco="4", schedule=sched)]
    # ordena por resolução
    ordem = {"4096x4096": 0, "8192x8192": 1, "16384x16384": 2}
    dados = sorted(dados, key=lambda r: ordem.get(r["resolucao"], 99))
    labels = [r["resolucao"] for r in dados]
    tempos = [r["tempo_medio"] for r in dados]
    ax.plot(labels, tempos, marker="o", label=f"{sched},1")
ax.set_xlabel("Resolução")
ax.set_ylabel("Tempo médio (s)")
ax.set_title("Weak Scaling — 16M pixels/thread")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PLOTS_DIR, "weak_scaling.png"), dpi=150)
plt.close(fig)

print("Gráficos salvos em", PLOTS_DIR)
print("Arquivos gerados:")
for f in sorted(os.listdir(PLOTS_DIR)):
    print("  ", f)
