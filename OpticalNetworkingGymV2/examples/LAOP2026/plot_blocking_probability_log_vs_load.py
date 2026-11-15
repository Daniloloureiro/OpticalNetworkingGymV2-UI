import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# --- Carregar dados FFQoT_Aware (results_medium) ---
daff_dir = SCRIPT_DIR / "results_medium"
daff_files = sorted(daff_dir.glob("*-medium-scenario-summary.csv"), reverse=True)
if not daff_files:
    raise FileNotFoundError("Nenhum CSV em results_medium/")
df_daff = pd.read_csv(daff_files[0])

# --- Carregar dados FF Legada (results_medium_ff) ---
ff_dir = SCRIPT_DIR / "results_medium_ff"
ff_files = sorted(ff_dir.glob("*-medium-ff-summary.csv"), reverse=True)
if not ff_files:
    raise FileNotFoundError("Nenhum CSV em results_medium_ff/")
df_ff = pd.read_csv(ff_files[0])

# --- Carregar dados FFQoTA_Otimizada (results_medium_relaxed) ---
relaxed_dir = SCRIPT_DIR / "results_medium_relaxed"
relaxed_files = sorted(relaxed_dir.glob("*-medium-relaxed-summary.csv"), reverse=True)
if not relaxed_files:
    raise FileNotFoundError("Nenhum CSV em results_medium_relaxed/")
df_relaxed = pd.read_csv(relaxed_files[0])

# --- Configuração de Estilo Premium ---
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

# Padrão de Estilo das Políticas
policy_styles = {
    "legacy": {
        "label": "FF Legada",
        "color": "#888888",
        "marker": "s",
        "linestyle": "--",
        "linewidth": 1.8,
        "markersize": 7,
    },
    "daff_orig": {
        "label": "FFQoT_Aware",
        "color": "#d62728",
        "marker": "^",
        "linestyle": "-.",
        "linewidth": 1.8,
        "markersize": 7,
    },
    "daff_relax": {
        "label": "FFQoTA_Otimizada",
        "color": "#1f77b4",
        "marker": "o",
        "linestyle": "-",
        "linewidth": 2.2,
        "markersize": 8,
    }
}

margins = [0.0, 3.0]
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True, dpi=200)
fig.patch.set_facecolor("#fafafa")

for idx, margin in enumerate(margins):
    ax = axes[idx]
    ax.set_facecolor("#ffffff")
    
    # Filtrar dados para a margem atual
    sub_daff = df_daff[df_daff["margin"] == margin].sort_values("load")
    sub_ff = df_ff[df_ff["margin"] == margin].sort_values("load")
    sub_relaxed = df_relaxed[df_relaxed["margin"] == margin].sort_values("load")
    
    # Tratamento para PB zero: plota no limite inferior (1e-3)
    y_ff = np.where(sub_ff["blocking_rate"] == 0, 1e-3, sub_ff["blocking_rate"])
    y_daff = np.where(sub_daff["blocking_rate"] == 0, 1e-3, sub_daff["blocking_rate"])
    y_relaxed = np.where(sub_relaxed["blocking_rate"] == 0, 1e-3, sub_relaxed["blocking_rate"])
    
    # Plotar as curvas de Probabilidade de Bloqueio em fração
    ax.plot(sub_ff["load"], y_ff, **policy_styles["legacy"])
    ax.plot(sub_daff["load"], y_daff, **policy_styles["daff_orig"])
    ax.plot(sub_relaxed["load"], y_relaxed, **policy_styles["daff_relax"])
    
    # Ajustes finos do layout
    ax.set_title(f"Margem de Admissão: {margin:.1f} dB", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
    ax.set_xticks(sorted(sub_daff["load"].unique()))
    
    # Grid em ambas escalas do log Y
    ax.grid(True, which="both", linestyle="--", alpha=0.35)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    # Configuração de Escala Logarítmica padrão (10^-3 a 10^1)
    ax.set_yscale('log')
    ax.set_ylim(10**-3, 10**1)
    
    if idx == 0:
        ax.set_ylabel("Probabilidade de Bloqueio (Fração)", fontsize=11, fontweight="bold", labelpad=8)

fig.suptitle("Probabilidade de Bloqueio na Admissão (Escala Logarítmica)\nFFQoT_Aware vs FF Legada vs FFQoTA_Otimizada (Nobel-EU, NLI, 1000 requisições)", 
             y=1.02, fontsize=13, fontweight="bold")

# Adicionar legenda na parte inferior centralizada
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=True, edgecolor="#cccccc", fontsize=11)

plt.tight_layout()

# Salvar gráficos
out_path_artifact = ARTIFACT_DIR / "blocking_probability_log_vs_load.png"
out_path_local = SCRIPT_DIR / "results_test" / "blocking_probability_log_vs_load.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print(f"Gráfico de bloqueio em escala logarítmica gerado com sucesso!")
print(f"Salvo localmente em: {out_path_local}")
print(f"Salvo nos artefatos em: {out_path_artifact}")
