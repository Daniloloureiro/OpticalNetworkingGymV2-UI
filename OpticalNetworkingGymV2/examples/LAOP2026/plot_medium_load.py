import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "results_medium"
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Encontrar o CSV mais recente de carga média
csv_files = sorted(RESULTS_DIR.glob("*-medium-scenario-summary.csv"), reverse=True)
if not csv_files:
    raise FileNotFoundError("Nenhum CSV de resumo encontrado em results_medium/")

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

# Agrupar por carga e plotar para Margens 0.0 e 3.0
# Como temos apenas duas margens (0.0 e 3.0), podemos plotar Barras ou Linhas.
# Vamos plotar linhas que comparam a perda efetiva de acordo com o Load para as duas margens separadas.
margins = sorted(df["margin"].unique())
colors = ["#2ca02c", "#d62728"] # Verde para Margin 0.0, Vermelho para Margin 3.0
markers = ["o", "s"]

for i, margin in enumerate(margins):
    sub = df[df["margin"] == margin].sort_values("load")
    ax.plot(
        sub["load"],
        sub["effective_loss_rate"] * 100,
        label=f"Margin = {margin} dB",
        color=colors[i % len(colors)],
        marker=markers[i % len(markers)],
        linestyle="-",
        linewidth=2.0,
        markersize=7,
    )

ax.set_title("Taxa de Perda Efetiva vs Carga de Tráfego (Carga Média)\nAlgoritmo: FFQoT_Aware ($k=3$)", pad=14, fontsize=12)
ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax.set_ylabel("Taxa de Perda Efetiva (%)", labelpad=8)
ax.set_xticks(sorted(df["load"].unique()))
ax.set_ylim(0, 50)
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="upper left")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

# Salvar no diretório de artifacts
out_path = ARTIFACT_DIR / "plot_medium_load.png"
fig.savefig(out_path, bbox_inches="tight")
print(f"Gráfico de carga média gerado e salvo em: {out_path}")
