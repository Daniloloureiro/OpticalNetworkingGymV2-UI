"""
debug_ase_nli.py
================
Debugging completo dos cálculos de ASE e NLI da QoT Engine.

Estratégia:
  1. Reimplementa as fórmulas de ASE e NLI em Python puro, com comentários
     referenciando cada constante e cada passo da fórmula.
  2. Compara resultado a resultado com a engine do simulador.
  3. Exibe todas as variáveis intermediárias por span, por enlace e ao total.
  4. Verifica consistência da fórmula OSNR = 1 / (ASE_inv + NLI_inv).

Fórmulas utilizadas (modelo GN - Gaussian Noise):
  - ASE por span: P_ASE = B_ref * h * f_c * (exp(2*alpha*L) - 1) * NF
  - NLI por span: P_NLI = eta * L_eff * sum_phi
    onde eta = (P/B)^3 * (8/(27*pi*beta2)) * gamma^2 * B
  - OSNR = P_launch / (P_ASE + P_NLI)  [razão de potências, linear]
  - OSNR_dB = 10*log10(OSNR)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from optical_networking_gym_v2 import make_env
from optical_networking_gym_v2.heuristics.runtime_heuristics import (
    build_runtime_heuristic_context,
)
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils

# ─── Constantes físicas (idênticas ao qot_kernel.py) ──────────────────────────
_ABS_BETA_2  = abs(-21.3e-27)          # |β₂|  [s²/m] — dispersão cromática
_GAMMA       = 1.3e-3                  # γ  [1/(W·m)] — coeficiente não-linear
_H_PLANCK    = 6.626e-34               # h  [J·s]     — constante de Planck
_PI_SQ       = math.pi * math.pi
_NLI_PREFAC_BASE = 8.0 / (27.0 * math.pi * _ABS_BETA_2)

SEP  = "=" * 80
SEP2 = "-" * 76


def hdr(title: str, level: int = 1) -> None:
    if level == 1:
        print(f"\n{SEP}\n  {title}\n{SEP}")
    else:
        print(f"\n  {SEP2}\n    {title}\n  {SEP2}")


def linear_to_db(val: float) -> float:
    """Converte razão linear → dB."""
    if val <= 0:
        return float("-inf")
    return 10.0 * math.log10(val)


def db_to_linear(val_db: float) -> float:
    return 10.0 ** (val_db / 10.0)


def compute_ase_span(
    span_length_km: float,
    attenuation_norm: float,      # α [Np/m] normalizado (já em Np/m)
    noise_figure_norm: float,     # NF linear (não em dB)
    center_frequency_hz: float,   # f_c [Hz]
    bandwidth_hz: float,          # B_ref [Hz]
) -> dict:
    """
    Calcula a potência de ruído ASE de um único span.

    Fórmula:
        G_span = exp(2 * α * L)                  [ganho do EDFA = inverso da atenuação]
        P_ASE  = B_ref * h * f_c * (G - 1) * NF  [potência de ruído ASE]

    Onde:
        α   = coeficiente de atenuação [Np/m]
        L   = comprimento do span [m]
        NF  = figura de ruído linear do amplificador
        h   = constante de Planck
        f_c = frequência central do canal [Hz]
        B_ref = largura de banda de referência [Hz]
    """
    L_m = span_length_km * 1e3                         # comprimento em metros
    alpha = attenuation_norm                           # α [Np/m]
    exponent = 2.0 * alpha * L_m                      # 2αL
    G_minus_1 = math.exp(exponent) - 1.0              # exp(2αL) - 1 = G_span - 1
    G_span_dB = 10.0 * math.log10(math.exp(exponent)) # ganho em dB (≈ atenuação do span)

    P_ASE = bandwidth_hz * _H_PLANCK * center_frequency_hz * G_minus_1 * noise_figure_norm

    return {
        "L_km": span_length_km,
        "L_m": L_m,
        "alpha_Np_m": alpha,
        "alpha_dB_km": alpha * 1e3 / (10 / math.log(10)),  # α em dB/km (aprox.)
        "2*alpha*L": exponent,
        "G_span_minus1": G_minus_1,
        "G_span_dB": G_span_dB,
        "NF_linear": noise_figure_norm,
        "h_Planck": _H_PLANCK,
        "f_c_THz": center_frequency_hz / 1e12,
        "B_ref_GHz": bandwidth_hz / 1e9,
        "P_ASE_W": P_ASE,
    }


def compute_nli_span(
    span_length_km: float,
    attenuation_norm: float,
    center_frequency_hz: float,
    bandwidth_hz: float,
    launch_power_w: float,
    running_services: list[dict],   # cada dict: {fc_hz, bw_hz, phi_mod, svc_id}
    current_service_id: int,
) -> dict:
    """
    Calcula a potência de ruído NLI de um único span (modelo GN).

    Fórmulas:
        L_eff_a = 1 / (2α)
        L_eff   = (1 - exp(-2αL)) / (2α)
        η       = (P/B)³ · (8/(27π·|β₂|)) · γ² · B      [pré-fator NLI]
        sum_phi = φ_self + Σ φ_xci                        [acumulação de fase]

        φ_self = asinh(π² |β₂| B² / (4α))

        φ_xci  = asinh(π²|β₂| L_eff_a B_j (Δf + B_j/2))
                 - asinh(π²|β₂| L_eff_a B_j (Δf - B_j/2))
                 - φ_mod_j · (B_j/|Δf|) · (5/3) · (L_eff/L)

        P_NLI  = η · L_eff · sum_phi
    """
    L_m     = span_length_km * 1e3
    alpha   = attenuation_norm
    B       = bandwidth_hz
    P       = launch_power_w

    l_eff_a = 1.0 / (2.0 * alpha)
    l_eff   = (1.0 - math.exp(-2.0 * alpha * L_m)) / (2.0 * alpha)

    # Pré-fator NLI η·B
    nli_prefactor = ((P / B) ** 3) * _NLI_PREFAC_BASE * (_GAMMA ** 2) * B

    # Termo de auto-interferência (SPM)
    phi_self = math.asinh(_PI_SQ * _ABS_BETA_2 * (B ** 2) / (4.0 * alpha))
    sum_phi  = phi_self

    xci_details = []
    for svc in running_services:
        if svc["svc_id"] == current_service_id:
            continue
        delta_f = svc["fc_hz"] - center_frequency_hz
        if delta_f == 0.0:
            continue
        B_j     = svc["bw_hz"]
        phi_mod = svc["phi_mod"]

        phi_xci = (
            math.asinh(_PI_SQ * _ABS_BETA_2 * l_eff_a * B_j * (delta_f + B_j / 2.0))
            - math.asinh(_PI_SQ * _ABS_BETA_2 * l_eff_a * B_j * (delta_f - B_j / 2.0))
        ) - (phi_mod * (B_j / abs(delta_f)) * (5.0 / 3.0) * (l_eff / L_m))

        sum_phi += phi_xci
        xci_details.append({
            "svc_id": svc["svc_id"],
            "delta_f_GHz": delta_f / 1e9,
            "B_j_GHz": B_j / 1e9,
            "phi_mod": phi_mod,
            "phi_xci": phi_xci,
        })

    P_NLI = nli_prefactor * l_eff * sum_phi

    return {
        "L_km": span_length_km,
        "alpha_Np_m": alpha,
        "l_eff_a_m": l_eff_a,
        "l_eff_m": l_eff,
        "nli_prefactor": nli_prefactor,
        "phi_self": phi_self,
        "sum_phi": sum_phi,
        "P_NLI_W": P_NLI,
        "n_interferers": len(xci_details),
        "xci_details": xci_details,
    }


def debug_one_candidate(env, label: str = "") -> None:
    """
    Pega a requisição atual do ambiente, constrói o candidato First-Fit
    e faz o debugging completo de ASE e NLI span a span.
    """
    context    = build_runtime_heuristic_context(env)
    cfg        = context.config
    req        = context.request
    state      = context.state
    analysis   = context.analysis
    topology   = context.topology

    # Pega o primeiro caminho e a primeira modulação viável
    paths      = analysis.paths
    mod_indices = analysis.modulation_indices

    hdr(f"{'DEBUG ASE/NLI — ' + label if label else 'DEBUG ASE/NLI'}", level=1)

    # ─── Informações da Requisição ─────────────────────────────────────────
    hdr("REQISIÇÃO & CONFIGURAÇÃO", level=2)
    print(f"    Origem    : {topology.node_names[req.source_id]} (ID={req.source_id})")
    print(f"    Destino   : {topology.node_names[req.destination_id]} (ID={req.destination_id})")
    print(f"    Bit Rate  : {req.bit_rate} Gbps")
    print(f"    Svc ID    : #{req.service_id}")
    print()
    print(f"    Potência de lançamento  : {cfg.launch_power_dbm:.2f} dBm "
          f"= {10**(cfg.launch_power_dbm/10)*1e-3:.6f} W "
          f"= {10**(cfg.launch_power_dbm/10)*1e-3*1e3:.4f} mW")
    print(f"    Freq. inicial do grid   : {cfg.frequency_start / 1e12:.4f} THz")
    print(f"    Largura por slot        : {cfg.frequency_slot_bandwidth / 1e9:.2f} GHz")
    print(f"    Número de slots totais  : {cfg.num_spectrum_resources}")
    print(f"    Modo QoT                : {cfg.qot_constraint}")
    print(f"    Margem                  : {cfg.margin:.2f} dB")
    print(f"    Inclui NLI?             : {context.simulator.qot_engine._include_nli}")
    launch_power_w = 10 ** ((cfg.launch_power_dbm - 30.0) / 10.0)

    # ─── Constantes Físicas ────────────────────────────────────────────────
    hdr("CONSTANTES FÍSICAS DO MODELO GN", level=2)
    print(f"    |β₂|   = {_ABS_BETA_2:.3e} s²/m   (dispersão cromática)")
    print(f"    γ      = {_GAMMA:.3e} 1/(W·m) (coef. não-linear)")
    print(f"    h      = {_H_PLANCK:.3e} J·s    (constante de Planck)")
    print(f"    π²     = {_PI_SQ:.6f}")
    print(f"    base NLI = 8/(27π·|β₂|) = {_NLI_PREFAC_BASE:.6e}")

    # ─── Encontra primeiro candidato viável ────────────────────────────────
    chosen_path  = None
    chosen_mod   = None
    chosen_slot  = None
    chosen_slots = 0

    for path_index, path in enumerate(paths):
        for mod_offset, mod_idx in enumerate(mod_indices):
            mod = cfg.modulations[mod_idx]
            req_slots = int(analysis.required_slots_by_path_mod[path_index, mod_offset])
            if req_slots <= 0:
                continue
            mask  = analysis.qot_valid_starts[path_index, mod_offset, :]
            cands = np.flatnonzero(mask).tolist()
            if not cands:
                continue
            chosen_path  = path
            chosen_mod   = mod
            chosen_slot  = cands[0]
            chosen_slots = req_slots
            path_index_used = path_index
            break
        if chosen_path is not None:
            break

    if chosen_path is None:
        print("  ⚠️ Sem candidato viável para depurar neste passo. Pulando.")
        return

    # ─── Candidato selecionado ─────────────────────────────────────────────
    hdr("CANDIDATO SELECIONADO (First-Fit)", level=2)
    nodes_str = " -> ".join(str(n) for n in chosen_path.node_names)
    bandwidth_hz = cfg.frequency_slot_bandwidth * chosen_slots
    center_freq_hz = (
        cfg.frequency_start
        + cfg.frequency_slot_bandwidth * chosen_slot
        + cfg.frequency_slot_bandwidth * (chosen_slots / 2.0)
    )
    print(f"    Caminho       : {nodes_str}")
    print(f"    Dist. total   : {chosen_path.length_km:.1f} km")
    print(f"    Links         : {list(chosen_path.link_ids)}")
    print(f"    Modulação     : {chosen_mod.name}")
    print(f"      OSNR_min    : {chosen_mod.minimum_osnr:.2f} dB")
    print(f"      SE          : {chosen_mod.spectral_efficiency} bit/s/Hz")
    print(f"    Slot inicial  : {chosen_slot}")
    print(f"    Slots usados  : {chosen_slots}")
    print(f"    Slots range   : [{chosen_slot}, {chosen_slot + chosen_slots - 1}]")
    print(f"    Freq. central : {center_freq_hz / 1e12:.6f} THz")
    print(f"    Largura banda : {bandwidth_hz / 1e9:.2f} GHz")
    print(f"    Pot. lançada  : {launch_power_w:.6e} W  ({cfg.launch_power_dbm:.2f} dBm)")

    # ─── Serviços Ativos nos Enlaces ────────────────────────────────────────
    hdr("SERVIÇOS ATIVOS NOS ENLACES DO CAMINHO (Interferentes)", level=2)
    for link_id in chosen_path.link_ids:
        active_ids = state.link_active_service_ids[link_id]
        link = context.topology.links[link_id]
        print(f"    Enlace {link_id} ({link.source_name} → {link.target_name}, "
              f"{len(link.spans)} spans):")
        if not active_ids:
            print(f"      (nenhum serviço ativo neste enlace)")
        for sid in active_ids:
            svc = state.active_services_by_id[sid]
            print(f"      Svc #{sid}: fc={svc.center_frequency/1e12:.4f} THz  "
                  f"bw={svc.bandwidth/1e9:.2f} GHz  "
                  f"Mod={svc.modulation.name if svc.modulation else '?'}  "
                  f"phi_mod={_PHI_MODULATION_BY_SE_PY.get(svc.modulation.spectral_efficiency, '?') if svc.modulation else '?'}")

    # ─── Cálculo Próprio (Python Puro) ─────────────────────────────────────
    hdr("CÁLCULO PRÓPRIO SPAN A SPAN (Python Puro — fórmulas GN)", level=2)
    print(f"    pré-fator NLI η·B = ((P/B)³ · (8/(27π|β₂|)) · γ² · B)")
    nli_prefactor = ((launch_power_w / bandwidth_hz) ** 3) * _NLI_PREFAC_BASE * (_GAMMA ** 2) * bandwidth_hz
    print(f"      (P/B)  = {launch_power_w/bandwidth_hz:.6e} W/Hz")
    print(f"      (P/B)³ = {(launch_power_w/bandwidth_hz)**3:.6e}")
    print(f"      η·B    = {nli_prefactor:.6e} W/Hz")
    print()

    total_acc_ase = 0.0
    total_acc_nli = 0.0
    total_acc_gsnr = 0.0
    span_global_idx = 0

    for link_id in chosen_path.link_ids:
        link = context.topology.links[link_id]
        link_spans = link.spans

        # Monta lista de interferentes deste enlace
        running_svcs = []
        for sid in state.link_active_service_ids[link_id]:
            svc = state.active_services_by_id[sid]
            if svc.modulation is None:
                continue
            se = svc.modulation.spectral_efficiency
            running_svcs.append({
                "svc_id": sid,
                "fc_hz": svc.center_frequency,
                "bw_hz": svc.bandwidth,
                "phi_mod": _PHI_MODULATION_BY_SE_PY.get(se, 1.0),
            })

        print(f"  ┌── Enlace {link_id}: {link.source_name} → {link.target_name} "
              f"({len(link_spans)} spans, {len(running_svcs)} interferentes)")

        link_ase = 0.0
        link_nli = 0.0
        link_gsnr = 0.0

        for span_idx, span in enumerate(link_spans):
            ase_r = compute_ase_span(
                span_length_km=span.length_km,
                attenuation_norm=span.attenuation_normalized,
                noise_figure_norm=span.noise_figure_normalized,
                center_frequency_hz=center_freq_hz,
                bandwidth_hz=bandwidth_hz,
            )
            nli_r = compute_nli_span(
                span_length_km=span.length_km,
                attenuation_norm=span.attenuation_normalized,
                center_frequency_hz=center_freq_hz,
                bandwidth_hz=bandwidth_hz,
                launch_power_w=launch_power_w,
                running_services=running_svcs,
                current_service_id=req.service_id,
            )

            P_ASE = ase_r["P_ASE_W"]
            P_NLI = nli_r["P_NLI_W"]
            ratio_ase  = P_ASE / launch_power_w  # ASE normalizada
            ratio_nli  = P_NLI / launch_power_w  # NLI normalizada

            link_ase  += ratio_ase
            link_nli  += ratio_nli
            link_gsnr += ratio_ase + ratio_nli

            print(f"  │  Span {span_global_idx} (Enlace {link_id}, span {span_idx}):")
            print(f"  │    Comprimento          : {span.length_km:.2f} km  ({ase_r['L_m']:.0f} m)")
            print(f"  │    Atenuação α          : {span.attenuation_normalized:.6e} Np/m")
            print(f"  │    Figura de ruído NF   : {span.noise_figure_normalized:.6e} linear  "
                  f"({linear_to_db(span.noise_figure_normalized):.2f} dB)")
            print(f"  │    2·α·L                : {ase_r['2*alpha*L']:.4f}")
            print(f"  │    exp(2αL)-1           : {ase_r['G_span_minus1']:.4f}  "
                  f"(ganho span = {ase_r['G_span_dB']:.2f} dB)")
            print(f"  │    P_ASE (span)         : {P_ASE:.6e} W")
            print(f"  │    P_ASE/P_launch       : {ratio_ase:.6e}  "
                  f"→ ASE span = {linear_to_db(1/ratio_ase):.4f} dB")
            if context.simulator.qot_engine._include_nli:
                print(f"  │    L_eff_a              : {nli_r['l_eff_a_m']:.2f} m")
                print(f"  │    L_eff                : {nli_r['l_eff_m']:.2f} m  "
                      f"(L_eff/L = {nli_r['l_eff_m']/ase_r['L_m']:.4f})")
                print(f"  │    φ_self (SPM)         : {nli_r['phi_self']:.6e}")
                print(f"  │    Interferentes (XCI)  : {nli_r['n_interferers']}")
                for xci in nli_r["xci_details"]:
                    print(f"  │      Svc #{xci['svc_id']:3}: Δf={xci['delta_f_GHz']:+.2f} GHz  "
                          f"B_j={xci['B_j_GHz']:.2f} GHz  "
                          f"φ_mod={xci['phi_mod']:.4f}  "
                          f"φ_xci={xci['phi_xci']:.6e}")
                print(f"  │    Σφ (self + XCI)      : {nli_r['sum_phi']:.6e}")
                print(f"  │    P_NLI (span)         : {P_NLI:.6e} W")
                print(f"  │    P_NLI/P_launch       : {ratio_nli:.6e}  "
                      f"→ NLI span = {linear_to_db(1/ratio_nli) if ratio_nli > 0 else 'inf':.4f} dB")
            print(f"  │")
            span_global_idx += 1

        link_ase_db  = linear_to_db(1.0 / link_ase) if link_ase > 0 else float("inf")
        link_nli_db  = linear_to_db(1.0 / link_nli) if link_nli > 0 else float("inf")
        link_gsnr_db = linear_to_db(1.0 / link_gsnr) if link_gsnr > 0 else float("inf")
        print(f"  └── Enlace {link_id} TOTAL:  "
              f"ASE={link_ase_db:.4f} dB  "
              f"NLI={link_nli_db:.4f} dB  "
              f"GSNR_parcial={link_gsnr_db:.4f} dB")

        total_acc_ase  += link_ase
        total_acc_nli  += link_nli
        total_acc_gsnr += link_gsnr

    # ─── Resultado Próprio ─────────────────────────────────────────────────
    hdr("RESULTADO CALCULADO MANUALMENTE", level=2)
    osnr_manual = linear_to_db(1.0 / total_acc_gsnr)
    ase_manual  = linear_to_db(1.0 / total_acc_ase)
    nli_manual  = linear_to_db(1.0 / total_acc_nli) if total_acc_nli > 0 else float("inf")

    print(f"    acc_GSNR (linear, ΣP/P_launch): {total_acc_gsnr:.8e}")
    print(f"    acc_ASE  (linear, ΣP/P_launch): {total_acc_ase:.8e}")
    print(f"    acc_NLI  (linear, ΣP/P_launch): {total_acc_nli:.8e}")
    print()
    print(f"    OSNR manual = 10·log10(1/acc_GSNR) = {osnr_manual:.6f} dB")
    print(f"    ASE  manual = 10·log10(1/acc_ASE)  = {ase_manual:.6f} dB")
    print(f"    NLI  manual = 10·log10(1/acc_NLI)  = {nli_manual:.6f} dB")

    # ─── Resultado da Engine ────────────────────────────────────────────────
    hdr("RESULTADO DA ENGINE DO SIMULADOR", level=2)
    engine = context.simulator.qot_engine
    cand = engine.build_candidate(
        request=req,
        path=chosen_path,
        modulation=chosen_mod,
        service_slot_start=chosen_slot,
        service_num_slots=chosen_slots,
    )
    result = engine.evaluate_candidate(state, cand)
    print(f"    OSNR engine  = {result.osnr:.6f} dB")
    print(f"    ASE  engine  = {result.ase:.6f} dB")
    print(f"    NLI  engine  = {result.nli:.6f} dB")
    print(f"    meets_threshold = {result.meets_threshold}")

    # ─── Comparação ────────────────────────────────────────────────────────
    hdr("COMPARAÇÃO: MANUAL vs ENGINE", level=2)
    delta_osnr = abs(osnr_manual - result.osnr)
    delta_ase  = abs(ase_manual  - result.ase)
    delta_nli  = abs(nli_manual  - result.nli) if math.isfinite(nli_manual) else float("inf")

    print(f"    {'Métrica':<12} {'Manual':>14} {'Engine':>14} {'|Δ|':>12} {'Status':>10}")
    print(f"    {'-'*12} {'-'*14} {'-'*14} {'-'*12} {'-'*10}")
    for metric, m_val, e_val, delta in [
        ("OSNR (dB)", osnr_manual, result.osnr, delta_osnr),
        ("ASE  (dB)", ase_manual,  result.ase,  delta_ase),
        ("NLI  (dB)", nli_manual,  result.nli,  delta_nli),
    ]:
        ok = "✅ OK" if delta < 0.001 else ("⚠️ DIFER." if delta < 0.1 else "❌ ERRO")
        print(f"    {metric:<12} {m_val:>14.6f} {e_val:>14.6f} {delta:>12.6f} {ok:>10}")

    # ─── Verificação da Fórmula OSNR ───────────────────────────────────────
    hdr("VERIFICAÇÃO: OSNR = -10·log10(ASE_lin + NLI_lin)", level=2)
    ase_lin = 10 ** (-ase_manual / 10.0)
    nli_lin = 10 ** (-nli_manual / 10.0) if math.isfinite(nli_manual) else 0.0
    osnr_recalc = -10.0 * math.log10(ase_lin + nli_lin)
    print(f"    ASE_linear  = 10^(-ASE_dB/10) = {ase_lin:.8e}")
    print(f"    NLI_linear  = 10^(-NLI_dB/10) = {nli_lin:.8e}")
    print(f"    ASE+NLI     = {ase_lin + nli_lin:.8e}")
    print(f"    OSNR = -10·log10(ASE+NLI) = {osnr_recalc:.6f} dB")
    print(f"    OSNR manual calculada     = {osnr_manual:.6f} dB")
    print(f"    Diferença                 = {abs(osnr_recalc - osnr_manual):.2e} dB  "
          f"{'✅ consistente' if abs(osnr_recalc - osnr_manual) < 0.001 else '❌ INCONSISTÊNCIA'}")


# φ(SE) — idêntico ao qot_kernel.py
_PHI_MODULATION_BY_SE_PY = {
    1: 1.0,
    2: 1.0,
    3: 2.0 / 3.0,
    4: 17.0 / 25.0,
    5: 69.0 / 100.0,
    6: 13.0 / 21.0,
}


def main():
    steps  = 3     # Analisa os 3 primeiros passos (rede progressivamente ocupada)
    margin = 1.0
    seed   = 10
    load   = 250.0

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

    from optical_networking_gym_v2.heuristics.runtime_heuristics import (
        select_ff_qot_aware_action,
    )

    for step_idx in range(steps):
        label = f"Passo {step_idx + 1}"
        debug_one_candidate(env, label=label)
        action = select_ff_qot_aware_action(env)
        env.step(action)
        print()


if __name__ == "__main__":
    main()
