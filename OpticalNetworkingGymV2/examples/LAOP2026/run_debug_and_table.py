"""
run_debug_and_table.py
======================
Simula o DAFF original por 25 passos e formata os resultados
em tabelas Markdown para exibição.
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


def simulate_daff_with_stats(env, steps_count: int):
    # Dicionários/Listas para armazenar as estatísticas por passo
    step_rows = []
    evaluation_details = []

    for step_idx in range(steps_count):
        context = build_runtime_heuristic_context(env)
        use_resource_only = context.config.mask_mode is MaskMode.RESOURCE_ONLY

        req_id = context.request.service_id
        src = context.request.source_id
        dst = context.request.destination_id
        bitrate = context.request.bit_rate

        evaluated_count = 0
        qot_failed_count = 0
        disrupted_count = 0
        disrupted_targets = set()

        chosen_action = context.reject_action
        chosen_path_str = "N/A"
        chosen_mod = "N/A"
        chosen_slots = "N/A"
        block_reason = "N/A"

        found_candidate = False

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
                    evaluated_count += 1

                    candidate = context.simulator.qot_engine.build_candidate(
                        request=context.request,
                        path=path,
                        modulation=modulation,
                        service_slot_start=int(initial_slot),
                        service_num_slots=req_slots,
                    )
                    qot_result = context.simulator.qot_engine.evaluate_candidate(context.state, candidate)
                    
                    if not qot_result.meets_threshold:
                        qot_failed_count += 1
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
                                
                                threshold = float(active_svc.modulation.minimum_osnr + context.config.margin)
                                new_osnr = float(update.osnr)
                                
                                if new_osnr < threshold:
                                    causes_disruption = True
                                    disrupted_targets.add(update.service_id)
                    finally:
                        context.state.apply_release(context.request.service_id)

                    if causes_disruption:
                        disrupted_count += 1
                        continue

                    # Encontrou candidato limpo!
                    chosen_action = encode_action(
                        context.config,
                        path_index=path_index,
                        modulation_offset=modulation_offset,
                        initial_slot=int(initial_slot),
                    )
                    chosen_path_str = f"K={path_index} ({path_nodes})"
                    chosen_mod = modulation.name
                    chosen_slots = f"[{initial_slot}, {initial_slot + req_slots - 1}]"
                    found_candidate = True
                    break

        if not found_candidate:
            if evaluated_count == 0:
                block_reason = "Falta de Recursos (Espectro)"
            elif qot_failed_count == evaluated_count:
                block_reason = "Qualidade de Sinal (QoT própria)"
            elif disrupted_count > 0:
                block_reason = "Evitar Disrupção (Vizinhos)"
            else:
                block_reason = "Outro"

        # Executa a ação no simulador original do Gym
        _, _, terminated, truncated, info = env.step(chosen_action)
        status = info.get("status", "unknown")

        step_rows.append({
            "req_id": req_id,
            "flow": f"{src} -> {dst}",
            "bitrate": bitrate,
            "status": "Aceito" if "accepted" in status else "Bloqueado",
            "path": chosen_path_str,
            "modulation": chosen_mod,
            "slots": chosen_slots,
            "block_reason": block_reason
        })

        evaluation_details.append({
            "req_id": req_id,
            "evaluated": evaluated_count,
            "qot_failed": qot_failed_count,
            "disruptions": disrupted_count,
            "disrupted_targets": sorted(list(disrupted_targets))
        })

        if terminated or truncated:
            break

    return step_rows, evaluation_details


def main():
    # Semente 10, carga 280 (alta carga para forçar bloqueios e disrupções)
    steps = 25
    load = 280.0
    margin = 1.0
    seed = 12

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

    step_rows, evaluation_details = simulate_daff_with_stats(env, steps)

    # Gera Tabela 1: Resumo dos Passos
    print("### TABELA 1: Histórico de Requisições e Alocações (DAFF Original)")
    print("| ID Req | Fluxo (Origem -> Destino) | Bitrate (Gbps) | Status | Modulação | Slots Alocados | Caminho Escolhido | Motivo do Bloqueio |")
    print("| :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |")
    for r in step_rows:
        print(f"| {r['req_id']} | {r['flow']} | {r['bitrate']} | {r['status']} | {r['modulation']} | {r['slots']} | {r['path']} | {r['block_reason']} |")

    print("\n" + "="*80 + "\n")

    # Gera Tabela 2: Detalhamento da Busca e Disrupções
    print("### TABELA 2: Estatísticas de Busca e Detecção de Disrupção por Requisição")
    print("| ID Req | Candidatos Avaliados | Falhas QoT Própria | Bloqueado p/ Evitar Disrupção | Serviços Vizinhos que Seriam Afetados |")
    print("| :---: | :---: | :---: | :---: | :--- |")
    for d in evaluation_details:
        targets_str = ", ".join([f"#{t}" for t in d["disrupted_targets"]]) if d["disrupted_targets"] else "Nenhum"
        print(f"| {d['req_id']} | {d['evaluated']} | {d['qot_failed']} | {d['disruptions']} | {targets_str} |")


if __name__ == "__main__":
    main()
