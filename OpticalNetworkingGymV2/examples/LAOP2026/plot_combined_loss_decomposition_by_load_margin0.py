import pandas as pd
import numpy as np
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

# 3. Carregar dados da DAFF Relaxada
relaxed_files = sorted(list(TEST_DIR.glob("*-relaxed-scenario-summary.csv")), reverse=True)
if not relaxed_files:
    raise FileNotFoundError("CSV consolidado relaxado não encontrado em results_test!")
df_relaxed = pd.read_csv(relaxed_files[0])

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

# Criar a figura com 1 linha e 3 colunas (eixo Y compartilhado)
fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), sharey=True, dpi=150)

for idx, heur in enumerate(heuristics):
    ax = axes[idx]
    df_sub = heur["df"]
    
    # Filtrar dados para a margem 0.0 dB e ordenar por carga
    sub = df_sub[df_sub["margin"] == margin_to_analyze].sort_values("load")
    sub = sub[sub["load"].isin(loads)]
    
    x = sub["load"].values
    bk = sub[heur["col_bk"]].values
    dp = sub[heur["col_dp"]].values
    tot = sub[heur["col_tot"]].values
    
    # Substituir zeros por NaN para evitar erros no log e não desenhar pontos nulos
    bk_plot = np.where(bk > 0, bk, np.nan)
    dp_plot = np.where(dp > 0, dp, np.nan)
    tot_plot = np.where(tot > 0, tot, np.nan)
    
    # Plotar as curvas de Bloqueio na Admissão e Queda QoT (derrubados)
    ax.plot(x, bk_plot, **comp_styles["blocking"], linewidth=2.0, markersize=7, clip_on=False)
    ax.plot(x, dp_plot, **comp_styles["disruption"], linewidth=1.6, markersize=7, clip_on=False)
    
    # Anotações dos valores (tratando zeros e evitando colisões no rodapé log)
    for i in range(len(x)):
        # 1. Anotação de Bloqueio (Azul)
        if bk[i] > 0:
            offset = 1.15 if bk[i] < 0.05 else 1.07
            ax.text(x[i], bk[i] * offset, f"{bk[i]*100:.1f}%", ha="center", va="bottom", fontsize=8.5, color="#3b82f6", fontweight="bold")
        else:
            # Bloqueio nulo anotado na base em azul
            ax.text(x[i], 1.2e-5, "0.0%", ha="center", va="bottom", fontsize=8.5, color="#3b82f6", fontstyle="italic")
            
        # 2. Anotação de Queda QoT (Vermelho)
        if dp[i] > 0:
            offset = 1.15 if dp[i] < 0.05 else 1.07
            ax.text(x[i], dp[i] * offset, f"{dp[i]*100:.1f}%", ha="center", va="bottom", fontsize=8.5, color="#ef4444", fontweight="bold")
        else:
            # Queda nula anotada um pouco acima na base em vermelho
            ax.text(x[i], 3.5e-5, "0.0%", ha="center", va="bottom", fontsize=8.5, color="#ef4444", fontstyle="italic")

    # Formatações do subplot
    ax.set_title(heur["name"], fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=6)
    ax.set_xticks(loads)
    ax.set_xticklabels([str(int(l)) for l in loads])
    
    # Eixo Y em escala logarítmica expandida de 10^-5 a 10^1
    ax.set_yscale('log')
    ax.set_ylim(1e-5, 10.0)
    ax.get_yaxis().set_major_formatter(ticker.LogFormatterMathtext())
    
    ax.grid(True, which="both", linestyle="--", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    if idx == 0:
        ax.set_ylabel("Taxa (Escala Log)", labelpad=8)

# Título Principal da Figura
fig.suptitle(f"Bloqueio na Admissão vs Queda QoT (Derrubados) vs Carga de Tráfego por Heurística\n(Cenário sem Restrições: Margem = {margin_to_analyze:g} dB | Nobel-EU | k=3 | NLI Ativo)", 
             y=0.98, fontsize=14, fontweight="bold")

# Legenda unificada inferior
handles2 = [
    mlines.Line2D([], [], color="#3b82f6", marker="s", linestyle="--", linewidth=2.0, label="Bloqueio na Admissão"),
    mlines.Line2D([], [], color="#ef4444", marker="x", linestyle=":", linewidth=2.0, label="Queda QoT (Derrubados)")
]
fig.legend(handles=handles2, loc="lower center", bbox_to_anchor=(0.5, -0.05), ncol=2, frameon=True, edgecolor="#cccccc", fontsize=11)

plt.tight_layout()
plt.subplots_adjust(top=0.86, bottom=0.15, wspace=0.12)

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "combined_smart_loss_decomposition_by_load_margin0.png"
out_path_local = TEST_DIR / "combined_smart_loss_decomposition_by_load_margin0.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráficos combinados de decomposição de perda por carga na margem 0 gerados com sucesso!")
print(f"Arquivos salvos localmente em results_test/combined_smart_loss_decomposition_by_load_margin0.png")
