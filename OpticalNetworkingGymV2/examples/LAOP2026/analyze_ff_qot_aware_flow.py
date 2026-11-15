"""
analyze_ff_qot_aware_flow.py
============================
Analisa o fluxo de execução da heurística FFQoT_Aware passo a passo,
mostrando todos os cálculos intermediários:
  - Construção da análise da requisição
  - Construção de candidatos (frequência, potência, slots)
  - Cálculo de QoT: ASE, NLI, OSNR
  - Verificação de disrupção em vizinhos
  - Decisão final
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


def analyze_step(env, step_idx: int, margin: float) -> tuple[int, bool]:
    """
    Executa e exibe o fluxo completo de um único passo da heurística FFQoT_Aware.
    Retorna (action, found_candidate).
    """
    context = build_runtime_heuristic_context(env)
    use_resource_only = context.config.mask_mode is MaskMode.RESOURCE_ONLY
    cfg = context.config

    # ─── CABEÇALHO DO PASSO ────────────────────────────────────────────────
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
        print(f"    Svc #{svc_id:<3}  Mod={mod_name:<6}  "
              f"Slots={fmt_slots(svc.service_slot_start, svc.service_slot_end_exclusive):<18}  "
              f"OSNR={svc.osnr:.3f} dB  "
              f"Limiar={threshold:.3f} dB  "
              f"Margem={margin_db:+.3f} dB  "
              f"ASE={svc.ase:.3f} dB  "
              f"NLI={svc.nli:.3f} dB")

    # ─── BLOCO 3: CANDIDATOS DISPONÍVEIS (ANÁLISE) ────────────────────────
    hdr("BLOCO 3: ANÁLISE DE CANDIDATOS (Caminhos × Modulações × Slots)", level=2)
    analysis = context.analysis
    paths = analysis.paths
    mod_indices = analysis.modulation_indices

    print(f"    K-caminhos disponíveis  : {len(paths)}")
    print(f"    Modulações consideradas : {len(mod_indices)}")
    print(f"    Espectro total          : {cfg.num_spectrum_resources} slots")
    print(f"    Margem de guarda        : {margin:.2f} dB")
    print(f"    Modo de máscara         : {'RESOURCE_ONLY' if use_resource_only else 'QoT_VALID'}")
    print()

    for path_index, path in enumerate(paths):
        nodes_str = " -> ".join(str(n) for n in path.node_names)
        print(f"    Caminho K={path_index}: {nodes_str}")
        print(f"             Comprimento={path.length_km:.1f} km  |  "
              f"Hops={path.hops}  |  Links={list(path.link_ids)}")

        for mod_offset, mod_idx in enumerate(mod_indices):
            mod = cfg.modulations[mod_idx]
            req_slots = int(analysis.required_slots_by_path_mod[path_index, mod_offset])

            # máscara por recurso
            res_mask   = analysis.resource_valid_starts[path_index, mod_offset, :]
            qot_mask   = analysis.qot_valid_starts[path_index, mod_offset, :]
            res_count  = int(res_mask.sum())
            qot_count  = int(qot_mask.sum())

            print(f"      - {mod.name:<6}  "
                  f"(OSNR_min={mod.minimum_osnr:.2f} dB, "
                  f"Limiar={mod.minimum_osnr + margin:.2f} dB, "
                  f"Slots_req={req_slots})  "
                  f"→ slots c/ recurso livre={res_count:>4}  "
                  f"slots válidos QoT={qot_count:>4}")

    # ─── BLOCO 4: BUSCA FFQoT_Aware (FIRST-FIT + DISRUPÇÃO) ───────────────
    hdr("BLOCO 4: BUSCA FFQoT_Aware — Avaliação Física Candidato a Candidato", level=2)

    chosen_action  = context.reject_action
    found          = False
    tot_tested     = 0
    tot_disrupt    = 0
    tot_qot_fail   = 0
    chosen_data: dict = {}

    # Limita o número de slots impressos por (caminho+mod) para não poluir saída
    MAX_SLOTS_PRINT = 8

    for path_index, path in enumerate(paths):
        if found:
            break

        nodes_str = " -> ".join(str(n) for n in path.node_names)
        print(f"\n    [Caminho K={path_index}] {nodes_str} ({path.length_km:.1f} km)")

        for mod_offset, mod_idx in enumerate(mod_indices):
            if found:
                break

            mod       = cfg.modulations[mod_idx]
            req_slots = int(analysis.required_slots_by_path_mod[path_index, mod_offset])

            if req_slots <= 0:
                print(f"      * {mod.name:<6}: Inviável para esta distância (req_slots=0). PULANDO.")
                continue

            mask = (analysis.resource_valid_starts if use_resource_only
                    else analysis.qot_valid_starts)[path_index, mod_offset, :]
            cands = np.flatnonzero(mask).tolist()

            if not cands:
                print(f"      * {mod.name:<6} ({req_slots} slots): "
                      f"Sem candidatos na máscara. PULANDO.")
                continue

            print(f"      * {mod.name:<6} (req={req_slots} slots, "
                  f"limiar={mod.minimum_osnr + margin:.2f} dB) "
                  f"→ {len(cands)} candidatos de slot")

            # Imprime apenas os primeiros MAX_SLOTS_PRINT slots
            shown = cands[:MAX_SLOTS_PRINT]
            remaining = len(cands) - len(shown)

            for slot in shown:
                if found:
                    break

                tot_tested += 1

                # Construção do candidato
                cand = context.simulator.qot_engine.build_candidate(
                    request=req,
                    path=path,
                    modulation=mod,
                    service_slot_start=slot,
                    service_num_slots=req_slots,
                )

                # Avaliação do próprio QoT do candidato
                qot = context.simulator.qot_engine.evaluate_candidate(context.state, cand)

                print(f"\n        ┌─ Slot {slot:>4}:")
                print(f"        │   Freq. central    = {cand.center_frequency / 1e12:.4f} THz")
                print(f"        │   Largura de banda = {cand.bandwidth / 1e9:.2f} GHz")
                print(f"        │   Potência lançada = {cand.launch_power:.4f} W  "
                      f"({10 * np.log10(cand.launch_power * 1e3):.2f} dBm)")
                print(f"        │   OSNR estimada    = {qot.osnr:.4f} dB  "
                      f"(ASE={qot.ase:.4f} dB, NLI={qot.nli:.4f} dB)")
                print(f"        │   OSNR necessária  = {mod.minimum_osnr + margin:.4f} dB  "
                      f"(min={mod.minimum_osnr:.4f} dB + margin={margin:.4f} dB)")
                print(f"        │   QoT OK?          = {qot.meets_threshold}")

                if not qot.meets_threshold:
                    print(f"        └─ ❌ FALHOU: OSNR insuficiente para o próprio serviço. Próximo slot.")
                    tot_qot_fail += 1
                    continue

                # Provisionamento temporário para verificar impacto nos vizinhos
                occ_start = slot
                occ_end   = slot + req_slots
                if occ_end < cfg.num_spectrum_resources:
                    occ_end += 1

                context.state.apply_provision(
                    request=req,
                    path=path,
                    service_slot_start=slot,
                    service_num_slots=req_slots,
                    occupied_slot_start=occ_start,
                    occupied_slot_end_exclusive=occ_end,
                    modulation=mod,
                    center_frequency=cand.center_frequency,
                    bandwidth=cand.bandwidth,
                    launch_power=cand.launch_power,
                )

                causes_disruption = False
                disrupted_svcs: list[tuple] = []

                try:
                    context.state.apply_qot_updates({
                        req.service_id: {
                            "osnr": qot.osnr,
                            "ase":  qot.ase,
                            "nli":  qot.nli,
                        }
                    })

                    impacted = context.simulator.qot_engine.impacted_service_ids(
                        context.state, path,
                        exclude_service_id=req.service_id,
                    )

                    if not impacted:
                        print(f"        │   Vizinhos impactados = NENHUM (caminhos não se cruzam)")
                    else:
                        print(f"        │   Vizinhos impactados = {list(impacted)}")
                        for upd in context.simulator.qot_engine.refresh_services(
                                context.state, impacted):
                            if upd.service_id not in context.state.active_services_by_id:
                                continue
                            svc      = context.state.active_services_by_id[upd.service_id]
                            if svc.modulation is None:
                                continue
                            thr      = svc.modulation.minimum_osnr + margin
                            new_osnr = float(upd.osnr)
                            old_osnr = float(svc.osnr)
                            delta    = new_osnr - old_osnr
                            violacao = thr - new_osnr
                            ok       = new_osnr >= thr

                            print(f"        │     Svc #{upd.service_id}  "
                                  f"Mod={svc.modulation.name}  "
                                  f"OSNR: {old_osnr:.4f} → {new_osnr:.4f} dB  "
                                  f"(Δ={delta:+.4f} dB)  "
                                  f"Limiar={thr:.4f} dB  "
                                  f"Violação={violacao:+.4f} dB  "
                                  f"{'✅ OK' if ok else '❌ DISRUPÇÃO'}")

                            if not ok:
                                causes_disruption = True
                                disrupted_svcs.append((upd.service_id,
                                                        old_osnr, new_osnr,
                                                        thr, delta, violacao))
                finally:
                    context.state.apply_release(req.service_id)

                if causes_disruption:
                    print(f"        └─ ❌ DISRUPÇÃO: Afeta {len(disrupted_svcs)} vizinho(s). Próximo slot.")
                    tot_disrupt += 1
                else:
                    print(f"        └─ ✅ APROVADO: Candidato limpo! FFQoT_Aware escolhe este slot.")
                    chosen_action = encode_action(
                        cfg,
                        path_index=path_index,
                        modulation_offset=mod_offset,
                        initial_slot=slot,
                    )
                    chosen_data = {
                        "path_k":    path_index,
                        "path_str":  nodes_str,
                        "path_km":   path.length_km,
                        "mod":       mod.name,
                        "mod_min":   mod.minimum_osnr,
                        "slot":      slot,
                        "req_slots": req_slots,
                        "osnr":      qot.osnr,
                        "ase":       qot.ase,
                        "nli":       qot.nli,
                        "freq_thz":  cand.center_frequency / 1e12,
                        "bw_ghz":    cand.bandwidth / 1e9,
                        "pwr_dbm":   10 * np.log10(cand.launch_power * 1e3),
                    }
                    found = True
                    break

            if not found and remaining > 0:
                print(f"      ... (mais {remaining} slots testados foram descartados)")

    # ─── BLOCO 5: DECISÃO FINAL DA FFQoT_Aware ──────────────────────────────
    hdr("BLOCO 5: DECISÃO FINAL DA FFQoT_Aware", level=2)
    print(f"    Total de candidatos avaliados     : {tot_tested}")
    print(f"    Reprovados por QoT própria        : {tot_qot_fail}")
    print(f"    Reprovados por disrupção vizinhos : {tot_disrupt}")

    if found:
        d = chosen_data
        print(f"    RESULTADO: ✅ ACEITAR REQUISIÇÃO")
        print(f"    ── Caminho   : K={d['path_k']} → {d['path_str']}")
        print(f"    ── Distância : {d['path_km']:.1f} km")
        print(f"    ── Modulação : {d['mod']} (OSNR_min={d['mod_min']:.2f} dB)")
        print(f"    ── Slot inicial  : {d['slot']}")
        print(f"    ── Slots usados  : [{d['slot']}, {d['slot']+d['req_slots']-1}] ({d['req_slots']} slots)")
        print(f"    ── Freq. central : {d['freq_thz']:.4f} THz")
        print(f"    ── Largura de B. : {d['bw_ghz']:.2f} GHz")
        print(f"    ── Potência Tx   : {d['pwr_dbm']:.2f} dBm")
        print(f"    ── OSNR final    : {d['osnr']:.4f} dB")
        print(f"       ASE          : {d['ase']:.4f} dB")
        print(f"       NLI          : {d['nli']:.4f} dB")
        print(f"       Margem real  : {d['osnr'] - (d['mod_min'] + margin):+.4f} dB")
    else:
        if tot_tested == 0:
            motivo = "Sem slots livres contíguos (Fragmentação de espectro)"
        elif tot_disrupt == tot_tested:
            motivo = "Todos os slots causavam disrupção em serviços vizinhos"
        else:
            motivo = "QoT própria insuficiente em todos os candidatos"
        print(f"    RESULTADO: ❌ BLOQUEAR REQUISIÇÃO")
        print(f"    ── Motivo: {motivo}")

    return chosen_action, found


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

    accepted = 0
    blocked  = 0

    for step_idx in range(steps):
        action, found = analyze_step(env, step_idx, margin)
        _, _, terminated, truncated, info = env.step(action)
        if found:
            accepted += 1
        else:
            blocked += 1
        if terminated or truncated:
            break

    # ─── RESUMO FINAL ──────────────────────────────────────────────────────
    hdr("RESUMO FINAL DA SIMULAÇÃO", level=1)
    print(f"  Passos executados : {steps}")
    print(f"  Aceitas           : {accepted}")
    print(f"  Bloqueadas        : {blocked}")
    print(f"  Taxa de bloqueio  : {blocked/steps*100:.1f}%")


if __name__ == "__main__":
    main()
