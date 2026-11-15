from __future__ import annotations

"""
run_medium_sweep_ff_nli_only.py
===============================
Mesmo cenário do run_medium_sweep.py (cargas 50–150 Erlangs, margens 0.0 e 3.0 dB)
com QoT NLI-only (qot_constraint="ASE+NLI", mas com o ruído ASE zerado no kernel)
utilizando a política First Fit normal (select_masked_first_fit_policy) em vez da DAFF.

Os resultados são salvos em results_medium_ff_nli_only/ para não misturar com os outros sweeps.
"""

import argparse
import csv
import json
import multiprocessing
from datetime import datetime
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from optical_networking_gym_v2 import (
    BUILTIN_TOPOLOGY_DIR,
    ScenarioConfig,
    make_env,
    get_modulations,
)
from optical_networking_gym_v2.utils import experiment_utils as sweep_utils
from optical_networking_gym_v2.utils.experiment_utils import DEFAULT_MODULATION_NAMES

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results_medium_ff_nli_only"

LOADS = [50.0, 75.0, 100.0, 125.0, 150.0]
MARGINS = [0.0, 3.0]
SEED = 10
EPISODE_LENGTH = 1000
K_PATHS = 3
MODULATIONS_TO_CONSIDER = 6


def build_ff_nli_only_scenario(load: float, margin: float) -> ScenarioConfig:
    """Constrói cenário idêntico ao run_medium_sweep.py com qot_constraint=ASE+NLI."""
    return ScenarioConfig(
        scenario_id=f"nobel-eu_ff_nli_only_seed{SEED}",
        topology_id="nobel-eu",
        topology_dir=BUILTIN_TOPOLOGY_DIR,
        k_paths=K_PATHS,
        num_spectrum_resources=320,
        episode_length=EPISODE_LENGTH,
        max_span_length_km=80.0,
        default_attenuation_db_per_km=0.2,
        default_noise_figure_db=4.5,
        bit_rates=(48, 120, 240, 480),
        load=load,
        mean_holding_time=10800.0,
        qot_constraint="ASE+NLI",          # <-- ASE+NLI (será NLI-only devido ao kernel modificado)
        measure_disruptions=True,
        drop_on_disruption=True,
        frequency_start=(3e8 / 1565e-9),
        frequency_slot_bandwidth=12.5e9,
        launch_power_dbm=0.0,
        margin=margin,
        bandwidth=4e12,
        modulations=get_modulations(DEFAULT_MODULATION_NAMES),
        modulations_to_consider=MODULATIONS_TO_CONSIDER,
        seed=SEED,
    )


def run_point_task(task_args: tuple[float, float]) -> Path:
    import time as _time
    load, margin = task_args

    load_str = f"load{int(load) if float(load).is_integer() else load}"
    margin_str = f"margin{margin:g}"
    pattern = f"*-trace-ff-nli-only-nobel-eu-{load_str}-{margin_str}-seed{SEED}.summary.json"
    matches = list(OUTPUT_DIR.glob(pattern))
    if matches:
        print(f"Resultado já existe para Load={load}, Margin={margin} dB. Reutilizando.")
        return matches[0]

    scenario = build_ff_nli_only_scenario(load=load, margin=margin)
    env = make_env(config=scenario)
    _, info = env.reset(seed=SEED)

    started_at = _time.perf_counter()
    print(f"Iniciando simulação FF NLI-only: Load={load}, Margin={margin} dB...")

    while True:
        action = sweep_utils.select_masked_first_fit_policy(env, info)
        _, _, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break

    elapsed_s = _time.perf_counter() - started_at
    snapshot = env.simulator.statistics.snapshot()
    now = datetime.now()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    base_name = (
        f"{now.strftime('%d-%m-%Hh%M')}"
        f"-trace-ff-nli-only"
        f"-nobel-eu"
        f"-{load_str}"
        f"-{margin_str}"
        f"-seed{SEED}"
    )
    summary_path = OUTPUT_DIR / f"{base_name}.summary.json"

    summary = {
        "date": now.isoformat(),
        "topology_id": "nobel-eu",
        "policy": "first_fit",
        "qot_constraint": "NLI_ONLY",
        "load": float(load),
        "margin": float(margin),
        "seed": SEED,
        "episode_length_requested": EPISODE_LENGTH,
        "steps_executed": int(env.simulator.steps_completed),
        "measure_disruptions": True,
        "drop_on_disruption": True,
        "service_blocking_rate": float(snapshot.episode_service_blocking_rate),
        "service_served_rate": float(snapshot.episode_service_served_rate),
        "bit_rate_blocking_rate": float(snapshot.episode_bit_rate_blocking_rate),
        "services_processed": int(snapshot.episode_services_processed),
        "services_accepted": int(snapshot.episode_services_accepted),
        "services_served": int(snapshot.episode_services_served),
        "blocked_due_to_resources": int(snapshot.episode_services_blocked_resources),
        "blocked_due_to_osnr": int(snapshot.episode_services_blocked_qot),
        "rejected": int(snapshot.episode_services_rejected_by_agent),
        "episode_disrupted_services_count": int(snapshot.episode_disrupted_services),
        "episode_disrupted_services_rate": float(snapshot.episode_disrupted_services_rate),
        "disrupted_or_dropped_services": int(snapshot.episode_services_dropped_qot),
        "elapsed_s": float(elapsed_s),
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Simulação concluída: Load={load}, Margin={margin} dB. Salva em: {summary_path.name}")
    return summary_path


def build_final_csvs() -> None:
    summary_files = list(OUTPUT_DIR.glob("*.summary.json"))
    if not summary_files:
        print("Nenhum arquivo summary.json encontrado.")
        return

    rows = []
    for filepath in summary_files:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        row = {
            "policy": data.get("policy", "first_fit"),
            "qot_constraint": data.get("qot_constraint", "NLI_ONLY"),
            "modulations": "BPSK+QPSK+8QAM+16QAM+32QAM+64QAM",
            "mod_count": MODULATIONS_TO_CONSIDER,
            "load": data["load"],
            "margin": data["margin"],
            "seed_base": data["seed"],
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
            "effective_loss_rate": (data["services_processed"] - data["services_served"]) / data["services_processed"],
            "elapsed_s": data["elapsed_s"],
        }
        rows.append(row)

    rows.sort(key=lambda x: (x["load"], x["margin"]))

    now_str = datetime.now().strftime("%d-%m-%Hh%M")
    csv_path = OUTPUT_DIR / f"{now_str}-medium-ff-nli-only-summary.csv"
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResumo unificado gravado em:\n - {csv_path}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [(load, margin) for load in LOADS for margin in MARGINS]

    num_cpus = min(multiprocessing.cpu_count(), len(tasks))
    print(f"Iniciando varredura FF NLI-only com {num_cpus} processos em paralelo...")
    print(f"Cargas: {LOADS}")
    print(f"Margens: {MARGINS} dB")
    print(f"qot_constraint: NLI-only (com ASE zerado no kernel)\n")

    start_time = time.perf_counter()
    with multiprocessing.Pool(processes=num_cpus) as pool:
        pool.map(run_point_task, tasks)

    elapsed = time.perf_counter() - start_time
    print(f"\nTodas as {len(tasks)} simulações concluídas em {elapsed:.2f} segundos!")
    build_final_csvs()


if __name__ == "__main__":
    main()
