"""
analyze_ff_qota_optimized_flow.py
=================================
Analisa o fluxo de execução da heurística FFQoTA_Otimizada (dois estágios) passo a passo,
mostrando todos os cálculos intermediários:
  - ESTÁGIO 1: busca candidato limpo (igual ao original)
  - ESTÁGIO 2: fallback ao "menos pior" quando nenhum candidato é limpo
    (menor n° de disrupções → menor déficit total OSNR → First-Fit)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from optical_networking_gym_v2 import make_env
from optical_networking_gym_v2.contracts.enums import MaskMode
from optical_networking_gym_v2.runtime.action_codec import encode_action
from optical_networking_gym_v2.heuristics.runtime_heuristics import (
    build_runtime_heuristic_context,
)
from optical_networking_gym_v2.heuristics.runtime_heuristics_test import (
    _candidate_disruption_cost,
    _DisruptionCost,
)
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils

SEP  = "=" * 80
SEP2 = "-" * 80
SEP3 = "·" * 60


def hdr(title: str, level: int = 1) -> None:
    if level == 1:
        print(f"\n{SEP}")
        print(f"  {title}")
        print(SEP)
    elif level == 2:
        print(f"\n  {SEP2}")
        print(f"    {title}")
        print(f"  {SEP2}")
    else:
        print(f"\n    {SEP3}")
        print(f"      {title}")
        print(f"    {SEP3}")


def fmt_slots(start: int, end_exc: int) -> str:
    return f"[{start}, {end_exc - 1}] ({end_exc - start} slots)"


def analyze_step_relaxed(env, step_idx: int, margin: float) -> tuple[int, str]:
    """
    Executa e exibe o fluxo completo de um único passo da heurística FFQoTA_Otimizada.
    Retorna (action, resultado: 'aceito_limpo' | 'aceito_fallback' | 'bloqueado').
    """
    context = build_runtime_heuristic_context(env)
    use_resource_only = context.config.mask_mode is MaskMode.RESOURCE_ONLY
    cfg = context.config

    req = context.request
    hdr(f"PASSO {step_idx + 1}  |  Requisição ID #{req.service_id}", level=1)

    # ─── BLOCO 1: DETALHES DA REQUISIÇÃO ──────────────────────────────────
    hdr("BLOCO 1: DETALHES DA REQUISIÇÃO", level=2)
    src_name = context.topology.node_names[req.source_id]
    dst_name = context.topology.node_names[req.destination_id]
    print(f"    Origem              : {src_name} (ID={req.source_id})")
    print(f"    Destino             : {dst_name} (ID={req.destination_id})")
    print(f"    Taxa de bits        : {req.bit_rate} Gbps")
    print(f"    ID do Serviço       : #{req.service_id}")

    # ─── BLOCO 2: ESTADO DA REDE ──────────────────────────────────────────
    hdr("BLOCO 2: ESTADO ATUAL DA REDE (Serviços Ativos)", level=2)
    active = context.state.active_services_by_id
    if not active:
        print("    (nenhum serviço ativo no momento)")
    for svc_id, svc in active.items():
        mod_name = svc.modulation.name if svc.modulation else "?"
        min_osnr  = svc.modulation.minimum_osnr if svc.modulation else 0.0
        threshold = min_osnr + margin
        margin_db = svc.osnr - threshold
        flag = "⚠️ ABAIXO" if margin_db < 0 else "✅"
        print(f"    Svc #{svc_id:<3}  Mod={mod_name:<6}  "
              f"Slots={fmt_slots(svc.service_slot_start, svc.service_slot_end_exclusive):<18}  "
              f"OSNR={svc.osnr:.3f} dB  Limiar={threshold:.3f} dB  "
              f"Margem={margin_db:+.3f} dB  {flag}  "
              f"ASE={svc.ase:.3f} dB  NLI={svc.nli:.3f} dB")

    # ─── BLOCO 3: CANDIDATOS DISPONÍVEIS ──────────────────────────────────
    hdr("BLOCO 3: ANÁLISE DE CANDIDATOS (Caminhos × Modulações × Slots)", level=2)
    analysis = context.analysis
    paths = analysis.paths
    mod_indices = analysis.modulation_indices

    print(f"    K-caminhos disponíveis  : {len(paths)}")
    print(f"    Modulações consideradas : {len(mod_indices)}")
    print(f"    Espectro total          : {cfg.num_spectrum_resources} slots")
    print(f"    Margem de guarda        : {margin:.2f} dB")
    print()

    for path_index, path in enumerate(paths):
        nodes_str = " -> ".join(str(n) for n in path.node_names)
        print(f"    Caminho K={path_index}: {nodes_str}")
        print(f"             {path.length_km:.1f} km | Hops={path.hops} | Links={list(path.link_ids)}")
        for mod_offset, mod_idx in enumerate(mod_indices):
            mod = cfg.modulations[mod_idx]
            req_slots = int(analysis.required_slots_by_path_mod[path_index, mod_offset])
            mask = (analysis.resource_valid_starts if use_resource_only
                    else analysis.qot_valid_starts)[path_index, mod_offset, :]
            qot_count = int(mask.sum())
            print(f"      - {mod.name:<6}  "
                  f"(OSNR_min={mod.minimum_osnr:.2f} dB, "
                  f"Limiar={mod.minimum_osnr + margin:.2f} dB, "
                  f"Slots_req={req_slots})  "
                  f"→ slots válidos QoT={qot_count:>4}")

    # ─── BLOCO 4: ESTÁGIO 1 — BUSCA CANDIDATO LIMPO ──────────────────────
    hdr("BLOCO 4 — ESTÁGIO 1: Busca Candidato SEM Disrupção", level=2)
    print("    (Idêntico ao FFQoT_Aware: First-Fit, rejeita qualquer disrupção)")

    chosen_action  = context.reject_action
    resultado      = "bloqueado"

    # Para o Estágio 2, guarda lista de custos
    fallback_candidates: list[_DisruptionCost] = []
    tot_tested  = 0
    tot_limpo   = 0
    tot_disrupt = 0
    tot_inviavel = 0
    escolha_data: dict = {}
    MAX_SLOTS_PRINT = 6

    stage1_found = False

    for path_index, path in enumerate(paths):
        if stage1_found:
            break
        nodes_str = " -> ".join(str(n) for n in path.node_names)
        print(f"\n    [Caminho K={path_index}] {nodes_str} ({path.length_km:.1f} km)")

        for mod_offset, mod_idx in enumerate(mod_indices):
            if stage1_found:
                break
            mod       = cfg.modulations[mod_idx]
            req_slots = int(analysis.required_slots_by_path_mod[path_index, mod_offset])
            if req_slots <= 0:
                print(f"      * {mod.name:<6}: Inviável para esta distância. PULANDO.")
                continue

            mask = (analysis.resource_valid_starts if use_resource_only
                    else analysis.qot_valid_starts)[path_index, mod_offset, :]
            cands = np.flatnonzero(mask).tolist()

            if not cands:
                print(f"      * {mod.name:<6} ({req_slots} slots): Sem candidatos. PULANDO.")
                continue

            print(f"      * {mod.name:<6} (req={req_slots} slots, "
                  f"limiar={mod.minimum_osnr + margin:.2f} dB) "
                  f"→ {len(cands)} candidatos de slot")

            shown = cands[:MAX_SLOTS_PRINT]
            remaining = len(cands) - len(shown)

            for slot in shown:
                if stage1_found:
                    break
                tot_tested += 1

                # Avalia custo de disrupção completo
                cost = _candidate_disruption_cost(
                    context,
                    path_index=path_index,
                    modulation_offset=mod_offset,
                    initial_slot=int(slot),
                )

                if cost is None:
                    tot_inviavel += 1
                    # Calcula QoT do candidato para mostrar motivo
                    cand = context.simulator.qot_engine.build_candidate(
                        request=req,
                        path=path,
                        modulation=mod,
                        service_slot_start=slot,
                        service_num_slots=req_slots,
                    )
                    qot = context.simulator.qot_engine.evaluate_candidate(context.state, cand)
                    print(f"\n        ┌─ Slot {slot:>4}: ❌ INVIÁVEL "
                          f"(OSNR={qot.osnr:.4f} dB < Limiar={mod.minimum_osnr + margin:.4f} dB)")
                    print(f"        └─ ASE={qot.ase:.4f} dB  NLI={qot.nli:.4f} dB")
                    continue

                # Candidato é fisicamente viável — avalia disrupção
                cand = context.simulator.qot_engine.build_candidate(
                    request=req,
                    path=path,
                    modulation=mod,
                    service_slot_start=slot,
                    service_num_slots=req_slots,
                )
                qot = context.simulator.qot_engine.evaluate_candidate(context.state, cand)

                print(f"\n        ┌─ Slot {slot:>4}:")
                print(f"        │   Freq. central    = {cand.center_frequency / 1e12:.4f} THz")
                print(f"        │   Potência lançada = {10 * np.log10(cand.launch_power * 1e3):.2f} dBm")
                print(f"        │   OSNR estimada    = {qot.osnr:.4f} dB  "
                      f"(ASE={qot.ase:.4f} dB, NLI={qot.nli:.4f} dB)")
                print(f"        │   OSNR necessária  = {mod.minimum_osnr + margin:.4f} dB")
                print(f"        │   Serviços afetados= {cost.disruption_count}  "
                      f"| Déficit total= {cost.total_deficit_db:.4f} dB")

                if cost.disruption_count == 0:
                    # CANDIDATO LIMPO — Estágio 1 encontrou
                    tot_limpo += 1
                    print(f"        └─ ✅ LIMPO: Sem disrupção! FFQoTA_Otimizada (Estágio 1) escolhe.")
                    chosen_action = encode_action(
                        cfg,
                        path_index=path_index,
                        modulation_offset=mod_offset,
                        initial_slot=slot,
                    )
                    escolha_data = {
                        "estagio": 1,
                        "path_k": path_index,
                        "path_str": nodes_str,
                        "path_km": path.length_km,
                        "mod": mod.name,
                        "mod_min": mod.minimum_osnr,
                        "slot": slot,
                        "req_slots": req_slots,
                        "osnr": qot.osnr,
                        "ase": qot.ase,
                        "nli": qot.nli,
                        "freq_thz": cand.center_frequency / 1e12,
                        "pwr_dbm": 10 * np.log10(cand.launch_power * 1e3),
                        "disruption_count": 0,
                        "total_deficit_db": 0.0,
                    }
                    resultado = "aceito_limpo"
                    stage1_found = True
                    break
                else:
                    # Candidato suja — guarda para Estágio 2
                    tot_disrupt += 1
                    print(f"        └─ ⚠️  DISRUPTIVO: "
                          f"{cost.disruption_count} svc(s) afetados, "
                          f"déficit={cost.total_deficit_db:.4f} dB — guardado para Estágio 2")
                    fallback_candidates.append(cost)

            if not stage1_found and remaining > 0:
                # Ainda precisa processar o restante para o Estágio 2
                extra = cands[MAX_SLOTS_PRINT:]
                print(f"      ... processando mais {len(extra)} slots para Estágio 2 ...")
                for slot in extra:
                    tot_tested += 1
                    cost = _candidate_disruption_cost(
                        context,
                        path_index=path_index,
                        modulation_offset=mod_offset,
                        initial_slot=int(slot),
                    )
                    if cost is None:
                        tot_inviavel += 1
                        continue
                    if cost.disruption_count == 0:
                        tot_limpo += 1
                        cand = context.simulator.qot_engine.build_candidate(
                            request=req, path=path, modulation=mod,
                            service_slot_start=slot, service_num_slots=req_slots,
                        )
                        qot = context.simulator.qot_engine.evaluate_candidate(context.state, cand)
                        print(f"        → ✅ Slot {slot}: LIMPO! Estágio 1 resolve.")
                        chosen_action = encode_action(
                            cfg, path_index=path_index,
                            modulation_offset=mod_offset, initial_slot=slot,
                        )
                        escolha_data = {
                            "estagio": 1, "path_k": path_index,
                            "path_str": nodes_str, "path_km": path.length_km,
                            "mod": mod.name, "mod_min": mod.minimum_osnr,
                            "slot": slot, "req_slots": req_slots,
                            "osnr": qot.osnr, "ase": qot.ase, "nli": qot.nli,
                            "freq_thz": cand.center_frequency / 1e12,
                            "pwr_dbm": 10 * np.log10(cand.launch_power * 1e3),
                            "disruption_count": 0, "total_deficit_db": 0.0,
                        }
                        resultado = "aceito_limpo"
                        stage1_found = True
                        break
                    else:
                        tot_disrupt += 1
                        fallback_candidates.append(cost)

    # ─── BLOCO 5: ESTÁGIO 2 — FALLBACK AO MENOS PIOR ────────────────────
    if not stage1_found:
        hdr("BLOCO 5 — ESTÁGIO 2: Fallback ao Candidato 'Menos Pior'", level=2)
        print(f"    Nenhum candidato limpo encontrado no Estágio 1.")
        print(f"    Total candidatos avaliados : {tot_tested}")
        print(f"    Inviáveis (QoT própria)    : {tot_inviavel}")
        print(f"    Disruptivos (com vizinhos) : {tot_disrupt}")
        print(f"    Disponíveis para fallback  : {len(fallback_candidates)}")

        if fallback_candidates:
            # Ordena pelo sort_key: (disruption_count, deficit_db, path_idx, mod_off, slot)
            fallback_candidates.sort(key=lambda c: c.sort_key())

            print(f"\n    Top-5 candidatos para fallback (ordenados por custo):")
            print(f"    {'Rank':<5} {'Svc Afetados':>13} {'Déficit(dB)':>13} "
                  f"{'K':>3} {'Mod':>6} {'Slot':>6}")
            print(f"    {'-'*5} {'-'*13} {'-'*13} {'-'*3} {'-'*6} {'-'*6}")

            for rank, fc in enumerate(fallback_candidates[:5]):
                mod_idx  = int(context.analysis.modulation_indices[fc.modulation_offset])
                mod_name = cfg.modulations[mod_idx].name
                print(f"    {rank+1:<5} {fc.disruption_count:>13} {fc.total_deficit_db:>13.4f} "
                      f"{fc.path_index:>3} {mod_name:>6} {fc.initial_slot:>6}")

            best = fallback_candidates[0]
            mod_idx  = int(context.analysis.modulation_indices[best.modulation_offset])
            mod      = cfg.modulations[mod_idx]
            path     = paths[best.path_index]
            nodes_str = " -> ".join(str(n) for n in path.node_names)
            req_slots = int(analysis.required_slots_by_path_mod[best.path_index, best.modulation_offset])

            # Calcula valores físicos do vencedor do fallback
            cand = context.simulator.qot_engine.build_candidate(
                request=req, path=path, modulation=mod,
                service_slot_start=best.initial_slot,
                service_num_slots=req_slots,
            )
            qot = context.simulator.qot_engine.evaluate_candidate(context.state, cand)

            print(f"\n    >>> FALLBACK ESCOLHIDO (candidato #1 da lista acima):")
            print(f"        Caminho   : K={best.path_index} → {nodes_str}")
            print(f"        Modulação : {mod.name} (limiar={mod.minimum_osnr + margin:.2f} dB)")
            print(f"        Slot      : {best.initial_slot}  "
                  f"(slots=[{best.initial_slot}, {best.initial_slot+req_slots-1}])")
            print(f"        OSNR      : {qot.osnr:.4f} dB  "
                  f"(ASE={qot.ase:.4f} dB, NLI={qot.nli:.4f} dB)")
            print(f"        Svc afetados: {best.disruption_count}  |  "
                  f"Déficit OSNR total: {best.total_deficit_db:.4f} dB")

            # Mostra quais serviços serão perturbados
            print(f"\n    Impacto nos vizinhos do fallback escolhido:")
            context.state.apply_provision(
                request=req, path=path,
                service_slot_start=best.initial_slot,
                service_num_slots=req_slots,
                occupied_slot_start=best.initial_slot,
                occupied_slot_end_exclusive=min(
                    best.initial_slot + req_slots + 1, cfg.num_spectrum_resources),
                modulation=mod,
                center_frequency=cand.center_frequency,
                bandwidth=cand.bandwidth,
                launch_power=cand.launch_power,
            )
            try:
                context.state.apply_qot_updates({
                    req.service_id: {"osnr": qot.osnr, "ase": qot.ase, "nli": qot.nli}
                })
                impacted = context.simulator.qot_engine.impacted_service_ids(
                    context.state, path, exclude_service_id=req.service_id)
                if not impacted:
                    print("        Nenhum vizinho impactado.")
                for upd in context.simulator.qot_engine.refresh_services(context.state, impacted):
                    if upd.service_id not in context.state.active_services_by_id:
                        continue
                    svc = context.state.active_services_by_id[upd.service_id]
                    if svc.modulation is None:
                        continue
                    thr      = svc.modulation.minimum_osnr + margin
                    new_osnr = float(upd.osnr)
                    old_osnr = float(svc.osnr)
                    delta    = new_osnr - old_osnr
                    violacao = thr - new_osnr
                    ok       = new_osnr >= thr
                    print(f"        Svc #{upd.service_id}  Mod={svc.modulation.name}  "
                          f"OSNR: {old_osnr:.4f} → {new_osnr:.4f} dB  "
                          f"(Δ={delta:+.4f} dB)  "
                          f"Limiar={thr:.4f} dB  "
                          f"Violação={violacao:+.4f} dB  "
                          f"{'✅ OK' if ok else '❌ DISRUPÇÃO (aceita pelo fallback)'}")
            finally:
                context.state.apply_release(req.service_id)

            chosen_action = encode_action(
                cfg, path_index=best.path_index,
                modulation_offset=best.modulation_offset,
                initial_slot=best.initial_slot,
            )
            escolha_data = {
                "estagio": 2,
                "path_k": best.path_index,
                "path_str": nodes_str,
                "path_km": path.length_km,
                "mod": mod.name,
                "mod_min": mod.minimum_osnr,
                "slot": best.initial_slot,
                "req_slots": req_slots,
                "osnr": qot.osnr,
                "ase": qot.ase,
                "nli": qot.nli,
                "freq_thz": cand.center_frequency / 1e12,
                "pwr_dbm": 10 * np.log10(cand.launch_power * 1e3),
                "disruption_count": best.disruption_count,
                "total_deficit_db": best.total_deficit_db,
            }
            resultado = "aceito_fallback"
        else:
            print(f"\n    Nenhum candidato viável encontrado (nem com fallback). BLOQUEANDO.")
    else:
        # Estágio 1 resolveu — imprime resumo de candidatos descartados durante busca
        print(f"\n    Estágio 1 encontrou candidato limpo.")
        print(f"    Candidatos avaliados antes do aceito: {tot_tested - 1} disruptivos testados.")

    # ─── BLOCO 6: DECISÃO FINAL ────────────────────────────────────────────
    hdr("BLOCO 6: DECISÃO FINAL DA FFQoTA_OTIMIZADA", level=2)
    print(f"    Total de candidatos avaliados      : {tot_tested}")
    print(f"    Inviáveis (QoT própria falhou)     : {tot_inviavel}")
    print(f"    Limpos (Estágio 1)                 : {tot_limpo}")
    print(f"    Disruptivos (Estágio 2)            : {tot_disrupt}")

    if resultado in ("aceito_limpo", "aceito_fallback"):
        d = escolha_data
        estagio_str = "1 (Candidato Limpo)" if d["estagio"] == 1 else "2 (Fallback Relaxado)"
        print(f"    Estágio de Decisão                 : {estagio_str}")
        print(f"    RESULTADO: ✅ ACEITAR REQUISIÇÃO")
        print(f"    ── Caminho   : K={d['path_k']} → {d['path_str']}")
        print(f"    ── Distância : {d['path_km']:.1f} km")
        print(f"    ── Modulação : {d['mod']} (OSNR_min={d['mod_min']:.2f} dB)")
        print(f"    ── Slot inicial : {d['slot']}")
        print(f"    ── Slots usados: [{d['slot']}, {d['slot']+d['req_slots']-1}] "
              f"({d['req_slots']} slots)")
        print(f"    ── OSNR final  : {d['osnr']:.4f} dB")
        print(f"       ASE         : {d['ase']:.4f} dB")
        print(f"       NLI         : {d['nli']:.4f} dB")
        print(f"       Freq. cent. : {d['freq_thz']:.4f} THz")
        print(f"       Margem real : {d['osnr'] - (d['mod_min'] + margin):+.4f} dB")
        if d["estagio"] == 2:
            print(f"    ── Disrupções aceitas: {d['disruption_count']} svc(s)  "
                  f"| Déficit total: {d['total_deficit_db']:.4f} dB")
    else:
        print(f"    RESULTADO: ❌ BLOQUEAR (sem candidato viável mesmo com fallback)")

    return chosen_action, resultado


def main():
    steps  = 10
    load   = 250.0
    margin = 1.0
    seed   = 10

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

    aceito_limpo    = 0
    aceito_fallback = 0
    bloqueado       = 0

    for step_idx in range(steps):
        action, resultado = analyze_step_relaxed(env, step_idx, margin)
        _, _, terminated, truncated, info = env.step(action)
        if resultado == "aceito_limpo":
            aceito_limpo += 1
        elif resultado == "aceito_fallback":
            aceito_fallback += 1
        else:
            bloqueado += 1
        if terminated or truncated:
            break

    # ─── RESUMO FINAL ──────────────────────────────────────────────────────
    hdr("RESUMO FINAL DA SIMULAÇÃO — FFQoTA_OTIMIZADA", level=1)
    total_aceito = aceito_limpo + aceito_fallback
    print(f"  Passos executados               : {steps}")
    print(f"  ✅ Aceitas (Estágio 1 — Limpo)  : {aceito_limpo}")
    print(f"  ⚠️  Aceitas (Estágio 2 — Fallback): {aceito_fallback}")
    print(f"  ❌ Bloqueadas                   : {bloqueado}")
    print(f"  Total aceitas                   : {total_aceito}")
    print(f"  Taxa de bloqueio FFQoTA_Otimizada: {bloqueado/steps*100:.1f}%")
    print(f"  Taxa de bloqueio FFQoT_Aware     : 40.0%  (referência)")
    melhora = 40.0 - (bloqueado / steps * 100)
    if melhora > 0:
        print(f"  Melhora vs Original             : -{melhora:.1f} pp ✅")
    else:
        print(f"  Diferença vs Original           : {melhora:+.1f} pp")


if __name__ == "__main__":
    main()
