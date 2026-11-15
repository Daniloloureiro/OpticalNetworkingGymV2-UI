import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
test_dir = SCRIPT_DIR / "results_test"
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Encontrar o CSV consolidado mais recente do DAFF Relaxada em results_test
csv_files = sorted(list(test_dir.glob("*-relaxed-scenario-summary.csv")), reverse=True)
if not csv_files:
    raise FileNotFoundError("Nenhum CSV consolidado *-relaxed-scenario-summary.csv encontrado em results_test!")
csv_file = csv_files[0]
print(f"Lendo dados de: {csv_file.name}")
df = pd.read_csv(csv_file).sort_values(by=["load", "margin"])

# Configurações de estilo premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

loads = [250.0, 275.0, 300.0]
margins = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# Cores e estilos para as cargas
load_styles = {
    250.0: {"color": "#1f77b4", "marker": "o", "linestyle": "-", "label": "Carga = 250 Erl"},
    275.0: {"color": "#2ca02c", "marker": "s", "linestyle": "-", "label": "Carga = 275 Erl"},
    300.0: {"color": "#d62728", "marker": "^", "linestyle": "-", "label": "Carga = 300 Erl"}
}

# Cores e estilos para as margens selecionadas
margin_styles = {
    0.0: {"color": "#3182bd", "marker": "o", "linestyle": "-", "label": "Margem = 0.0 dB"},
    1.0: {"color": "#31a354", "marker": "s", "linestyle": "-", "label": "Margem = 1.0 dB"},
    2.0: {"color": "#fd8d3c", "marker": "d", "linestyle": "-", "label": "Margem = 2.0 dB"},
    3.0: {"color": "#de2d26", "marker": "^", "linestyle": "-", "label": "Margem = 3.0 dB"}
}

# ===========================================================================
# GRÁFICO 1: PB vs Margem de Admissão (Apenas Escala Logarítmica 10^-3 a 10^1)
# ===========================================================================
fig1, ax1 = plt.subplots(figsize=(8.0, 5.8), dpi=220)
fig1.patch.set_facecolor("#fafafa")
ax1.set_facecolor("#ffffff")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.grid(True, which="both", linestyle="--", alpha=0.35)

ax1.set_title("Probabilidade de Bloqueio vs Margem de Admissão (Escala Logarítmica)\nFFQoTA_Otimizada (Cargas Altas | Nobel-EU | k=3)", pad=14, fontsize=11, fontweight="bold")
ax1.set_xlabel("Margem de Admissão (dB)", labelpad=8)
ax1.set_ylabel("Probabilidade de Bloqueio (Fração)", labelpad=8)
ax1.set_xticks(margins)
ax1.set_xticklabels([f"{m:g}" for m in margins])

for load in loads:
    sub = df[df["load"] == load].sort_values("margin")
    x = sub["margin"]
    y = sub["blocking_rate"]
    st = load_styles[load]
    
    # Tratamento para PB zero: plota no limite inferior (1e-3) para continuidade da escala log
    y_log = np.where(y == 0, 1e-3, y)
    ax1.plot(x, y_log, **st, linewidth=2.0, markersize=7)

ax1.set_yscale("log")
ax1.set_ylim(10**-3, 10**1)
ax1.legend(title="Carga de Tráfego", frameon=True, edgecolor="#cccccc")

plt.tight_layout()

# Salvar Gráfico 1
out_path1_artifact = ARTIFACT_DIR / "blocking_probability_qota_vs_margin.png"
out_path1_local = test_dir / "blocking_probability_qota_vs_margin.png"
fig1.savefig(out_path1_artifact, bbox_inches="tight")
fig1.savefig(out_path1_local, bbox_inches="tight")
plt.close(fig1)


# ===========================================================================
# GRÁFICO 2: PB vs Carga de Tráfego (Apenas Escala Logarítmica 10^-3 a 10^1)
# ===========================================================================
fig2, ax2 = plt.subplots(figsize=(8.0, 5.8), dpi=220)
fig2.patch.set_facecolor("#fafafa")
ax2.set_facecolor("#ffffff")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.grid(True, which="both", linestyle="--", alpha=0.35)

ax2.set_title("Probabilidade de Bloqueio vs Carga de Tráfego (Escala Logarítmica)\nFFQoTA_Otimizada (Cargas Altas | Nobel-EU | k=3)", pad=14, fontsize=11, fontweight="bold")
ax2.set_xlabel("Carga de Tráfego (Erlangs)", labelpad=8)
ax2.set_ylabel("Probabilidade de Bloqueio (Fração)", labelpad=8)
ax2.set_xticks(loads)
ax2.set_xticklabels([f"{int(l)}" for l in loads])

selected_margins = [0.0, 1.0, 2.0, 3.0]
for margin_val in selected_margins:
    sub = df[df["margin"] == margin_val].sort_values("load")
    x = sub["load"]
    y = sub["blocking_rate"]
    st = margin_styles[margin_val]
    
    # Tratamento para PB zero
    y_log = np.where(y == 0, 1e-3, y)
    ax2.plot(x, y_log, **st, linewidth=2.0, markersize=7)

ax2.set_yscale("log")
ax2.set_ylim(10**-3, 10**1)
ax2.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc")

plt.tight_layout()

# Salvar Gráfico 2
out_path2_artifact = ARTIFACT_DIR / "blocking_probability_qota_vs_load.png"
out_path2_local = test_dir / "blocking_probability_qota_vs_load.png"
fig2.savefig(out_path2_artifact, bbox_inches="tight")
fig2.savefig(out_path2_local, bbox_inches="tight")
plt.close(fig2)

print("Gráficos de PB em fração absoluta (Escala 10^-3 a 10^1) gerados com sucesso!")
