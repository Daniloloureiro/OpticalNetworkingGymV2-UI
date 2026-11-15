"""
runtime_heuristics_test.py
==========================
Versão experimental da heurística FFQoT_Aware com
**fallback relaxado em dois estágios** (FFQoTA_Otimizada).

Problema da FFQoT_Aware (select_ff_qot_aware_action):
  - Comportamento binário: qualquer candidato que cause ao menos 1 disrupção
    é completamente descartado.
  - Se todos os candidatos causam alguma disrupção, a requisição é REJEITADA,
    mesmo que a disrupção fosse mínima (ex: 0.01 dB abaixo do limiar).

Melhoria proposta — FFQoTA_Otimizada (dois estágios):
  Estágio 1 (igual ao original): busca candidato que não cause nenhuma
    disrupção. Se encontrar, retorna imediatamente (comportamento idêntico ao
    original no caso favorável).
  Estágio 2 (fallback NOVO): se nenhum candidato for "limpo", em vez de
    rejeitar, escolhe o candidato "menos pior", selecionado por:
      (a) menor número de serviços afetados (disruption_count)
      (b) em empate, menor déficit total de OSNR (soma das violações)
      (c) em empate final, posição First-Fit (menor slot inicial)

Isso reduz a rigidez da heurística original, permitindo aceitar mais
requisições em cenários de alta carga, ao custo de um leve aumento de
disrupções — o que pode ser compensado pela redução do bloqueio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from optical_networking_gym_v2.contracts.enums import MaskMode
from optical_networking_gym_v2.runtime.action_codec import encode_action

from .runtime_heuristics import (
    RuntimeHeuristicContext,
    _candidate_causes_disruption,  # reutiliza a função auxiliar existente
    build_runtime_heuristic_context,
)

if TYPE_CHECKING:
    from optical_networking_gym_v2.envs.optical_env import OpticalEnv
    from optical_networking_gym_v2.runtime.simulator import Simulator


# ---------------------------------------------------------------------------
# Estrutura de custo de disrupção de um candidato
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _DisruptionCost:
    """Métricas de custo de disrupção de um candidato (slot/path/mod)."""
    disruption_count: int    # número de serviços que seriam interrompidos
    total_deficit_db: float  # soma dos déficits OSNR de todos os afetados
    path_index: int
    modulation_offset: int
    initial_slot: int

    def sort_key(self) -> tuple[int, float, int, int, int]:
        """Menor é melhor: menos disrupções, menor deficit, posição FF."""
        return (
            self.disruption_count,
            self.total_deficit_db,
            self.path_index,
            self.modulation_offset,
            self.initial_slot,
        )


def _candidate_disruption_cost(
    context: RuntimeHeuristicContext,
    *,
    path_index: int,
    modulation_offset: int,
    initial_slot: int,
) -> _DisruptionCost | None:
    """
    Avalia o custo de disrupção de um candidato sem usar o mecanismo binário.

    Retorna None se o candidato nem sequer passa no limiar de QoT para o
    próprio serviço requisitado (candidato inviável de qualquer forma).

    Caso contrário, retorna um _DisruptionCost com:
      - disruption_count: quantos serviços existentes ficariam abaixo do limiar
      - total_deficit_db: soma dos déficits OSNR (limiar - osnr_novo) dos afetados

    Se disruption_count == 0, o candidato é "limpo" (não causa disrupção).
    """
    simulator = context.simulator
    state = context.state

    path = context.analysis.paths[path_index]
    modulation_index = int(context.analysis.modulation_indices[modulation_offset])
    modulation = context.config.modulations[modulation_index]
    service_num_slots = int(context.analysis.required_slots_by_path_mod[path_index, modulation_offset])
    if service_num_slots <= 0:
        return None

    occupied_slot_start = int(initial_slot)
    occupied_slot_end_exclusive = int(initial_slot + service_num_slots)
    if occupied_slot_end_exclusive < context.config.num_spectrum_resources:
        occupied_slot_end_exclusive += 1

    # Avalia QoT do candidato para o próprio serviço
    candidate = simulator.qot_engine.build_candidate(
        request=context.request,
        path=path,
        modulation=modulation,
        service_slot_start=int(initial_slot),
        service_num_slots=service_num_slots,
    )
    qot_result = simulator.qot_engine.evaluate_candidate(state, candidate)
    if not qot_result.meets_threshold:
        # Candidato inviável: não passa nem para o próprio serviço
        return None

    # Provisiona temporariamente para medir impacto nos outros serviços
    state.apply_provision(
        request=context.request,
        path=path,
        service_slot_start=int(initial_slot),
        service_num_slots=service_num_slots,
        occupied_slot_start=occupied_slot_start,
        occupied_slot_end_exclusive=occupied_slot_end_exclusive,
        modulation=modulation,
        center_frequency=candidate.center_frequency,
        bandwidth=candidate.bandwidth,
        launch_power=candidate.launch_power,
    )
    disruption_count = 0
    total_deficit_db = 0.0
    try:
        state.apply_qot_updates(
            {
                context.request.service_id: {
                    "osnr": qot_result.osnr,
                    "ase": qot_result.ase,
                    "nli": qot_result.nli,
                }
            }
        )
        impacted_ids = simulator.qot_engine.impacted_service_ids(
            state,
            path,
            exclude_service_id=context.request.service_id,
        )
        for update in simulator.qot_engine.refresh_services(state, impacted_ids):
            if update.service_id not in state.active_services_by_id:
                continue
            service = state.active_services_by_id[update.service_id]
            if service.modulation is None:
                continue
            threshold = float(service.modulation.minimum_osnr + context.config.margin)
            new_osnr = float(update.osnr)
            if new_osnr < threshold:
                disruption_count += 1
                total_deficit_db += threshold - new_osnr
    finally:
        state.apply_release(context.request.service_id)

    return _DisruptionCost(
        disruption_count=disruption_count,
        total_deficit_db=total_deficit_db,
        path_index=path_index,
        modulation_offset=modulation_offset,
        initial_slot=initial_slot,
    )


def select_ff_qota_optimized_action(
    source: "OpticalEnv | Simulator | RuntimeHeuristicContext",
    *,
    allow_disruption_fallback: bool = True,
) -> int:
    """
    FFQoTA_Otimizada (dois estágios).

    Parâmetros
    ----------
    source :
        Ambiente, simulador, ou contexto heurístico.
    allow_disruption_fallback : bool, default=True
        Se True (padrão), ativa o Estágio 2 quando nenhum candidato limpo
        é encontrado. Se False, comporta-se identicamente ao FFQoT_Aware.

    Estágio 1 — Candidato Limpo (idêntico ao FFQoT_Aware)
    --------------------------------------------------------
    Itera sobre todos os candidatos viáveis (path × mod × slot) em ordem
    First-Fit. Se encontrar um candidato que não cause nenhuma disrupção,
    retorna imediatamente.

    Estágio 2 — Fallback Relaxado (NOVO)
    --------------------------------------
    Se nenhum candidato limpo existe, escolhe o "menos pior" dentre todos os
    candidatos avaliados, priorizando:
      1. Menor número de serviços interrompidos.
      2. Menor déficit total de OSNR (soma das violações, em dB).
      3. Menor índice de slot (critério First-Fit como desempate final).
    """
    context = build_runtime_heuristic_context(source)
    use_resource_only = context.config.mask_mode is MaskMode.RESOURCE_ONLY

    # Coleta de candidatos para o Estágio 2 (apenas quando necessário)
    best_fallback: _DisruptionCost | None = None

    for path_index, _path in enumerate(context.analysis.paths):
        for modulation_offset, _modulation_index in enumerate(context.analysis.modulation_indices):
            if use_resource_only:
                candidate_indices = np.flatnonzero(
                    context.analysis.resource_valid_starts[path_index, modulation_offset, :]
                )
            else:
                candidate_indices = np.flatnonzero(
                    context.analysis.qot_valid_starts[path_index, modulation_offset, :]
                )

            for initial_slot in candidate_indices.tolist():
                # --- Estágio 1: verifica se o candidato é limpo ---
                if not _candidate_causes_disruption(
                    context,
                    path_index=path_index,
                    modulation_offset=modulation_offset,
                    initial_slot=int(initial_slot),
                ):
                    # Candidato limpo encontrado — retorna imediatamente (FF)
                    return encode_action(
                        context.config,
                        path_index=path_index,
                        modulation_offset=modulation_offset,
                        initial_slot=int(initial_slot),
                    )

                # --- Estágio 2: avalia custo de disrupção para fallback ---
                if not allow_disruption_fallback:
                    continue

                # Só avalia custo se ainda não temos um fallback perfeito
                # (disruption_count==0 seria "limpo", já tratado acima).
                # Calcula o custo completo para comparação posterior.
                cost = _candidate_disruption_cost(
                    context,
                    path_index=path_index,
                    modulation_offset=modulation_offset,
                    initial_slot=int(initial_slot),
                )
                if cost is None:
                    # Candidato inviável (não passa no limiar de QoT)
                    continue
                if best_fallback is None or cost.sort_key() < best_fallback.sort_key():
                    best_fallback = cost

    # Estágio 2: usa o melhor fallback encontrado, se houver
    if best_fallback is not None:
        return encode_action(
            context.config,
            path_index=best_fallback.path_index,
            modulation_offset=best_fallback.modulation_offset,
            initial_slot=best_fallback.initial_slot,
        )

    # Nenhum candidato viável — rejeita
    return context.reject_action


__all__ = [
    "select_ff_qota_optimized_action",
]
