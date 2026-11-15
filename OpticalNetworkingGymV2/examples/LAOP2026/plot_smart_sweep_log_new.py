import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
SMART_DIR = SCRIPT_DIR / "results_smart"

# Carregar o CSV mais recente da varredura inteligente
smart_csvs = sorted(list(SMART_DIR.glob("*-smart-scenario-summary.csv")), reverse=True)
if not smart_csvs:
    raise FileNotFoundError("Nenhum CSV encontrado em results_smart/")
smart_csv = smart_csvs[0]
print(f"Lendo dados de: {smart_csv.name}")

df = pd.read_csv(smart_csv).sort_values(by=["load", "margin"])

loads = sorted(df["load"].unique())
margins = sorted(df["margin"].unique())

# Configurações globais do Matplotlib para visual premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

fig, ax = plt.subplots(figsize=(10, 6), dpi=200)

# Paleta de cores baseada nas margens
colors = plt.cm.viridis([i / len(margins) for i in range(len(margins))])

for i, margin in enumerate(margins):
    sub = df[df["margin"] == margin].sort_values("load")
    x = sub["load"]
    y = sub["blocking_rate"]
    
    # Adicionando um pequeno delta (1e-5) para que BP = 0 apareça no gráfico logarítmico
    y_plot = [max(val, 1e-4) for val in y]
    
    ax.plot(
        x, y_plot,
        label=f"Margem = {margin:g} dB",
        color=colors[i],
        marker="o",
        linestyle="-",
        linewidth=2.0,
        markersize=6,
        clip_on=False
    )
    
    # Anotações para a carga mais baixa
    for val_x, val_y in zip(x, y):
        if val_x == loads[0] or val_x == loads[-1]:
            ax.text(val_x, max(val_y, 1e-4), f"{val_y*100:.1f}%", 
                    ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#555555")

ax.set_title("Probabilidade de Bloqueio vs Carga (Com Lançamento Ajustado para 4.0 dBm)\nTopologia Nobel-EU | k=3 | Escala Logarítmica", pad=12, fontsize=12, fontweight="bold")
ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax.set_ylabel("Probabilidade de Bloqueio (Escala Log)", labelpad=8)
ax.set_xticks(loads)
ax.set_xticklabels([f"{l:g}" for l in loads])
ax.set_yscale('log')
ax.set_ylim(5e-5, 1.0)
ax.grid(True, which="both", linestyle="--", alpha=0.45)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="lower right")

ax.get_yaxis().set_major_formatter(ticker.LogFormatterMathtext())

# Salvar
output_path = SCRIPT_DIR / "smart_blocking_log_corrected.png"
fig.savefig(output_path, bbox_inches="tight")
print(f"Gráfico salvo em: {output_path.name}")
plt.close(fig)
