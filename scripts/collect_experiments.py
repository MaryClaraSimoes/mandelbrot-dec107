"""
Coleta de experimentos MPI para o Conjunto de Mandelbrot.

Para cada execução MPI, o script:
  1. gera (uma única vez por cenário) a matriz de referência e o tempo
     serial com o binário serial;
  2. executa a versão MPI e extrai as métricas impressas pelo main.c;
  3. valida a matriz .bin da execução contra a referência chamando o
     validate.py do projeto (critério da Seção 5.5 do enunciado);
  4. registra tudo em uma linha do CSV.

Uso rápido (apenas testar o pipeline):
    python3 scripts/collect_experiments.py --quick

Uso completo:
    python3 scripts/collect_experiments.py \\
        --executable ./mpi/mandelbrot_mpi \\
        --serial-executable ./serial/mandelbrot_seq \\
        --output experiments_mpi.csv
"""
import argparse
import csv
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

# Nome do .bin que o main.c serial grava no diretório de execução.
SERIAL_BIN_NAME = "mandelbrot_serial.bin"
# Linha impressa pelo main.c serial: "Tempo de calculo: 6.7844 segundos".
SERIAL_TIME_RE = re.compile(r"Tempo de calculo:\s*([0-9]+(?:\.[0-9]+)?)")

# Trechos da saída do validate.py 
VALIDATE_DIV_RE = re.compile(r"Pixels divergentes:\s+([0-9,]+)")
VALIDATE_DMAX_RE = re.compile(r"Diff m[aá]xima observada:\s+([0-9]+)")
VALIDATE_MOTIVO_RE = re.compile(r"^\s+[0-9]+\.\s+\S")

FIELDS = [
    "cenario", "estrategia", "processos", "resolucao", "max_iter", "repeticao",
    "tempo_total_s", "t_min_s", "t_max_s", "t_mean_s", "f_lb",
    "t_serial_s", "speedup", "eficiencia",
    "corretude", "px_divergentes", "diff_max",
    "timestamp",
]

# Chaves que o main.c imprime em formato "chave=valor" a serem extraidas.
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
             workdir: Path, timeout: int,
             hwthread_above: int = 0) -> dict | None:
    """Executa um cenário MPI e retorna o dicionário de métricas (ou None em erro)."""
    cmd = [mpiexec]
    # OpenMPI recusa mais processos que núcleos físicos ("slots") por padrão.
    # Só liberamos as threads lógicas acima do limite informado, para não
    # distorcer os casos de poucos processos.
    if hwthread_above and processes > hwthread_above:
        cmd.append("--use-hwthread-cpus")
    cmd += [
        "-np", str(processes), executable,
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
    except FileNotFoundError:
        print(f"  ERRO: comando não encontrado: {mpiexec}")
        return None

    if result.returncode != 0:
        msg = (result.stderr or result.stdout).strip()
        print(f"  ERRO rc={result.returncode}:")
        print("    " + msg.replace("\n", "\n    "))
        return None

    return parse_output(result.stdout)


# ============================ Referência serial ============================

def get_serial_ref(cache: dict, serial_exe: str, refroot: Path,
                     w: int, h: int, it: int, preset: str | None,
                     repeats: int, timeout: int, keep_matrix: bool):
    """
    Retorna (caminho_do_bin_de_referencia | None, T_serial_médio).

    Roda o serial 'repeats' vezes por cenário (w, h, max_iter, preset). A matriz
    de referência vem da última execução e o tempo é a média, igual ao 
    baseline T1 usado na Etapa 1. O resultado fica em cache: 
    cenários repetidos (ex.: strong e weak com p=1) não rodam de novo.
    """
    key = (w, h, it, preset)
    if key in cache:
        return cache[key]

    refdir = refroot / f"{w}x{h}_it{it}_{preset or 'padrao'}"
    refdir.mkdir(parents=True, exist_ok=True)

    cmd = [serial_exe, "--width", str(w), "--height", str(h),
           "--max-iter", str(it)]
    if preset:
        cmd += ["--preset", preset]

    print(f"  [ref] serial {w}x{h} max_iter={it} preset={preset or '-'} "
          f"({repeats} execucao(oes))")

    tempos = []
    for _ in range(repeats):
        try:
            res = subprocess.run(cmd, cwd=str(refdir), capture_output=True,
                                 text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"timeout de {timeout}s no serial: {' '.join(cmd)}")
        if res.returncode != 0:
            msg = (res.stderr or res.stdout).strip()
            raise RuntimeError(f"serial falhou (rc={res.returncode}): {msg}")
        m = SERIAL_TIME_RE.search(res.stdout)
        if not m:
            raise RuntimeError("Não encontrado: 'Tempo de calculo: X segundos' "
                               "na saída do serial.")
        tempos.append(float(m.group(1)))

    bin_path = refdir / SERIAL_BIN_NAME
    if not bin_path.is_file() or bin_path.stat().st_size != w * h * 4:
        raise RuntimeError(f"{SERIAL_BIN_NAME} ausente ou com tamanho errado "
                           f"em {refdir} (esperado {w * h * 4} bytes).")

    for extra in list(refdir.glob("*.pgm")) + list(refdir.glob("*.ppm")):
        extra.unlink()

    t_serial = sum(tempos) / len(tempos)
    if not keep_matrix:
        bin_path.unlink()
        bin_path = None

    print(f"  [ref] T_serial = {t_serial:.4f}s  "
          f"(execuções: {', '.join(f'{t:.4f}' for t in tempos)})")
    cache[key] = (bin_path, t_serial)
    return cache[key]


# ============================ Validação (validate.py) ============================

def localizar_validador(explicito: str | None) -> Path | None:
    """Acha o validate.py: --validator, cwd, raiz do repositório ou pasta do script."""
    if explicito:
        p = Path(explicito).resolve()
        return p if p.is_file() else None
    aqui = Path(__file__).resolve().parent
    for cand in (Path.cwd() / "validate.py", aqui.parent / "validate.py",
                 aqui / "validate.py"):
        if cand.is_file():
            return cand
    return None


def validar(validador: Path, ref_bin: Path | None, run_bin: Path,
            w: int, h: int, timeout: int, log_path: Path, contexto: str):
    """
    Chama o validate.py e retorna (veredito, px_divergentes, diff_max).

    Vereditos:
      identica        validate.py aprovou e há 0 pixels divergentes
      tolerancia      aprovou, com divergências dentro da Seção 5.5
      FALHA           reprovou (rc=1)
      ERRO_ARQUIVO    referência/saída ausente ou com tamanho errado
      ERRO_VALIDADOR  o validate.py não conseguiu rodar (rc=2, timeout, ...)
    Em FALHA/ERRO_VALIDADOR a saída completa (com os primeiros pixels
    divergentes) vai para `log_path`.
    """
    esperado = w * h * 4
    if ref_bin is None or not ref_bin.is_file():
        return "ERRO_ARQUIVO", "", ""
    if not run_bin.is_file() or run_bin.stat().st_size != esperado:
        return "ERRO_ARQUIVO", "", ""

    cmd = [sys.executable, str(validador), str(ref_bin), str(run_bin),
           "--width", str(w), "--height", str(h), "--verbose"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        print(f"    VALIDADOR: timeout após {timeout}s")
        return "ERRO_VALIDADOR", "", ""

    m_div = VALIDATE_DIV_RE.search(res.stdout)
    m_max = VALIDATE_DMAX_RE.search(res.stdout)
    divergentes = int(m_div.group(1).replace(",", "")) if m_div else ""
    diff_max = int(m_max.group(1)) if m_max else ""

    if res.returncode == 0:
        if divergentes == "":
            print("    AVISO: validate.py retornou aprovação, porém a contagem de "
                  "pixels divergentes não pôde ser extraída da saída do validador.")
            veredito = "aprovada"
        else:
            veredito = "identica" if divergentes == 0 else "tolerancia"
    elif res.returncode == 1:
        veredito = "FALHA"
    else:
        veredito = "ERRO_VALIDADOR"

    if veredito in ("FALHA", "ERRO_VALIDADOR"):
        with log_path.open("a") as lf:
            lf.write(f"=== {contexto} | veredito={veredito} ===\n")
            lf.write(res.stdout)
            if res.stderr:
                lf.write("[stderr]\n" + res.stderr)
            lf.write("\n")
        if veredito == "FALHA":
            for linha in res.stdout.splitlines():
                if VALIDATE_MOTIVO_RE.match(linha):
                    print("    " + linha.strip())
        else:
            print("    " + (res.stderr.strip() or res.stdout.strip()
                             or f"rc={res.returncode}"))
        print(f"    (saída completa do validate.py em {log_path})")

    return veredito, divergentes, diff_max


# ================================== Main ==================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--executable", default="./mpi/mandelbrot_mpi",
                    help="Caminho do binário MPI (padrão: ./mpi/mandelbrot_mpi).")
    ap.add_argument("--serial-executable", default="./serial/mandelbrot_seq",
                    help="Caminho do binário serial de referência "
                         "(padrão: ./serial/mandelbrot_seq).")
    ap.add_argument("--serial-repeats", type=int, default=3,
                    help="Execuções do serial por cenário para o baseline "
                         "(padrão: 3).")
    ap.add_argument("--validator", default=None,
                    help="Caminho do validate.py (padrão: procura no diretório "
                         "atual e na raiz do repositório).")
    ap.add_argument("--no-validate", action="store_true",
                    help="Não valida as matrizes (o serial ainda roda para "
                         "fornecer o T_serial do Speedup).")
    ap.add_argument("--mpiexec", default="mpirun",
                    help="Comando MPI para iniciar processos (padrão: mpirun).")
    ap.add_argument("--hwthread-above", type=int, default=0,
                    help="Adiciona --use-hwthread-cpus quando np > N "
                         "(N = núcleos físicos; 0 desativa).")
    ap.add_argument("--output", default="experiments_mpi.csv",
                    help="Arquivo CSV de saída.")
    ap.add_argument("--processes", default="1,2,4,8",
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
    serial_exe = str(Path(args.serial_executable).resolve())
    if not Path(serial_exe).is_file():
        print(f"Executável serial não encontrado: {serial_exe}", file=sys.stderr)
        return 2

    # `mpirun` puro é achado pelo PATH; caminho relativo precisa ser resolvido
    # aqui, porque as execuções acontecem em outro diretório (cwd=workdir).
    if "/" in args.mpiexec:
        args.mpiexec = str(Path(args.mpiexec).resolve())

    validate = not args.no_validate
    validador = None
    if validate:
        validador = localizar_validador(args.validator)
        if validador is None:
            print("validate.py não encontrado. Rode da raiz do repositório, "
                  "informe --validator ou use --no-validate.", file=sys.stderr)
            return 2
    procs_list = [int(x) for x in args.processes.split(",") if x.strip()]
    strategies = ["block", "cyclic"]

    # ======================= Configuração dos cenários =======================
    if args.quick:
        strong = dict(w=512, h=512, it=200)
        weak_map = {1: 512, 4: 1024, 9: 1536}
        seahorse = dict(w=512, h=512)
    else:
        strong = dict(w=4096, h=4096, it=1000)
        weak_map = {1: 4096, 4: 8192, 9: 12288}
        seahorse = dict(w=4096, h=4096)

    # ======================= Diretório de trabalho temporário =======================
    if args.keep:
        workdir = Path(tempfile.mkdtemp(prefix="mandel_mpi_"))
        cleanup = False
    else:
        tmp = tempfile.TemporaryDirectory(prefix="mandel_mpi_")
        workdir = Path(tmp.name)
        cleanup = True
    refroot = workdir / "ref"
    rundir = workdir / "run"
    refroot.mkdir()
    rundir.mkdir()

    print(f"Executável : {exe}")
    print(f"Serial     : {serial_exe}")
    print(f"Workdir    : {workdir}")
    print(f"Modo       : {'quick' if args.quick else 'full'}")
    print(f"Validação  : "
          f"{('validate.py -> ' + str(validador)) if validate else 'desligada'}")
    print(f"Início     : {datetime.now().isoformat(timespec='seconds')}\n")

    out = Path(args.output)
    log_validacao = out.with_suffix(".validacao.log")
    log_validacao.unlink(missing_ok=True)
    csv_file = out.open("w", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    writer.writeheader()
    csv_file.flush()

    ref_cache: dict = {}
    contagem = Counter()
    n_rows = 0
    n_sem_dados = 0

    def executar(cenario: str, strat: str, procs: int,
                 w: int, h: int, it: int, rep: int, preset: str | None) -> None:
        nonlocal n_rows, n_sem_dados

        # Baseline serial do cenário (T_serial) + matriz de referência.
        try:
            ref_bin, t_serial = get_serial_ref(
                ref_cache, serial_exe, refroot, w, h, it, preset,
                args.serial_repeats, args.timeout, keep_matrix=validate)
        except RuntimeError as e:
            print(f"\nERRO ao gerar referência serial: {e}", file=sys.stderr)
            csv_file.close()
            sys.exit(2)

        # Remove saídas antigas: nunca validar o arquivo de outra execução.
        saidas = [rundir / f"mandelbrot_mpi_{strat}.{ext}"
                  for ext in ("bin", "pgm", "ppm")]
        for s in saidas:
            s.unlink(missing_ok=True)

        metrics = run_case(exe, args.mpiexec, procs, w, h, it, strat, preset,
                           rundir, args.timeout, args.hwthread_above)
        if not metrics:
            print("  (sem dados)")
            n_sem_dados += 1
            return

        corretude, divergentes, diff_max = "nao_validado", "", ""
        if validate:
            print("    validando com validate.py ...", flush=True)
            contexto = f"{cenario} {strat} np={procs} {w}x{h} rep={rep}"
            corretude, divergentes, diff_max = validar(
                validador, ref_bin, saidas[0], w, h, args.timeout,
                log_validacao, contexto)
        contagem[corretude] += 1

        if not args.keep:
            for s in saidas:
                s.unlink(missing_ok=True)

        try:
            tempo = float(metrics.get("tempo_total_s"))
            speedup = t_serial / tempo
            eficiencia = speedup / int(metrics.get("processos", procs))
        except (TypeError, ValueError, ZeroDivisionError):
            speedup, eficiencia = "", ""

        row = {
            "cenario": cenario,
            "estrategia": metrics.get("estrategia", strat),
            "processos": metrics.get("processos", procs),
            "resolucao": metrics.get("resolucao", f"{w}x{h}"),
            "max_iter": metrics.get("max_iter", it),
            "repeticao": rep,
            "tempo_total_s": metrics.get("tempo_total_s", ""),
            "t_min_s": metrics.get("t_min_s", ""),
            "t_max_s": metrics.get("t_max_s", ""),
            "t_mean_s": metrics.get("t_mean_s", ""),
            "f_lb": metrics.get("f_lb", ""),
            "t_serial_s": f"{t_serial:.6f}",
            "speedup": speedup,
            "eficiencia": eficiencia,
            "corretude": corretude,
            "px_divergentes": divergentes,
            "diff_max": diff_max,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        writer.writerow(row)
        csv_file.flush()
        n_rows += 1
        print(f"    -> t={row['tempo_total_s']:>10s}s  "
              f"f_lb={row['f_lb']:>8s}  res={row['resolucao']}  "
              f"corretude={corretude}")

    # ======================= Strong scaling =======================
    if args.only in ("strong", "all"):
        print(f"[strong] {strong['w']}x{strong['h']}  max_iter={strong['it']}")
        for strat in strategies:
            for p in procs_list:
                for i in range(3):
                    print(f"  strat={strat:6s}  np={p:>2d}")
                    executar("strong", strat, p,
                             strong["w"], strong["h"], strong["it"], i, None)

    # ======================= Weak scaling =======================
    if args.only in ("weak", "all"):
        print("[weak] 4096²@1, 8192²@4, 12288²@9 (ou versão quick)")
        for strat in strategies:
            for p in sorted(weak_map.keys()):
                s = weak_map[p]
                for i in range(3):
                    print(f"  strat={strat:6s}  np={p:>2d}  res={s}x{s}")
                    executar("weak", strat, p, s, s, strong["it"], i, None)

    # ======================= Seahorse =======================
    if args.only in ("seahorse", "all"):
        print(f"[seahorse] {seahorse['w']}x{seahorse['h']}  "
              f"(preset define max_iter=5000)")
        for strat in strategies:
            for p in procs_list:
                for i in range(3):
                    print(f"  strat={strat:6s}  np={p:>2d}")
                    executar("seahorse", strat, p,
                             seahorse["w"], seahorse["h"], 5000, i, "seahorse")

    # ==============================================
    csv_file.close()
    if cleanup:
        tmp.cleanup()

    print(f"\n{n_rows} linhas escritas em {out.resolve()}")
    if n_sem_dados:
        print(f"Execuções sem dados (falharam ou deram timeout): {n_sem_dados}")
    if validate:
        resumo = ", ".join(f"{k}={v}" for k, v in sorted(contagem.items()))
        print(f"Corretude: {resumo or 'nenhuma execução validada'}")
    print(f"Fim: {datetime.now().isoformat(timespec='seconds')}")

    problemas = False
    if (contagem["FALHA"] or contagem["ERRO_ARQUIVO"]
            or contagem["ERRO_VALIDADOR"]):
        print("ATENÇÃO: há execuções reprovadas na validação (ver coluna "
              "'corretude' do CSV).", file=sys.stderr)
        problemas = True
    if n_sem_dados:
        print("ATENÇÃO: o CSV está incompleto (veja as mensagens de erro "
              "acima).", file=sys.stderr)
        problemas = True
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())