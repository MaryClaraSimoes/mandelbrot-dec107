#!/usr/bin/env python3
"""
generate_report_plots.py — Gera graficos PNG (via pycairo) e tabelas Markdown
a partir de tuning.csv, scaling.csv, stride_scaling.csv e ncu_*.csv coletados
no mesmo host (Intel Core 7 240H + NVIDIA GeForce RTX 5050 Laptop GPU).
"""
import csv
import math
import os
from collections import OrderedDict
import cairo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUN_DIR = os.environ.get("TUN_DIR", os.path.join(ROOT, "output", "tuning"))
PROF_DIR = os.environ.get("PROF_DIR", os.path.join(ROOT, "output", "prof"))
TUNING_CSV = os.path.join(TUN_DIR, "tuning.csv")
SCALING_CSV = os.path.join(TUN_DIR, "scaling.csv")
STRIDE_CSV = os.path.join(TUN_DIR, "stride_scaling.csv")
PLOTS_DIR = os.path.join(ROOT, "docs", "plots")
TABLES_MD = os.path.join(TUN_DIR, "tuning_tables.md")
GPU_SMS = int(os.environ.get("GPU_SMS", "20"))


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for c in ["h2d_ms", "kernel_ms", "kernel_min_ms", "kernel_max_ms", "d2h_ms",
                      "total_ms", "total_min_ms", "total_max_ms", "write_ms"]:
                r[c] = float(r[c])
            for c in ["ctab", "bx", "by", "streams", "chunk", "width", "height", "max_iter", "reps"]:
                r[c] = int(r[c])
            rows.append(r)
    return rows


def parse_pt_float(s):
    s = s.strip()
    if s in ("", "n/a", "N/A"):
        return 0.0
    # Handle pt_BR formatted numbers like "30.037.312" or "79,12"
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    return float(s)


def load_ncu_metrics(prof_dir):
    tags = ["naive_full", "compact_full", "naive_seahorse", "compact_seahorse"]
    data = {}
    for tag in tags:
        path = os.path.join(prof_dir, f"ncu_{tag}.csv")
        if not os.path.exists(path):
            return None
        lines = [ln for ln in open(path, encoding="utf-8") if not ln.startswith("==")]
        metrics = {}
        for r in csv.DictReader(lines):
            metrics[r["Metric Name"]] = parse_pt_float(r["Metric Value"])
        data[tag] = metrics
    return data


def vlabel(r):
    return r["variant"] + ("+ctab" if r["ctab"] else "") + ("[__const__]" if r["params"] == "const" else "")


def blabel(r):
    return f"1D {r['bx'] * r['by']}" if r["layout"] == "1d" else f"2D {r['bx']}x{r['by']}"


def sel(rows, group, scen):
    return [r for r in rows if r["group"] == group and r["scenario"] == scen]


def draw_text(ctx, x, y, text, size=12, bold=False, color=(0.15, 0.15, 0.15), align="left", angle=0.0):
    ctx.save()
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    ctx.set_source_rgb(*color)
    ext = ctx.text_extents(text)
    ctx.translate(x, y)
    if angle != 0.0:
        ctx.rotate(angle)
    dx = 0.0
    if align == "center":
        dx = -ext.width / 2.0 - ext.x_bearing
    elif align == "right":
        dx = -ext.width - ext.x_bearing
    ctx.move_to(dx, 0)
    ctx.show_text(text)
    ctx.restore()


def setup_canvas(w, h):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.paint()
    return surf, ctx


def draw_grid_axes(ctx, x0, y0, pw, ph, ymin, ymax, nticks=5, ylabel=""):
    ctx.save()
    for i in range(nticks + 1):
        frac = i / nticks
        yy = y0 + ph - frac * ph
        val = ymin + frac * (ymax - ymin)
        ctx.set_source_rgb(0.90, 0.90, 0.92)
        ctx.set_line_width(1.0)
        ctx.move_to(x0, yy)
        ctx.line_to(x0 + pw, yy)
        ctx.stroke()
        label = f"{val:.0f}" if (ymax - ymin) >= 25 else f"{val:.1f}"
        draw_text(ctx, x0 - 8, yy + 4, label, size=11, color=(0.3, 0.3, 0.3), align="right")

    ctx.set_source_rgb(0.3, 0.3, 0.35)
    ctx.set_line_width(1.5)
    ctx.move_to(x0, y0)
    ctx.line_to(x0, y0 + ph)
    ctx.line_to(x0 + pw, y0 + ph)
    ctx.stroke()
    if ylabel:
        draw_text(ctx, x0 - 54, y0 + ph / 2, ylabel, size=12, bold=True, align="center", angle=-math.pi / 2)
    ctx.restore()


def plot_grouped_bars(path, title, labels, series_list, ylabel, ymin=0.0, ymax=None, rotate_labels=True):
    W, H = 980, 480
    surf, ctx = setup_canvas(W, H)
    draw_text(ctx, W / 2, 32, title, size=15.5, bold=True, align="center")

    x0, y0, pw, ph = 88, 68, W - 120, H - 165
    all_vals = [v for _, vals, _ in series_list for v in vals]
    if ymax is None:
        ymax = max(all_vals) * 1.15

    draw_grid_axes(ctx, x0, y0, pw, ph, ymin, ymax, nticks=5, ylabel=ylabel)

    ng = len(labels)
    ns = len(series_list)
    grp_w = pw / ng
    bar_w = min(38, grp_w * 0.72 / ns)
    total_bw = bar_w * ns

    for gi, lbl in enumerate(labels):
        gx = x0 + gi * grp_w + (grp_w - total_bw) / 2.0
        for si, (sname, vals, col) in enumerate(series_list):
            val = vals[gi]
            bh = max(((val - ymin) / (ymax - ymin)) * ph, 2.0)
            bx = gx + si * bar_w
            by = y0 + ph - bh
            ctx.set_source_rgb(*col)
            ctx.rectangle(bx, by, bar_w - 2, bh)
            ctx.fill()
            txt = f"{val:.0f}" if val >= 1000 else (f"{val:.1f}" if val >= 10 else f"{val:.2f}")
            draw_text(ctx, bx + (bar_w - 2) / 2, by - 5, txt,
                      size=9.5, color=(0.15, 0.15, 0.15), align="center")
        lx = x0 + (gi + 0.5) * grp_w
        if rotate_labels:
            draw_text(ctx, lx + 3, y0 + ph + 16, lbl, size=11, align="right", angle=-0.45)
        else:
            draw_text(ctx, lx, y0 + ph + 20, lbl, size=11, align="center")

    lx = x0 + pw - 10
    for si in range(ns - 1, -1, -1):
        sname, _, col = series_list[si]
        tw = len(sname) * 7.2 + 26
        lx -= tw
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, 44, 14, 12)
        ctx.fill()
        draw_text(ctx, lx + 18, 54, sname, size=11)

    surf.write_to_png(path)


def plot_chunk_sweep(path, ck_full, ck_sea, naive_full, naive_sea):
    W, H = 920, 460
    surf, ctx = setup_canvas(W, H)
    draw_text(ctx, W / 2, 32, "Variante compact: Tempo de Kernel vs. Chunk (RTX 5050, Bloco 8x8)", size=15.5, bold=True, align="center")
    x0, y0, pw, ph = 85, 68, W - 125, H - 140
    all_v = [r["kernel_ms"] for r in ck_full + ck_sea] + [naive_full, naive_sea]
    ymin = math.floor((min(all_v) - 15.0) / 20.0) * 20.0
    ymax = math.ceil((max(all_v) + 20.0) / 20.0) * 20.0
    draw_grid_axes(ctx, x0, y0, pw, ph, ymin, ymax, nticks=6, ylabel="Kernel (ms, mediana)")

    chunks = [r["chunk"] for r in ck_full]
    xs = [x0 + (i / (len(chunks) - 1)) * (pw - 40) + 20 for i in range(len(chunks))]

    for i, ch in enumerate(chunks):
        ctx.set_source_rgb(0.93, 0.93, 0.95)
        ctx.set_line_width(1.0)
        ctx.move_to(xs[i], y0)
        ctx.line_to(xs[i], y0 + ph)
        ctx.stroke()
        draw_text(ctx, xs[i], y0 + ph + 20, str(ch), size=11, align="center")
    draw_text(ctx, x0 + pw / 2, y0 + ph + 45, "chunk (iteracoes por rodada)", size=12, bold=True, align="center")

    def ymap(v):
        return y0 + ph - ((v - ymin) / (ymax - ymin)) * ph

    for val, col, name, dy in [
        (naive_full, (0.16, 0.45, 0.72), f"naive Full ({naive_full:.1f} ms)", 14),
        (naive_sea,  (0.85, 0.37, 0.01), f"naive Seahorse ({naive_sea:.1f} ms)", -6),
    ]:
        yy = ymap(val)
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_dash([6.0, 4.0])
        ctx.set_line_width(1.6)
        ctx.move_to(x0, yy)
        ctx.line_to(x0 + pw, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, x0 + 18, yy + dy, name, size=10.5, color=col, align="left")

    for rows, col in [(ck_full, (0.16, 0.45, 0.72)), (ck_sea, (0.85, 0.37, 0.01))]:
        pts = [(xs[i], ymap(r["kernel_ms"])) for i, r in enumerate(rows)]
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.5)
        ctx.move_to(*pts[0])
        for px, py in pts[1:]:
            ctx.line_to(px, py)
        ctx.stroke()
        for idx, (px, py) in enumerate(pts):
            ctx.arc(px, py, 4.5, 0, 2 * math.pi)
            ctx.fill()
            off = -10 if (rows is ck_full or idx in (0, 1, 2)) else 15
            draw_text(ctx, px, py + off, f"{rows[idx]['kernel_ms']:.1f}", size=10, color=col, align="center")

    ctx.set_source_rgb(0.16, 0.45, 0.72)
    ctx.rectangle(x0 + 15, 44, 16, 4)
    ctx.fill()
    draw_text(ctx, x0 + 36, 51, "compact Full (4096x4096, MAX_ITER=1000)", size=11)
    ctx.set_source_rgb(0.85, 0.37, 0.01)
    ctx.rectangle(x0 + 330, 44, 16, 4)
    ctx.fill()
    draw_text(ctx, x0 + 351, 51, "compact Seahorse (4096x4096, MAX_ITER=5000)", size=11)

    surf.write_to_png(path)


def plot_scaling(path, scaling_rows):
    W, H = 980, 470
    surf, ctx = setup_canvas(W, H)
    draw_text(ctx, W / 2, 32, "Escalabilidade CUDA por Resolucao — RTX 5050 (Input Padrao, MAX_ITER=1000)",
              size=15.5, bold=True, align="center")

    res_list = ["1024", "2048", "4096", "8192", "16384"]
    naive_sync = {}
    naive_strm = {}
    for r in scaling_rows:
        n = str(r["width"])
        if r["variant"] == "naive" and r["ctab"] == 0 and r["mode"] == "sync":
            naive_sync[n] = (r["width"] * r["height"]) / (r["total_ms"] * 1e-3) / 1e6
        if r["variant"] == "naive" and r["mode"] == "streams":
            naive_strm[n] = (r["width"] * r["height"]) / (r["total_ms"] * 1e-3) / 1e6

    mp_ymax = math.ceil(max(list(naive_sync.values()) + list(naive_strm.values())) / 10.0) * 10.0 + 10.0

    x0, y0, pw, ph = 80, 72, 400, 315
    draw_text(ctx, x0 + pw / 2, 56, "Vazao do Pipeline Total (Mpixel/s)", size=12.5, bold=True, align="center")
    draw_grid_axes(ctx, x0, y0, pw, ph, 0.0, mp_ymax, nticks=7, ylabel="Mpixel/s")

    grp_w = pw / len(res_list)
    bw = 26
    for i, n in enumerate(res_list):
        gx = x0 + i * grp_w + (grp_w - 2 * bw) / 2
        for j, (mp, col) in enumerate([(naive_sync[n], (0.25, 0.55, 0.78)), (naive_strm[n], (0.13, 0.62, 0.35))]):
            bh = (mp / mp_ymax) * ph
            ctx.set_source_rgb(*col)
            ctx.rectangle(gx + j * bw, y0 + ph - bh, bw - 2, bh)
            ctx.fill()
            draw_text(ctx, gx + j * bw + (bw - 2) / 2, y0 + ph - bh - 5, f"{mp:.1f}", size=9.5, align="center")
        draw_text(ctx, x0 + (i + 0.5) * grp_w, y0 + ph + 18, f"{n}x{n}", size=10.5, align="center")

    ctx.set_source_rgb(0.25, 0.55, 0.78); ctx.rectangle(x0 + 10, y0 + ph + 38, 12, 10); ctx.fill()
    draw_text(ctx, x0 + 26, y0 + ph + 47, "naive 8x8 (sync)", size=10.5)
    ctx.set_source_rgb(0.13, 0.62, 0.35); ctx.rectangle(x0 + 165, y0 + ph + 38, 12, 10); ctx.fill()
    draw_text(ctx, x0 + 181, y0 + ph + 47, "naive 8x8 (16 streams)", size=10.5)

    x1, y1, pw1, ph1 = 560, 72, 385, 315
    draw_text(ctx, x1 + pw1 / 2, 56, "Fracao de Transferencia D->H e Tempo Total (ms)", size=12.5, bold=True, align="center")
    draw_grid_axes(ctx, x1, y1, pw1, ph1, 0.0, 5.0, nticks=5, ylabel="% D->H no Pipeline (sync)")

    grp_w1 = pw1 / len(res_list)
    for i, n in enumerate(res_list):
        r = next(x for x in scaling_rows if str(x["width"]) == n and x["variant"] == "naive" and x["ctab"] == 0 and x["mode"] == "sync")
        pct = 100.0 * r["d2h_ms"] / r["total_ms"]
        bh = (pct / 5.0) * ph1
        bx = x1 + i * grp_w1 + (grp_w1 - 46) / 2
        ctx.set_source_rgb(0.84, 0.45, 0.18)
        ctx.rectangle(bx, y1 + ph1 - bh, 46, bh)
        ctx.fill()
        draw_text(ctx, bx + 23, y1 + ph1 - bh - 6, f"{pct:.2f}%", size=10, align="center")
        t_lbl = f"{r['total_ms']:.0f}ms" if r["total_ms"] >= 100 else f"{r['total_ms']:.1f}ms"
        draw_text(ctx, bx + 23, y1 + ph1 - bh + 15, t_lbl, size=8.5, color=(1, 1, 1), align="center")
        draw_text(ctx, x1 + (i + 0.5) * grp_w1, y1 + ph1 + 18, f"{n}x{n}", size=10.5, align="center")

    surf.write_to_png(path)


def write_tuning_tables(tuning, scaling):
    gpu_name = tuning[0]["gpu"]
    md = [f"# Tabelas de Tuning e Escalabilidade ({gpu_name})", ""]
    md.append(f"GPU: {gpu_name}. Mediana de {tuning[0]['reps']} repeticoes apos aquecimento (tempos em ms).")
    md.append("")
    for scen in OrderedDict.fromkeys(r["scenario"] for r in tuning):
        s0 = next(r for r in tuning if r["scenario"] == scen)
        md += [f"## Cenario `{scen}` ({s0['width']}x{s0['height']}, MAX_ITER={s0['max_iter']})", ""]
        bs = sel(tuning, "blocksweep", scen)
        md += ["### Bloco/Grade", "", "| Config | Kernel (ms) | Min (ms) | Max (ms) |", "|---|---|---|---|"]
        for r in bs:
            md.append(f"| {blabel(r)} | {r['kernel_ms']:.3f} | {r['kernel_min_ms']:.3f} | {r['kernel_max_ms']:.3f} |")
        md.append("")
        vs = sel(tuning, "variants", scen)
        nv = next(r for r in vs if vlabel(r) == "naive")
        md += ["### Variantes", "", "| Variante | Bloco | Chunk | Kernel (ms) | H->D (ms) | Ganho vs naive | Verificacao |", "|---|---|---|---|---|---|---|"]
        for r in vs:
            md.append(f"| {vlabel(r)} | {blabel(r)} | {r['chunk'] or '-'} | {r['kernel_ms']:.3f} | {r['h2d_ms']:.3f} | {nv['kernel_ms']/r['kernel_ms']:.3f}x | {r['verify']} |")
        md.append("")
        ck = sel(tuning, "chunk", scen)
        md += ["### compact x chunk", "", "| Chunk | Kernel (ms) | Total (ms) | Ganho vs naive |", "|---|---|---|---|"]
        for r in ck:
            md.append(f"| {r['chunk']} | {r['kernel_ms']:.3f} | {r['total_ms']:.3f} | {nv['kernel_ms']/r['kernel_ms']:.3f}x |")
        md.append("")
        ms = sel(tuning, "modes", scen)
        base = ms[0]
        md += ["### Modos Host-Device", "", "| Modo | Streams | Kernel (ms) | D->H (ms) | Total (ms) | Ganho vs sync |", "|---|---|---|---|---|---|"]
        for r in ms:
            k_s = "-" if r["kernel_ms"] < 0 else f"{r['kernel_ms']:.3f}"
            d_s = "-" if r["d2h_ms"] < 0 else f"{r['d2h_ms']:.3f}"
            md.append(f"| {r['mode']} | {r['streams'] or '-'} | {k_s} | {d_s} | {r['total_ms']:.3f} | {base['total_ms']/r['total_ms']:.3f}x |")
        md.append("")
    os.makedirs(os.path.dirname(TABLES_MD), exist_ok=True)
    with open(TABLES_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


def plot_strong_weak_stride(path, stride_rows):
    W, H = 980, 460
    surf, ctx = setup_canvas(W, H)
    draw_text(ctx, W / 2, 30, f"Escalabilidade Forte e Fraca via Grid-Stride (RTX 5050, {GPU_SMS} SMs, 16x16)",
              size=15.5, bold=True, align="center")

    full_s = [r for r in stride_rows if r["group"] == "strong_stride" and r["scenario"].startswith("full_B")]
    sea_s = [r for r in stride_rows if r["group"] == "strong_stride" and r["scenario"].startswith("seahorse_B")]
    t1_f = float(full_s[0]["kernel_ms"])
    t1_s = float(sea_s[0]["kernel_ms"])
    bs = [int(r["scenario"].split("_B")[1]) for r in full_s]
    max_f = max(t1_f / float(r["kernel_ms"]) for r in full_s)
    max_s = max(t1_s / float(r["kernel_ms"]) for r in sea_s)
    s_ymax = 24.0

    x0, y0, pw, ph = 75, 72, 430, 305
    draw_text(ctx, x0 + pw / 2, 55, "Escalabilidade Forte 4096x4096 (Speedup vs 1 Bloco)", size=12, bold=True, align="center")
    draw_grid_axes(ctx, x0, y0, pw, ph, 0.0, s_ymax, nticks=6, ylabel="Speedup vs 1 Bloco")

    xs = [x0 + (i / (len(bs) - 1)) * (pw - 30) + 15 for i in range(len(bs))]
    for i, b in enumerate(bs):
        draw_text(ctx, xs[i], y0 + ph + 18, str(b), size=10, align="center")
    draw_text(ctx, x0 + pw / 2, y0 + ph + 40, "Blocos lancados (256 threads/bloco)", size=11, bold=True, align="center")

    def ymap_s(v):
        return y0 + ph - (v / s_ymax) * ph

    ctx.save()
    ctx.set_source_rgb(0.45, 0.45, 0.48)
    ctx.set_dash([5.0, 4.0])
    ctx.set_line_width(1.5)
    pts_id = [(xs[i], ymap_s(min(b, GPU_SMS))) for i, b in enumerate(bs)]
    ctx.move_to(*pts_id[0])
    for px, py in pts_id[1:]:
        ctx.line_to(px, py)
    ctx.stroke()
    ctx.restore()

    for rows, t1, col in [(full_s, t1_f, (0.16, 0.45, 0.72)), (sea_s, t1_s, (0.85, 0.37, 0.01))]:
        pts = [(xs[i], ymap_s(t1 / float(r["kernel_ms"]))) for i, r in enumerate(rows)]
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.3)
        ctx.move_to(*pts[0])
        for px, py in pts[1:]:
            ctx.line_to(px, py)
        ctx.stroke()
        for px, py in pts:
            ctx.arc(px, py, 4.0, 0, 2 * math.pi)
            ctx.fill()

    ctx.set_source_rgb(0.45, 0.45, 0.48); ctx.rectangle(x0 + 10, y0 + 12, 14, 3); ctx.fill()
    draw_text(ctx, x0 + 28, y0 + 17, f"Ideal min(B, {GPU_SMS} SMs)", size=10)
    ctx.set_source_rgb(0.16, 0.45, 0.72); ctx.rectangle(x0 + 10, y0 + 28, 14, 3); ctx.fill()
    draw_text(ctx, x0 + 28, y0 + 33, f"Full (max {max_f:.2f}x)", size=10)
    ctx.set_source_rgb(0.85, 0.37, 0.01); ctx.rectangle(x0 + 10, y0 + 44, 14, 3); ctx.fill()
    draw_text(ctx, x0 + 28, y0 + 49, f"Seahorse (max {max_s:.2f}x)", size=10)

    wrows = [r for r in stride_rows if r["group"] == "weak_stride"]
    w_ymax = math.ceil(max(float(r["total_ms"]) for r in wrows) / 2000.0) * 2000.0 + 1000.0
    x1, y1, pw1, ph1 = 580, 72, 360, 305
    draw_text(ctx, x1 + pw1 / 2, 55, "Escalabilidade Fraca (16M px/bloco)", size=12, bold=True, align="center")
    draw_grid_axes(ctx, x1, y1, pw1, ph1, 0.0, w_ymax, nticks=5, ylabel="Tempo Total (ms)")

    grp_w = pw1 / len(wrows)
    for i, r in enumerate(wrows):
        tm = float(r["total_ms"])
        bh = (tm / w_ymax) * ph1
        bx = x1 + i * grp_w + (grp_w - 50) / 2
        col = (0.16, 0.45, 0.72) if i < 2 else (0.13, 0.62, 0.35)
        ctx.set_source_rgb(*col)
        ctx.rectangle(bx, y1 + ph1 - bh, 50, bh)
        ctx.fill()
        eff = float(wrows[0]["total_ms"]) / tm * 100.0
        draw_text(ctx, bx + 25, y1 + ph1 - bh - 17, f"{tm/1000:.2f} s", size=10.5, bold=True, align="center")
        draw_text(ctx, bx + 25, y1 + ph1 - bh - 5, f"({eff:.1f}%)", size=9.5, color=(0.3, 0.3, 0.3), align="center")
        b = r["scenario"].split("_B")[1]
        draw_text(ctx, x1 + (i + 0.5) * grp_w, y1 + ph1 + 18, f"{r['width']}² (B={b})", size=10.5, align="center")
    draw_text(ctx, x1 + pw1 / 2, y1 + ph1 + 40, f"Todos B <= {GPU_SMS} SMs (1 unica onda)", size=10, color=(0.13, 0.52, 0.30), align="center")

    surf.write_to_png(path)


def plot_ncu_profiling(path, ncu_data):
    W, H = 980, 450
    surf, ctx = setup_canvas(W, H)
    draw_text(ctx, W / 2, 30, "Perfilamento em Hardware — NVIDIA Nsight Compute (RTX 5050, 1024x1024, 8x8)",
              size=15.0, bold=True, align="center")

    tags = ["naive_full", "compact_full", "naive_seahorse", "compact_seahorse"]
    flat_cases = ["naive Full", "compact Full", "naive Seahorse", "compact Seahorse"]
    occ_act = [ncu_data[t]["sm__warps_active.avg.pct_of_peak_sustained_active"] for t in tags]
    fp64    = [ncu_data[t]["sm__inst_executed_pipe_fp64.avg.pct_of_peak_sustained_active"] for t in tags]
    dram    = [ncu_data[t]["dram__throughput.avg.pct_of_peak_sustained_elapsed"] for t in tags]
    lanes   = [ncu_data[t]["smsp__thread_inst_executed_per_inst_executed.ratio"] for t in tags]

    x0, y0, pw, ph = 75, 72, 460, 295
    draw_text(ctx, x0 + pw / 2, 55, "Ocupacao Alcancada, Pipeline FP64 e Banda DRAM (%)", size=11.5, bold=True, align="center")
    draw_grid_axes(ctx, x0, y0, pw, ph, 0.0, 100.0, nticks=5, ylabel="% do Pico")

    series = [
        ("Ocupacao alcancada", occ_act, (0.16, 0.45, 0.72)),
        ("Uso FP64 pipe", fp64, (0.13, 0.62, 0.35)),
        ("Banda DRAM", dram, (0.85, 0.37, 0.01)),
    ]
    ng = len(flat_cases)
    ns = len(series)
    grp_w = pw / ng
    bw = 24
    for gi, lbl in enumerate(flat_cases):
        gx = x0 + gi * grp_w + (grp_w - bw * ns) / 2
        for si, (_, vals, col) in enumerate(series):
            v = vals[gi]
            bh = max((v / 100.0) * ph, 2.0)
            bx = gx + si * bw
            by = y0 + ph - bh
            ctx.set_source_rgb(*col)
            ctx.rectangle(bx, by, bw - 2, bh)
            ctx.fill()
            txt = f"{v:.2f}%" if v < 1 else f"{v:.1f}%"
            draw_text(ctx, bx + (bw - 2) / 2, by - 5, txt, size=8.5, align="center")
        draw_text(ctx, x0 + (gi + 0.5) * grp_w, y0 + ph + 18, lbl, size=10, align="center")

    lx = x0 + 10
    for sname, _, col in series:
        ctx.set_source_rgb(*col); ctx.rectangle(lx, y0 + ph + 38, 12, 10); ctx.fill()
        draw_text(ctx, lx + 16, y0 + ph + 47, sname, size=10)
        lx += len(sname) * 6.5 + 32

    x1, y1, pw1, ph1 = 605, 72, 340, 295
    draw_text(ctx, x1 + pw1 / 2, 55, "Threads Ativas por Instrucao de Warp (Ideal = 32)", size=11.5, bold=True, align="center")
    draw_grid_axes(ctx, x1, y1, pw1, ph1, 0.0, 32.0, nticks=4, ylabel="Lanes Ativas / 32")

    ctx.save()
    ctx.set_source_rgb(0.45, 0.45, 0.48)
    ctx.set_dash([5.0, 4.0])
    ctx.set_line_width(1.4)
    ctx.move_to(x1, y1)
    ctx.line_to(x1 + pw1, y1)
    ctx.stroke()
    ctx.restore()

    grp_w1 = pw1 / ng
    for gi, lbl in enumerate(flat_cases):
        v = lanes[gi]
        bh = (v / 32.0) * ph1
        bx = x1 + gi * grp_w1 + (grp_w1 - 42) / 2
        col = (0.16, 0.45, 0.72) if "Full" in lbl else (0.85, 0.37, 0.01)
        ctx.set_source_rgb(*col)
        ctx.rectangle(bx, y1 + ph1 - bh, 42, bh)
        ctx.fill()
        draw_text(ctx, bx + 21, y1 + ph1 - bh - 16, f"{v:.2f}/32", size=10, bold=True, align="center")
        draw_text(ctx, bx + 21, y1 + ph1 - bh - 5, f"({v/32*100:.1f}%)", size=9, color=(0.3, 0.3, 0.3), align="center")
        draw_text(ctx, x1 + (gi + 0.5) * grp_w1, y1 + ph1 + 18, lbl, size=9.5, align="center")

    surf.write_to_png(path)


def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    tuning = load_csv(TUNING_CSV)
    scaling = load_csv(SCALING_CSV)
    write_tuning_tables(tuning, scaling)

    # 1. Block sweep
    bs_full = sel(tuning, "blocksweep", "full")
    bs_sea = sel(tuning, "blocksweep", "seahorse")
    plot_grouped_bars(
        os.path.join(PLOTS_DIR, "blocksweep_comparison.png"),
        "Varredura de Geometria de Bloco/Grade — Kernel naive (RTX 5050, 4096x4096)",
        [blabel(r) for r in bs_full],
        [("Full (MAX_ITER=1000)", [r["kernel_ms"] for r in bs_full], (0.16, 0.45, 0.72)),
         ("Seahorse (MAX_ITER=5000)", [r["kernel_ms"] for r in bs_sea], (0.85, 0.37, 0.01))],
        "Tempo do Kernel (ms, mediana)"
    )

    # 2. Variants comparison
    vs_full = sel(tuning, "variants", "full")
    vs_sea = sel(tuning, "variants", "seahorse")
    plot_grouped_bars(
        os.path.join(PLOTS_DIR, "variants_comparison.png"),
        "Comparacao de Variantes de Kernel (RTX 5050, 4096x4096, 8x8 vs base 16x16)",
        [vlabel(r) for r in vs_full],
        [("Full (MAX_ITER=1000)", [r["kernel_ms"] for r in vs_full], (0.16, 0.45, 0.72)),
         ("Seahorse (MAX_ITER=5000)", [r["kernel_ms"] for r in vs_sea], (0.85, 0.37, 0.01))],
        "Tempo do Kernel (ms, mediana)"
    )

    # 3. Chunk sweep
    ck_full = sel(tuning, "chunk", "full")
    ck_sea = sel(tuning, "chunk", "seahorse")
    nv_full = next(r["kernel_ms"] for r in vs_full if vlabel(r) == "naive")
    nv_sea = next(r["kernel_ms"] for r in vs_sea if vlabel(r) == "naive")
    plot_chunk_sweep(os.path.join(PLOTS_DIR, "compact_chunk_sweep.png"), ck_full, ck_sea, nv_full, nv_sea)

    # 4. Transfer modes
    ms_full = sel(tuning, "modes", "full")
    ms_sea = sel(tuning, "modes", "seahorse")
    mlabs = [r["mode"] + (f" S={r['streams']}" if r["streams"] else "") for r in ms_full]
    m_all = [r["total_ms"] for r in ms_full + ms_sea]
    m_ymin = math.floor((min(m_all) - 20.0) / 20.0) * 20.0
    m_ymax = math.ceil((max(m_all) + 25.0) / 20.0) * 20.0
    plot_grouped_bars(
        os.path.join(PLOTS_DIR, "transfer_modes.png"),
        "Custo Host-Device: sync vs pinned vs CUDA streams (RTX 5050, Bloco 8x8)",
        mlabs,
        [("Full (total wall ms)", [r["total_ms"] for r in ms_full], (0.16, 0.45, 0.72)),
         ("Seahorse (total wall ms)", [r["total_ms"] for r in ms_sea], (0.85, 0.37, 0.01))],
        "Tempo Total Pipeline (ms, mediana)",
        ymin=m_ymin, ymax=m_ymax
    )

    # 5. Scaling
    plot_scaling(os.path.join(PLOTS_DIR, "scaling_cuda.png"), scaling)

    # 6. Same-host paradigm comparison (Core 7 240H + RTX 5050 Laptop GPU)
    plot_grouped_bars(
        os.path.join(PLOTS_DIR, "paradigm_comparison.png"),
        "Comparacao no Mesmo Host (Core 7 240H + RTX 5050 Laptop) — 4096x4096",
        ["Serial (1T)", "MPI cyclic (16P)", "OpenMP dyn,1 (16T)", "CUDA base (16x16)", "CUDA otimizado"],
        [("Full (MAX_ITER=1000)", [12431.1, 2000.3, 1767.2, 297.1, 284.2], (0.16, 0.45, 0.72)),
         ("Seahorse (MAX_ITER=5000)", [5603.4, 1084.1, 805.4, 231.5, 182.6], (0.85, 0.37, 0.01))],
        "Tempo Total (ms)",
        rotate_labels=False
    )

    if os.path.exists(STRIDE_CSV):
        stride_rows = load_csv(STRIDE_CSV)
        plot_strong_weak_stride(os.path.join(PLOTS_DIR, "strong_weak_stride.png"), stride_rows)

    ncu_data = load_ncu_metrics(PROF_DIR)
    if ncu_data:
        plot_ncu_profiling(os.path.join(PLOTS_DIR, "ncu_profiling.png"), ncu_data)

    print("Generated plots in", PLOTS_DIR)


if __name__ == "__main__":
    main()
