import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Dados das modulações (extraídos de defaults.py)
modulations = ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"]
se_values = [1, 2, 3, 4, 5, 6]  # Eficiência Espectral (bit/s/Hz)
osnr_thresholds = [3.7193, 6.7296, 10.8454, 13.2406, 16.1609, 19.0135]  # Limiar OSNR (dB)
inband_xt = [-14.0, -17.0, -20.0, -23.0, -26.0, -29.0]  # Diafonia em banda (dB)

# Configuração de estilo premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

fig, ax = plt.subplots(figsize=(10, 6.5), dpi=200)

# Cor de destaque gradual para os pontos
colors = ["#2563eb", "#0d9488", "#059669", "#d97706", "#dc2626", "#7c3aed"]

# 1. Plotar a linha de tendência suave
ax.plot(osnr_thresholds, se_values, color="#94a3b8", linestyle="-", linewidth=1.5, zorder=1)

# 2. Plotar os pontos de cada formato de modulação
for idx, (osnr, se, mod, color) in enumerate(zip(osnr_thresholds, se_values, modulations, colors)):
    ax.scatter(osnr, se, color=color, s=120, edgecolors="#ffffff", linewidths=1.5, label=mod, zorder=3)
    
    # Adicionar anotações ao lado de cada ponto
    ax.text(osnr - 0.2, se + 0.15, f"{mod}", ha="right", va="bottom", 
            fontsize=9.5, fontweight="bold", color=color,
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'))

# Ajustes de eixos
ax.set_xlabel("Limiar Mínimo de OSNR Requerido (dB)", labelpad=10, fontweight="bold", color="#1e293b")
ax.set_ylabel("Eficiência Espectral (bit/s/Hz)", labelpad=10, fontweight="bold", color="#1e293b")
ax.set_title("Características dos Formatos de Modulação do Simulador\n(Relação entre Eficiência Espectral e Limiar Mínimo de OSNR)", 
             pad=15, fontsize=13, fontweight="bold", color="#0f172a")

# Configurar limites e ticks
ax.set_xlim(2, 21)
ax.set_ylim(0.5, 7.0)
ax.set_yticks(se_values)
ax.set_xticks(np.arange(2, 22, 2))
ax.grid(True, linestyle="--", alpha=0.5)

# Remover spines desnecessárias
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# 3. Adicionar tabela descritiva embutida no plot (canto inferior direito)
table_data = []
for m, se, osnr, xt in zip(modulations, se_values, osnr_thresholds, inband_xt):
    table_data.append([m, f"{se} b/s/Hz", f"{osnr:.2f} dB", f"{xt:.1f} dB"])

columns = ["Modulação", "Eficiência", "Limiar OSNR", "Inband XT"]
the_table = ax.table(
    cellText=table_data,
    colLabels=columns,
    loc="lower right",
    bbox=[0.50, 0.05, 0.46, 0.35],
    cellLoc="center"
)

# Estilizar a tabela embutida
the_table.auto_set_font_size(False)
the_table.set_fontsize(8.5)
for (row, col), cell in the_table.get_celld().items():
    cell.set_edgecolor("#cbd5e1")
    if row == 0:
        cell.set_text_props(weight='bold', color='white')
        cell.set_facecolor('#475569')  # Cabeçalho cinza escuro
    else:
        cell.set_facecolor('#f8fafc')  # Fundo suave para linhas

plt.tight_layout()

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "modulation_characteristics.png"
out_path_local = SCRIPT_DIR / "results_test" / "modulation_characteristics.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráfico de características das modulações gerado com sucesso!")
print(f"Salvo localmente em results_test/modulation_characteristics.png")
