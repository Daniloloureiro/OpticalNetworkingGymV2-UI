import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "results_smart"
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Encontrar o CSV mais recente
csv_files = sorted(RESULTS_DIR.glob("*-smart-scenario-summary.csv"), reverse=True)
if not csv_files:
    raise FileNotFoundError("Nenhum CSV de resumo encontrado em results_smart/")

csv_path = csv_files[0]
print(f"Lendo dados de: {csv_path.name}")
df = pd.read_csv(csv_path)

# Estilo de plotagem
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

fig, ax = plt.subplots(figsize=(8, 5), dpi=200)

# Agrupar por carga e plotar
loads = sorted(df["load"].unique())
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
markers = ["o", "s", "^", "D", "v"]

for i, load in enumerate(loads):
    sub = df[df["load"] == load].sort_values("margin")
    ax.plot(
        sub["margin"],
        sub["effective_loss_rate"] * 100,
        label=f"Load = {load} Erl",
        color=colors[i % len(colors)],
        marker=markers[i % len(markers)],
        linestyle="-",
        linewidth=1.8,
        markersize=6,
    )

ax.set_title("Taxa de Perda Efetiva vs Margem de Admissão de QoT (Carga Reduzida)\nAlgoritmo: FFQoT_Aware ($k=3$)", pad=14, fontsize=12)
ax.set_xlabel("Margem de admissão de QoT (dB)", labelpad=8)
ax.set_ylabel("Taxa de Perda Efetiva (%)", labelpad=8)
ax.set_xticks(sorted(df["margin"].unique()))
ax.set_ylim(0, 32)
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(frameon=True, edgecolor="#cccccc", facecolor="#fafafa")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

# Salvar no diretório de artifacts
out_path = ARTIFACT_DIR / "plot_low_load.png"
fig.savefig(out_path, bbox_inches="tight")
print(f"Gráfico gerado com sucesso e salvo em: {out_path}")
