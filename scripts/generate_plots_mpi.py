"""
Gera gráficos e tabelas resumo a partir de experiments_mpi.csv (Etapa 2 — MPI),
com comparações contra os resultados OpenMP de experiments.csv (Etapa 1).

Entradas: experiments_mpi.csv  (na raiz do projeto)
          experiments.csv      (na raiz do projeto; opcional — sem ele, só MPI)
Saídas:   docs/plots_mpi/*.png
          docs/summary_tables_mpi.md

Convenções
----------
* Todos os valores reportados são média amostral ± desvio padrão amostral
  sobre as repetições de cada configuração.
  Speedup, eficiência e f_lb são calculados por repetição e só então
  agregados (média ± dp), de modo que o dp também reflete a variação deles.
* Speedup = T_serial / T_paralelo ; Eficiência = Speedup / p.
* Weak scaling: eficiência fraca = T(p=1) / T(p), com T(p=1) = média das
  repetições com p=1 da mesma estratégia/política.
* λ (MPI) = (t_max - t_min) / t_max (0.0 = ideal).
* Referências (ideal / serial): quando a referência distorce a escala do
  gráfico (ref_max / topo_dados > LIMIAR_REF), são gerados DOIS arquivos:
      <nome>.png          -> só os resultados (escala ajustada aos dados)
      <nome>_com_ref.png  -> resultados + referência (ideal/serial)
  Caso contrário, gera-se um único <nome>.png já com a referência.
"""

import csv
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------
# Caminhos e parâmetros
# ---------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_MPI = os.path.join(ROOT, "experiments_mpi.csv")
CSV_OMP = os.path.join(ROOT, "experiments.csv")
PLOTS_DIR = os.path.join(ROOT, "docs", "plots_mpi")
TABLES_PATH = os.path.join(ROOT, "docs", "summary_tables_mpi.md")

os.makedirs(PLOTS_DIR, exist_ok=True)

LIMIAR_REF = 1.25          # referência > 1.25x o topo dos dados => separa os gráficos
P_COMUNS = [1, 2, 4, 8]    # nº de processos/threads presentes nas duas etapas
ESTRATEGIAS = ["block", "cyclic"]

# (cenário MPI, cenário OpenMP, bloco strong OMP, bloco schedule OMP, rótulo)
CMP = [
    ("strong", "full", "1", "2", "Input padrão"),
    ("seahorse", "seahorse", "3", "3b", "Seahorse"),
]

ESTILO = {
    "MPI block":        dict(color="tab:blue",   marker="o", linestyle="-"),
    "MPI cyclic":       dict(color="tab:orange", marker="s", linestyle="-"),
    "OpenMP static":    dict(color="tab:green",  marker="^", linestyle="-"),
    "OpenMP static,1":  dict(color="tab:olive",  marker="P", linestyle="none"),
    "OpenMP dynamic,1": dict(color="tab:red",    marker="*", linestyle="none"),
}

# ---------------------------------------------------------------
# Utilidades estatísticas
# ---------------------------------------------------------------
def media_dp(valores):
    """Média amostral e desvio padrão amostral (None se n == 1)."""
    if not valores:
        return None, None
    if len(valores) == 1:
        return valores[0], None
    return statistics.mean(valores), statistics.stdev(valores)


# ---------------------------------------------------------------
# Leitura do CSV MPI
# ---------------------------------------------------------------
if not os.path.exists(CSV_MPI):
    sys.exit(f"Arquivo não encontrado: {CSV_MPI}")

CAMPOS_MPI = {
    "tempo": "tempo_total_s",
    "speedup": "speedup",
    "efic": "eficiencia",
    "flb": "f_lb",
    "t_serial": "t_serial_s",
}

raw = defaultdict(lambda: defaultdict(list))
corretude = defaultdict(list)
px_div_todos, diff_todos = [], []

with open(CSV_MPI, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        key = (row["cenario"], row["estrategia"], int(row["processos"]),
               row["resolucao"], int(row["max_iter"]))
        for nome, col in CAMPOS_MPI.items():
            raw[key][nome].append(float(row[col]))
        corretude[key].append(row["corretude"].strip())
        px_div_todos.append(int(float(row["px_divergentes"])))
        diff_todos.append(float(row["diff_max"]))


def corr_str(lista):
    ok = sum(c.lower() in ("identica", "idêntica") for c in lista)
    if ok == len(lista):
        return f"idêntica ({ok}/{len(lista)})"
    return f"**DIVERGENTE** ({ok}/{len(lista)} idênticas)"


# T(p=1) do weak scaling, por estratégia
t1_weak_mpi = {}
for (cen, est, p, res, it), d in raw.items():
    if cen == "weak" and p == 1:
        t1_weak_mpi[est] = statistics.mean(d["tempo"])

resumo_mpi = []
for key in sorted(raw):
    cen, est, p, res, it = key
    d = raw[key]
    r = {
        "cenario": cen, "estrategia": est, "p": p, "resolucao": res,
        "max_iter": it, "n": len(d["tempo"]),
        "t_serial": statistics.mean(d["t_serial"]),
        "corretude": corr_str(corretude[key]),
    }
    for nome in ("tempo", "speedup", "efic", "flb"):
        r[nome], r[nome + "_sd"] = media_dp(d[nome])
    if cen == "weak" and est in t1_weak_mpi:
        r["efic_fraca"], r["efic_fraca_sd"] = media_dp(
            [t1_weak_mpi[est] / t for t in d["tempo"]])
    else:
        r["efic_fraca"] = r["efic_fraca_sd"] = None
    resumo_mpi.append(r)


def mpi_get(cenario, estrategia, p):
    for r in resumo_mpi:
        if (r["cenario"], r["estrategia"], r["p"]) == (cenario, estrategia, p):
            return r
    return None


def mpi_serie(cenario, estrategia, campo):
    rs = sorted((r for r in resumo_mpi
                 if r["cenario"] == cenario and r["estrategia"] == estrategia),
                key=lambda r: r["p"])
    return ([r["p"] for r in rs], [r[campo] for r in rs],
            [r[campo + "_sd"] for r in rs])


# ---------------------------------------------------------------
# Leitura do CSV OpenMP (opcional)
# ---------------------------------------------------------------
resumo_omp = {}   # chave: (bloco, cenario, threads, schedule, chunk)
TEM_OMP = os.path.exists(CSV_OMP)

if TEM_OMP:
    baseline_omp = {}
    grupos = defaultdict(lambda: {"tempo": [], "flb": []})
    with open(CSV_OMP, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["bloco"] == "baseline":
                baseline_omp[row["cenario"]] = float(row["tempo_s"])
                continue
            key = (row["bloco"], row["cenario"], row["resolucao"],
                   int(row["threads"]), row["schedule"], row["chunk"] or "-")
            grupos[key]["tempo"].append(float(row["tempo_s"]))
            if row["lambda"]:
                try:
                    grupos[key]["flb"].append(float(row["lambda"]))
                except ValueError:
                    pass

    # T(p=1) do weak scaling OpenMP, por (schedule, chunk)
    t1_weak_omp = {}
    for (b, c, res, t, s, ch), g in grupos.items():
        if b == "4" and t == 1:
            t1_weak_omp[(s, ch)] = statistics.mean(g["tempo"])

    for (b, c, res, t, s, ch), g in sorted(grupos.items()):
        r = {"resolucao": res, "n": len(g["tempo"])}
        r["tempo"], r["tempo_sd"] = media_dp(g["tempo"])
        r["flb"], r["flb_sd"] = media_dp(g["flb"])
        t1 = baseline_omp.get(c)
        if b != "4" and t1:
            r["speedup"], r["speedup_sd"] = media_dp([t1 / x for x in g["tempo"]])
            r["efic"], r["efic_sd"] = media_dp([t1 / x / t for x in g["tempo"]])
        else:
            r["speedup"] = r["speedup_sd"] = r["efic"] = r["efic_sd"] = None
        if b == "4" and (s, ch) in t1_weak_omp:
            r["efic_fraca"], r["efic_fraca_sd"] = media_dp(
                [t1_weak_omp[(s, ch)] / x for x in g["tempo"]])
        else:
            r["efic_fraca"] = r["efic_fraca_sd"] = None
        resumo_omp[(b, c, t, s, ch)] = r
else:
    print(f"AVISO: {CSV_OMP} não encontrado — comparações com OpenMP serão omitidas.")


def omp_get(bloco, cenario, threads, schedule, chunk="-"):
    return resumo_omp.get((bloco, cenario, threads, schedule, chunk))


def omp_serie(bloco, cenario, campo, pmax=max(P_COMUNS)):
    pts = sorted((k[2], r) for k, r in resumo_omp.items()
                 if k[0] == bloco and k[1] == cenario and k[3] == "static"
                 and k[2] <= pmax)
    return ([p for p, _ in pts], [r[campo] for _, r in pts],
            [r[campo + "_sd"] for _, r in pts])


# ---------------------------------------------------------------
# Tabelas resumo em Markdown
# ---------------------------------------------------------------
def fmt(v, casas=4):
    return "—" if v is None else f"{v:.{casas}f}"


def pm(m, s, casas=4):
    """'média ± desvio padrão' (n=1 não tem desvio padrão definido)."""
    if m is None:
        return "—"
    if s is None:
        return f"{m:.{casas}f} (n=1)"
    return f"{m:.{casas}f} ± {s:.{casas}f}"


def pixels_por_unidade(resolucao, p):
    w, h = resolucao.lower().split("x")
    return int(w) * int(h) // p


def rotulo_cenario_mpi(cen):
    rs = [r for r in resumo_mpi if r["cenario"] == cen]
    return f"{rs[0]['resolucao']}, {rs[0]['max_iter']} iterações" if rs else cen


def linhas_cmp(cm, co, b1, b2):
    """Linhas (rótulo, p, dict) para as tabelas de comparação OpenMP x MPI."""
    linhas = []
    for p in P_COMUNS:
        if TEM_OMP:
            o = omp_get(b1, co, p, "static")
            if o:
                linhas.append(("OpenMP static", p, o))
        for est in ESTRATEGIAS:
            m = mpi_get(cm, est, p)
            if m:
                linhas.append((f"MPI {est}", p, m))
        if TEM_OMP and p == max(P_COMUNS):
            for sched in ("static", "dynamic"):
                o = omp_get(b2, co, p, sched, "1")
                if o:
                    linhas.append((f"OpenMP {sched},1", p, o))
    return linhas


NOTA_DP = ("Valores: **média ± desvio padrão amostral** (n = 3 repetições). "
           "Speedup, eficiência e f_lb calculados por repetição e depois agregados.\n\n")

with open(TABLES_PATH, "w", encoding="utf-8") as f:
    f.write("# Tabelas Resumo — Etapa 2 (MPI)\n\n")
    f.write("Geradas a partir de `experiments_mpi.csv` "
            "(comparações com `experiments.csv`, Etapa 1 — OpenMP).\n\n")

    # Tabelas 1 e 2 — Strong scaling MPI
    for num, (cen, nome) in enumerate([("strong", "input padrão"),
                                       ("seahorse", "Seahorse")], start=1):
        rs = [r for r in resumo_mpi if r["cenario"] == cen]
        if not rs:
            continue
        f.write(f"## Tabela {num} — Strong scaling MPI, {nome} "
                f"({rotulo_cenario_mpi(cen)})\n\n")
        f.write(NOTA_DP)
        f.write(f"T_serial = {rs[0]['t_serial']:.6f} s.\n\n")
        f.write("| Estratégia | Processos | Tempo (s) | Speedup | Eficiência | f_lb | Corretude |\n")
        f.write("|:---|:-:|:-:|:-:|:-:|:-:|:---|\n")
        for est in ESTRATEGIAS:
            for r in sorted((x for x in rs if x["estrategia"] == est),
                            key=lambda x: x["p"]):
                f.write(f"| {est} | {r['p']} | {pm(r['tempo'], r['tempo_sd'], 6)} | "
                        f"{pm(r['speedup'], r['speedup_sd'])} | "
                        f"{pm(r['efic'], r['efic_sd'])} | "
                        f"{pm(r['flb'], r['flb_sd'])} | {r['corretude']} |\n")
        f.write("\n")

    # Tabela 3 — Weak scaling MPI
    rs = [r for r in resumo_mpi if r["cenario"] == "weak"]
    if rs:
        f.write("## Tabela 3 — Weak scaling MPI\n\n")
        f.write(NOTA_DP)
        f.write("Eficiência fraca = T(p=1) / T(p). Speedup é relativo ao serial "
                "da respectiva resolução.\n\n")
        f.write("| Estratégia | Processos | Resolução | Pixels/proc | T_serial (s) | Tempo (s) | "
                "Speedup vs serial | Eficiência fraca | f_lb | Corretude |\n")
        f.write("|:---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:---|\n")
        for est in ESTRATEGIAS:
            for r in sorted((x for x in rs if x["estrategia"] == est),
                            key=lambda x: x["p"]):
                f.write(f"| {est} | {r['p']} | {r['resolucao']} | "
                        f"{pixels_por_unidade(r['resolucao'], r['p']):,} | "
                        f"{r['t_serial']:.6f} | {pm(r['tempo'], r['tempo_sd'], 6)} | "
                        f"{pm(r['speedup'], r['speedup_sd'])} | "
                        f"{pm(r['efic_fraca'], r['efic_fraca_sd'])} | "
                        f"{pm(r['flb'], r['flb_sd'])} | {r['corretude']} |\n")
        f.write("\n")

    # Tabelas 4 e 5 — Comparação OpenMP x MPI (strong)
    if TEM_OMP:
        for num, (cm, co, b1, b2, nome) in enumerate(CMP, start=4):
            f.write(f"## Tabela {num} — Comparação OpenMP × MPI, {nome} (strong scaling)\n\n")
            f.write(NOTA_DP)
            f.write("| Implementação | p | Resolução | Tempo (s) | Speedup | Eficiência | λ / f_lb |\n")
            f.write("|:---|:-:|:-:|:-:|:-:|:-:|:-:|\n")
            for rot, p, r in linhas_cmp(cm, co, b1, b2):
                casas_t = 6 if rot.startswith("MPI") else 4
                f.write(f"| {rot} | {p} | {r['resolucao']} | {pm(r['tempo'], r['tempo_sd'], casas_t)} | "
                        f"{pm(r['speedup'], r['speedup_sd'])} | {pm(r['efic'], r['efic_sd'])} | "
                        f"{pm(r['flb'], r['flb_sd'])} |\n")
            f.write("\n")

        # Tabela 6 — Comparação weak scaling
        f.write("## Tabela 6 — Comparação OpenMP × MPI (weak scaling)\n\n")
        f.write(NOTA_DP.replace("(n = 3 repetições)", "(n = 3 no MPI)"))
        f.write("Eficiência fraca = T(p=1) / T(p). A carga por unidade de execução difere "
                "entre as etapas (16M pixels/thread no OpenMP; 262.144 pixels/processo no MPI), "
                "então compare a **eficiência**, não o tempo. No OpenMP, o bloco 4 tem "
                "apenas 1 repetição por configuração (`n=1`: desvio padrão não definido).\n\n")
        f.write("| Implementação | p | Resolução | Pixels/unidade | Tempo (s) | Eficiência fraca |\n")
        f.write("|:---|:-:|:-:|:-:|:-:|:-:|\n")
        linhas = []
        for (b, c, t, s, ch), r in resumo_omp.items():
            if b == "4":
                rot = "OpenMP static" if s == "static" else f"OpenMP {s},{ch}"
                linhas.append((rot, t, r))
        for r in resumo_mpi:
            if r["cenario"] == "weak":
                linhas.append((f"MPI {r['estrategia']}", r["p"], r))
        ordem_impl = {"OpenMP static": 0, "OpenMP dynamic,1": 1,
                      "MPI block": 2, "MPI cyclic": 3}
        for rot, p, r in sorted(linhas, key=lambda x: (ordem_impl.get(x[0], 9), x[1])):
            f.write(f"| {rot} | {p} | {r['resolucao']} | "
                    f"{pixels_por_unidade(r['resolucao'], p):,} | "
                    f"{pm(r['tempo'], r['tempo_sd'], 6 if rot.startswith('MPI') else 4)} | "
                    f"{pm(r['efic_fraca'], r['efic_fraca_sd'])} |\n")
        f.write("\n")

    # Tabela 7 — Corretude
    f.write("## Tabela 7 — Verificação de corretude (todas as execuções MPI)\n\n")
    n_tot = sum(len(v) for v in corretude.values())
    n_ok = sum(c.lower() in ("identica", "idêntica")
               for v in corretude.values() for c in v)
    f.write("| Execuções | Idênticas ao serial | Máx. px divergentes | Máx. diff |\n")
    f.write("|:-:|:-:|:-:|:-:|\n")
    f.write(f"| {n_tot} | {n_ok} | {max(px_div_todos)} | {max(diff_todos):g} |\n\n")

print("Tabelas salvas em", TABLES_PATH)


# ---------------------------------------------------------------
# Infraestrutura de gráficos
# ---------------------------------------------------------------
def salvar(nome, builder, ref_max):
    """
    builder(com_ref) -> Figure.
    Se a referência (ref_max) distorcer a escala dos dados, salva dois arquivos
    (<nome>.png sem referência e <nome>_com_ref.png); senão, um só com referência.
    """
    fig = builder(False)
    topo_dados = max(ax.get_ylim()[1] for ax in fig.axes)
    distorce = ref_max is not None and ref_max / topo_dados > LIMIAR_REF
    if distorce:
        fig.savefig(os.path.join(PLOTS_DIR, f"{nome}.png"), dpi=150)
        plt.close(fig)
        fig2 = builder(True)
        fig2.savefig(os.path.join(PLOTS_DIR, f"{nome}_com_ref.png"), dpi=150)
        plt.close(fig2)
        print(f"  {nome}: referência distorce a escala -> 2 gráficos (sem/com ref)")
    else:
        plt.close(fig)
        fig2 = builder(True)
        fig2.savefig(os.path.join(PLOTS_DIR, f"{nome}.png"), dpi=150)
        plt.close(fig2)


def plot_serie(ax, x, y, e, rotulo):
    e = [0.0 if v is None else v for v in e]
    ax.errorbar(x, y, yerr=e, capsize=3, label=rotulo, **ESTILO[rotulo])


def ref_ideal_speedup(ax):
    pmax = max(P_COMUNS)
    ax.plot([1, pmax], [1, pmax], "--", color="gray", label="ideal (linear)")


def ref_um(ax, rotulo):
    ax.axhline(1.0, linestyle="--", color="gray", label=rotulo)

def ref_zero(ax, rotulo):
    ax.axhline(0.0, linestyle="--", color="gray", label=rotulo)

def formatar_p(ax, ps=P_COMUNS):
    ax.set_xscale("log", base=2)
    ax.set_xticks(ps)
    ax.set_xticklabels([str(p) for p in ps])
    ax.minorticks_off()
    ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------
# Gráficos — MPI (strong scaling)
# ---------------------------------------------------------------
def builder_strong_mpi(campo, ylabel, titulo, ref):
    def build(com_ref):
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for ax, (cen, nome) in zip(axes, [("strong", "Input padrão"),
                                          ("seahorse", "Seahorse")]):
            for est in ESTRATEGIAS:
                x, y, e = mpi_serie(cen, est, campo)
                plot_serie(ax, x, y, e, f"MPI {est}")
            if com_ref:
                if ref == "speedup":
                    ref_ideal_speedup(ax)
                elif ref == "um":
                    ref_um(ax, "ideal (100%)" if campo == "efic" else "ideal (1.0)")
                elif ref == "zero":
                     ref_zero(ax, "ideal (0.0)")
                elif ref == "serial":
                    ts = next(r["t_serial"] for r in resumo_mpi if r["cenario"] == cen)
                    ax.axhline(ts, linestyle="--", color="gray", label="serial")
            formatar_p(ax)
            ax.set_xlabel("Número de processos")
            ax.set_title(f"{nome} ({rotulo_cenario_mpi(cen)})", fontsize=10)
            ax.legend()
        axes[0].set_ylabel(ylabel)
        fig.suptitle(titulo)
        fig.tight_layout()
        return fig
    return build


print("Gerando gráficos MPI...")
t_serial_max = max(r["t_serial"] for r in resumo_mpi if r["cenario"] in ("strong", "seahorse"))

salvar("speedup_strong_mpi",
       builder_strong_mpi("speedup", "Speedup", "MPI — Speedup vs Processos", "speedup"),
       ref_max=max(P_COMUNS))
salvar("efficiency_strong_mpi",
       builder_strong_mpi("efic", "Eficiência", "MPI — Eficiência vs Processos", "um"),
       ref_max=1.0)
salvar("time_strong_mpi",
       builder_strong_mpi("tempo", "Tempo médio (s)", "MPI — Tempo vs Processos", "serial"),
       ref_max=t_serial_max)
salvar("lambda_strong_mpi",
       builder_strong_mpi("flb", "f_lb ((t_max - t_min) / t_max)",
                          "MPI — Fator de balanceamento vs Processos", "zero"),
       ref_max=0.0)


# ---------------------------------------------------------------
# Gráficos — MPI (weak scaling)
# ---------------------------------------------------------------
def weak_serie(est):
    return sorted((r for r in resumo_mpi if r["cenario"] == "weak" and r["estrategia"] == est),
                  key=lambda r: r["p"])


def builder_weak_mpi(campo, ylabel, titulo, ref):
    def build(com_ref):
        fig, ax = plt.subplots(figsize=(8, 5))
        rotulos = None
        for est in ESTRATEGIAS:
            rs = weak_serie(est)
            if not rs:
                continue
            xs = list(range(len(rs)))
            plot_serie(ax, xs, [r[campo] for r in rs], [r[campo + "_sd"] for r in rs],
                       f"MPI {est}")
            rotulos = [f"p={r['p']}\n{r['resolucao']}" for r in rs]
            if com_ref and ref == "tempo":
                ax.axhline(rs[0]["tempo"], linestyle=":", alpha=0.6,
                           color=ESTILO[f"MPI {est}"]["color"],
                           label=f"ideal weak ({est}: T constante)")
        if com_ref:
            if ref == "tempo":
                rs = weak_serie(ESTRATEGIAS[0])
                ax.plot(range(len(rs)), [r["t_serial"] for r in rs], "x--",
                        color="gray", label="serial (mesma resolução)")
            elif ref == "um":
                ref_um(ax, "ideal (100%)")
        if rotulos:
            ax.set_xticks(range(len(rotulos)))
            ax.set_xticklabels(rotulos)
        ax.set_xlim(-0.3, len(rotulos or [0]) - 1 + 0.3)
        ax.set_ylabel(ylabel)
        ax.set_title(titulo)
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        return fig
    return build


if any(r["cenario"] == "weak" for r in resumo_mpi):
    ts_weak_max = max(r["t_serial"] for r in resumo_mpi if r["cenario"] == "weak")
    salvar("weak_scaling_mpi_time",
           builder_weak_mpi("tempo", "Tempo médio (s)",
                            "MPI — Weak Scaling (carga fixa por processo): tempo", "tempo"),
           ref_max=ts_weak_max)
    salvar("weak_scaling_mpi_efficiency",
           builder_weak_mpi("efic_fraca", "Eficiência fraca T(1)/T(p)",
                            "MPI — Weak Scaling: eficiência", "um"),
           ref_max=1.0)
    salvar("weak_scaling_mpi_lambda",
           builder_weak_mpi("flb", "f_lb ((t_max - t_min) / t_max)",
                            "MPI — Weak Scaling: Fator de balanceamento", "zero"), 
           ref_max=0.0)


# ---------------------------------------------------------------
# Gráficos — Comparação OpenMP x MPI
# ---------------------------------------------------------------
def builder_cmp(campo, ylabel, titulo, ref):
    def build(com_ref):
        fig, axes = plt.subplots(1, 2, figsize=(13, 5))
        for ax, (cm, co, b1, b2, nome) in zip(axes, CMP):
            for est in ESTRATEGIAS:
                x, y, e = mpi_serie(cm, est, campo)
                plot_serie(ax, [p for p in x if p in P_COMUNS],
                           [v for p, v in zip(x, y) if p in P_COMUNS],
                           [s for p, s in zip(x, e) if p in P_COMUNS], f"MPI {est}")
            x, y, e = omp_serie(b1, co, campo)
            plot_serie(ax, x, y, e, "OpenMP static")
            for sched in ("static", "dynamic"):
                r = omp_get(b2, co, max(P_COMUNS), sched, "1")
                if r and r[campo] is not None:
                    rot = f"OpenMP {sched},1"
                    ax.errorbar([max(P_COMUNS)], [r[campo]], yerr=[r[campo + "_sd"] or 0.0],
                                capsize=3, markersize=10,
                                label=f"{rot} (p={max(P_COMUNS)})", **ESTILO[rot])
            if com_ref:
                if ref == "speedup":
                    ref_ideal_speedup(ax)
                else:
                    ref_um(ax, "ideal (100%)" if campo == "efic" else "ideal (1.0)")
            formatar_p(ax)
            ax.set_xlabel("Número de processos / threads")
            ax.set_title(nome)
            ax.legend(fontsize=8)
        axes[0].set_ylabel(ylabel)

        res_omp_set = sorted({
            r["resolucao"] 
            for k, r in resumo_omp.items() 
            if k[0] in (b1, b2) and r.get("resolucao")
        })
        res_mpi_set = sorted({r["resolucao"] for r in resumo_mpi if r["cenario"] in ("strong", "seahorse")})
        
        res_omp_str = " | ".join(s.replace('x', '×') for s in res_omp_set) if res_omp_set else "?"
        res_mpi_str = " | ".join(s.replace('x', '×') for s in res_mpi_set) if res_mpi_set else "?"
        
        fig.suptitle(f"{titulo}\n(OpenMP: {res_omp_str} | MPI: {res_mpi_str})", fontsize=11)

        fig.tight_layout()
        return fig
    return build


if TEM_OMP:
    salvar("cmp_speedup",
           builder_cmp("speedup", "Speedup", "OpenMP × MPI — Speedup", "speedup"),
           ref_max=max(P_COMUNS))
    salvar("cmp_efficiency",
           builder_cmp("efic", "Eficiência", "OpenMP × MPI — Eficiência", "um"),
           ref_max=1.0)

    # Weak scaling: eficiência fraca OpenMP x MPI
    def builder_cmp_weak(com_ref):
        fig, ax = plt.subplots(figsize=(8, 5))
        ps_todos = set()
        for est in ESTRATEGIAS:
            rs = weak_serie(est)
            if rs:
                ps = [r["p"] for r in rs]
                ps_todos.update(ps)
                plot_serie(ax, ps, [r["efic_fraca"] for r in rs],
                           [r["efic_fraca_sd"] for r in rs], f"MPI {est}")
        for sched, ch, rot in [("static", "-", "OpenMP static"),
                               ("dynamic", "1", "OpenMP dynamic,1")]:
            pts = sorted((k[2], r) for k, r in resumo_omp.items()
                         if k[0] == "4" and k[3] == sched and k[4] == ch)
            if pts:
                ps_todos.update(p for p, _ in pts)
                est = dict(ESTILO[rot])
                est["linestyle"] = "-"
                est["markersize"] = 8
                ax.errorbar([p for p, _ in pts], [r["efic_fraca"] for _, r in pts],
                            yerr=[r["efic_fraca_sd"] or 0.0 for _, r in pts],
                            capsize=3, label=rot, **est)
        if com_ref:
            ref_um(ax, "ideal (100%)")
        formatar_p(ax, sorted(ps_todos))
        ax.set_xlabel("Número de processos / threads")
        ax.set_ylabel("Eficiência fraca T(1)/T(p)")

        # Extrai os pixels/unidade do OpenMP (bloco 4)
        px_omp_vals = set()
        for k, r in resumo_omp.items():
            if k[0] == "4":
                px_omp_vals.add(pixels_por_unidade(r["resolucao"], k[2]))
                
        # Extrai os pixels/unidade do MPI (cenário weak)
        px_mpi_vals = set()
        for r in resumo_mpi:
            if r["cenario"] == "weak":
                px_mpi_vals.add(pixels_por_unidade(r["resolucao"], r["p"]))
                
        # Função para formatar com separador de milhar (ex: 262.144)
        def fmt_px(val):
            return f"{val:,}".replace(",", ".")

        omp_str = " | ".join(fmt_px(v) for v in sorted(px_omp_vals)) if px_omp_vals else "?"
        mpi_str = " | ".join(fmt_px(v) for v in sorted(px_mpi_vals)) if px_mpi_vals else "?"
        
        ax.set_title(f"OpenMP × MPI — Weak Scaling: eficiência\n"
                    f"(OpenMP: {omp_str} pixels/thread | MPI: {mpi_str} pixels/processo)", fontsize=11)
        ax.legend()
        fig.tight_layout()
        return fig

    salvar("cmp_weak_efficiency", builder_cmp_weak, ref_max=1.0)

print("Gráficos salvos em", PLOTS_DIR)
print("Arquivos gerados:")
for nome in sorted(os.listdir(PLOTS_DIR)):
    print("  ", nome)