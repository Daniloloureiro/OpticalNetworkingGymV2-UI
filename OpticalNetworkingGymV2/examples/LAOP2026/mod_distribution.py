"""
mod_distribution.py
====================
Distribuição de uso por formato de modulação para as 3 heurísticas.
Roda as 3 em paralelo com episode_length=300 para terminar em ~3 min.
"""
import sys
import multiprocessing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

SCRIPT_DIR  = Path(__file__).resolve().parent
OUTPUT_DIR  = SCRIPT_DIR / "results_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODULATIONS = ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"]
MOD_COLORS  = ["#4393c3", "#92c5de", "#f4a582", "#d6604d", "#b2182b", "#67001f"]
POLICY_COLORS = ["#555555", "#d62728", "#1f77b4"]

LOAD        = 250.0
FIXED_MARGIN = 1.0
SEED        = 10
EPISODE_LEN = 300
MOD_COUNT   = 6


# ──────────────────────────────────────────────────────────────
# Funções de worker (top-level para funcionar com multiprocessing)
# ──────────────────────────────────────────────────────────────
def _run_policy(policy_key: str) -> dict:
    """Roda 1 episódio com a política indicada e retorna contagem por mod."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from optical_networking_gym_v2 import make_env
    from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils
    from optical_networking_gym_v2.utils import experiment_utils as sweep_utils

    scenario = scenario_utils.build_nobel_eu_graph_load_scenario(
        topology_id="nobel-eu", episode_length=EPISODE_LEN,
        seed=SEED, load=LOAD, mean_holding_time=10800.0,
        num_spectrum_resources=320, k_paths=5, launch_power_dbm=0.0,
        modulations_to_consider=MOD_COUNT, margin=FIXED_MARGIN,
        measure_disruptions=True, drop_on_disruption=True,
    )
    env = make_env(config=scenario)
    _, info = env.reset(seed=SEED)

    while True:
        if policy_key == "legacy":
            mask = info.get("mask")
            if mask is None:
                mask = env.action_masks()
            from optical_networking_gym_v2 import select_first_fit_action
            action = int(select_first_fit_action(mask))
        elif policy_key == "ff_qot_aware":
            action = int(sweep_utils.select_ff_qot_aware_policy(env, {}))
        else:  # ff_qota_optimized
            from optical_networking_gym_v2.heuristics.runtime_heuristics_test import (
                select_ff_qota_optimized_action,
            )
            action = int(select_ff_qota_optimized_action(env.heuristic_context()))

        _, _, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break

    snap       = env.simulator.statistics.snapshot()
    mods       = env.simulator.config.modulations
    hist       = dict(snap.episode_modulation_histogram)
    se_to_name = {m.spectral_efficiency: m.name for m in mods}
    mod_counts = {m: 0 for m in MODULATIONS}
    for se, cnt in hist.items():
        name = se_to_name.get(int(se))
        if name and name in mod_counts:
            mod_counts[name] = int(cnt)

    accepted = int(snap.episode_services_accepted)
    return {
        "policy":     policy_key,
        "accepted":   accepted,
        "blocking":   float(snap.episode_service_blocking_rate),
        "disrupted":  int(snap.episode_disrupted_services),
        "mod_counts": mod_counts,
        "mod_fracs":  {k: (v / accepted if accepted > 0 else 0.0)
                       for k, v in mod_counts.items()},
    }


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    POLICY_KEYS = ["legacy", "ff_qot_aware", "ff_qota_optimized"]
    POLICY_LABELS = {
        "legacy":  "Legada\n(FF mascarado)",
        "ff_qot_aware":    "FFQoT_Aware",
        "ff_qota_optimized": "FFQoTA_Otimizada",
    }

    print(f"Coletando distribuição por modulação em paralelo")
    print(f"  load={LOAD} Erl | margin={FIXED_MARGIN} dB | {EPISODE_LEN} requisições\n")

    with multiprocessing.Pool(processes=3) as pool:
        results_list = pool.map(_run_policy, POLICY_KEYS)

    results_by_policy = {r["policy"]: r for r in results_list}

    # Imprime tabela no terminal
    for key in POLICY_KEYS:
        r = results_by_policy[key]
        lbl = POLICY_LABELS[key].replace("\n", " ")
        print(f"  {lbl}:")
        print(f"    aceitos={r['accepted']}  bloqueio={r['blocking']*100:.1f}%  disrupções={r['disrupted']}")
        for m in MODULATIONS:
            cnt = r["mod_counts"][m]
            pct = r["mod_fracs"][m] * 100
            bar = "█" * int(pct / 2)
            print(f"    {m:<8} {cnt:4d} ({pct:5.1f}%) {bar}")
        print()

    policy_names  = POLICY_KEYS
    display_names = [POLICY_LABELS[k] for k in POLICY_KEYS]

    # ──────────────────────────────────────────────────────────────
    # Gráfico 1: Barras empilhadas — distribuição relativa
    # ──────────────────────────────────────────────────────────────
    x     = np.arange(len(policy_names))
    width = 0.55
    fig1, ax1 = plt.subplots(figsize=(8.5, 5.5), dpi=180)
    bottom = np.zeros(len(policy_names))
    bars_by_mod = {}

    for i, mod in enumerate(MODULATIONS):
        fracs = np.array([results_by_policy[p]["mod_fracs"][mod] * 100 for p in policy_names])
        bars  = ax1.bar(x, fracs, width, bottom=bottom, color=MOD_COLORS[i],
                        label=mod, edgecolor="white", linewidth=0.6, zorder=3)
        bars_by_mod[mod] = (bars, bottom.copy(), fracs)
        bottom += fracs

    # Rótulos dentro dos segmentos
    for mod, (bars, bot, fracs) in bars_by_mod.items():
        for bi, (bar, b, f) in enumerate(zip(bars, bot, fracs)):
            if f > 5:
                ax1.text(bar.get_x() + bar.get_width() / 2, b + f / 2,
                         f"{f:.0f}%", ha="center", va="center",
                         fontsize=9, color="white", fontweight="bold")

    # Anotação acima de cada barra
    for bi, pk in enumerate(policy_names):
        r = results_by_policy[pk]
        ax1.text(bi, 102,
                 f"n={r['accepted']}\n({(1-r['blocking'])*100:.0f}% aceito)",
                 ha="center", va="bottom", fontsize=8.5, color="#222222")

    ax1.set_xticks(x)
    ax1.set_xticklabels(display_names, fontsize=10.5)
    ax1.set_ylim(0, 118)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax1.set_ylabel("Proporção dos serviços aceitos (%)", labelpad=8)
    ax1.set_title(
        f"Taxa de uso por formato de modulação\n"
        f"(load={int(LOAD)} Erl, margem={FIXED_MARGIN} dB, {EPISODE_LEN} req., seed={SEED})",
        pad=13, fontsize=12,
    )
    ax1.legend(title="Modulação", bbox_to_anchor=(1.02, 1), loc="upper left",
               frameon=True, framealpha=0.92, edgecolor="#cccccc", fontsize=9.5)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    plt.tight_layout()
    out1 = OUTPUT_DIR / f"modulation_stacked_margin{FIXED_MARGIN:g}.png"
    fig1.savefig(out1, bbox_inches="tight")
    print(f"Salvo: {out1}")
    plt.close(fig1)

    # ──────────────────────────────────────────────────────────────
    # Gráfico 2: Barras agrupadas — contagem absoluta por modulação
    # ──────────────────────────────────────────────────────────────
    fig2, ax2 = plt.subplots(figsize=(10, 5), dpi=180)
    n_mods  = len(MODULATIONS)
    n_pol   = len(policy_names)
    group_w = 0.72
    bar_w   = group_w / n_pol
    offsets = np.linspace(-(group_w - bar_w) / 2, (group_w - bar_w) / 2, n_pol)

    for pi, (pk, offset) in enumerate(zip(policy_names, offsets)):
        counts = [results_by_policy[pk]["mod_counts"][m] for m in MODULATIONS]
        pos    = np.arange(n_mods) + offset
        bars   = ax2.bar(pos, counts, bar_w, label=POLICY_LABELS[pk].replace("\n", " "),
                         color=POLICY_COLORS[pi], edgecolor="white",
                         linewidth=0.4, alpha=0.88)
        for bar, cnt in zip(bars, counts):
            if cnt > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                         str(cnt), ha="center", va="bottom",
                         fontsize=7.5, color=POLICY_COLORS[pi])

    ax2.set_xticks(np.arange(n_mods))
    ax2.set_xticklabels(MODULATIONS, fontsize=12)
    ax2.set_ylabel("Serviços aceitos (contagem)", labelpad=8)
    ax2.set_title(
        f"Contagem de serviços aceitos por modulação e heurística\n"
        f"(load={int(LOAD)} Erl, margem={FIXED_MARGIN} dB, {EPISODE_LEN} req., seed={SEED})",
        pad=13, fontsize=12,
    )
    ax2.legend(frameon=True, framealpha=0.92, edgecolor="#cccccc", fontsize=9.5)
    ax2.grid(axis="y", linestyle="--", alpha=0.35)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    plt.tight_layout()
    out2 = OUTPUT_DIR / f"modulation_counts_margin{FIXED_MARGIN:g}.png"
    fig2.savefig(out2, bbox_inches="tight")
    print(f"Salvo: {out2}")
    plt.close(fig2)

    print("\n✅ Concluído!")
