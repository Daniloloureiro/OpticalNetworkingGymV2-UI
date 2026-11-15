import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# --- Carregar dados FFQoT_Aware (results_medium) ---
daff_dir = SCRIPT_DIR / "results_medium"
daff_files = sorted(daff_dir.glob("*-medium-scenario-summary.csv"), reverse=True)
if not daff_files:
    raise FileNotFoundError("Nenhum CSV em results_medium/")
df_daff = pd.read_csv(daff_files[0])
df_daff["mode"] = "FFQoT_Aware"

# --- Carregar dados FF Legada (results_medium_ff) ---
ff_dir = SCRIPT_DIR / "results_medium_ff"
ff_files = sorted(ff_dir.glob("*-medium-ff-summary.csv"), reverse=True)
if not ff_files:
    raise FileNotFoundError("Nenhum CSV em results_medium_ff/")
df_ff = pd.read_csv(ff_files[0])
df_ff["mode"] = "FF Legada (First Fit)"

# --- Carregar dados FFQoTA_Otimizada (results_medium_relaxed) ---
relaxed_dir = SCRIPT_DIR / "results_medium_relaxed"
relaxed_files = sorted(relaxed_dir.glob("*-medium-relaxed-summary.csv"), reverse=True)
if not relaxed_files:
    raise FileNotFoundError("Nenhum CSV em results_medium_relaxed/")
df_relaxed = pd.read_csv(relaxed_files[0])
df_relaxed["mode"] = "FFQoTA_Otimizada"

# --- Estilo ---
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

margins = [0.0, 3.0]

# FFQoT_Aware: tons de verde
colors_daff = {0.0: "#2ca02c", 3.0: "#a1d99b"}
markers_daff = {0.0: "o", 3.0: "s"}

# FF Legada: tons de azul/roxo
colors_ff = {0.0: "#1f77b4", 3.0: "#9467bd"}
markers_ff = {0.0: "^", 3.0: "D"}

# FFQoTA_Otimizada: tons de laranja/vermelho
colors_relaxed = {0.0: "#ff7f0e", 3.0: "#e377c2"}
markers_relaxed = {0.0: "v", 3.0: "X"}

fig, axes = plt.subplots(1, 2, figsize=(15, 6), dpi=180)

# === Painel 1: Probabilidade de Bloqueio ===
ax1 = axes[0]
for margin in margins:
    sub_daff = df_daff[df_daff["margin"] == margin].sort_values("load")
    sub_ff   = df_ff[df_ff["margin"] == margin].sort_values("load")
    sub_relaxed = df_relaxed[df_relaxed["margin"] == margin].sort_values("load")

    ax1.plot(sub_daff["load"], sub_daff["blocking_rate"],
             color=colors_daff[margin], marker=markers_daff[margin],
             linestyle="-", linewidth=2.0, markersize=7,
             label=f"FFQoT_Aware – Margem {margin} dB")
    ax1.plot(sub_ff["load"], sub_ff["blocking_rate"],
             color=colors_ff[margin], marker=markers_ff[margin],
             linestyle="--", linewidth=1.8, markersize=7,
             label=f"FF Legada – Margem {margin} dB")
    ax1.plot(sub_relaxed["load"], sub_relaxed["blocking_rate"],
             color=colors_relaxed[margin], marker=markers_relaxed[margin],
             linestyle="-.", linewidth=1.8, markersize=7,
             label=f"FFQoTA_Otimizada – Margem {margin} dB")

ax1.set_yscale("log")
ax1.set_ylim(1e-4, 1.0)
import matplotlib.ticker as ticker
ax1.yaxis.set_major_formatter(ticker.LogFormatterMathtext())

ax1.set_title("Probabilidade de Bloqueio na Admissão\nFFQoT_Aware vs FF Legada vs FFQoTA_Otimizada (Nobel-EU, k=3, NLI)", pad=12, fontsize=11)
ax1.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax1.set_ylabel("Probabilidade de Bloqueio", labelpad=8)
ax1.set_xticks(sorted(df_daff["load"].unique()))
ax1.grid(True, linestyle="--", alpha=0.5, which="both")
ax1.legend(fontsize=8.0, frameon=True, edgecolor="#cccccc", loc="lower right")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

# === Painel 2: Taxa de Disrupção ===
ax2 = axes[1]
for margin in margins:
    sub_ff = df_ff[df_ff["margin"] == margin].sort_values("load")
    sub_relaxed = df_relaxed[df_relaxed["margin"] == margin].sort_values("load")

    # Plot FF Legada
    ax2.plot(sub_ff["load"], sub_ff["disruption_rate"],
             color=colors_ff[margin], marker=markers_ff[margin],
             linestyle="--", linewidth=1.8, markersize=7,
             label=f"FF Legada – Margem {margin} dB")
    
    # Plot FFQoTA_Otimizada
    ax2.plot(sub_relaxed["load"], sub_relaxed["disruption_rate"],
             color=colors_relaxed[margin], marker=markers_relaxed[margin],
             linestyle="-.", linewidth=1.8, markersize=7,
             label=f"FFQoTA_Otimizada – Margem {margin} dB")

# FFQoT_Aware tem 0% de disrupções (estritamente 0)
ax2.plot([], [], color=colors_daff[0.0], linestyle="-", linewidth=2.0, label="FFQoT_Aware – 0% disrupções (ambas margens)")

ax2.set_yscale("log")
ax2.set_ylim(1e-4, 1.0)
ax2.yaxis.set_major_formatter(ticker.LogFormatterMathtext())

ax2.set_title("Taxa de Disrupção de Serviços Ativos\n(Queda de canais devido ao efeito do NLI)", pad=12, fontsize=11)
ax2.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax2.set_ylabel("Taxa de Disrupção (fração)", labelpad=8)
ax2.set_xticks(sorted(df_ff["load"].unique()))
ax2.grid(True, linestyle="--", alpha=0.5, which="both")
ax2.legend(fontsize=8.0, frameon=True, edgecolor="#cccccc", loc="upper left")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

fig.suptitle("Comparação de Desempenho: FFQoT_Aware vs FF Legada vs FFQoTA_Otimizada\nRestrição de QoT com NLI Ativo | Topologia Nobel-EU | k=3 | 1000 requisições",
             y=1.02, fontsize=12, fontweight="bold")
plt.tight_layout()

out_path_artifact = ARTIFACT_DIR / "plot_daff_vs_ff_comparison_new.png"
out_path_local = relaxed_dir / "plot_daff_vs_ff_comparison_new.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")

print(f"Gráfico salvo com sucesso em:\n  - Artifacts: {out_path_artifact.name}\n  - Local: {out_path_local.name}")
plt.close(fig)
