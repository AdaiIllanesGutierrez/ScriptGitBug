#!/usr/bin/env python3
"""
extraer_metricas.py

Uso:
    python3 extraer_metricas.py \
        --results-csv ~/tesis/resultados/JUAMPI/results.csv \
        --out-csv     ~/tesis/resultados/JUAMPI/results_with_metrics.csv \
        --algoritmo   JUAMPI
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict


# Detecta cualquier criterio de cobertura que EvoSuite haya logueado, en vez
# de asumir de antemano una lista fija (LINE, BRANCH, WEAKMUTATION, MUTATION,
# EXCEPTION, etc. varían según la config de EvoSuite usada en cada corrida).
COVERAGE_RE = re.compile(r"Coverage of criterion (\w+): ([0-9]+(?:\.[0-9]+)?)%")
GOALS_RE = re.compile(r"Number of covered goals: ([0-9]+)")

# Líneas típicas de resumen de EvoSuite con el total de tests generados.
TESTS_RE = re.compile(r"\* (?:Total number of test cases:|Generated) ?(\d+)")


def clean_value(v: str) -> str:
    """Quita \\r y espacios sobrantes -- CSVs movidos entre máquinas (por ej.
    vía carpeta compartida de VirtualBox) a veces arrastran finales de línea
    estilo Windows que rompen las rutas al hacer Path(...)."""
    if v is None:
        return v
    return v.replace("\r", "").replace("\n", "").strip()


def remap_logs_dir(original_logs_dir: str, results_csv_dir: Path, override_base: Path | None) -> Path:
    """
    El results.csv y las carpetas de cada corrida (work_root) son siempre
    hermanas dentro de la misma BASE_WORK_ROOT (así las escribe
    run_screened_bugs.py). Si este results.csv se movió a otra máquina, la
    ruta absoluta guardada en logs_dir (de la máquina vieja) ya no existe,
    pero el NOMBRE de la subcarpeta de cada corrida es el mismo en cualquier
    máquina. Por eso alcanza con tomar ese nombre y recomponerlo contra la
    carpeta real donde está el results.csv ahora.
    """
    original = Path(clean_value(original_logs_dir))

    # Si la ruta original ya existe tal cual en esta máquina, no tocar nada.
    if original.is_dir():
        return original

    run_folder_name = original.parent.name  # ej: bug__clase__seed_X__java8
    base = override_base if override_base is not None else results_csv_dir
    remapped = base / run_folder_name / "logs"
    return remapped


def parse_evosuite_log(log_path: Path) -> dict:
    """
    Parsea un evosuite_fixed.log y devuelve un dict:
        {"coverage__LINE": "100", "goals__LINE": "37",
         "coverage__BRANCH": "94", "goals__BRANCH": "12", ...}

    Si el archivo no existe (por ejemplo la corrida fue RUNNER ERROR antes de
    llegar a generar tests), devuelve un dict vacío -- no se inventan valores.
    """
    metrics = {}

    if not log_path.is_file():
        return metrics

    current_criterion = None

    # logging.info() en el runner escribe a stderr, no a stdout -- por eso acá
    # leemos el archivo tal cual, sin asumir que todo esté en un solo stream.
    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            cov_match = COVERAGE_RE.search(line)
            if cov_match:
                current_criterion = cov_match.group(1)
                metrics[f"coverage__{current_criterion}"] = cov_match.group(2)
                continue

            goals_match = GOALS_RE.search(line)
            if goals_match and current_criterion:
                metrics[f"goals__{current_criterion}"] = goals_match.group(1)
                current_criterion = None

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae métricas de EvoSuite (coverage/mutación) para un algoritmo."
    )
    parser.add_argument("--results-csv", required=True, help="results.csv de run_screened_bugs.py")
    parser.add_argument("--out-csv", required=True, help="CSV de salida con métricas agregadas")
    parser.add_argument(
        "--algoritmo",
        required=True,
        choices=["MUTATION", "JUAMPI"],
        help="Nombre del algoritmo (se agrega como columna, para poder unir después)",
    )
    parser.add_argument(
        "--logs-base",
        default=None,
        help=(
            "Carpeta base donde están las subcarpetas de cada corrida en ESTA "
            "máquina, si es distinta de la carpeta donde está --results-csv. "
            "Por default se asume que están junto al results.csv (así las "
            "escribe run_screened_bugs.py)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobreescribir --out-csv si ya existe (por default NO se sobreescribe)",
    )
    args = parser.parse_args()

    results_csv = Path(args.results_csv).expanduser()
    out_csv = Path(args.out_csv).expanduser()
    logs_base = Path(args.logs_base).expanduser() if args.logs_base else None

    if not results_csv.is_file():
        sys.exit(f"ERROR: no existe {results_csv}")

    if out_csv.exists() and not args.force:
        sys.exit(
            f"ERROR: {out_csv} ya existe. No se sobreescribe.\n"
            f"Usá --force si realmente querés reemplazarlo, o elegí otro --out-csv."
        )

    rows = []
    all_criteria = set()
    n_remapped = 0
    n_missing = 0

    with open(results_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k: clean_value(v) for k, v in row.items()}

            original_logs_dir = row.get("logs_dir", "")
            resolved_logs_dir = remap_logs_dir(original_logs_dir, results_csv.parent, logs_base)
            if str(resolved_logs_dir) != original_logs_dir:
                n_remapped += 1

            evosuite_log = resolved_logs_dir / "evosuite_fixed.log"
            if not evosuite_log.is_file():
                n_missing += 1

            metrics = parse_evosuite_log(evosuite_log)
            all_criteria.update(
                key.split("__", 1)[1] for key in metrics if key.startswith("coverage__")
            )

            new_row = dict(row)
            new_row["algoritmo"] = args.algoritmo
            new_row["logs_dir"] = str(resolved_logs_dir)
            new_row.update(metrics)
            rows.append(new_row)

    # Columnas dinámicas de cobertura/goals, ordenadas alfabéticamente para
    # que el CSV sea estable entre corridas.
    coverage_cols = [f"coverage__{c}" for c in sorted(all_criteria)]
    goals_cols = [f"goals__{c}" for c in sorted(all_criteria)]

    base_cols = [
        "algoritmo",
        "bug_id",
        "class_under_test",
        "seed",
        "java_version",
        "exit_code",
        "fixed_result",
        "buggy_result",
        "result",
        "conclusion",
    ]
    tail_cols = ["work_root", "logs_dir"]

    fieldnames = base_cols + coverage_cols + goals_cols + tail_cols

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)

    print(f"OK: {len(rows)} filas escritas en {out_csv}")
    print(f"Criterios de cobertura detectados: {sorted(all_criteria) or '(ninguno -- revisar logs)'}")
    print(f"Rutas remapeadas a esta máquina: {n_remapped}/{len(rows)}")
    if n_missing:
        print(
            f"⚠️  {n_missing}/{len(rows)} filas sin evosuite_fixed.log encontrado "
            f"(ni en la ruta original ni remapeada) -- sus métricas quedan vacías."
        )

    result_counts = Counter(row.get("result", "") for row in rows)
    print("\nResumen de resultados:")
    for result, count in sorted(result_counts.items()):
        print(f"  {count:4}  {result}")


if __name__ == "__main__":
    main()
