"""
osnr_ase_vs_nli.py
==================
Teste de diagnóstico: quanto do OSNR degradado vem de ASE vs NLI?

Para cada serviço aceito, lê diretamente do estado do simulador:
  - osnr   (dB): OSNR total = ASE + NLI
  - ase    (dB): OSNR limitado apenas por ASE (sem NLI)
  - nli    (dB): OSNR limitado apenas por NLI (sem ASE)

O OSNR real satisfaz:  1/OSNR = 1/OSNR_ase + 1/OSNR_nli
  → penalidade NLI = OSNR_ase − OSNR_real

Uso:
  python examples/LAOP2026/osnr_ase_vs_nli.py [--load 250] [--margin 1.0] [--episode-length 300]
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import numpy as np

from optical_networking_gym_v2 import make_env, select_first_fit_action
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODS_ORDERED = ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"]
MOD_COLORS   = ["#4393c3", "#92c5de", "#f4a582", "#d6604d", "#b2182b", "#67001f"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Diagnóstico ASE vs NLI no OSNR")
    p.add_argument("--load",             type=float, default=250.0)
    p.add_argument("--margin",           type=float, default=1.0)
    p.add_argument("--seed",             type=int,   default=10)
    p.add_argument("--episode-length",   type=int,   default=300)
    p.add_argument("--k-paths",          type=int,   default=5)
    p.add_argument("--launch-power-dbm", type=float, default=0.0)
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
        drop_on_disruption=False,   # mantemos todos para ver o OSNR
    )
    env = make_env(config=scenario)
    _, info = env.reset(seed=args.seed)

    seen_ids: set[int] = set()
    records: list[dict] = []

    while True:
        # first-fit simples para rapidez
        mask = info.get("mask")
        if mask is None:
            mask = env.action_masks()
        action = int(select_first_fit_action(mask))
        _, _, terminated, truncated, info = env.step(action)

        status = str(info.get("status", ""))
        if "accepted" in status:
            # Lê os atributos diretamente do estado do simulador
            active = env.simulator.state.active_services_by_id
            for svc_id, svc in active.items():
                if svc_id in seen_ids:
                    continue
                seen_ids.add(svc_id)
                osnr_real = float(svc.osnr)  # dB total  (ASE + NLI)
                ase_db    = float(svc.ase)   # dB se só ASE existisse
                nli_db    = float(svc.nli)   # dB se só NLI existisse

                # Penalidade NLI = OSNR sem NLI − OSNR real
                penalty_nli = ase_db - osnr_real  # sempre ≥ 0

                # Parcela NLI no ruído em escala linear
                # 1/OSNR = 1/ASE + 1/NLI  →  NLI_frac = (1/NLI) / (1/ASE + 1/NLI)
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

    if not records:
        print("Nenhum serviço aceito registrado.")
        return

    # ─── Estatísticas no terminal ────────────────────────────────
    osnrs   = [r["osnr_real"]   for r in records]
    ases    = [r["ase_db"]      for r in records]
    nlis    = [r["nli_db"]      for r in records]
    deltas  = [r["penalty_nli"] for r in records]
    fracs   = [r["nli_frac"]    for r in records]

    print(f"\n{'='*64}")
    print(f"  DIAGNÓSTICO ASE vs NLI")
    print(f"  load={args.load} Erl | margin={args.margin} dB | "
          f"P_launch={args.launch_power_dbm} dBm | {len(records)} serviços")
    print(f"{'='*64}")
    print(f"\n  Métrica               {'média':>8}  {'mín':>8}  {'máx':>8}")
    print(f"  {'-'*48}")
    print(f"  OSNR (ASE+NLI)  dB    {np.mean(osnrs):>8.2f}  {np.min(osnrs):>8.2f}  {np.max(osnrs):>8.2f}")
    print(f"  OSNR apenas ASE dB    {np.mean(ases):>8.2f}  {np.min(ases):>8.2f}  {np.max(ases):>8.2f}")
    print(f"  OSNR apenas NLI dB    {np.mean(nlis):>8.2f}  {np.min(nlis):>8.2f}  {np.max(nlis):>8.2f}")
    print(f"  Penalidade NLI  dB    {np.mean(deltas):>8.2f}  {np.min(deltas):>8.2f}  {np.max(deltas):>8.2f}")
    print(f"  Parcela NLI     %     {np.mean(fracs):>8.1f}  {np.min(fracs):>8.1f}  {np.max(fracs):>8.1f}")

    by_mod: dict[str, list] = defaultdict(list)
    for r in records:
        by_mod[r["mod"]].append(r)

    print(f"\n  {'Mod':<8}  {'n':>4}  {'OSNR real':>10}  {'ASE only':>9}  "
          f"{'Δ NLI(dB)':>10}  {'NLI%':>7}  {'hops':>5}")
    print(f"  {'-'*65}")
    for m in MODS_ORDERED:
        if m not in by_mod:
            continue
        rs = by_mod[m]
        print(f"  {m:<8}  {len(rs):>4}  "
              f"{np.mean([r['osnr_real'] for r in rs]):>9.2f}  "
              f"{np.mean([r['ase_db'] for r in rs]):>9.2f}  "
              f"  {np.mean([r['penalty_nli'] for r in rs]):>9.2f}  "
              f"{np.mean([r['nli_frac'] for r in rs]):>6.1f}%  "
              f"{np.mean([r['n_hops'] for r in rs]):>5.1f}")

    # ─── Veredicto ───────────────────────────────────────────────
    mean_frac = np.mean(fracs)
    print(f"\n  ► {'ASE é dominante' if mean_frac < 30 else 'NLI tem contribuição significativa' if mean_frac < 60 else 'NLI é dominante'}")
    print(f"    NLI representa em média {mean_frac:.1f}% do ruído total.")
    print(f"    Penalidade média de {np.mean(deltas):.2f} dB por NLI no OSNR efetivo.")

    # ─── Gráfico 1: Histogramas ───────────────────────────────────
    fig1, axes1 = plt.subplots(1, 2, figsize=(12, 4.5), dpi=170)

    ax = axes1[0]
    vmin = min(np.min(osnrs), np.min(ases))
    vmax = max(np.max(osnrs), np.max(ases))
    bins = np.linspace(vmin, vmax, 35)
    ax.hist(ases,  bins=bins, alpha=0.72, color="#1f77b4", label=f"Apenas ASE  (μ={np.mean(ases):.1f} dB)", zorder=3)
    ax.hist(osnrs, bins=bins, alpha=0.72, color="#d62728", label=f"ASE + NLI   (μ={np.mean(osnrs):.1f} dB)", zorder=3)
    ax.axvline(np.mean(ases),  color="#1f77b4", linestyle="--", linewidth=1.6)
    ax.axvline(np.mean(osnrs), color="#d62728", linestyle="--", linewidth=1.6)
    ax.set_xlabel("OSNR (dB)", labelpad=6)
    ax.set_ylabel("Serviços aceitos")
    ax.set_title("Distribuição do OSNR\nApenas ASE vs ASE+NLI")
    ax.legend(frameon=True, framealpha=0.9, fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax2 = axes1[1]
    ax2.hist(fracs, bins=30, color="#2ca02c", alpha=0.82, zorder=3, edgecolor="white")
    ax2.axvline(mean_frac, color="#2ca02c", linestyle="--", linewidth=1.8,
                label=f"Média = {mean_frac:.1f}%")
    ax2.set_xlabel("Contribuição do NLI no ruído total (%)")
    ax2.set_ylabel("Serviços aceitos")
    ax2.set_title("Parcela do NLI\nno ruído total (ASE+NLI)")
    ax2.legend(frameon=True, framealpha=0.9, fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig1.suptitle(
        f"Diagnóstico ASE vs NLI — load={int(args.load)} Erl, margin={args.margin} dB, "
        f"P={args.launch_power_dbm} dBm, {len(records)} serviços",
        fontsize=11, y=1.03,
    )
    plt.tight_layout()
    out1 = OUTPUT_DIR / f"osnr_ase_vs_nli_load{int(args.load)}_margin{args.margin:g}.png"
    fig1.savefig(out1, bbox_inches="tight")
    print(f"\n  Salvo: {out1.name}")
    plt.close(fig1)

    # ─── Gráfico 2: Boxplot da penalidade NLI por modulação ──────
    fig2, ax3 = plt.subplots(figsize=(9, 4.5), dpi=170)
    mod_data   = [[r["penalty_nli"] for r in by_mod[m]] for m in MODS_ORDERED if m in by_mod]
    mod_labels = [m for m in MODS_ORDERED if m in by_mod]
    colors_sel = [MOD_COLORS[i] for i, m in enumerate(MODS_ORDERED) if m in by_mod]

    bp = ax3.boxplot(mod_data, labels=mod_labels, patch_artist=True,
                     medianprops={"color": "black", "linewidth": 2},
                     flierprops={"marker": ".", "markersize": 4, "alpha": 0.5})
    for patch, color in zip(bp["boxes"], colors_sel):
        patch.set_facecolor(color)
        patch.set_alpha(0.78)

    ax3.axhline(0, color="#aaaaaa", linestyle="--", linewidth=1.0)
    ax3.set_xlabel("Formato de modulação")
    ax3.set_ylabel("Penalidade NLI (dB)\n= OSNR_ase − OSNR_real")
    ax3.set_title(
        f"Penalidade do NLI por formato de modulação\n"
        f"(load={int(args.load)} Erl, margin={args.margin} dB, P={args.launch_power_dbm} dBm)"
    )
    ax3.grid(axis="y", linestyle="--", alpha=0.4)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    plt.tight_layout()
    out2 = OUTPUT_DIR / f"nli_penalty_by_mod_load{int(args.load)}_margin{args.margin:g}.png"
    fig2.savefig(out2, bbox_inches="tight")
    print(f"  Salvo: {out2.name}")
    plt.close(fig2)

    # ─── Gráfico 3: Scatter OSNR_real vs n_hops, colorido por mod ─
    fig3, ax4 = plt.subplots(figsize=(8, 4.5), dpi=170)
    for i, m in enumerate(MODS_ORDERED):
        if m not in by_mod:
            continue
        rs = by_mod[m]
        ax4.scatter([r["n_hops"] for r in rs], [r["penalty_nli"] for r in rs],
                    label=m, color=MOD_COLORS[i], alpha=0.65, s=28, zorder=3)
    ax4.set_xlabel("Número de enlaces (hops) no caminho")
    ax4.set_ylabel("Penalidade NLI (dB)")
    ax4.set_title("Penalidade NLI vs número de hops\n(quanto mais hops → mais NLI acumulado)")
    ax4.legend(title="Modulação", frameon=True, framealpha=0.9, fontsize=9)
    ax4.grid(linestyle="--", alpha=0.4)
    ax4.spines["top"].set_visible(False)
    ax4.spines["right"].set_visible(False)
    plt.tight_layout()
    out3 = OUTPUT_DIR / f"nli_vs_hops_load{int(args.load)}_margin{args.margin:g}.png"
    fig3.savefig(out3, bbox_inches="tight")
    print(f"  Salvo: {out3.name}")
    plt.close(fig3)

    print("\n✅ Diagnóstico ASE vs NLI concluído!")


if __name__ == "__main__":
    main()
