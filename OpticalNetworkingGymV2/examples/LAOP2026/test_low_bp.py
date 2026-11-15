import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))
sys.path.insert(0, str(Path(".").resolve()))

from optical_networking_gym_v2 import make_env
from optical_networking_gym_v2.heuristics.runtime_heuristics import (
    build_runtime_heuristic_context,
    select_disruption_aware_first_fit_action,
)
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils

def run_test(launch_power, bit_rates):
    scenario = scenario_utils.build_nobel_eu_graph_load_scenario(
        topology_id="nobel-eu",
        episode_length=2000,
        seed=42,
        load=0.01,
        num_spectrum_resources=320,
        k_paths=3,
        launch_power_dbm=launch_power,
        modulations_to_consider=6,
        margin=0.0,
        measure_disruptions=False,
    )
    
    # Hacking dataclass to test different bit rates
    object.__setattr__(scenario, "bit_rates", bit_rates)
    probs = tuple(1.0/len(bit_rates) for _ in bit_rates)
    object.__setattr__(scenario, "bit_rate_probabilities", probs)
    
    # recreate traffic source with new bit rates
    traffic_src = scenario._build_default_traffic_source()
    object.__setattr__(scenario, "traffic_source", traffic_src)
    
    env = make_env(config=scenario)
    env.reset(seed=42)
    
    total = 0
    blocked = 0
    
    for step in range(2000):
        ctx = build_runtime_heuristic_context(env)
        action = select_disruption_aware_first_fit_action(env)
        total += 1
        if action == ctx.reject_action:
            blocked += 1
            
        _, _, term, trunc, _ = env.step(action)
        if term or trunc:
            env.reset()
            
    bp = blocked / total
    return bp

tests = [
    (0.0, (48, 120, 240, 480)),
    (2.0, (48, 120, 240, 480)),
    (4.0, (48, 120, 240, 480)),
    (6.0, (48, 120, 240, 480)),
    (0.0, (48, 120, 240)),  # Without 480G
    (2.0, (48, 120, 240)),
    (4.0, (48, 120, 240)),
]

print("Testando configurações para reduzir a BP (abaixo de 10%)")
print("Carga = 0.01 Erl (Rede Vazia)")
print(f"{'Power (dBm)':>12} | {'Bit Rates (Gbps)':>20} | {'BP (%)':>8}")
print("-" * 48)
for pwr, brs in tests:
    bp = run_test(pwr, brs)
    print(f"{pwr:>12.1f} | {str(brs):>20} | {bp*100:>7.2f}%")
