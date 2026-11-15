import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
LEGACY_DIR = SCRIPT_DIR.parent / "Resultados antigos" / "results"
SMART_DIR = SCRIPT_DIR / "results_smart"
TEST_DIR = SCRIPT_DIR / "results_test"
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# 1. Carregar dados da FF Legada
legacy_file = LEGACY_DIR / "17-05-17h33-publishable-scenario-summary.csv"
if not legacy_file.exists():
    raise FileNotFoundError(f"CSV legado não encontrado: {legacy_file}")
df_legacy = pd.read_csv(legacy_file)

# 2. Carregar dados da DAFF Original
smart_files = sorted(list(SMART_DIR.glob("*-smart-scenario-summary.csv")), reverse=True)
if not smart_files:
    raise FileNotFoundError("CSV consolidado original não encontrado em results_smart!")
df_daff = pd.read_csv(smart_files[0])
df_daff["policy"] = df_daff["policy"].replace({"disruption_aware_first_fit": "FFQoT_Aware"})

# 3. Carregar dados da DAFF Relaxada
relaxed_files = sorted(list(TEST_DIR.glob("*-relaxed-scenario-summary.csv")), reverse=True)
if not relaxed_files:
    raise FileNotFoundError("CSV consolidado relaxado não encontrado em results_test!")
df_relaxed = pd.read_csv(relaxed_files[0])
df_relaxed["policy"] = df_relaxed["policy"].replace({"relaxed_disruption_aware_first_fit": "FFQoTA_Otimizada"})

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
margin_to_analyze = 0.0

# Definições das heurísticas e colunas mapeadas
heuristics = [
    {
        "name": "First Fit Legada",
        "df": df_legacy,
        "col_bk": "blocking_rate_mean",
        "col_dp": "drop_rate_mean",
        "col_sv": "served_rate_mean"
    },
    {
        "name": "FFQoT_Aware",
        "df": df_daff,
        "col_bk": "blocking_rate",
        "col_dp": "drop_rate",
        "col_sv": "served"
    },
    {
        "name": "FFQoTA_Otimizada",
        "df": df_relaxed,
        "col_bk": "blocking_rate",
        "col_dp": "drop_rate",
        "col_sv": "served"
    }
]

# Cores padrão para cada tipo de evento (Bloqueado, Derrubado, Atendido)
event_styles = {
    "blocked": {"color": "#3b82f6", "label": "Bloqueados na Admissão"},
    "dropped": {"color": "#ef4444", "hatch": "//", "label": "Derrubados (Queda QoT)"},
    "served": {"color": "#10b981", "label": "Atendidos com Sucesso (Servidos)"}
}

# Criar a figura com 1 linha e 3 colunas (eixo Y compartilhado)
fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), sharey=True, dpi=150)

width = 0.25  # Largura de cada barra individual (cabem três lado a lado por carga)
x_positions = np.arange(len(loads))

for p_idx, heur in enumerate(heuristics):
    ax = axes[p_idx]
    df_sub = heur["df"]
    
    # Filtrar dados para a margem 0.0 dB
    sub = df_sub[df_sub["margin"] == margin_to_analyze].sort_values("load")
    sub = sub[sub["load"].isin(loads)]
    
    # Obter contagens absolutas a partir das taxas (total processado = 1000)
    blocked = np.round(sub[heur["col_bk"]].values * 1000)
    disrupted = np.round(sub[heur["col_dp"]].values * 1000)
    
    # Determinar atendidos (served): se a coluna for do consolidado do legado (taxa), multiplica por 1000
    if heur["col_sv"] == "served_rate_mean":
        served = np.round(sub[heur["col_sv"]].values * 1000)
    else:
        served = sub[heur["col_sv"]].values
    
    # Plotar as três barras lado a lado para cada carga
    # 1. Barra de Bloqueados (Esquerda, Azul)
    ax.bar(x_positions - width, blocked, width, 
           color=event_styles["blocked"]["color"], alpha=0.85, edgecolor="none")
    
    # 2. Barra de Derrubados (Centro, Vermelha, Hachurada)
    ax.bar(x_positions, disrupted, width, 
           color=event_styles["dropped"]["color"], alpha=0.85, hatch=event_styles["dropped"]["hatch"], edgecolor="#ffffff", linewidth=0.5)
    
    # 3. Barra de Atendidos/Servidos (Direita, Verde)
    ax.bar(x_positions + width, served, width, 
           color=event_styles["served"]["color"], alpha=0.85, edgecolor="none")
    
    # Adicionar rótulos numéricos no topo de cada respectiva barra
    for i in range(len(loads)):
        b_val = int(blocked[i])
        d_val = int(disrupted[i])
        s_val = int(served[i])
        
        # Rótulo de Bloqueados
        if b_val > 0:
            ax.text(x_positions[i] - width, b_val + 10, f"{b_val}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")
        else:
            ax.text(x_positions[i] - width, 12, "0", ha="center", va="bottom", fontsize=8.0, color="#777777", fontstyle="italic")
            
        # Rótulo de Derrubados
        if d_val > 0:
            ax.text(x_positions[i], d_val + 10, f"{d_val}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")
        else:
            ax.text(x_positions[i], 12, "0", ha="center", va="bottom", fontsize=8.0, color="#777777", fontstyle="italic")
            
        # Rótulo de Atendidos (Servidos)
        if s_val > 0:
            ax.text(x_positions[i] + width, s_val + 10, f"{s_val}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")
        else:
            ax.text(x_positions[i] + width, 12, "0", ha="center", va="bottom", fontsize=8.0, color="#777777", fontstyle="italic")

    # Formatação de cada subplot
    ax.set_title(heur["name"], fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=6)
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(int(l)) for l in loads])
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    if p_idx == 0:
        ax.set_ylabel("Quantidade de Serviços (de 1000)", labelpad=8)
        ax.set_ylim(0, 1050)  # Expandido até 1050 para comportar o total de 1000 conexões atendidas

# Título Principal da Figura
fig.suptitle(f"Quantidade de Serviços Rejeitados vs Derrubados vs Atendidos por Heurística\n(Margem = {margin_to_analyze:g} dB | Topologia Nobel-EU | k=3 | NLI Ativo | Total: 1000 conexões)", 
             y=0.98, fontsize=14, fontweight="bold")

# Criar elementos customizados para a legenda unificada inferior
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=event_styles["blocked"]["color"], label="Bloqueados na Admissão"),
    Patch(facecolor=event_styles["dropped"]["color"], hatch=event_styles["dropped"]["hatch"], edgecolor="#ffffff", label="Derrubados (Queda QoT)"),
    Patch(facecolor=event_styles["served"]["color"], label="Atendidos com Sucesso (Servidos)")
]
fig.legend(handles=legend_elements, loc="lower center", bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=True, edgecolor="#cccccc", fontsize=11)

plt.tight_layout()
plt.subplots_adjust(top=0.86, bottom=0.15, wspace=0.12)

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "blocking_vs_disrupted_bars_margin0.png"
out_path_local = TEST_DIR / "blocking_vs_disrupted_bars_margin0.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráfico de barras comparativo de bloqueados, derrubados e servidos gerado com sucesso!")
print(f"Arquivos salvos localmente em results_test/blocking_vs_disrupted_bars_margin0.png")
