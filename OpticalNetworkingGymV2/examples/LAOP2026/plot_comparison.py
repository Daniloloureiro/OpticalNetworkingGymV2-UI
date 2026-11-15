"""
plot_comparison.py
==================
Gera gráficos comparativos entre as três heurísticas:
  1. Legada        (old_masked_first_fit)       — results_antigos/17-05-17h33
  2. FFQoT_Aware   (disruption_aware_first_fit)  — results_smart/
  3. FFQoTA_Otimizada (relaxed_daff)             — results_test/*.summary.json

Salva os PNGs no diretório results_test/.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
SCRIPT_DIR    = Path(__file__).resolve().parent
SMART_DIR     = SCRIPT_DIR / "results_smart"
TEST_DIR      = SCRIPT_DIR / "results_test"
LEGACY_DIR    = SCRIPT_DIR.parent / "Resultados antigos" / "results"

OUTPUT_DIR    = TEST_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOADS   = [250.0, 275.0, 300.0]
MARGINS = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# ---------------------------------------------------------------------------
# Estilo global
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

POLICY_STYLE = {
    "legacy": {
        "label":    "Legada (FF mascarado)",
        "color":    "#888888",
        "marker":   "s",
        "linestyle": "--",
        "linewidth": 1.6,
        "markersize": 6,
        "zorder": 1,
    },
    "ff_qot_aware": {
        "label":    "FFQoT_Aware (sem disrupção)",
        "color":    "#d62728",
        "marker":   "^",
        "linestyle": "-.",
        "linewidth": 1.8,
        "markersize": 7,
        "zorder": 2,
    },
    "ff_qota_optimized": {
        "label":    "FFQoTA_Otimizada (fallback 2-estágios)",
        "color":    "#1f77b4",
        "marker":   "o",
        "linestyle": "-",
        "linewidth": 2.2,
        "markersize": 7,
        "zorder": 3,
    },
}

LOAD_COLORS = {250.0: "#2166ac", 275.0: "#1a9850", 300.0: "#d73027"}

# ---------------------------------------------------------------------------
# 1. Carrega dados LEGADOS (CSV summary — 17h33, 6 modulações)
# ---------------------------------------------------------------------------
def load_legacy() -> pd.DataFrame:
    legacy_file = LEGACY_DIR / "17-05-17h33-publishable-scenario-summary.csv"
    if not legacy_file.exists():
        raise FileNotFoundError(f"Arquivo legado não encontrado: {legacy_file}")
    df = pd.read_csv(legacy_file)
    # Normaliza colunas para esquema comum
    return pd.DataFrame({
        "heuristic": "legacy",
        "load":      df["load"],
        "margin":    df["margin"],
        "effective_loss_rate": df["effective_loss_rate_mean"],
        "blocking_rate":       df["blocking_rate_mean"],
        "disruption_rate":     df["disruption_rate_mean"],
        "drop_rate":           df["drop_rate_mean"],
        "served_rate":         df["served_rate_mean"],
        "bit_rate_blocking_rate": df["bit_rate_blocking_rate_mean"],
    })

# ---------------------------------------------------------------------------
# 2. Carrega dados FFQoT_Aware ORIGINAL (CSV summary — results_smart/)
# ---------------------------------------------------------------------------
def load_ff_qot_aware() -> pd.DataFrame:
    smart_files = sorted(SMART_DIR.glob("*-smart-scenario-summary.csv"), reverse=True)
    if not smart_files:
        raise FileNotFoundError(f"Nenhum CSV em {SMART_DIR}")
    df = pd.read_csv(smart_files[0])
    print(f"  FFQoT_Aware: lendo {smart_files[0].name}")
    return pd.DataFrame({
        "heuristic": "ff_qot_aware",
        "load":      df["load"],
        "margin":    df["margin"],
        "effective_loss_rate": df["effective_loss_rate"],
        "blocking_rate":       df["blocking_rate"],
        "disruption_rate":     df["disruption_rate"],
        "drop_rate":           df["drop_rate"],
        "served_rate":         df["served_rate"],
        "bit_rate_blocking_rate": df["bit_rate_blocking_rate"],
    })

# ---------------------------------------------------------------------------
# 3. Carrega dados FFQoTA_Otimizada (JSON individual — results_test/)
# ---------------------------------------------------------------------------
def load_ff_qota_optimized() -> pd.DataFrame:
    json_files = list(TEST_DIR.glob("*.summary.json"))
    if not json_files:
        raise FileNotFoundError(f"Nenhum summary.json em {TEST_DIR}")
    print(f"  FFQoTA_Otimizada: encontrados {len(json_files)} arquivo(s) summary.json")
    rows = []
    for f in json_files:
        d = json.loads(f.read_text(encoding="utf-8"))
        processed = int(d["services_processed"])
        served    = int(d["services_served"])
        disrupted = int(d["episode_disrupted_services_count"])
        dropped   = int(d["disrupted_or_dropped_services"])
        rejected  = int(d["rejected"])
        rows.append({
            "heuristic": "ff_qota_optimized",
            "load":   float(d["load"]),
            "margin": float(d["margin"]),
            "effective_loss_rate":     (processed - served) / processed,
            "blocking_rate":           float(d["service_blocking_rate"]),
            "disruption_rate":         float(d["episode_disrupted_services_rate"]),
            "drop_rate":               dropped / processed,
            "served_rate":             float(d["service_served_rate"]),
            "bit_rate_blocking_rate":  float(d["bit_rate_blocking_rate"]),
        })
    return pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Carrega e unifica tudo
# ---------------------------------------------------------------------------
print("Carregando dados...")
df_legacy  = load_legacy()
df_daff    = load_ff_qot_aware()
df_relaxed = load_ff_qota_optimized()

df_all = pd.concat([df_legacy, df_daff, df_relaxed], ignore_index=True)
df_all = df_all.sort_values(["heuristic", "load", "margin"]).reset_index(drop=True)

# Quais loads e margens estão disponíveis nas 3 fontes
available_loads   = sorted(df_all["load"].unique())
available_margins = sorted(df_all["margin"].unique())
heuristics = ["legacy", "ff_qot_aware", "ff_qota_optimized"]

print(f"\nLoads disponíveis: {available_loads}")
print(f"Margens disponíveis: {available_margins}")
print(f"Pontos por heurística:")
for h in heuristics:
    n = len(df_all[df_all["heuristic"] == h])
    print(f"  {h}: {n} pontos")

# ---------------------------------------------------------------------------
# Gráfico 1: Effective Loss vs Margin — 1 linha por heurística × load
# ---------------------------------------------------------------------------
HEURISTIC_LOAD_STYLE = {
    ("legacy",  250.0): {"color": "#aaaaaa", "linestyle": "--",  "marker": "s", "lw": 1.5},
    ("legacy",  275.0): {"color": "#777777", "linestyle": "--",  "marker": "s", "lw": 1.5},
    ("legacy",  300.0): {"color": "#444444", "linestyle": "--",  "marker": "s", "lw": 1.5},
    ("ff_qot_aware",    250.0): {"color": "#fc8d59", "linestyle": "-.",  "marker": "^", "lw": 1.8},
    ("ff_qot_aware",    275.0): {"color": "#d73027", "linestyle": "-.",  "marker": "^", "lw": 1.8},
    ("ff_qot_aware",    300.0): {"color": "#67000d", "linestyle": "-.",  "marker": "^", "lw": 1.8},
    ("ff_qota_optimized", 250.0): {"color": "#74add1", "linestyle": "-",   "marker": "o", "lw": 2.2},
    ("ff_qota_optimized", 275.0): {"color": "#1a9850", "linestyle": "-",   "marker": "o", "lw": 2.2},
    ("ff_qota_optimized", 300.0): {"color": "#2166ac", "linestyle": "-",   "marker": "o", "lw": 2.2},
}

fig1, ax1 = plt.subplots(figsize=(9, 5.5), dpi=200)

for h in heuristics:
    style_base = POLICY_STYLE[h]
    for load in available_loads:
        sub = df_all[(df_all["heuristic"] == h) & (df_all["load"] == load)].sort_values("margin")
        if sub.empty:
            continue
        st = HEURISTIC_LOAD_STYLE.get((h, load), {})
        
        # Label mais limpo
        if h == "legacy" and load == available_loads[0]:
            label = f"Legada — {int(load)} Erl"
        elif h == "ff_qot_aware" and load == available_loads[0]:
            label = f"FFQoT_Aware — {int(load)} Erl"
        elif h == "ff_qota_optimized" and load == available_loads[0]:
            label = f"FFQoTA_Otimizada — {int(load)} Erl"
        else:
            label = f"— {int(load)} Erl"

        ax1.plot(
            sub["margin"],
            sub["effective_loss_rate"] * 100,
            color=st.get("color", style_base["color"]),
            linestyle=st.get("linestyle", style_base["linestyle"]),
            marker=st.get("marker", style_base["marker"]),
            linewidth=st.get("lw", style_base["linewidth"]),
            markersize=6,
            label=label,
            zorder=style_base["zorder"],
        )

# Linhas de referência de heurística na legenda (proxies)
proxy_legacy  = mlines.Line2D([], [], color="#777777", linestyle="--",  marker="s", markersize=6, linewidth=1.6, label="Legada (FF mascarado)")
proxy_daff    = mlines.Line2D([], [], color="#d73027", linestyle="-.",  marker="^", markersize=7, linewidth=1.8, label="FFQoT_Aware")
proxy_relaxed = mlines.Line2D([], [], color="#1a9850", linestyle="-",   marker="o", markersize=7, linewidth=2.2, label="FFQoTA_Otimizada")
proxy_250     = mlines.Line2D([], [], color="#74add1", linewidth=2.5, label="250 Erl")
proxy_275     = mlines.Line2D([], [], color="#1a9850", linewidth=2.5, label="275 Erl")
proxy_300     = mlines.Line2D([], [], color="#2166ac", linewidth=2.5, label="300 Erl")

leg1 = ax1.legend(handles=[proxy_legacy, proxy_daff, proxy_relaxed],
                  title="Heurística", title_fontsize=10,
                  frameon=True, framealpha=0.92, edgecolor="#cccccc",
                  loc="upper right", fontsize=9)
ax1.add_artist(leg1)
leg2 = ax1.legend(handles=[proxy_250, proxy_275, proxy_300],
                  title="Carga", title_fontsize=10,
                  frameon=True, framealpha=0.92, edgecolor="#cccccc",
                  loc="center right", fontsize=9)

ax1.set_title("Taxa de perda efetiva vs Margem de admissão\n(Comparação: Legada × FFQoT_Aware × FFQoTA_Otimizada)",
              pad=14, fontsize=12)
ax1.set_xlabel("Margem de admissão (dB)", labelpad=8)
ax1.set_ylabel("Taxa de perda efetiva (%)", labelpad=8)
ax1.set_xticks(MARGINS)
ax1.grid(True, linestyle="--", alpha=0.45)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

plt.tight_layout()
out1 = OUTPUT_DIR / "comparison_effective_loss_vs_margin.png"
fig1.savefig(out1, bbox_inches="tight")
print(f"\nSalvo: {out1.name}")
plt.close(fig1)

# ---------------------------------------------------------------------------
# Gráfico 2: Decomposição — blocking vs disruption vs total por heurística
#            (um painel por load, 3 curvas por heurística = 9 curvas/painel)
# ---------------------------------------------------------------------------
DECOMP_STYLE = {
    # (heuristic, component): (color, linestyle, marker)
    ("legacy",  "blocking"):    ("#aaaaaa", "--",  "s"),
    ("legacy",  "disruption"):  ("#cccccc", ":",   "x"),
    ("legacy",  "total"):       ("#555555", "--",  "D"),
    ("ff_qot_aware",    "blocking"):    ("#fc8d59", "-.",  "^"),
    ("ff_qot_aware",    "disruption"):  ("#fdbf6f", ":",   "+"),
    ("ff_qot_aware",    "total"):       ("#d62728", "-.",  "D"),
    ("ff_qota_optimized", "blocking"):    ("#74add1", "-",   "o"),
    ("ff_qota_optimized", "disruption"):  ("#a6d96a", ":",   "P"),
    ("ff_qota_optimized", "total"):       ("#1a9850", "-",   "D"),
}

HEURISTIC_LABELS = {
    "legacy":  "Legada",
    "ff_qot_aware":    "FFQoT_Aware",
    "ff_qota_optimized": "FFQoTA_Otimizada",
}

fig2, axes2 = plt.subplots(1, len(available_loads), figsize=(5 * len(available_loads), 5),
                            sharey=True, dpi=200)
if len(available_loads) == 1:
    axes2 = [axes2]

for idx, load in enumerate(available_loads):
    ax = axes2[idx]
    for h in heuristics:
        sub = df_all[(df_all["heuristic"] == h) & (df_all["load"] == load)].sort_values("margin")
        if sub.empty:
            continue
        x = sub["margin"]
        hl = HEURISTIC_LABELS[h]

        bk_c, bk_ls, bk_mk = DECOMP_STYLE[(h, "blocking")]
        di_c, di_ls, di_mk = DECOMP_STYLE[(h, "disruption")]
        to_c, to_ls, to_mk = DECOMP_STYLE[(h, "total")]

        ax.plot(x, sub["blocking_rate"] * 100,
                color=bk_c, linestyle=bk_ls, marker=bk_mk, markersize=5, linewidth=1.6,
                label=f"{hl} – Bloqueio")
        ax.plot(x, sub["drop_rate"] * 100,
                color=di_c, linestyle=di_ls, marker=di_mk, markersize=5, linewidth=1.4,
                label=f"{hl} – Queda QoT")
        ax.plot(x, sub["effective_loss_rate"] * 100,
                color=to_c, linestyle=to_ls, marker=to_mk, markersize=5.5, linewidth=2.0,
                label=f"{hl} – Total")

    ax.set_title(f"Load {int(load)} Erl", pad=10, fontsize=11)
    ax.set_xlabel("Margem (dB)", labelpad=6)
    ax.set_xticks(MARGINS)
    ax.grid(True, linestyle="--", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if idx == 0:
        ax.set_ylabel("Taxa (%)", labelpad=8)

fig2.suptitle(
    "Decomposição da perda efetiva: Bloqueio × Queda QoT × Total\n"
    "(Legada × FFQoT_Aware × FFQoTA_Otimizada)",
    y=1.03, fontsize=12,
)
handles2, labels2 = axes2[0].get_legend_handles_labels()
fig2.legend(handles2, labels2,
            loc="lower center", bbox_to_anchor=(0.5, -0.22),
            ncol=3, frameon=True, framealpha=0.92, edgecolor="#cccccc",
            fontsize=8.5)

plt.tight_layout()
out2 = OUTPUT_DIR / "comparison_loss_decomposition.png"
fig2.savefig(out2, bbox_inches="tight")
print(f"Salvo: {out2.name}")
plt.close(fig2)

# ---------------------------------------------------------------------------
# Gráfico 3: Tabela de pontos disponíveis (heat-map de cobertura)
#            Mostra quais (load × margin) cada heurística tem resultado
# ---------------------------------------------------------------------------
fig3, axes3 = plt.subplots(1, 3, figsize=(12, 3.5), dpi=160)

for ax_idx, h in enumerate(heuristics):
    ax = axes3[ax_idx]
    grid = np.full((len(available_loads), len(MARGINS)), np.nan)
    sub_h = df_all[df_all["heuristic"] == h]
    for li, load in enumerate(available_loads):
        for mi, margin in enumerate(MARGINS):
            row = sub_h[(sub_h["load"] == load) & (sub_h["margin"] == margin)]
            if not row.empty:
                grid[li, mi] = float(row.iloc[0]["effective_loss_rate"]) * 100

    vmin = np.nanmin(grid) if not np.all(np.isnan(grid)) else 0
    vmax = np.nanmax(grid) if not np.all(np.isnan(grid)) else 100
    im = ax.imshow(grid, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=max(vmax, 70))
    ax.set_xticks(range(len(MARGINS)))
    ax.set_xticklabels([f"{m:g}" for m in MARGINS], fontsize=8)
    ax.set_yticks(range(len(available_loads)))
    ax.set_yticklabels([f"{int(l)}" for l in available_loads], fontsize=9)
    ax.set_xlabel("Margem (dB)", fontsize=9)
    ax.set_title(HEURISTIC_LABELS[h], fontsize=10, pad=8)
    if ax_idx == 0:
        ax.set_ylabel("Load (Erl)", fontsize=9)
    # Valores nas células
    for li in range(len(available_loads)):
        for mi in range(len(MARGINS)):
            v = grid[li, mi]
            if not np.isnan(v):
                ax.text(mi, li, f"{v:.1f}%", ha="center", va="center",
                        fontsize=7, color="black" if v < 60 else "white")
            else:
                ax.text(mi, li, "N/A", ha="center", va="center",
                        fontsize=7, color="#999999")

fig3.colorbar(im, ax=axes3[-1], shrink=0.8, label="Perda efetiva (%)")
fig3.suptitle("Mapa de Perda Efetiva — Comparação das Heurísticas", fontsize=11, y=1.04)
plt.tight_layout()
out3 = OUTPUT_DIR / "comparison_heatmap.png"
fig3.savefig(out3, bbox_inches="tight")
print(f"Salvo: {out3.name}")
plt.close(fig3)

print("\n✅ Todos os gráficos de comparação gerados!")
print(f"   Saída: {OUTPUT_DIR}")
