"""
run_debug_10_markdown_report.py
===============================
Simula as 10 primeiras requisições com a DAFF original, extrai
todos os dados físicos de OSNR e gera um relatório formatado em Markdown.
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


def generate_report():
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

    rows = []

    for step_idx in range(steps):
        context = build_runtime_heuristic_context(env)
        use_resource_only = context.config.mask_mode is MaskMode.RESOURCE_ONLY

        req_id = context.request.service_id
        src_name = context.topology.node_names[context.request.source_id]
        dst_name = context.topology.node_names[context.request.destination_id]
        bitrate = context.request.bit_rate

        chosen_action = context.reject_action
        found_candidate = False
        allocated_osnr = 0.0
        chosen_path_str = "N/A"
        chosen_mod = "N/A"
        chosen_slots = "N/A"
        block_reason = "N/A"
        path_len = 0.0

        for path_index, path in enumerate(context.analysis.paths):
            if found_candidate:
                break
            
            path_nodes = " -> ".join([str(n) for n in path.node_names])

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

                for initial_slot in candidate_indices.tolist():
                    candidate = context.simulator.qot_engine.build_candidate(
                        request=context.request,
                        path=path,
                        modulation=modulation,
                        service_slot_start=int(initial_slot),
                        service_num_slots=req_slots,
                    )
                    qot_result = context.simulator.qot_engine.evaluate_candidate(context.state, candidate)
                    
                    if not qot_result.meets_threshold:
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
                    finally:
                        context.state.apply_release(context.request.service_id)

                    if causes_disruption:
                        continue

                    # Candidato limpo encontrado!
                    chosen_action = encode_action(
                        context.config,
                        path_index=path_index,
                        modulation_offset=modulation_offset,
                        initial_slot=int(initial_slot),
                    )
                    allocated_osnr = qot_result.osnr
                    chosen_path_str = f"K={path_index} ({path_nodes})"
                    path_len = path.length_km
                    chosen_mod = modulation.name
                    chosen_slots = f"[{initial_slot}, {initial_slot + req_slots - 1}]"
                    found_candidate = True
                    break

        if not found_candidate:
            # Detecta motivo
            # Conta se havia recursos livres de espectro
            free_slots_avail = False
            for path_index, path in enumerate(context.analysis.paths):
                for modulation_offset, mod_idx in enumerate(context.analysis.modulation_indices):
                    req_slots = int(context.analysis.required_slots_by_path_mod[path_index, modulation_offset])
                    if req_slots <= 0:
                        continue
                    candidate_indices = np.flatnonzero(context.analysis.qot_valid_starts[path_index, modulation_offset, :])
                    if len(candidate_indices) > 0:
                        free_slots_avail = True
                        break
            if not free_slots_avail:
                block_reason = "Falta de Espectro (Slots)"
            else:
                block_reason = "Evitar Disrupção (Física)"

        # Aplica a decisão no ambiente
        _, _, _, _, info = env.step(chosen_action)

        rows.append({
            "step": step_idx + 1,
            "req_id": req_id,
            "flow": f"{src_name} -> {dst_name}",
            "bitrate": bitrate,
            "status": "Aceito" if found_candidate else "Bloqueado",
            "mod": chosen_mod,
            "slots": chosen_slots,
            "osnr": f"{allocated_osnr:.2f} dB" if found_candidate else "N/A",
            "dist": f"{path_len:.1f} km" if found_candidate else "N/A",
            "block_reason": block_reason
        })

    # Imprime a tabela em formato Markdown
    print("### TABELA DE RESULTADOS DO DEBUGGER: 10 REQUISIÇÕES")
    print("| Passo | ID Global | Fluxo (Cidades) | Bitrate (Gbps) | Status | Modulação | Slots Alocados | OSNR Alocada | Distância | Motivo do Bloqueio |")
    print("| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for r in rows:
        print(f"| {r['step']} | {r['req_id']} | {r['flow']} | {r['bitrate']} | {r['status']} | {r['mod']} | {r['slots']} | {r['osnr']} | {r['dist']} | {r['block_reason']} |")


if __name__ == "__main__":
    generate_report()
