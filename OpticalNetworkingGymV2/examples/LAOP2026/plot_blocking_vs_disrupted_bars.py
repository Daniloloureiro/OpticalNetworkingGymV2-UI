import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Encontrar os CSVs consolidados mais recentes de hoje (17-06)
daff_csv = sorted(list((SCRIPT_DIR / "results_medium").glob("*-medium-scenario-summary.csv")), reverse=True)[0]
ff_csv = sorted(list((SCRIPT_DIR / "results_medium_ff").glob("*-medium-ff-summary.csv")), reverse=True)[0]
relaxed_csv = sorted(list((SCRIPT_DIR / "results_medium_relaxed").glob("*-medium-relaxed-summary.csv")), reverse=True)[0]

print(f"Lendo DAFF de: {daff_csv.name}")
print(f"Lendo FF de: {ff_csv.name}")
print(f"Lendo Relaxada de: {relaxed_csv.name}")

df_daff = pd.read_csv(daff_csv).sort_values(by=["load", "margin"])
df_daff["policy"] = df_daff["policy"].replace({"disruption_aware_first_fit": "FFQoT_Aware"})
df_ff = pd.read_csv(ff_csv).sort_values(by=["load", "margin"])
df_relaxed = pd.read_csv(relaxed_csv).sort_values(by=["load", "margin"])
df_relaxed["policy"] = df_relaxed["policy"].replace({"relaxed_disruption_aware_first_fit": "FFQoTA_Otimizada"})

# Configurações de estilo premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 10,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

# Grid 1x2 (Margem 0.0 dB e Margem 3.0 dB)
fig, axes = plt.subplots(1, 2, figsize=(16, 7.5), dpi=150)

loads = sorted(df_daff["load"].unique())
margins = [0.0, 3.0]

# Definições das políticas
policies = {
    "FFQoT_Aware": {"df": df_daff, "color": "#2ca02c", "label": "FFQoT_Aware"},
    "FFQoTA_Otimizada": {"df": df_relaxed, "color": "#1f77b4", "label": "FFQoTA_Otimizada"},
    "FF Legada": {"df": df_ff, "color": "#d62728", "label": "FF Legada"}
}

width = 0.25  # Largura da barra
x_positions = np.arange(len(loads))

# Configurações do hatch para representar "Derrubados"
# Sólido = Bloqueados na Admissão
# Hachurado = Derrubados (Disrompidos)
for idx, margin in enumerate(margins):
    ax = axes[idx]
    
    for p_idx, (p_name, p_info) in enumerate(policies.items()):
        df_sub = p_info["df"][p_info["df"]["margin"] == margin].sort_values("load")
        
        # Obter valores de bloqueados e disrompidos (de 1000 conexões)
        blocked = df_sub["rejected_by_agent"].values
        disrupted = df_sub["disrupted"].values
        
        # Posições de plotagem agrupadas
        pos = x_positions + (p_idx - 1) * width
        
        # Barra de Bloqueados (sólida)
        rects_b = ax.bar(pos, blocked, width, 
                         color=p_info["color"], alpha=0.85, edgecolor="none")
        
        # Barra de Derrubados (empilhada por cima com hachura '//')
        rects_d = ax.bar(pos, disrupted, width, bottom=blocked, 
                         color=p_info["color"], alpha=0.85, hatch="//", edgecolor="#ffffff", linewidth=0.5)
        
        # Adicionar rótulos numéricos
        for i in range(len(loads)):
            b_val = int(blocked[i])
            d_val = int(disrupted[i])
            total = b_val + d_val
            
            # Escrever o total no topo de cada barra
            if total > 0:
                ax.text(pos[i], total + 8, f"{total}", ha="center", va="bottom", fontsize=8.0, fontweight="bold", color="#333333")
            
            # Se houver disrupções, escrever o valor de disrupções em itálico e branco dentro da parte hachurada
            if d_val > 15:
                ax.text(pos[i], b_val + (d_val / 2), f"d:{d_val}", ha="center", va="center", fontsize=7.5, color="#ffffff", fontweight="bold")
            elif d_val > 0:
                ax.text(pos[i], b_val + d_val + 1, f"d:{d_val}", ha="center", va="bottom", fontsize=7.0, color=p_info["color"], fontstyle="italic")

    # Formatação de cada painel
    ax.set_title(f"Margem de Admissão: {margin:g} dB", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
    ax.set_ylabel("Quantidade de Serviços (de 1000)", labelpad=8)
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(int(l)) for l in loads])
    ax.set_ylim(0, 580)
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

# Título Geral
fig.suptitle("Comparativo de Desempenho Físico: Serviços Rejeitados vs Derrubados (Disrompidos)\n(Composição das Barras: Parte Sólida = Bloqueado na Admissão | Parte Hachurada (//) = Derrubado)", 
             y=0.98, fontsize=14, fontweight="bold")

# Criar elementos customizados para a legenda única
from matplotlib.patches import Patch
legend_elements = [
    # Legenda das políticas
    Patch(facecolor="#2ca02c", label="FFQoT_Aware"),
    Patch(facecolor="#1f77b4", label="FFQoTA_Otimizada"),
    Patch(facecolor="#d62728", label="FF Legada"),
    # Legenda da composição da barra
    Patch(facecolor="#7f7f7f", label="Bloqueado na Admissão (Sólido)"),
    Patch(facecolor="#7f7f7f", hatch="//", edgecolor="#ffffff", label="Derrubado / Disrompido (Hachurado //)")
]

fig.legend(handles=legend_elements, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=5, frameon=True, edgecolor="#cccccc", fontsize=10)

plt.tight_layout()
plt.subplots_adjust(top=0.88, bottom=0.12, wspace=0.18)

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "blocking_vs_disrupted_bars.png"
out_path_local = SCRIPT_DIR / "results_medium" / "blocking_vs_disrupted_bars.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")

print(f"Gráfico salvo com sucesso em:\n  - Artifacts: {out_path_artifact.name}\n  - Local: {out_path_local.name}")
plt.close(fig)
