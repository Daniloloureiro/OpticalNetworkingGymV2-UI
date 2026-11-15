import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Configuração de Estilo Premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

# Gerar amostra estatística exata do holding time configurado (Média = 3 horas)
np.random.seed(42)
mean_holding_time_hours = 3.0
num_samples = 100000
holding_times = np.random.exponential(scale=mean_holding_time_hours, size=num_samples)

# Criar a figura com 2 subplots lado a lado
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), dpi=200)

# ==========================================
# SUBPLOT 1: Histograma de Frequência Relativa (%)
# ==========================================
# Bins de 30 minutos (0.5 horas) até 15 horas
bin_width = 0.5
bins = np.arange(0, 15 + bin_width, bin_width)

# Calcular pesos para converter o histograma em porcentagem do total
weights = np.ones_like(holding_times) / len(holding_times) * 100

counts, _, patches_hist = ax1.hist(
    holding_times, bins=bins, weights=weights,
    color="#0f766e", edgecolor="#0d5c56", alpha=0.85, rwidth=0.9, label="Amostras da Simulação"
)

# Plotar a curva de densidade teórica (escalada para a largura do bin e em porcentagem)
t = np.linspace(0, 15, 1000)
pdf_theoretical = (1.0 / mean_holding_time_hours) * np.exp(-t / mean_holding_time_hours)
pdf_percentage = pdf_theoretical * bin_width * 100
ax1.plot(t, pdf_percentage, color="#b91c1c", linestyle="-", linewidth=2.2, label="Densidade Teórica (PDF)")

# Detalhes do Subplot 1
ax1.set_title("A. Distribuição de Frequência Relativa", fontsize=12, fontweight="bold", pad=12)
ax1.set_xlabel("Holding Time (horas)", labelpad=8)
ax1.set_ylabel("Porcentagem das Conexões (%)", labelpad=8)
ax1.set_xlim(-0.2, 15.2)
ax1.set_xticks(np.arange(0, 16, 2))
ax1.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.legend(frameon=True, edgecolor="#cccccc", fontsize=10)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

# Anotação da Média
ax1.axvline(mean_holding_time_hours, color="#2563eb", linestyle="--", linewidth=1.5)
ax1.text(mean_holding_time_hours + 0.2, max(pdf_percentage)*0.8, f"Média = {mean_holding_time_hours:.1f}h\n(10.800 s)", 
         color="#2563eb", fontweight="bold", fontsize=9.5)


# ==========================================
# SUBPLOT 2: Função de Distribuição Acumulada (CDF) (%)
# ==========================================
# CDF Empírica
sorted_times = np.sort(holding_times)
cdf_empirical = np.arange(1, len(sorted_times) + 1) / len(sorted_times) * 100

# CDF Teórica
cdf_theoretical = (1 - np.exp(-t / mean_holding_time_hours)) * 100

ax2.plot(sorted_times, cdf_empirical, color="#1e3a8a", linewidth=2.5, label="CDF Empírica (Simulação)", clip_on=False)
ax2.plot(t, cdf_theoretical, color="#ff7f0e", linestyle="--", linewidth=1.8, label="CDF Teórica ($1 - e^{-t/H}$)")

# Detalhes do Subplot 2
ax2.set_title("B. Função de Distribuição Acumulada (CDF)", fontsize=12, fontweight="bold", pad=12)
ax2.set_xlabel("Holding Time (horas)", labelpad=8)
ax2.set_ylabel("Porcentagem Acumulada (%)", labelpad=8)
ax2.set_xlim(-0.2, 15.2)
ax2.set_ylim(-2, 102)
ax2.set_xticks(np.arange(0, 16, 2))
ax2.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax2.grid(True, linestyle="--", alpha=0.5)
ax2.legend(frameon=True, edgecolor="#cccccc", fontsize=10, loc="lower right")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

# Anotação do ponto da Média na CDF (63.2%)
percent_at_mean = (1 - np.exp(-1)) * 100
ax2.plot([mean_holding_time_hours, mean_holding_time_hours], [-5, percent_at_mean], color="#2563eb", linestyle=":", linewidth=1.2)
ax2.plot([-1, mean_holding_time_hours], [percent_at_mean, percent_at_mean], color="#2563eb", linestyle=":", linewidth=1.2)
ax2.plot(mean_holding_time_hours, percent_at_mean, "o", color="#2563eb", markersize=6)
ax2.text(mean_holding_time_hours + 0.3, percent_at_mean - 6, f"{percent_at_mean:.1f}% das conexões\nduram < {mean_holding_time_hours:.1f}h", 
         color="#2563eb", fontweight="bold", fontsize=9.5)

# Título Geral
fig.suptitle("Distribuição Estatística do Tempo de Retenção (Holding Time)\n"
             "Simulação Estocástica de Poisson | Média de Retenção (H) = 3.0 horas (10.800 s)", 
             y=0.98, fontsize=14, fontweight="bold", color="#0f172a")

plt.tight_layout()
plt.subplots_adjust(top=0.85)

# Salvar gráficos
out_path_artifact = ARTIFACT_DIR / "holding_time_distribution.png"
out_path_local = SCRIPT_DIR / "results_test" / "holding_time_distribution.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráficos de distribuição do holding time gerados com sucesso!")
print(f"Salvo localmente em: {out_path_local}")
print(f"Salvo nos artefatos em: {out_path_artifact}")
