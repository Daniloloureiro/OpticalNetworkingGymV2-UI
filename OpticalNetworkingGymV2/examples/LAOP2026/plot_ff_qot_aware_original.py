import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# --- Carregar dados DAFF Original (results_medium) ---
daff_dir = SCRIPT_DIR / "results_medium"
daff_files = sorted(daff_dir.glob("*-medium-scenario-summary.csv"), reverse=True)
if not daff_files:
    raise FileNotFoundError("Nenhum CSV em results_medium/")
df_daff = pd.read_csv(daff_files[0])
df_daff["policy"] = df_daff["policy"].replace({"disruption_aware_first_fit": "FFQoT_Aware"})

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
colors   = {0.0: "#2ca02c", 3.0: "#d62728"}   # Verde / Vermelho
markers  = {0.0: "o", 3.0: "s"}

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=180)

# === Painel 1: Probabilidade de Bloqueio ===
ax1 = axes[0]
for margin in margins:
    sub = df_daff[df_daff["margin"] == margin].sort_values("load")
    ax1.plot(sub["load"], sub["blocking_rate"],
             color=colors[margin], marker=markers[margin],
             linestyle="-", linewidth=2.0, markersize=7,
             label=f"Margem {margin} dB")

ax1.set_yscale("log")
ax1.set_ylim(1e-4, 1.0)
import matplotlib.ticker as ticker
ax1.yaxis.set_major_formatter(ticker.LogFormatterMathtext())

ax1.set_title("Probabilidade de Bloqueio\nFFQoT_Aware (Nobel-EU, k=3, ASE+NLI)", pad=12, fontsize=11)
ax1.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax1.set_ylabel("Probabilidade de Bloqueio", labelpad=8)
ax1.set_xticks(sorted(df_daff["load"].unique()))
ax1.grid(True, linestyle="--", alpha=0.5, which="both")
ax1.legend(fontsize=9, frameon=True, edgecolor="#cccccc", loc="upper left")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

# === Painel 2: Taxa de Disrupção ===
ax2 = axes[1]
for margin in margins:
    sub = df_daff[df_daff["margin"] == margin].sort_values("load")
    ax2.plot(sub["load"], sub["disruption_rate"],
             color=colors[margin], marker=markers[margin],
             linestyle="-", linewidth=2.0, markersize=7,
             label=f"Margem {margin} dB")

ax2.set_yscale("log")
ax2.set_ylim(1e-4, 1.0)
ax2.yaxis.set_major_formatter(ticker.LogFormatterMathtext())

ax2.set_title("Taxa de Disrupção\n(Queda de canais ativos devido ao NLI)", pad=12, fontsize=11)
ax2.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax2.set_ylabel("Taxa de Disrupção", labelpad=8)
ax2.set_xticks(sorted(df_daff["load"].unique()))
ax2.grid(True, linestyle="--", alpha=0.5, which="both")
ax2.legend(fontsize=9, frameon=True, edgecolor="#cccccc", loc="upper left")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

fig.suptitle("Desempenho da Heurística FFQoT_Aware\nModelo Físico Completo (ASE+NLI) | Topologia Nobel-EU | k=3 | 1000 requisições",
             y=1.02, fontsize=12, fontweight="bold")
plt.tight_layout()

out_path_artifact = ARTIFACT_DIR / "plot_ff_qot_aware_original.png"
out_path_local = daff_dir / "plot_ff_qot_aware_original.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")

print(f"Gráfico salvo com sucesso em:\n  - Artifacts: {out_path_artifact.name}\n  - Local: {out_path_local.name}")
plt.close(fig)
