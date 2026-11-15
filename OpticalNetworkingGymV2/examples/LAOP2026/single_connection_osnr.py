"""
single_connection_osnr.py
==========================
Decompõe o OSNR de uma ÚNICA conexão recém-aceita:
  • Contribuição de ASE e NLI por enlace e por span
  • OSNR acumulado ao longo do caminho (tracejado)
  • Comparação: OSNR com NLI vs sem NLI

Uso:
  python examples/LAOP2026/single_connection_osnr.py \
      --load 250 --margin 1.0 [--connection-index N]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from optical_networking_gym_v2 import make_env, select_first_fit_action
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils
from optical_networking_gym_v2.optical.kernels.qot_kernel import accumulate_link_noise

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def db(x: float) -> float:
    return 10.0 * math.log10(max(x, 1e-300))


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument("--load",              type=float, default=250.0)
    p.add_argument("--margin",            type=float, default=1.0)
    p.add_argument("--seed",              type=int,   default=10)
    p.add_argument("--launch-power-dbm",  type=float, default=0.0)
    p.add_argument("--connection-index",  type=int,   default=0,
                   help="Qual conexão aceita usar (0=primeira, 1=segunda...)")
    p.add_argument("--k-paths",           type=int,   default=3)
    return p


def main():
    args = build_parser().parse_args()
    P_lin = 10 ** ((args.launch_power_dbm - 30.0) / 10.0)  # W

    scenario = scenario_utils.build_nobel_eu_graph_load_scenario(
        topology_id="nobel-eu", episode_length=500, seed=args.seed,
        load=args.load, mean_holding_time=10800.0,
        num_spectrum_resources=320, k_paths=args.k_paths,
        launch_power_dbm=args.launch_power_dbm, modulations_to_consider=6,
        margin=args.margin, measure_disruptions=True, drop_on_disruption=False,
    )
    env   = make_env(config=scenario)
    _, info = env.reset(seed=args.seed)
    qot   = env.simulator.qot_engine
    state = env.simulator.state
    topo  = env.simulator.topology

    # ── Encontra a N-ésima conexão aceita ─────────────────────────
    seen_ids: set[int] = set()
    target_svc = None
    target_count = 0

    while True:
        mask = info.get("mask")
        if mask is None:
            mask = env.action_masks()
        action = int(select_first_fit_action(mask))
        _, _, term, trunc, info = env.step(action)

        if "accepted" in str(info.get("status", "")):
            active = env.simulator.state.active_services_by_id
            new_ids = set(active.keys()) - seen_ids
            seen_ids = set(active.keys())
            for svc_id in sorted(new_ids):
                if target_count == args.connection_index:
                    target_svc = active[svc_id]
                target_count += 1

        if target_svc is not None or term or trunc:
            break

    if target_svc is None:
        print(f"Conexão #{args.connection_index} não encontrada. Tente um índice menor.")
        return

    svc  = target_svc
    path = svc.path
    mod  = svc.modulation
    req  = svc.request

    print(f"\n{'='*68}")
    print(f"  DETALHE DE UMA CONEXÃO — conexão índice #{args.connection_index}")
    print(f"{'='*68}")
    print(f"  Rota   : {' → '.join(str(n) for n in path.node_names)}")
    print(f"  Hops   : {len(path.link_ids)} enlace(s)")
    print(f"  Modula.: {mod.name if mod else '?'}  "
          f"(OSNR_min={mod.minimum_osnr:.2f} dB + margin={args.margin:.1f} → "
          f"limiar={mod.minimum_osnr+args.margin:.2f} dB)")
    print(f"  Slots  : [{svc.service_slot_start}, {svc.service_slot_end_exclusive})  "
          f"({svc.service_num_slots} slots  |  BW={svc.bandwidth/1e9:.1f} GHz)")
    print(f"  f_c    : {svc.center_frequency/1e12:.4f} THz")
    print(f"  P_tx   : {args.launch_power_dbm:.1f} dBm  ({P_lin*1e3:.4f} mW)")
    print(f"\n  OSNR gravado: {svc.osnr:.4f} dB  "
          f"(ASE={svc.ase:.4f} dB, NLI={svc.nli:.4f} dB)")

    # ── Cálculo per-link reutilizando o kernel do simulador ───────
    _PHI = {1: 1.0, 2: 1.0, 3: 2/3, 4: 17/25, 5: 69/100, 6: 13/21}

    print(f"\n  {'Enlace':<6}  {'Nós':<30}  {'Spans':>5}  "
          f"{'km':>7}  {'ASE_link':>10}  {'NLI_link':>10}  "
          f"{'OSNR_acc':>9}  {'NLI%':>6}")
    print(f"  {'-'*90}")

    cum_gsnr = 0.0
    cum_ase  = 0.0
    cum_nli  = 0.0
    link_rows = []

    for hop_i, link_id in enumerate(path.link_ids):
        link_obj = topo.links[link_id]
        n_spans  = len(link_obj.spans)
        dist_km  = sum(s.length_km for s in link_obj.spans)

        # Serviços ativos no enlace (interferentes NLI)
        svc_ids_on_link = tuple(sorted(state.link_active_service_ids[link_id]))
        run_ids     = np.array([i for i in svc_ids_on_link if i != svc.service_id], dtype=np.int32)
        run_freqs   = np.array([state.active_services_by_id[i].center_frequency for i in run_ids], dtype=np.float64)
        run_bws     = np.array([state.active_services_by_id[i].bandwidth         for i in run_ids], dtype=np.float64)
        run_phis    = np.array([_PHI[state.active_services_by_id[i].modulation.spectral_efficiency]
                                for i in run_ids], dtype=np.float64)

        span_lengths_km   = qot._link_span_lengths_km[link_id]
        span_attenuation  = qot._link_span_attenuation_normalized[link_id]
        span_noise_figure = qot._link_span_noise_figure_normalized[link_id]

        link_gsnr, link_ase, link_nli = accumulate_link_noise(
            span_lengths_km, span_attenuation, span_noise_figure,
            run_ids, run_freqs, run_bws, run_phis,
            current_service_id=svc.service_id,
            center_frequency=svc.center_frequency,
            bandwidth=svc.bandwidth,
            launch_power=P_lin,
            include_nli=True,
        )

        # sem NLI
        _, link_ase_only, _ = accumulate_link_noise(
            span_lengths_km, span_attenuation, span_noise_figure,
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.float64),
            current_service_id=svc.service_id,
            center_frequency=svc.center_frequency,
            bandwidth=svc.bandwidth,
            launch_power=P_lin,
            include_nli=False,
        )

        cum_gsnr += link_gsnr
        cum_ase  += link_ase
        cum_nli  += link_nli

        osnr_acc_db = db(1.0 / cum_gsnr)
        ase_link_db = db(P_lin / link_ase) if link_ase > 0 else float("inf")
        nli_link_db = db(P_lin / link_nli) if link_nli > 0 else float("inf")
        nli_frac    = link_nli / (link_ase + link_nli) * 100 if (link_ase + link_nli) > 0 else 0.0

        src_name = str(link_obj.source_name)
        dst_name = str(link_obj.target_name)
        nos_str  = f"{src_name} → {dst_name}"

        print(f"  {hop_i+1:<6}  {nos_str:<30}  {n_spans:>5}  "
              f"{dist_km:>7.1f}  {ase_link_db:>10.2f}  {nli_link_db:>10.2f}  "
              f"{osnr_acc_db:>9.2f}  {nli_frac:>5.1f}%")

        link_rows.append({
            "hop": hop_i + 1,
            "link_id": link_id,
            "nos": nos_str,
            "n_spans": n_spans,
            "dist_km": dist_km,
            "ase_link": link_ase,
            "nli_link": link_nli,
            "ase_link_db": ase_link_db,
            "nli_link_db": nli_link_db,
            "ase_only_db": db(P_lin / link_ase_only) if link_ase_only > 0 else float("inf"),
            "cum_gsnr": cum_gsnr,
            "cum_ase": cum_ase,
            "cum_nli": cum_nli,
            "osnr_acc": osnr_acc_db,
            "nli_frac": nli_frac,
            "n_interferers": len(run_ids),
        })

    # Totais
    final_osnr = db(1.0 / cum_gsnr)
    final_ase  = db(P_lin / cum_ase) if cum_ase > 0 else float("inf")
    final_nli  = db(P_lin / cum_nli) if cum_nli > 0 else float("inf")
    final_frac = cum_nli / (cum_ase + cum_nli) * 100 if (cum_ase + cum_nli) > 0 else 0.0
    threshold  = mod.minimum_osnr + args.margin if mod else 0.0
    margin_db  = final_osnr - threshold

    print(f"  {'─'*90}")
    print(f"  TOTAL               OSNR={final_osnr:.4f} dB  "
          f"ASE={final_ase:.4f} dB  NLI={final_nli:.4f} dB  NLI%={final_frac:.1f}%")
    print(f"  Limiar={threshold:.2f} dB  →  margem real={margin_db:.4f} dB  "
          f"({'✅ aceito' if margin_db >= 0 else '❌ abaixo do limiar'})")

    # ═══════════════════════════════════════════════════════════════
    # Gráfico: OSNR acumulado hop a hop + barras de ASE/NLI por link
    # ═══════════════════════════════════════════════════════════════
    hops     = [r["hop"] for r in link_rows]
    osnr_acc = [r["osnr_acc"] for r in link_rows]
    ase_dbs  = [r["ase_link_db"] for r in link_rows]
    nli_dbs  = [r["nli_link_db"] for r in link_rows]
    nos_labels = [r["nos"].replace(" → ", "\n→\n") for r in link_rows]

    fig, axes = plt.subplots(2, 1, figsize=(max(8, len(hops)*2.2), 8), dpi=160,
                              gridspec_kw={"height_ratios": [2, 1.2]})

    # ── Painel superior: OSNR acumulado ──────────────────────────
    ax1 = axes[0]
    ax1.plot(hops, osnr_acc, "o-", color="#2166ac", linewidth=2.5,
             markersize=9, zorder=5, label="OSNR acumulado (ASE+NLI)")

    # OSNR apenas ASE acumulado
    cum_ase_only_arr = []
    c_ase_only = 0.0
    for r in link_rows:
        c_ase_only += r["ase_link"]
        cum_ase_only_arr.append(db(P_lin / c_ase_only) if c_ase_only > 0 else float("inf"))
    ax1.plot(hops, cum_ase_only_arr, "s--", color="#74add1", linewidth=1.8,
             markersize=7, zorder=4, alpha=0.85, label="OSNR acumulado (apenas ASE)")

    # Linha de limiar
    ax1.axhline(threshold, color="#d62728", linestyle="--", linewidth=1.8,
                label=f"Limiar QoT = {threshold:.1f} dB  ({mod.name if mod else '?'}+{args.margin:.1f} dB)")
    ax1.axhline(final_osnr, color="#2166ac", linestyle=":", linewidth=1.2, alpha=0.6)

    # Anota margem final
    ax1.annotate(f"  margem = {margin_db:+.2f} dB", xy=(hops[-1], final_osnr),
                 fontsize=9, color="#2166ac", va="center")

    ax1.set_ylabel("OSNR acumulado (dB)", labelpad=8)
    ax1.set_title(
        f"Detalhe por enlace — conexão #{args.connection_index}\n"
        f"{'  →  '.join(str(n) for n in path.node_names)}\n"
        f"{mod.name if mod else '?'} | P={args.launch_power_dbm:.0f} dBm | "
        f"margin={args.margin:.1f} dB | load={int(args.load)} Erl",
        pad=10, fontsize=10.5,
    )
    ax1.set_xticks(hops)
    ax1.set_xticklabels([f"Hop {h}" for h in hops], fontsize=9)
    ax1.legend(frameon=True, framealpha=0.9, fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # ── Painel inferior: barras ASE e NLI por enlace (em dB) ─────
    ax2 = axes[1]
    bw = 0.35
    x  = np.array(hops, dtype=float)

    # Converte para ruído linear normalizado (1/OSNR_link) para comparar grandezas
    ase_inv  = [r["ase_link"] / P_lin for r in link_rows]   # ASE/P  (ruído relativo)
    nli_inv  = [r["nli_link"] / P_lin for r in link_rows]   # NLI/P

    # Plota em dB relativo (10*log10(ruído_relativo))
    ase_rel_db = [10*math.log10(v) if v > 0 else -60 for v in ase_inv]
    nli_rel_db = [10*math.log10(v) if v > 0 else -60 for v in nli_inv]

    b1 = ax2.bar(x - bw/2, ase_rel_db, bw, label="ASE por enlace",
                 color="#1f77b4", alpha=0.82, edgecolor="white")
    b2 = ax2.bar(x + bw/2, nli_rel_db, bw, label="NLI por enlace",
                 color="#d62728", alpha=0.82, edgecolor="white")

    # Rótulo de interferentes
    for i, r in enumerate(link_rows):
        if r["n_interferers"] > 0:
            ax2.text(x[i] + bw/2, nli_rel_db[i] + 0.3,
                     f"{r['n_interferers']} serv.", ha="center", va="bottom",
                     fontsize=7.5, color="#d62728")

    ax2.set_ylabel("Ruído por enlace\n(10·log₁₀(N/P), dB rel.)", labelpad=8)
    ax2.set_xlabel("Enlace (hop)", labelpad=6)
    ax2.set_xticks(hops)
    ax2.set_xticklabels(nos_labels, fontsize=7.5)
    ax2.legend(frameon=True, framealpha=0.9, fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout(h_pad=2.5)
    tag = f"conn{args.connection_index}_load{int(args.load)}_margin{args.margin:g}"
    out = OUTPUT_DIR / f"single_connection_{tag}.png"
    fig.savefig(out, bbox_inches="tight")
    print(f"\n  Salvo: {out.name}")
    plt.close(fig)
    print("✅ Concluído!")


if __name__ == "__main__":
    main()
