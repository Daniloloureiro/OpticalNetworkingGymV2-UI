"""
run_debug_blocked_details.py
============================
Analisa em detalhe as requisições bloqueadas (Requisição #6 e #8)
durante a simulação de 10 passos da DAFF original, extraindo
os cálculos físicos de OSNR e as razões exatas do bloqueio.
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


def analyze_blocked_requests():
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

        # Armazenar o estado antes do processamento
        active_before = {
            svc_id: {
                "osnr": svc.osnr,
                "slots": [svc.service_slot_start, svc.service_slot_end_exclusive - 1],
                "mod": svc.modulation.name,
                "min_osnr": svc.modulation.minimum_osnr
            }
            for svc_id, svc in context.state.active_services_by_id.items()
        }

        chosen_action = context.reject_action
        found_candidate = False

        # Se for um dos passos bloqueados (#6 ou #8), vamos coletar logs exaustivos
        is_target = (step_idx + 1) in [6, 8]

        if is_target:
            print(f"\n================================================================================")
            print(f"📊 DETALHAMENTO FÍSICO DE BLOQUEIO: REQUISIÇÃO #{step_idx+1} (ID: #{req_id})")
            print(f"   Fluxo: {src} -> {dst} | Demanda: {bitrate} Gbps")
            print(f"================================================================================")
            print(f"   Serviços Ativos na Rede antes deste passo:")
            for s_id, s_info in active_before.items():
                print(f"     - Svc #{s_id}: Mod={s_info['mod']}, Slots={s_info['slots']}, OSNR={s_info['osnr']:.2f} dB (Limiar={s_info['min_osnr']+margin:.2f} dB)")

        disruption_examples = []
        tested_slots_count = 0
        qot_fail_count = 0

        for path_index, path in enumerate(context.analysis.paths):
            path_nodes = " -> ".join([str(n) for n in path.node_names])
            
            if is_target:
                print(f"\n   -> Analisando Caminho K={path_index}: {path_nodes} ({path.length_km:.1f} km)")

            for modulation_offset, mod_idx in enumerate(context.analysis.modulation_indices):
                modulation = context.config.modulations[mod_idx]
                req_slots = int(context.analysis.required_slots_by_path_mod[path_index, modulation_offset])

                if req_slots <= 0:
                    if is_target:
                        print(f"      * Modulação {modulation.name}: Inviável para esta distância.")
                    continue

                if use_resource_only:
                    candidate_indices = np.flatnonzero(
                        context.analysis.resource_valid_starts[path_index, modulation_offset, :]
                    )
                else:
                    candidate_indices = np.flatnonzero(
                        context.analysis.qot_valid_starts[path_index, modulation_offset, :]
                    )

                if is_target:
                    print(f"      * Modulação {modulation.name} (Exige {modulation.minimum_osnr + margin:.2f} dB, necessita de {req_slots} slots):")
                    if len(candidate_indices) == 0:
                        print(f"        └─ [RECURSO] Bloqueado por máscara de recurso (sem {req_slots} slots contíguos livres).")
                    else:
                        print(f"        └─ Encontrados {len(candidate_indices)} slots candidatos de espectro livre.")

                for initial_slot in candidate_indices.tolist():
                    tested_slots_count += 1
                    candidate = context.simulator.qot_engine.build_candidate(
                        request=context.request,
                        path=path,
                        modulation=modulation,
                        service_slot_start=int(initial_slot),
                        service_num_slots=req_slots,
                    )
                    qot_result = context.simulator.qot_engine.evaluate_candidate(context.state, candidate)
                    
                    if not qot_result.meets_threshold:
                        qot_fail_count += 1
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
                    disrupted_list = []
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
                                    disrupted_list.append((update.service_id, active_svc.osnr, new_osnr, threshold))
                    finally:
                        context.state.apply_release(context.request.service_id)

                    if causes_disruption:
                        if len(disruption_examples) < 3: # Salva alguns exemplos para exibir
                            disruption_examples.append({
                                "path": path_nodes,
                                "mod": modulation.name,
                                "slot": initial_slot,
                                "disrupted": disrupted_list
                            })
                        continue

                    # Candidato limpo encontrado!
                    chosen_action = encode_action(
                        context.config,
                        path_index=path_index,
                        modulation_offset=modulation_offset,
                        initial_slot=int(initial_slot),
                    )
                    found_candidate = True
                    break
                if found_candidate:
                    break
            if found_candidate:
                break

        # Se for uma das requisições alvo, detalhe o resultado físico
        if is_target:
            if not found_candidate:
                print(f"\n   ❌ VEREDICTO DE BLOQUEIO:")
                if tested_slots_count == 0:
                    print(f"      -> MOTIVO: Falta Absoluta de Espectro Livre.")
                    print(f"         Não existem slots vazios contíguos suficientes em nenhum caminho ou modulação viável.")
                else:
                    print(f"      -> MOTIVO: Bloqueado para Evitar Disrupção Física de Vizinhos.")
                    print(f"         Total de candidatos testados com recursos livres e QoT própria OK: {tested_slots_count}")
                    print(f"         Todos os {tested_slots_count} causavam quedas de OSNR abaixo do limiar em outros serviços.")
                    print(f"         Exemplos de falhas de disrupção físico-óptica analisadas:")
                    for ex in disruption_examples:
                        print(f"           * No Caminho {ex['path']} usando {ex['mod']} no Slot {ex['slot']}:")
                        for d in ex["disrupted"]:
                            print(f"             - Svc #{d[0]}: OSNR cairia de {d[1]:.2f} dB para {d[2]:.2f} dB (Limiar exigido era {d[3]:.2f} dB - Violação de {d[3]-d[2]:.2f} dB)")
            else:
                print(f"\n   >> OUTCOME: Requisição Aceita!")

        # Aplica a decisão no ambiente
        env.step(chosen_action)


if __name__ == "__main__":
    analyze_blocked_requests()
