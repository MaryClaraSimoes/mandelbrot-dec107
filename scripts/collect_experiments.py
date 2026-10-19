"""
Coleta de experimentos MPI para o Conjunto de Mandelbrot.

Uso rápido (apenas testar o pipeline):
    python3 scripts/collect_experiments.py --quick

Uso completo:
    python3 scripts/collect_experiments.py \\
        --executable ./mpi/mandelbrot_mpi \\
        --output experiments_mpi.csv
"""
import argparse
import csv
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

FIELDS = [
    "cenario", "estrategia", "processos", "resolucao", "max_iter",
    "tempo_total_s", "t_min_s", "t_max_s", "t_mean_s", "f_lb",
    "timestamp",
]

# Chaves que o main.c imprime em formato "chave=valor" a serem extraidos.
WANTED_KEYS = {
    "versao", "estrategia", "resolucao", "max_iter", "processos",
    "tempo_total_s", "t_min_s", "t_max_s", "t_mean_s", "f_lb",
}


def parse_output(stdout: str) -> dict:
    """Extrai o primeiro bloco de métricas 'chave=valor' da saída."""
    metrics = {}
    for raw in stdout.splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        # Ignora linhas de log do io_utils que contenham "=" acidental.
        if line.startswith(("Imagem", "Matriz", "Exportacao", "Exportação",
                            "BALANCE_MPI", "====", "Configuracoes", "  -")):
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key in WANTED_KEYS and key not in metrics:
            metrics[key] = val.strip()
    return metrics


def run_case(executable: str, mpiexec: str, processes: int,
             width: int, height: int, max_iter: int,
             strategy: str, preset: str | None,
             workdir: Path, timeout: int) -> dict | None:
    """Executa um cenário e retorna o dicionário de métricas (ou None em erro)."""
    cmd = [
        mpiexec, "-np", str(processes), executable,
        "--width", str(width), "--height", str(height),
        "--max-iter", str(max_iter), "--strategy", strategy,
    ]
    # --preset vem por último para sobrescrever max_iter/domínio (é o caso do seahorse).
    if preset:
        cmd += ["--preset", preset]

    try:
        result = subprocess.run(
            cmd, cwd=str(workdir), capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT após {timeout}s")
        return None

    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        print(f"  ERRO rc={result.returncode}: {' | '.join(tail)}")
        return None

    return parse_output(result.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--executable", default="./mpi/mandelbrot_mpi",
                    help="Caminho do binário MPI (padrão: ./mpi/mandelbrot_mpi).")
    ap.add_argument("--mpiexec", default="mpirun",
                    help="Comando MPI para iniciar processos (padrão: mpirun).")
    ap.add_argument("--output", default="experiments_mpi.csv",
                    help="Arquivo CSV de saída.")
    ap.add_argument("--processes", default="1,2,4,8,16",
                    help="Lista de contagens de processos separada por vírgula.")
    ap.add_argument("--only", choices=["strong", "weak", "seahorse", "all"],
                    default="all", help="Executar apenas um subconjunto de cenários.")
    ap.add_argument("--quick", action="store_true",
                    help="Modo rápido (resolução baixa) para validar o pipeline.")
    ap.add_argument("--timeout", type=int, default=3600,
                    help="Timeout por execução em segundos (padrão: 3600).")
    ap.add_argument("--keep", action="store_true",
                    help="Não apaga o diretório de trabalho (debug).")
    args = ap.parse_args()

    exe = str(Path(args.executable).resolve())
    if not Path(exe).is_file():
        print(f"Executável não encontrado: {exe}", file=sys.stderr)
        return 2

    procs_list = [int(x) for x in args.processes.split(",") if x.strip()]
    strategies = ["block", "cyclic"]

    # ======================= Configuração dos cenários =======================
    if args.quick:
        strong = dict(w=512, h=512, it=200)
        weak_map = {1: 512, 4: 1024, 16: 2048}
        seahorse = dict(w=512, h=512)
    else:
        strong = dict(w=4096, h=4096, it=1000)
        weak_map = {1: 4096, 4: 8192, 16: 16384}
        seahorse = dict(w=4096, h=4096)

    # ======================= Diretório de trabalho temporário =======================
    if args.keep:
        workdir = Path(tempfile.mkdtemp(prefix="mandel_mpi_"))
        cleanup = False
    else:
        tmp = tempfile.TemporaryDirectory(prefix="mandel_mpi_")
        workdir = Path(tmp.name)
        cleanup = True

    print(f"Executável : {exe}")
    print(f"Workdir    : {workdir}")
    print(f"Modo       : {'quick' if args.quick else 'full'}")
    print(f"Início     : {datetime.now().isoformat(timespec='seconds')}\n")

    rows: list[dict] = []

    def record(cenario: str, strat: str, procs: int,
               w: int, h: int, it: int, metrics: dict | None) -> None:
        if not metrics:
            print("  (sem dados)")
            return
        row = {
            "cenario": cenario,
            "estrategia": metrics.get("estrategia", strat),
            "processos": metrics.get("processos", procs),
            "resolucao": metrics.get("resolucao", f"{w}x{h}"),
            "max_iter": metrics.get("max_iter", it),
            "tempo_total_s": metrics.get("tempo_total_s", ""),
            "t_min_s": metrics.get("t_min_s", ""),
            "t_max_s": metrics.get("t_max_s", ""),
            "t_mean_s": metrics.get("t_mean_s", ""),
            "f_lb": metrics.get("f_lb", ""),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        rows.append(row)
        print(f"    -> t={row['tempo_total_s']:>10s}s  "
              f"f_lb={row['f_lb']:>8s}  res={row['resolucao']}")

    # ======================= Strong scaling =======================
    if args.only in ("strong", "all"):
        print(f"[strong] {strong['w']}x{strong['h']}  max_iter={strong['it']}")
        for strat in strategies:
            for p in procs_list:
                print(f"  strat={strat:6s}  np={p:>2d}")
                m = run_case(exe, args.mpiexec, p,
                             strong["w"], strong["h"], strong["it"],
                             strat, preset=None,
                             workdir=workdir, timeout=args.timeout)
                record("strong", strat, p,
                       strong["w"], strong["h"], strong["it"], m)

    # ======================= Weak scaling =======================
    if args.only in ("weak", "all"):
        print("[weak] 4096²@1, 8192²@4, 16384²@16 (ou versão quick)")
        for strat in strategies:
            for p in procs_list:
                if p not in weak_map:
                    continue
                s = weak_map[p]
                print(f"  strat={strat:6s}  np={p:>2d}  res={s}x{s}")
                m = run_case(exe, args.mpiexec, p,
                             s, s, strong["it"],
                             strat, preset=None,
                             workdir=workdir, timeout=args.timeout)
                record("weak", strat, p, s, s, strong["it"], m)

    # ======================= Seahorse =======================
    if args.only in ("seahorse", "all"):
        print(f"[seahorse] {seahorse['w']}x{seahorse['h']}  "
              f"(preset define max_iter={5000 if not args.quick else 5000})")
        for strat in strategies:
            for p in procs_list:
                print(f"  strat={strat:6s}  np={p:>2d}")
                m = run_case(exe, args.mpiexec, p,
                             seahorse["w"], seahorse["h"], 5000,
                             strat, preset="seahorse",
                             workdir=workdir, timeout=args.timeout)
                record("seahorse", strat, p,
                       seahorse["w"], seahorse["h"], 5000, m)

    # ======================= CSV =======================
    out = Path(args.output)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    if cleanup:
        tmp.cleanup()

    print(f"\n{len(rows)} linhas escritas em {out.resolve()}")
    print(f"Fim: {datetime.now().isoformat(timespec='seconds')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())