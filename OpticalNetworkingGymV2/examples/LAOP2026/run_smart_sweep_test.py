"""
run_smart_sweep_test.py
=======================
Varredura de carga × margem usando a heurística FFQoTA_Otimizada
(trace_disruptions_test.py).

Usa os mesmos parâmetros do run_smart_sweep.py original para permitir
comparação direta entre as duas heurísticas.
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing
from datetime import datetime
from pathlib import Path
import sys
import time

# Garantir que a pasta do projeto esteja no path do python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Importa o script de simulação com a nova heurística
from examples.LAOP2026.trace_disruptions_test import run_trace

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results_test"

LOADS = [250.0, 275.0, 300.0]
MARGINS = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
SEED = 10
EPISODE_LENGTH = 1000
MODULATIONS_TO_CONSIDER = 6


def run_point_task(task_args):
    load, margin = task_args
    load_str = f"load{int(load) if float(load).is_integer() else load}"
    margin_str = f"margin{margin:g}"
    # Padrão do nome do arquivo gerado pelo trace_disruptions_test.py
    pattern = f"*-trace-relaxed-nobel-eu-{load_str}-{margin_str}-seed{SEED}.summary.json"
    matches = list(OUTPUT_DIR.glob(pattern))
    if matches:
        print(f"Resultado já existe para Load={load}, Margin={margin} dB. Reutilizando dados.")
        return matches[0]

    args = argparse.Namespace(
        topology_id="nobel-eu",
        load=load,
        margin=margin,
        seed=SEED,
        episode_length=EPISODE_LENGTH,
        mean_holding_time=10800.0,
        num_spectrum_resources=320,
        k_paths=3,
        launch_power_dbm=0.0,
        modulations_to_consider=MODULATIONS_TO_CONSIDER,
        drop_on_disruption=True,
        stop_after_disruptions=0,
        stop_on_first_disruption=False,
        output_dir=OUTPUT_DIR,
        write_step_trace=False,
        no_fallback=False,  # Estágio 2 habilitado (comportamento relaxado)
    )
    print(f"Iniciando simulação RELAXADA: Load={load}, Margin={margin} dB...")
    result = run_trace(args)
    print(f"Concluída: Load={load}, Margin={margin} dB → {result.summary_path.name}")
    return result.summary_path


def build_final_csvs():
    summary_files = list(OUTPUT_DIR.glob("*.summary.json"))
    if not summary_files:
        print("Nenhum arquivo summary.json encontrado.")
        return

    rows = []
    for filepath in summary_files:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            row = {
                "policy": "FFQoTA_Otimizada",
                "threshold_set": "legacy",
                "modulations": "BPSK+QPSK+8QAM+16QAM+32QAM+64QAM",
                "mod_count": MODULATIONS_TO_CONSIDER,
                "load": data["load"],
                "margin": data["margin"],
                "seed_base": data["seed"],
                "episode_index": 0,
                "episode_seed": data["seed"],
                "steps_requested": data["episode_length_requested"],
                "measure_disruptions": data["measure_disruptions"],
                "drop_on_disruption": data["drop_on_disruption"],
                "allow_disruption_fallback": data.get("allow_disruption_fallback", True),
                "processed": data["services_processed"],
                "accepted": data["services_accepted"],
                "served": data["services_served"],
                "blocking_rate": data["service_blocking_rate"],
                "served_rate": data["service_served_rate"],
                "bit_rate_blocking_rate": data["bit_rate_blocking_rate"],
                "blocked_resources": data["blocked_due_to_resources"],
                "blocked_qot": data["blocked_due_to_osnr"],
                "rejected_by_agent": data["rejected"],
                "disrupted": data["episode_disrupted_services_count"],
                "dropped_qot": data["disrupted_or_dropped_services"],
                "disruption_rate": data["episode_disrupted_services_rate"],
                "drop_rate": data["episode_disrupted_services_rate"],
                "effective_loss_rate": (
                    (data["services_processed"] - data["services_served"]) / data["services_processed"]
                ),
                "mean_accepted_osnr": data.get("mean_osnr_accepted", 0.0),
                "elapsed_s": data["elapsed_s"],
            }
            rows.append(row)

    rows.sort(key=lambda x: (x["load"], x["margin"]))

    now_str = datetime.now().strftime("%d-%m-%Hh%M")
    episodes_csv_path = OUTPUT_DIR / f"{now_str}-relaxed-scenario-episodes.csv"
    summary_csv_path = OUTPUT_DIR / f"{now_str}-relaxed-scenario-summary.csv"

    fieldnames = list(rows[0].keys())

    for csv_path in [episodes_csv_path, summary_csv_path]:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"\nResumos unificados gravados em:")
    print(f" - {episodes_csv_path}")
    print(f" - {summary_csv_path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [(load, margin) for load in LOADS for margin in MARGINS]

    num_cpus = min(multiprocessing.cpu_count(), len(tasks))
    print(f"Iniciando varredura FFQoTA_Otimizada com {num_cpus} processos em paralelo...")
    print(f"Heurística: FFQoTA_Otimizada (2 estágios)")
    print(f"Parâmetros: Loads={LOADS}, Margins={MARGINS}, Seed={SEED}\n")

    start_time = time.perf_counter()
    with multiprocessing.Pool(processes=num_cpus) as pool:
        pool.map(run_point_task, tasks)

    elapsed = time.perf_counter() - start_time
    print(f"\nTodas as {len(tasks)} simulações concluídas em {elapsed:.2f} segundos!")

    build_final_csvs()


if __name__ == "__main__":
    main()
