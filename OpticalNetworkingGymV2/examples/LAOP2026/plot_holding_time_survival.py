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

# Gerar amostra de holding times (Média = 3 horas)
np.random.seed(42)
mean_holding_time_hours = 3.0
num_samples = 100000
holding_times = np.random.exponential(scale=mean_holding_time_hours, size=num_samples)

# Ordenar os tempos de retenção para calcular a CCDF empírica (função de sobrevivência)
sorted_times = np.sort(holding_times)
# Fração de conexões que duram pelo menos o tempo t
survival_empirical = (1.0 - np.arange(0, len(sorted_times)) / len(sorted_times)) * 100

# Curva teórica
t = np.linspace(0, 22, 1000)
survival_theoretical = np.exp(-t / mean_holding_time_hours) * 100

# Pontos-chave de interesse amostrados
points_of_interest = [
    {"label": "Mediana (50%)", "percent": 50.0, "time": np.percentile(holding_times, 50), "color": "#16a34a"},
    {"label": "Média (36.8%)", "percent": np.exp(-1)*100, "time": mean_holding_time_hours, "color": "#2563eb"},
    {"label": "Restam 10%", "percent": 10.0, "time": np.percentile(holding_times, 90), "color": "#d97706"},
    {"label": "Restam 5%", "percent": 5.0, "time": np.percentile(holding_times, 95), "color": "#7c3aed"},
    {"label": "Restam 1% (Quase Zero)", "percent": 1.0, "time": np.percentile(holding_times, 99), "color": "#b91c1c"},
    {"label": "Restam 0.1% (Zero na prática)", "percent": 0.1, "time": np.percentile(holding_times, 99.9), "color": "#475569"},
]

# Criar figura com 2 subplots lado a lado
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5), dpi=200)

# ==========================================
# PAINEL A: Escala Linear (Visão da curva clássica de queda)
# ==========================================
ax1.plot(sorted_times, survival_empirical, color="#0f766e", linewidth=2.5, label="Amostras da Simulação", clip_on=False)
ax1.plot(t, survival_theoretical, color="#ff7f0e", linestyle="--", linewidth=1.5, label="Decaimento Teórico ($100 \\times e^{-t/H}$)")

# Destacar os pontos-chave de interesse principais (Mediana e Média) no Painel A
for pt in points_of_interest[:3]:
    p_time = pt["time"]
    p_pct = pt["percent"]
    color = pt["color"]
    
    # Linhas de guia
    ax1.plot([p_time, p_time], [-5, p_pct], color=color, linestyle=":", linewidth=1.2)
    ax1.plot([-2, p_time], [p_pct, p_pct], color=color, linestyle=":", linewidth=1.2)
    ax1.plot(p_time, p_pct, "o", color=color, markersize=7)
    
    # Texto
    ax1.text(p_time + 0.3, p_pct + 1.5, f"{pt['label']}: {p_time:.2f}h", 
             color=color, fontweight="bold", fontsize=9)

# Detalhes Painel A
ax1.set_title("A. Decaimento de Conexões Ativas (Escala Linear)", fontsize=12, fontweight="bold", pad=12)
ax1.set_xlabel("Holding Time (horas)", labelpad=8)
ax1.set_ylabel("Conexões Ainda Ativas (%)", labelpad=8)
ax1.set_xlim(-0.2, 22.2)
ax1.set_ylim(-3, 103)
ax1.set_xticks(np.arange(0, 23, 2))
ax1.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.legend(frameon=True, edgecolor="#cccccc", fontsize=10)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)


# ==========================================
# PAINEL B: Escala Logarítmica (Foco na cauda onde cai para zero)
# ==========================================
ax2.plot(sorted_times, survival_empirical, color="#0f766e", linewidth=2.5, label="Amostras da Simulação", clip_on=False)
ax2.plot(t, survival_theoretical, color="#ff7f0e", linestyle="--", linewidth=1.5, label="Decaimento Teórico")

# Destacar os pontos-chave de transição para zero (10%, 5%, 1%, 0.1%)
for pt in points_of_interest[2:]:
    p_time = pt["time"]
    p_pct = pt["percent"]
    color = pt["color"]
    
    # Linhas de guia
    ax2.plot([p_time, p_time], [1e-3, p_pct], color=color, linestyle=":", linewidth=1.2)
    ax2.plot([-2, p_time], [p_pct, p_pct], color=color, linestyle=":", linewidth=1.2)
    ax2.plot(p_time, p_pct, "o", color=color, markersize=7)
    
    # Texto (ajustar deslocamento para leitura em escala log Y)
    offset_factor = 1.25 if p_pct > 1.0 else 1.45
    ax2.text(p_time + 0.3, p_pct * offset_factor, f"{pt['label']}: {p_time:.2f}h", 
             color=color, fontweight="bold", fontsize=9)

# Detalhes Painel B
ax2.set_title("B. Decaimento da Cauda para Zero (Escala Log Y)", fontsize=12, fontweight="bold", pad=12)
ax2.set_xlabel("Holding Time (horas)", labelpad=8)
ax2.set_ylabel("Conexões Ainda Ativas (Escala Log %)", labelpad=8)
ax2.set_yscale('log')
ax2.set_xlim(-0.2, 22.2)
ax2.set_ylim(0.05, 120)  # De 0.05% a 120%
ax2.set_xticks(np.arange(0, 23, 2))

# Formatar ticks do eixo Y logarítmico para exibir porcentagens amigáveis
ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%g%%"))
ax2.yaxis.set_minor_formatter(mticker.NullFormatter())
ax2.grid(True, which="both", linestyle="--", alpha=0.5)
ax2.legend(frameon=True, edgecolor="#cccccc", fontsize=10)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

# Título Principal
fig.suptitle("Curva de Sobrevivência de Conexões: Transição das Conexões Ativas para Zero\n"
             "Simulação de Poisson | Tempo Médio de Posse (H) = 3.0 horas (10.800 s)", 
             y=0.98, fontsize=14, fontweight="bold", color="#0f172a")

plt.tight_layout()
plt.subplots_adjust(top=0.86)

# Salvar gráficos
out_path_artifact = ARTIFACT_DIR / "holding_time_survival.png"
out_path_local = SCRIPT_DIR / "results_test" / "holding_time_survival.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráficos de sobrevivência (decaimento para zero) gerados com sucesso!")
print(f"Salvo localmente em: {out_path_local}")
print(f"Salvo nos artefatos em: {out_path_artifact}")
