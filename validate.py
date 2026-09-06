#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate.py — Validador de Corretude para o Conjunto de Mandelbrot
===================================================================

Compara pixel a pixel duas matrizes binárias de contagens de iteração
(formato int32 nativo, Row-Major, sem cabeçalho) e verifica se a
diferença respeita a margem de tolerância definida no projeto.

Não depende de bibliotecas externas (apenas a biblioteca padrão).

Critérios de Validação (conforme README):
  - Concordância exata esperada na quase totalidade dos pixels.
  - Tolerância: até 0,01% dos pixels totais podem divergir em no
    máximo 1 iteração (fronteiras do fractal).

Uso:
  python3 validate.py <referencia.bin> <teste.bin> [--width W] [--height H]
                      [--tolerance FRAC] [--max-diff D] [--verbose]

Exemplos:
  python3 validate.py mandelbrot_serial.bin mandelbrot_omp.bin
  python3 validate.py ref.bin cuda.bin --width 8192 --height 8192
  python3 validate.py mandelbrot_serial.bin mandelbrot_mpi.bin --verbose
"""

from __future__ import print_function

import argparse
import array
import os
import sys

INT32_BYTES = 4
DEFAULT_WIDTH = 4096
DEFAULT_HEIGHT = 4096
DEFAULT_TOLERANCE = 0.0001  # 0,01%
DEFAULT_MAX_DIFF = 1
VERBOSE_LIMIT = 20


def load_matrix(filepath, width, height):
    """Carrega uma matriz binária de int32 em formato Row-Major.

    Returns:
        array.array('i') com width * height elementos.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o tamanho do arquivo não corresponder às dimensões.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError("Arquivo não encontrado: {0}".format(filepath))

    expected_count = width * height
    expected_size = expected_count * INT32_BYTES
    actual_size = os.path.getsize(filepath)

    if actual_size != expected_size:
        raise ValueError(
            "Tamanho do arquivo '{0}' ({1} bytes) não corresponde às "
            "dimensões {2}x{3} esperadas ({4} bytes).".format(
                filepath, actual_size, width, height, expected_size
            )
        )

    data = array.array("i")
    with open(filepath, "rb") as fp:
        data.fromfile(fp, expected_count)

    if data.itemsize != INT32_BYTES:
        raise ValueError(
            "Este interpretador Python usa int de {0} bytes; "
            "esperado int32 (4 bytes).".format(data.itemsize)
        )

    return data


def infer_dimensions(path, width, height):
    """Confirma ou infere (width, height) a partir do tamanho do arquivo."""
    size = os.path.getsize(path)
    if size % INT32_BYTES != 0:
        raise ValueError(
            "Arquivo '{0}' tem {1} bytes, que não é múltiplo de 4 "
            "(int32).".format(path, size)
        )

    n_pixels = size // INT32_BYTES

    if width is not None and height is not None:
        return width, height
    if width is not None:
        if n_pixels % width != 0:
            raise ValueError(
                "Largura {0} não divide o número de pixels ({1}).".format(
                    width, n_pixels
                )
            )
        return width, n_pixels // width
    if height is not None:
        if n_pixels % height != 0:
            raise ValueError(
                "Altura {0} não divide o número de pixels ({1}).".format(
                    height, n_pixels
                )
            )
        return n_pixels // height, height

    default_n = DEFAULT_WIDTH * DEFAULT_HEIGHT
    if n_pixels == default_n:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT

    # Matriz quadrada (caso comum neste projeto)
    side = int(round(n_pixels ** 0.5))
    if side * side == n_pixels:
        return side, side

    raise ValueError(
        "Não foi possível inferir dimensões de '{0}' ({1} pixels). "
        "Informe --width e --height.".format(path, n_pixels)
    )


def validate(ref_path, test_path, width, height, tolerance, max_diff, verbose):
    """Compara duas matrizes pixel a pixel.

    Returns:
        True se a validação passou, False caso contrário.
    """
    total_pixels = width * height

    print("=" * 60)
    print(" Validador de Corretude — Conjunto de Mandelbrot")
    print("=" * 60)
    print("  Referência:   {0}".format(ref_path))
    print("  Teste:        {0}".format(test_path))
    print("  Dimensões:    {0} x {1} ({2:,} pixels)".format(
        width, height, total_pixels
    ))
    print("  Tolerância:   {0:.4f}% dos pixels".format(tolerance * 100.0))
    print("  Diff máxima:  {0} iteração(ões) por pixel".format(max_diff))
    print("-" * 60)

    print("Carregando matriz de referência...")
    ref = load_matrix(ref_path, width, height)

    print("Carregando matriz de teste...")
    test = load_matrix(test_path, width, height)

    pixels_diff = 0
    pixels_over = 0
    max_observed_diff = 0
    sum_diff = 0
    first_divergent = []

    for i in range(total_pixels):
        d = ref[i] - test[i]
        if d < 0:
            d = -d
        if d == 0:
            continue
        pixels_diff += 1
        sum_diff += d
        if d > max_observed_diff:
            max_observed_diff = d
        if d > max_diff:
            pixels_over += 1
        if verbose and len(first_divergent) < VERBOSE_LIMIT:
            py = i // width
            px = i % width
            first_divergent.append((py, px, ref[i], test[i], d))

    pixels_exact = total_pixels - pixels_diff
    mean_diff = (float(sum_diff) / float(total_pixels)) if total_pixels else 0.0
    pct_diff = (float(pixels_diff) / float(total_pixels)) * 100.0
    pct_exact = (float(pixels_exact) / float(total_pixels)) * 100.0

    print("\n{0:^60}".format("Estatísticas da Comparação"))
    print("-" * 60)
    print("  Pixels idênticos:        {0:>12,}  ({1:.4f}%)".format(
        pixels_exact, pct_exact
    ))
    print("  Pixels divergentes:      {0:>12,}  ({1:.6f}%)".format(
        pixels_diff, pct_diff
    ))
    print("  Diff média:              {0:>12.6f}".format(mean_diff))
    print("  Diff máxima observada:   {0:>12}".format(max_observed_diff))
    print("  Pixels com diff > {0}:    {1:>12,}".format(max_diff, pixels_over))
    print("-" * 60)

    max_allowed = int(total_pixels * tolerance)
    passed = True
    reasons = []

    if pixels_diff > max_allowed:
        passed = False
        reasons.append(
            "Pixels divergentes ({0:,}) excedem o limite tolerável "
            "({1:,} = {2:.4f}% de {3:,})".format(
                pixels_diff, max_allowed, tolerance * 100.0, total_pixels
            )
        )

    if pixels_over > 0:
        passed = False
        reasons.append(
            "{0:,} pixel(s) divergem em mais de {1} iteração(ões) "
            "(máximo observado: {2})".format(
                pixels_over, max_diff, max_observed_diff
            )
        )

    print()
    if passed:
        print("  [OK]  VALIDACAO APROVADA — Matrizes dentro da tolerancia")
    else:
        print("  [FALHA]  VALIDACAO REPROVADA — Divergencia fora dos limites")
        print()
        print("Motivos da reprovação:")
        for i, reason in enumerate(reasons, 1):
            print("  {0}. {1}".format(i, reason))

    if verbose and pixels_diff > 0:
        print("\nPrimeiros pixels divergentes (até {0}):".format(VERBOSE_LIMIT))
        print("  {0:>8}  {1:>8}  {2:>8}  {3:>8}  {4:>8}".format(
            "Linha", "Coluna", "Ref", "Teste", "Diff"
        ))
        print("  {0}  {0}  {0}  {0}  {0}".format("-" * 8))
        for py, px, rv, tv, d in first_divergent:
            print("  {0:>8}  {1:>8}  {2:>8}  {3:>8}  {4:>8}".format(
                py, px, rv, tv, d
            ))
        if pixels_diff > VERBOSE_LIMIT:
            print("  ... e mais {0:,} pixel(s)".format(
                pixels_diff - VERBOSE_LIMIT
            ))

    print()
    return passed


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Validador de Corretude para o Conjunto de Mandelbrot. "
            "Compara duas matrizes binárias (int32, Row-Major) pixel a pixel."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python3 validate.py mandelbrot_serial.bin mandelbrot_omp.bin\n"
            "  python3 validate.py ref.bin cuda.bin --width 8192 --height 8192\n"
            "  python3 validate.py ref.bin mpi.bin --verbose --tolerance 0.0001\n"
        ),
    )

    parser.add_argument(
        "reference",
        help="Caminho para a matriz binária de referência (serial).",
    )
    parser.add_argument(
        "test",
        help="Caminho para a matriz binária a ser validada.",
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=None,
        help="Largura da matriz em pixels (inferida do arquivo se omitida).",
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=None,
        help="Altura da matriz em pixels (inferida do arquivo se omitida).",
    )
    parser.add_argument(
        "--tolerance", "-t",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=(
            "Fração máxima de pixels divergentes tolerável "
            "(padrão: 0.0001 = 0,01%%)."
        ),
    )
    parser.add_argument(
        "--max-diff", "-d",
        type=int,
        default=DEFAULT_MAX_DIFF,
        help=(
            "Diferença máxima de iterações permitida por pixel "
            "divergente (padrão: 1)."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Exibir detalhes dos pixels divergentes.",
    )

    args = parser.parse_args()

    try:
        width, height = infer_dimensions(
            args.reference, args.width, args.height
        )
        passed = validate(
            ref_path=args.reference,
            test_path=args.test,
            width=width,
            height=height,
            tolerance=args.tolerance,
            max_diff=args.max_diff,
            verbose=args.verbose,
        )
    except (FileNotFoundError, ValueError, EOFError) as exc:
        print("Erro: {0}".format(exc), file=sys.stderr)
        sys.exit(2)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
