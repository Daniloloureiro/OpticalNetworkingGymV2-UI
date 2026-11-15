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
margins_to_analyze = [0.0, 3.0]

# Cores e estilos de cada margem analisada (Azul para Margem 0.0 dB, Laranja para Margem 3.0 dB)
margin_styles = {
    0.0: {"color": "#1f77b4", "marker": "o", "linestyle": "-", "label": "Margem = 0.0 dB"},
    3.0: {"color": "#ff7f0e", "marker": "s", "linestyle": "-", "label": "Margem = 3.0 dB"}
}

# Criar a figura com 1 linha e 3 colunas (eixo Y compartilhado)
fig, axes = plt.subplots(1, 3, figsize=(18, 6.0), sharey=True, dpi=150)

heuristics = [
    {"name": "First Fit Legada", "df": df_legacy, "col_y": "effective_loss_rate_mean"},
    {"name": "FFQoT_Aware", "df": df_daff, "col_y": "effective_loss_rate"},
    {"name": "FFQoTA_Otimizada", "df": df_relaxed, "col_y": "effective_loss_rate"}
]

for idx, heur in enumerate(heuristics):
    ax = axes[idx]
    df_sub = heur["df"]
    col_y = heur["col_y"]
    
    for margin in margins_to_analyze:
        # Filtrar dados para a margem específica e ordenar por carga
        sub = df_sub[df_sub["margin"] == margin].sort_values("load")
        
        # Filtrar apenas as cargas de interesse
        sub = sub[sub["load"].isin(loads)]
        
        x = sub["load"]
        y = sub[col_y]
        st = margin_styles[margin]
        
        # Plotar curva (valores em fração para escala log)
        ax.plot(x, y, **st, linewidth=2.0, markersize=7, clip_on=False)
        
        # Anotações dos valores em porcentagem com offset logarítmico
        for val_x, val_y in zip(x, y):
            offset = 1.12 if val_y < 0.1 else 1.06
            ax.text(val_x, val_y * offset, f"{val_y*100:.1f}%", 
                     ha="center", va="bottom", fontsize=8.0, color="#333333")

    # Formatações do subplot
    ax.set_title(heur["name"], fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=6)
    ax.set_xticks(loads)
    ax.set_xticklabels([str(int(l)) for l in loads])
    
    # Eixo Y em escala logarítmica de 10^-3 a 10^0 (1.0)
    ax.set_yscale('log')
    ax.set_ylim(1e-3, 1.0)
    ax.get_yaxis().set_major_formatter(ticker.LogFormatterMathtext())
    
    ax.grid(True, which="both", linestyle="--", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    if idx == 0:
        ax.set_ylabel("Taxa de Perda Efetiva (Escala Log)", labelpad=8)

# Título Principal da Figura
fig.suptitle("Taxa de Perda Efetiva vs Carga de Tráfego por Heurística\n(Análise Comparativa: Margens 0.0 dB vs 3.0 dB | Nobel-EU | k=3 | NLI Ativo)", 
             y=0.98, fontsize=14, fontweight="bold")

# Legenda unificada inferior
handles = [
    mlines.Line2D([], [], color="#1f77b4", marker="o", linestyle="-", label="Margem = 0.0 dB"),
    mlines.Line2D([], [], color="#ff7f0e", marker="s", linestyle="-", label="Margem = 3.0 dB")
]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=2, frameon=True, edgecolor="#cccccc", fontsize=11)

plt.tight_layout()
plt.subplots_adjust(top=0.86, bottom=0.14, wspace=0.12)

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "combined_smart_loss_by_load.png"
out_path_local = TEST_DIR / "combined_smart_loss_by_load.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráficos combinados de perda efetiva por carga gerados com sucesso!")
print(f"Arquivos salvos localmente em results_test/combined_smart_loss_by_load.png")
