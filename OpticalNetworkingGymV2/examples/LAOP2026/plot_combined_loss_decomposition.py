import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.ticker as ticker
import matplotlib.lines as mlines

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
df_legacy = pd.read_csv(legacy_file).sort_values(by=["load", "margin"])

# 2. Carregar dados da DAFF Original
smart_files = sorted(list(SMART_DIR.glob("*-smart-scenario-summary.csv")), reverse=True)
if not smart_files:
    raise FileNotFoundError("CSV consolidado original não encontrado em results_smart!")
df_daff = pd.read_csv(smart_files[0]).sort_values(by=["load", "margin"])
df_daff["policy"] = df_daff["policy"].replace({"disruption_aware_first_fit": "FFQoT_Aware"})

# 3. Carregar dados da DAFF Relaxada
relaxed_files = sorted(list(TEST_DIR.glob("*-relaxed-scenario-summary.csv")), reverse=True)
if not relaxed_files:
    raise FileNotFoundError("CSV consolidado relaxado não encontrado em results_test!")
df_relaxed = pd.read_csv(relaxed_files[0]).sort_values(by=["load", "margin"])
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
margins = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# Cores e marcadores padrão para as componentes da decomposição
comp_styles = {
    "blocking": {"color": "#3b82f6", "marker": "s", "linestyle": "--", "label": "Bloqueio Admissão"},
    "disruption": {"color": "#ef4444", "marker": "x", "linestyle": ":", "label": "Queda QoT (Derrubado)"},
    "total": {"color": "#10b981", "marker": "o", "linestyle": "-", "label": "Perda Efetiva Total"}
}

heuristics = [
    {
        "name": "First Fit Legada",
        "df": df_legacy,
        "col_bk": "blocking_rate_mean",
        "col_dp": "drop_rate_mean",
        "col_tot": "effective_loss_rate_mean"
    },
    {
        "name": "FFQoT_Aware",
        "df": df_daff,
        "col_bk": "blocking_rate",
        "col_dp": "drop_rate",
        "col_tot": "effective_loss_rate"
    },
    {
        "name": "FFQoTA_Otimizada",
        "df": df_relaxed,
        "col_bk": "blocking_rate",
        "col_dp": "drop_rate",
        "col_tot": "effective_loss_rate"
    }
]

# Criar um grid de 3 linhas (uma para cada carga) por 3 colunas (uma para cada heurística)
fig, axes = plt.subplots(3, 3, figsize=(18, 14), sharex=True, sharey=True, dpi=150)

for row_idx, load in enumerate(loads):
    for col_idx, heur in enumerate(heuristics):
        ax = axes[row_idx, col_idx]
        df_sub = heur["df"]
        
        # Filtrar dados para a carga e heurística específicas
        sub = df_sub[df_sub["load"] == load].sort_values("margin")
        x = sub["margin"]
        
        # Plotar as três curvas da decomposição
        ax.plot(x, sub[heur["col_bk"]] * 100, **comp_styles["blocking"], linewidth=1.6, markersize=5)
        ax.plot(x, sub[heur["col_dp"]] * 100, **comp_styles["disruption"], linewidth=1.4, markersize=6)
        ax.plot(x, sub[heur["col_tot"]] * 100, **comp_styles["total"], linewidth=2.2, markersize=6)
        
        # Rótulos de dados no topo de cada ponto da curva Total
        for val_x, val_y in zip(x, sub[heur["col_tot"]].values):
            ax.text(val_x, val_y * 100 + 1.5, f"{val_y*100:.1f}%", 
                     ha="center", va="bottom", fontsize=8.0, color="#333333")
            
        # Títulos das colunas (apenas na primeira linha)
        if row_idx == 0:
            ax.set_title(heur["name"], fontsize=12, fontweight="bold", pad=12)
            
        # Rótulos das linhas no eixo Y (apenas na primeira coluna)
        if col_idx == 0:
            ax.set_ylabel(f"Carga: {int(load)} Erl\nTaxa (%)", fontsize=11, fontweight="bold", labelpad=8)
            
        # Rótulos do eixo X (apenas na última linha)
        if row_idx == 2:
            ax.set_xlabel("Margem (dB)", labelpad=6)
            ax.set_xticks(margins)
            ax.set_xticklabels([f"{m:g}" for m in margins])
            
        ax.grid(True, linestyle="--", alpha=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

# Ajuste fino do limite do eixo Y para todas as figuras (compartilhado)
axes[0, 0].set_ylim(-5, 85)

# Título Principal
fig.suptitle("Decomposição da Perda Efetiva por Heurística e Carga de Tráfego\n(Bloqueio na Admissão vs Queda QoT devido ao NLI | Nobel-EU | k=3 | NLI Ativo)", 
             y=0.98, fontsize=14, fontweight="bold")

# Legenda unificada na parte inferior
handles2 = [
    mlines.Line2D([], [], color="#3b82f6", marker="s", linestyle="--", label="Bloqueio na Admissão"),
    mlines.Line2D([], [], color="#ef4444", marker="x", linestyle=":", label="Queda QoT (Derrubados)"),
    mlines.Line2D([], [], color="#10b981", marker="o", linestyle="-", linewidth=2.2, label="Perda Efetiva Total")
]
fig.legend(handles=handles2, loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=3, frameon=True, edgecolor="#cccccc", fontsize=11)

plt.tight_layout()
plt.subplots_adjust(top=0.90, bottom=0.10, hspace=0.15, wspace=0.10)

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "combined_smart_loss_decomposition.png"
out_path_local = TEST_DIR / "combined_smart_loss_decomposition.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráficos combinados de decomposição de perda gerados com sucesso!")
print(f"Arquivos salvos localmente em results_test/combined_smart_loss_decomposition.png")
