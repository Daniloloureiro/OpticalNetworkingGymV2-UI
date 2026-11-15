"""
run_ff_qot_aware_osnr_stats.py
==============================
Simula o comportamento da heurística FFQoT_Aware
e analisa as estatísticas de OSNR (ASE vs NLI) obtidas durante a simulação.

Uso:
  python examples/LAOP2026/run_ff_qot_aware_osnr_stats.py [--load 250] [--margin 1.0] [--episode-length 300]
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

# Adiciona caminhos do projeto
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import numpy as np

from optical_networking_gym_v2 import make_env
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils
from optical_networking_gym_v2.utils import experiment_utils as sweep_utils

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODS_ORDERED = ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"]
MOD_COLORS   = ["#4393c3", "#92c5de", "#f4a582", "#d6604d", "#b2182b", "#67001f"]

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simulação com FFQoT_Aware e análise de OSNR")
    p.add_argument("--load",             type=float, default=250.0)
    p.add_argument("--margin",           type=float, default=1.0)
    p.add_argument("--seed",             type=int,   default=10)
    p.add_argument("--episode-length",   type=int,   default=300)
    p.add_argument("--k-paths",          type=int,   default=3)
    p.add_argument("--launch-power-dbm", type=float, default=0.0)
    p.add_argument("--drop-on-disruption", type=bool, default=True, 
                   help="Derrubar serviços que sofrem disrupção (padrão FFQoT_Aware)")
    return p

def main() -> None:
    args = build_parser().parse_args()

    scenario = scenario_utils.build_nobel_eu_graph_load_scenario(
        topology_id="nobel-eu",
        episode_length=args.episode_length,
        seed=args.seed,
        load=args.load,
        mean_holding_time=10800.0,
        num_spectrum_resources=320,
        k_paths=args.k_paths,
        launch_power_dbm=args.launch_power_dbm,
        modulations_to_consider=6,
        margin=args.margin,
        measure_disruptions=True,
        drop_on_disruption=args.drop_on_disruption,
    )
    env = make_env(config=scenario)
    _, info = env.reset(seed=args.seed)

    seen_ids: set[int] = set()
    records: list[dict] = []

    while True:
        # Usa a heurística FFQoT_Aware
        action = int(sweep_utils.select_ff_qot_aware_policy(env, {}))
        _, _, terminated, truncated, info = env.step(action)

        status = str(info.get("status", ""))
        if "accepted" in status:
            # Lê os atributos diretamente do estado do simulador para os serviços ativos
            active = env.simulator.state.active_services_by_id
            for svc_id, svc in active.items():
                if svc_id in seen_ids:
                    continue
                seen_ids.add(svc_id)
                osnr_real = float(svc.osnr)  # dB total (ASE + NLI)
                ase_db    = float(svc.ase)   # dB se só ASE existisse
                nli_db    = float(svc.nli)   # dB se só NLI existisse

                # Penalidade NLI = OSNR sem NLI − OSNR real
                penalty_nli = ase_db - osnr_real

                # Parcela NLI no ruído em escala linear
                inv_ase = 10 ** (-ase_db / 10.0)
                inv_nli = 10 ** (-nli_db / 10.0)
                nli_frac_pct = (inv_nli / (inv_ase + inv_nli) * 100) if (inv_ase + inv_nli) > 0 else 0.0

                mod_name = svc.modulation.name if svc.modulation else "?"
                n_hops   = len(svc.path.link_ids)

                records.append({
                    "mod":         mod_name,
                    "osnr_real":   osnr_real,
                    "ase_db":      ase_db,
                    "nli_db":      nli_db,
                    "penalty_nli": penalty_nli,
                    "nli_frac":    nli_frac_pct,
                    "n_hops":      n_hops,
                })

        if terminated or truncated:
            break

    # Estatísticas de snapshot final da rede
    snap = env.simulator.statistics.snapshot()
    
    if not records:
        print("Nenhum serviço aceito registrado na simulação.")
        return

    # ─── Estatísticas no terminal ────────────────────────────────
    osnrs   = [r["osnr_real"]   for r in records]
    ases    = [r["ase_db"]      for r in records]
    nlis    = [r["nli_db"]      for r in records]
    deltas  = [r["penalty_nli"] for r in records]
    fracs   = [r["nli_frac"]    for r in records]

    print(f"\n{'='*72}")
    print(f"  RESULTADOS DA SIMULAÇÃO: FFQoT_Aware")
    print(f"{'='*72}")
    print(f"  Configurações:")
    print(f"    Carga espectral  : {args.load} Erl")
    print(f"    Margem de guard. : {args.margin} dB")
    print(f"    Canal Tx Power   : {args.launch_power_dbm} dBm")
    print(f"    Passos simulação : {args.episode_length} requisições")
    print(f"    Drop on Disrupt. : {args.drop_on_disruption}")
    print(f"{'-'*72}")
    print(f"  Estatísticas da Rede:")
    print(f"    Total requisitado: {snap.episode_services_processed}")
    print(f"    Aceitos          : {snap.episode_services_accepted}")
    print(f"    Taxa de Bloqueio : {snap.episode_service_blocking_rate * 100:.2f}%")
    print(f"    Serviços Derrub. : {snap.episode_disrupted_services} (disrompidos)")
    print(f"{'-'*72}")
    print(f"  Métricas de OSNR (Média ± Desvio Padrão [Mín, Máx]):")
    print(f"    OSNR Total (dB)   : {np.mean(osnrs):5.2f} ± {np.std(osnrs):.2f} dB  [{np.min(osnrs):.2f}, {np.max(osnrs):.2f}]")
    print(f"    OSNR Apenas ASE   : {np.mean(ases):5.2f} ± {np.std(ases):.2f} dB  [{np.min(ases):.2f}, {np.max(ases):.2f}]")
    print(f"    OSNR Apenas NLI   : {np.mean(nlis):5.2f} ± {np.std(nlis):.2f} dB  [{np.min(nlis):.2f}, {np.max(nlis):.2f}]")
    print(f"    Penalidade NLI    : {np.mean(deltas):5.2f} ± {np.std(deltas):.2f} dB  [{np.min(deltas):.2f}, {np.max(deltas):.2f}]")
    print(f"    Fração NLI (%)    : {np.mean(fracs):5.1f}% ± {np.std(fracs):.1f}%     [{np.min(fracs):.1f}%, {np.max(fracs):.1f}%]")
    print(f"{'-'*72}")

    # Distribuição por modulação
    by_mod: dict[str, list] = defaultdict(list)
    for r in records:
        by_mod[r["mod"]].append(r)

    print(f"  OSNR Detalhada por Formato de Modulação:")
    print(f"  {'Mod':<8} | {'Qtd':>5} | {'OSNR Real':^11} | {'ASE Only':^11} | {'Pen. NLI':^10} | {'NLI%':^8} | {'Hops':^6}")
    print(f"  {'-'*70}")
    for m in MODS_ORDERED:
        if m not in by_mod:
            continue
        rs = by_mod[m]
        m_osnr = np.mean([r['osnr_real'] for r in rs])
        m_ase  = np.mean([r['ase_db'] for r in rs])
        m_pen  = np.mean([r['penalty_nli'] for r in rs])
        m_frac = np.mean([r['nli_frac'] for r in rs])
        m_hops = np.mean([r['n_hops'] for r in rs])
        print(f"  {m:<8} | {len(rs):>5d} | {m_osnr:>9.2f} B | {m_ase:>9.2f} B | {m_pen:>8.2f} B | {m_frac:>6.1f}% | {m_hops:>4.1f}")
    print(f"{'='*72}")

    # ─── Veredicto ───────────────────────────────────────────────
    mean_frac = np.mean(fracs)
    dominant_str = "ASE é o fator limitante principal" if mean_frac < 30 else "NLI e ASE compartilham a limitação" if mean_frac < 60 else "NLI é o fator limitante principal (efeitos não lineares dominam)"
    print(f"\n  ► Diagnóstico Físico: {dominant_str}")
    print(f"    O ruído não linear (NLI) representa, em média, {mean_frac:.1f}% do ruído total das conexões.")
    print(f"    Isso impõe uma penalidade média de {np.mean(deltas):.2f} dB no OSNR real dos serviços.")

    # ─── Gráficos ────────────────────────────────────────────────
    # Gráfico 1: Histogramas
    fig1, axes1 = plt.subplots(1, 2, figsize=(12, 4.5), dpi=160)

    ax = axes1[0]
    vmin = min(np.min(osnrs), np.min(ases))
    vmax = max(np.max(osnrs), np.max(ases))
    bins = np.linspace(vmin, vmax, 30)
    ax.hist(ases,  bins=bins, alpha=0.7, color="#1f77b4", label=f"Apenas ASE  (μ={np.mean(ases):.1f} dB)", zorder=3)
    ax.hist(osnrs, bins=bins, alpha=0.7, color="#d62728", label=f"Total (ASE+NLI) (μ={np.mean(osnrs):.1f} dB)", zorder=3)
    ax.axvline(np.mean(ases),  color="#1f77b4", linestyle="--", linewidth=1.5)
    ax.axvline(np.mean(osnrs), color="#d62728", linestyle="--", linewidth=1.5)
    ax.set_xlabel("OSNR (dB)", labelpad=6)
    ax.set_ylabel("Quantidade de conexões")
    ax.set_title("Distribuição do OSNR: Apenas ASE vs OSNR Real (FFQoT_Aware)")
    ax.legend(frameon=True, framealpha=0.9, fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax2 = axes1[1]
    ax2.hist(fracs, bins=25, color="#2ca02c", alpha=0.8, zorder=3, edgecolor="white")
    ax2.axvline(mean_frac, color="#2ca02c", linestyle="--", linewidth=1.8, label=f"Média = {mean_frac:.1f}%")
    ax2.set_xlabel("Fração de Ruído NLI no Ruído Total (%)")
    ax2.set_ylabel("Quantidade de conexões")
    ax2.set_title("Percentual de Ruído NLI por Conexão")
    ax2.legend(frameon=True, framealpha=0.9, fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig1.suptitle(
        f"Análise de OSNR com FFQoT_Aware — Carga: {int(args.load)} Erl, Margem: {args.margin} dB",
        fontsize=11.5, y=1.02, fontweight="bold",
    )
    plt.tight_layout()
    out1 = OUTPUT_DIR / f"ff_qot_aware_osnr_distribution_load{int(args.load)}_margin{args.margin:g}.png"
    fig1.savefig(out1, bbox_inches="tight")
    plt.close(fig1)

    # Gráfico 2: Boxplot da penalidade NLI por modulação
    fig2, ax3 = plt.subplots(figsize=(8.5, 4.5), dpi=160)
    mod_data   = [[r["penalty_nli"] for r in by_mod[m]] for m in MODS_ORDERED if m in by_mod]
    mod_labels = [m for m in MODS_ORDERED if m in by_mod]
    colors_sel = [MOD_COLORS[i] for i, m in enumerate(MODS_ORDERED) if m in by_mod]

    bp = ax3.boxplot(mod_data, labels=mod_labels, patch_artist=True,
                     medianprops={"color": "black", "linewidth": 2},
                     flierprops={"marker": ".", "markersize": 4, "alpha": 0.5})
    for patch, color in zip(bp["boxes"], colors_sel):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    ax3.axhline(0, color="#aaaaaa", linestyle="--", linewidth=1.0)
    ax3.set_xlabel("Formato de Modulação", labelpad=8)
    ax3.set_ylabel("Penalidade NLI (dB)\n(OSNR_ase - OSNR_real)", labelpad=8)
    ax3.set_title(f"Penalidade de NLI por Formato de Modulação (FFQoT_Aware)\n"
                 f"Carga: {int(args.load)} Erl, Margem: {args.margin} dB", pad=12)
    ax3.grid(axis="y", linestyle="--", alpha=0.4)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    plt.tight_layout()
    out2 = OUTPUT_DIR / f"ff_qot_aware_nli_penalty_by_mod_load{int(args.load)}_margin{args.margin:g}.png"
    fig2.savefig(out2, bbox_inches="tight")
    plt.close(fig2)

    print(f"\n  Gráficos salvos com sucesso em: {OUTPUT_DIR.name}/")
    print(f"    • {out1.name}")
    print(f"    • {out2.name}")
    print("✅ Execução concluída!")

if __name__ == "__main__":
    main()
