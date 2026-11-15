"""
debug_ff_qot_aware_step_by_step.py
==================================
Script interativo para depurar passo a passo o comportamento da heurística
FFQoT_Aware.

O script executa a simulação e, a cada passo, detalha a busca por
candidatos viáveis e as avaliações de disrupção física (OSNR dos serviços ativos).
"""

from __future__ import annotations

import argparse
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


def debug_select_ff_qot_aware_action(env) -> int:
    """
    Executa a mesma lógica de select_ff_qot_aware_action,
    mas imprimindo todos os detalhes no console de forma explicativa.
    """
    context = build_runtime_heuristic_context(env)
    use_resource_only = context.config.mask_mode is MaskMode.RESOURCE_ONLY

    print(f"\n================================================================================")
    print(f"🔍 [FFQoT_Aware DEBUG] PASSO DA SIMULAÇÃO: Requisição #{context.request.service_id}")
    print(f"================================================================================")
    print(f"  • Detalhes da Requisição:")
    print(f"    - Origem: {context.request.source_id} -> Destino: {context.request.destination_id}")
    print(f"    - Demanda de Taxa de Bits: {context.request.bit_rate} Gbps")
    print(f"  • Estado da Rede:")
    active_services = context.state.active_services_by_id
    print(f"    - Serviços Ativos no momento: {list(active_services.keys())}")
    for svc_id, svc in active_services.items():
        print(f"      * Svc #{svc_id}: Mod={svc.modulation.name if svc.modulation else '?'}, "
              f"OSNR={svc.osnr:.2f} dB, Slots=[{svc.service_slot_start}, {svc.service_slot_end_exclusive-1}]")

    evaluated_count = 0
    qot_failed_count = 0
    disrupted_count = 0

    for path_index, path in enumerate(context.analysis.paths):
        path_nodes = " -> ".join([str(n) for n in path.node_names])
        print(f"\n  ➡ Avaliando Caminho K={path_index} (Comprimento: {path.length_km:.1f} km, Nós: {path_nodes})")

        for modulation_offset, mod_idx in enumerate(context.analysis.modulation_indices):
            modulation = context.config.modulations[mod_idx]
            req_slots = int(context.analysis.required_slots_by_path_mod[path_index, modulation_offset])

            if req_slots <= 0:
                print(f"    ├─ Modulação {modulation.name}: Inválida (slots necessários <= 0)")
                continue

            print(f"    ├─ Modulação {modulation.name} (Slots necessários: {req_slots}, Limiar de OSNR: {modulation.minimum_osnr:.2f} dB)")

            if use_resource_only:
                candidate_indices = np.flatnonzero(
                    context.analysis.resource_valid_starts[path_index, modulation_offset, :]
                )
            else:
                candidate_indices = np.flatnonzero(
                    context.analysis.qot_valid_starts[path_index, modulation_offset, :]
                )

            if len(candidate_indices) == 0:
                print(f"    │  └─ [RECURSO INDISPONÍVEL] Sem slots livres/viáveis para este par Caminho+Modulação.")
                continue

            print(f"    │  Slots iniciais candidatos para testar: {candidate_indices.tolist()}")

            for initial_slot in candidate_indices.tolist():
                evaluated_count += 1
                print(f"    │  ┌─ Slot {initial_slot}:")

                # 1. Constrói e avalia o próprio QoT do serviço candidato
                candidate = context.simulator.qot_engine.build_candidate(
                    request=context.request,
                    path=path,
                    modulation=modulation,
                    service_slot_start=int(initial_slot),
                    service_num_slots=req_slots,
                )
                qot_result = context.simulator.qot_engine.evaluate_candidate(context.state, candidate)
                required_osnr_with_margin = float(modulation.minimum_osnr + context.config.margin)
                
                print(f"    │  │  - OSNR estimada do novo serviço: {qot_result.osnr:.2f} dB (Requerida com Margem: {required_osnr_with_margin:.2f} dB)")
                
                if not qot_result.meets_threshold:
                    print(f"    │  │  └─ ❌ FALHA DE QoT: O próprio serviço candidato não atinge a OSNR mínima.")
                    qot_failed_count += 1
                    continue

                # 2. Provisiona temporariamente para avaliar impacto físico em outros serviços ativos
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
                disrupted_details = []

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
                        print(f"    │  │  - Serviços ativos impactados fisicamente (interferência NLI): {impacted_ids}")
                        for update in context.simulator.qot_engine.refresh_services(context.state, impacted_ids):
                            if update.service_id not in context.state.active_services_by_id:
                                continue
                            active_svc = context.state.active_services_by_id[update.service_id]
                            if active_svc.modulation is None:
                                continue
                            
                            threshold = float(active_svc.modulation.minimum_osnr + context.config.margin)
                            new_osnr = float(update.osnr)
                            original_osnr = float(active_svc.osnr)
                            
                            print(f"    │  │    * Svc #{update.service_id}: OSNR anterior={original_osnr:.2f} dB -> Nova OSNR={new_osnr:.2f} dB (Limiar={threshold:.2f} dB)")
                            
                            if new_osnr < threshold:
                                causes_disruption = True
                                disrupted_details.append(
                                    f"Svc #{update.service_id} (Queda de {original_osnr:.2f} dB para {new_osnr:.2f} dB, Limiar={threshold:.2f} dB)"
                                )
                    else:
                        print(f"    │  │  - Nenhum serviço ativo compartilha enlaces físicos com este caminho.")

                finally:
                    # Libera o provisionamento temporário
                    context.state.apply_release(context.request.service_id)

                if causes_disruption:
                    print(f"    │  │  └─ ❌ DISRUPÇÃO DETECTADA: Esse candidato degradará a QoT dos seguintes serviços:")
                    for detail in disrupted_details:
                        print(f"    │  │       • {detail}")
                    disrupted_count += 1
                    continue

                # Encontrou o primeiro candidato válido (First Fit) que não causa nenhuma disrupção
                print(f"    │  └─ ✅ SUCESSO: Candidato escolhido! (Sem disrupções na rede)")
                return encode_action(
                    context.config,
                    path_index=path_index,
                    modulation_offset=modulation_offset,
                    initial_slot=int(initial_slot),
                )

    print(f"\n🚨 [BLOQUEIO] A requisição #{context.request.service_id} foi REJEITADA pela heurística FFQoT_Aware.")
    print(f"  Resumo das buscas executadas:")
    print(f"    - Candidatos totais avaliados: {evaluated_count}")
    print(f"    - Reprovados na QoT própria: {qot_failed_count}")
    print(f"    - Reprovados por causar disrupção: {disrupted_count}")
    return context.reject_action


def main() -> None:
    parser = argparse.ArgumentParser(description="Depurador interativo FFQoT_Aware passo a passo.")
    parser.add_argument("--load", type=float, default=250.0, help="Carga de tráfego (Erlang).")
    parser.add_argument("--margin", type=float, default=1.0, help="Margem de QoT (dB).")
    parser.add_argument("--seed", type=int, default=10, help="Semente aleatória.")
    parser.add_argument("--steps", type=int, default=20, help="Número de requisições a simular.")
    parser.add_argument("--interactive", action="store_true", help="Pausar a cada passo para ler o log.")
    args = parser.parse_args()

    # Cria o cenário Nobel-EU
    scenario = scenario_utils.build_nobel_eu_graph_load_scenario(
        topology_id="nobel-eu",
        episode_length=args.steps,
        seed=args.seed,
        load=args.load,
        mean_holding_time=10800.0,
        num_spectrum_resources=320,
        k_paths=3,
        launch_power_dbm=0.0,
        modulations_to_consider=6,
        margin=args.margin,
        measure_disruptions=True,
        drop_on_disruption=True,
    )
    
    env = make_env(config=scenario)
    _, info = env.reset(seed=args.seed)

    print("Iniciando a depuração passo a passo da heurística FFQoT_Aware...")
    print(f"Configurações: Carga={args.load} Erl, Margem={args.margin} dB, Passos={args.steps}")
    
    step = 0
    while True:
        step += 1
        
        # Seleciona a ação usando o nosso método de depuração
        action = debug_select_ff_qot_aware_action(env)
        
        # Executa a ação no simulador
        _, _, terminated, truncated, info = env.step(action)
        
        status = info.get("status", "unknown")
        print(f"\nOutcome do Passo: Status='{status}', Aceito={info.get('accepted')}")
        
        if args.interactive and not (terminated or truncated):
            input("\nPressione Enter para continuar para a próxima requisição...")

        if terminated or truncated:
            break

    # Imprime estatísticas finais da simulação
    snap = env.simulator.statistics.snapshot()
    print("\n================================================================================")
    print("🏁 SIMULAÇÃO CONCLUÍDA - ESTATÍSTICAS FINAIS:")
    print("================================================================================")
    print(f"  - Requisições Processadas: {snap.episode_services_processed}")
    print(f"  - Aceitas                : {snap.episode_services_accepted}")
    print(f"  - Serviços Derrubados    : {snap.episode_disrupted_services}")
    print(f"  - Taxa de Bloqueio Efetiva: {snap.episode_service_blocking_rate * 100:.2f}%")
    print("================================================================================")


if __name__ == "__main__":
    main()
