"""
run_debug_10_osnr.py
====================
Simula 10 requisições usando a DAFF original e imprime os detalhes de
OSNR (estimada para o candidato, limiar e impacto nos vizinhos).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante caminhos corretos de importação
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from optical_networking_gym_v2 import make_env
from optical_networking_gym_v2.contracts.enums import MaskMode
from optical_networking_gym_v2.runtime.action_codec import encode_action
from optical_networking_gym_v2.heuristics.runtime_heuristics import (
    RuntimeHeuristicContext,
    build_runtime_heuristic_context,
)
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils


def run_debug_10():
    steps = 10
    load = 250.0
    margin = 1.0
    seed = 10

    scenario = scenario_utils.build_nobel_eu_graph_load_scenario(
        topology_id="nobel-eu",
        episode_length=steps,
        seed=seed,
        load=load,
        mean_holding_time=10800.0,
        num_spectrum_resources=320,
        k_paths=3,
        launch_power_dbm=0.0,
        modulations_to_consider=6,
        margin=margin,
        measure_disruptions=True,
        drop_on_disruption=True,
    )
    
    env = make_env(config=scenario)
    env.reset(seed=seed)

    for step_idx in range(steps):
        context = build_runtime_heuristic_context(env)
        use_resource_only = context.config.mask_mode is MaskMode.RESOURCE_ONLY

        req_id = context.request.service_id
        src = context.request.source_id
        dst = context.request.destination_id
        bitrate = context.request.bit_rate

        print(f"\n================================================================================")
        print(f"👉 REQUISIÇÃO #{step_idx+1} (ID Global: #{req_id})")
        print(f"   Fluxo: {src} -> {dst} | Demanda: {bitrate} Gbps")
        print(f"================================================================================")
        
        active_services = context.state.active_services_by_id
        if active_services:
            print("   Serviços ativos atualmente na rede:")
            for svc_id, svc in active_services.items():
                print(f"     - Svc #{svc_id}: Mod={svc.modulation.name}, Slots=[{svc.service_slot_start}, {svc.service_slot_end_exclusive-1}], OSNR Atual={svc.osnr:.2f} dB")
        else:
            print("   Serviços ativos atualmente na rede: NENHUM")

        chosen_action = context.reject_action
        found_candidate = False

        for path_index, path in enumerate(context.analysis.paths):
            if found_candidate:
                break
            
            path_nodes = " -> ".join([str(n) for n in path.node_names])
            print(f"\n   [Caminho K={path_index}] {path_nodes} ({path.length_km:.1f} km)")

            for modulation_offset, mod_idx in enumerate(context.analysis.modulation_indices):
                if found_candidate:
                    break
                
                modulation = context.config.modulations[mod_idx]
                req_slots = int(context.analysis.required_slots_by_path_mod[path_index, modulation_offset])

                if req_slots <= 0:
                    continue

                if use_resource_only:
                    candidate_indices = np.flatnonzero(
                        context.analysis.resource_valid_starts[path_index, modulation_offset, :]
                    )
                else:
                    candidate_indices = np.flatnonzero(
                        context.analysis.qot_valid_starts[path_index, modulation_offset, :]
                    )

                if len(candidate_indices) == 0:
                    print(f"     * Modulação {modulation.name} (SE: {modulation.spectral_efficiency}): Sem slots livres.")
                    continue

                print(f"     * Modulação {modulation.name} (Limiar de OSNR: {modulation.minimum_osnr + margin:.2f} dB, Slots: {req_slots})")
                print(f"       Testando slots iniciais candidatos: {candidate_indices.tolist()[:5]}...")

                for initial_slot in candidate_indices.tolist():
                    candidate = context.simulator.qot_engine.build_candidate(
                        request=context.request,
                        path=path,
                        modulation=modulation,
                        service_slot_start=int(initial_slot),
                        service_num_slots=req_slots,
                    )
                    qot_result = context.simulator.qot_engine.evaluate_candidate(context.state, candidate)
                    req_osnr_with_margin = modulation.minimum_osnr + margin

                    print(f"       - Slot Inicial {initial_slot}: OSNR Estimada = {qot_result.osnr:.2f} dB ", end="")
                    if not qot_result.meets_threshold:
                        print(f"❌ [Falhou QoT Própria (Exige {req_osnr_with_margin:.2f} dB)]")
                        continue

                    # Provisionamento temporário
                    occupied_slot_start = int(initial_slot)
                    occupied_slot_end_exclusive = int(initial_slot + req_slots)
                    if occupied_slot_end_exclusive < context.config.num_spectrum_resources:
                        occupied_slot_end_exclusive += 1

                    context.state.apply_provision(
                        request=context.request,
                        path=path,
                        service_slot_start=int(initial_slot),
                        service_num_slots=req_slots,
                        occupied_slot_start=occupied_slot_start,
                        occupied_slot_end_exclusive=occupied_slot_end_exclusive,
                        modulation=modulation,
                        center_frequency=candidate.center_frequency,
                        bandwidth=candidate.bandwidth,
                        launch_power=candidate.launch_power,
                    )

                    causes_disruption = False
                    disruption_details = []
                    try:
                        context.state.apply_qot_updates(
                            {
                                context.request.service_id: {
                                    "osnr": qot_result.osnr,
                                    "ase": qot_result.ase,
                                    "nli": qot_result.nli,
                                }
                            }
                        )
                        impacted_ids = context.simulator.qot_engine.impacted_service_ids(
                            context.state,
                            path,
                            exclude_service_id=context.request.service_id,
                        )

                        if impacted_ids:
                            for update in context.simulator.qot_engine.refresh_services(context.state, impacted_ids):
                                if update.service_id not in context.state.active_services_by_id:
                                    continue
                                active_svc = context.state.active_services_by_id[update.service_id]
                                if active_svc.modulation is None:
                                    continue
                                
                                threshold = float(active_svc.modulation.minimum_osnr + margin)
                                new_osnr = float(update.osnr)
                                
                                if new_osnr < threshold:
                                    causes_disruption = True
                                    disruption_details.append(
                                        f"Svc #{update.service_id} (OSNR caiu de {active_svc.osnr:.2f} para {new_osnr:.2f} dB, Min={threshold:.2f} dB)"
                                    )
                    finally:
                        context.state.apply_release(context.request.service_id)

                    if causes_disruption:
                        print(f"❌ [Causa disrupção nos vizinhos: {', '.join(disruption_details)}]")
                        continue

                    # Candidato limpo encontrado!
                    print(f"✅ [Aprovado! OSNR={qot_result.osnr:.2f} dB]")
                    chosen_action = encode_action(
                        context.config,
                        path_index=path_index,
                        modulation_offset=modulation_offset,
                        initial_slot=int(initial_slot),
                    )
                    found_candidate = True
                    break

        # Aplica a decisão no ambiente
        _, _, _, _, info = env.step(chosen_action)
        status = info.get("status", "unknown")
        
        if found_candidate:
            print(f"\n   >> OUTCOME: REQUISIÇÃO ACEITA. Status='{status}'")
        else:
            print(f"\n   >> OUTCOME: REQUISIÇÃO BLOQUEADA. Status='{status}'")

    print("\n================================================================================")
    print("🏁 Depuração de 10 passos concluída.")
    print("================================================================================")


if __name__ == "__main__":
    run_debug_10()
