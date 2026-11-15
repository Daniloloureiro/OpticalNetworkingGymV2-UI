from __future__ import annotations

"""
run_legacy_ff_no_disruptions.py
===============================
Executa a simulação com a heurística First Fit Legada (First Fit normal)
usando margem de 0.0 dB e desativando a medição e a queda por disrupções:
  - measure_disruptions = False
  - drop_on_disruption = False

Varre as cargas de tráfego: 250.0, 275.0, 300.0 Erlangs.
Salva os resultados consolidados em CSV.
"""

import sys
import csv
import json
import time
from pathlib import Path
from datetime import datetime

# Inserir paths do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from optical_networking_gym_v2 import ScenarioConfig, make_env, get_modulations, BUILTIN_TOPOLOGY_DIR
from optical_networking_gym_v2.utils import experiment_utils as sweep_utils
from optical_networking_gym_v2.utils.experiment_utils import DEFAULT_MODULATION_NAMES

OUTPUT_DIR = PROJECT_ROOT / "examples" / "LAOP2026" / "results_legacy_ff_no_disruptions"
LOADS = [250.0, 275.0, 300.0]
MARGIN = 0.0
SEED = 10
EPISODE_LENGTH = 1000

def build_ff_scenario(load: float) -> ScenarioConfig:
    return ScenarioConfig(
        scenario_id=f"nobel-eu_ff_no_disr_seed{SEED}",
        topology_id="nobel-eu",
        topology_dir=BUILTIN_TOPOLOGY_DIR,
        k_paths=3,
        num_spectrum_resources=320,
        episode_length=EPISODE_LENGTH,
        max_span_length_km=80.0,
        default_attenuation_db_per_km=0.2,
        default_noise_figure_db=4.5,
        bit_rates=(48, 120, 240, 480),
        load=load,
        mean_holding_time=10800.0,
        qot_constraint="ASE+NLI",          # NLI ativo fisicamente
        measure_disruptions=False,         # <-- DESATIVADO
        drop_on_disruption=False,          # <-- DESATIVADO
        frequency_start=(3e8 / 1565e-9),
        frequency_slot_bandwidth=12.5e9,
        launch_power_dbm=0.0,
        margin=MARGIN,
        bandwidth=4e12,
        modulations=get_modulations(DEFAULT_MODULATION_NAMES),
        modulations_to_consider=6,
        seed=SEED,
    )

def run_simulation(load: float) -> dict:
    scenario = build_ff_scenario(load)
    env = make_env(config=scenario)
    _, info = env.reset(seed=SEED)
    
    start_time = time.perf_counter()
    while True:
        action = int(sweep_utils.select_masked_first_fit_policy(env, info))
        _, _, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break
            
    elapsed = time.perf_counter() - start_time
    stats = env.simulator.statistics.snapshot()
    
    # Calcular perda efetiva
    eff_loss = (stats.episode_services_processed - stats.episode_services_served) / stats.episode_services_processed
    
    return {
        "policy": "legacy_ff",
        "qot_constraint": "ASE+NLI",
        "measure_disruptions": False,
        "drop_on_disruption": False,
        "load": float(load),
        "margin": float(MARGIN),
        "seed": SEED,
        "processed": int(stats.episode_services_processed),
        "accepted": int(stats.episode_services_accepted),
        "served": int(stats.episode_services_served),
        "blocking_rate": float(stats.episode_service_blocking_rate),
        "blocked_resources": int(stats.episode_services_blocked_resources),
        "blocked_qot": int(stats.episode_services_blocked_qot),
        "rejected_by_agent": int(stats.episode_services_rejected_by_agent),
        "disrupted": int(stats.episode_disrupted_services),
        "dropped_qot": int(stats.episode_services_dropped_qot),
        "effective_loss_rate": float(eff_loss),
        "elapsed_s": float(elapsed),
    }

def main():
    print("=" * 60)
    print("  INICIANDO SIMULAÇÃO: FF LEGADA (SEM DISRUPÇÕES)")
    print("=" * 60)
    print(f"  Topologia           : Nobel-EU")
    print(f"  Margem              : {MARGIN} dB")
    print(f"  Cargas              : {LOADS} Erlangs")
    print(f"  Conexões            : {EPISODE_LENGTH}")
    print(f"  measure_disruptions : False")
    print(f"  drop_on_disruption  : False")
    print("-" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    
    for load in LOADS:
        print(f"Executando Load={load} Erlangs...")
        res = run_simulation(load)
        results.append(res)
        print(f"  Finalizado em {res['elapsed_s']:.3f}s. Bloqueio: {res['blocking_rate']*100:.2f}% | Quedas: {res['dropped_qot']}")
        
    # Salvar unificado em CSV
    now_str = datetime.now().strftime("%d-%m-%Hh%M")
    csv_path = OUTPUT_DIR / f"{now_str}-legacy-ff-no-disruptions-summary.csv"
    fieldnames = list(results[0].keys())
    
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    print("\n" + "=" * 80)
    print(f"{'LOAD':<6} | {'ACEITOS':<8} | {'REJ_AGENT':<9} | {'BLOQ_SPEC':<9} | {'BLOQ_QOT':<8} | {'QUEDAS':<6} | {'PERDA_EFET':<10}")
    print("-" * 80)
    for r in results:
        print(f"{r['load']:<6.1f} | {r['accepted']:<8} | {r['rejected_by_agent']:<9} | {r['blocked_resources']:<9} | {r['blocked_qot']:<8} | {r['dropped_qot']:<6} | {r['effective_loss_rate']*100:<9.2f}%")
    print("=" * 80)
    print(f"Resumo unificado gravado em:\n  - {csv_path}")

if __name__ == "__main__":
    main()
