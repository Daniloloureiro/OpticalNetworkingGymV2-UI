import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
import glob
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
LEGACY_DIR = SCRIPT_DIR.parent / "Resultados antigos" / "results"
SMART_DIR = SCRIPT_DIR / "results_smart"
RELAXED_DIR = SCRIPT_DIR / "results_test"

# 1. Carregar dados Legados (pegar o mais recente consolidado)
legacy_files = sorted(list(LEGACY_DIR.glob("*-publishable-scenario-summary.csv")), reverse=True)
if not legacy_files:
    raise FileNotFoundError(f"Nenhum CSV legado encontrado em {LEGACY_DIR}")
legacy_csv = legacy_files[0]
print(f"Lendo dados legados de: {legacy_csv.name}")
df_legacy = pd.read_csv(legacy_csv)
legacy_data = {}
for _, row in df_legacy.iterrows():
    l = float(row["load"])
    m = float(row["margin"])
    # Tratar os nomes de coluna caso variem
    col = "blocking_rate_mean" if "blocking_rate_mean" in df_legacy.columns else "blocking_rate"
    legacy_data[(l, m)] = float(row[col])

# 2. Carregar dados DAFF Original (pegar o mais recente consolidado)
smart_files = sorted(list(SMART_DIR.glob("*-smart-scenario-summary.csv")), reverse=True)
if not smart_files:
    raise FileNotFoundError(f"Nenhum CSV original encontrado em {SMART_DIR}")
smart_csv = smart_files[0]
print(f"Lendo dados originais de: {smart_csv.name}")
df_smart = pd.read_csv(smart_csv)
original_data = {}
for _, row in df_smart.iterrows():
    l = float(row["load"])
    m = float(row["margin"])
    original_data[(l, m)] = float(row["blocking_rate"])

# 3. Carregar dados DAFF Relaxada
relaxed_files = glob.glob(str(RELAXED_DIR / "*.summary.json"))
relaxed_data = {}
for f in relaxed_files:
    try:
        with open(f, 'r') as file:
            d = json.load(file)
            l = float(d.get("load"))
            m = float(d.get("margin"))
            relaxed_data[(l, m)] = float(d.get("service_blocking_rate", 0))
    except Exception as e:
        print(f"Erro ao ler {f}: {e}")

# Definições
loads = [250.0, 275.0, 300.0]
margins = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# Configurações do matplotlib para visual premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

fig, axes = plt.subplots(1, 3, figsize=(16, 6.0), sharey=True, dpi=200)

# Estilos das políticas
policy_styles = {
    "legacy": {
        "label": "Legada (FF Mascarado)",
        "color": "#888888",
        "marker": "s",
        "linestyle": "--",
        "linewidth": 1.6,
    },
    "daff_orig": {
        "label": "FFQoT_Aware",
        "color": "#d62728",
        "marker": "^",
        "linestyle": "-.",
        "linewidth": 1.8,
    },
    "daff_relax": {
        "label": "FFQoTA_Otimizada",
        "color": "#1f77b4",
        "marker": "o",
        "linestyle": "-",
        "linewidth": 2.2,
    }
}

for col_idx, load in enumerate(loads):
    ax = axes[col_idx]
    
    legacy_vals = []
    orig_vals = []
    relax_vals = []
    relax_margins = []
    
    for margin in margins:
        key = (load, margin)
        
        # Legada
        legacy_vals.append(legacy_data.get(key, 0.0))
        
        # Original
        orig_vals.append(original_data.get(key, 0.0))
        
        # Relaxada (ignorar margens ausentes para não plotar zeros na escala log)
        if key in relaxed_data:
            relax_vals.append(relaxed_data[key])
            relax_margins.append(margin)
            
    # Plotar Curvas
    ax.plot(margins, legacy_vals, **policy_styles["legacy"], clip_on=False)
    ax.plot(margins, orig_vals, **policy_styles["daff_orig"], clip_on=False)
    ax.plot(relax_margins, relax_vals, **policy_styles["daff_relax"], clip_on=False)
    
    # Rótulo de dados ausentes na DAFF Relaxada
    if load in [275.0, 300.0]:
        ax.text(2.5, 3e-3, "N/A\n(Otimizada)", ha="center", va="center", color="#999999", 
                fontstyle="italic", fontsize=9, bbox=dict(facecolor='white', alpha=0.8, edgecolor='#dddddd', boxstyle='round,pad=0.3'))
        ax.text(3.0, 3e-3, "N/A\n(Otimizada)", ha="center", va="center", color="#999999", 
                fontstyle="italic", fontsize=9, bbox=dict(facecolor='white', alpha=0.8, edgecolor='#dddddd', boxstyle='round,pad=0.3'))

    # Títulos e formatações dos eixos
    ax.set_title(f"Carga: {int(load)} Erl", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Margem de admissão (dB)", labelpad=8)
    ax.set_xticks(margins)
    ax.set_xticklabels([f"{m:g}" for m in margins])
    
    # Eixo Y Logarítmico focado de 10^-3 até 10^0 (1.0)
    ax.set_yscale('log')
    ax.set_ylim(1e-3, 1.0)
    
    ax.grid(True, which="both", linestyle="--", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    if col_idx == 0:
        ax.set_ylabel("Probabilidade de Bloqueio (Escala Log)", fontsize=11, fontweight="bold", labelpad=8)
        # Formatar ticks do eixo Y
        import matplotlib.ticker as ticker
        ax.get_yaxis().set_major_formatter(ticker.LogFormatterMathtext())

fig.suptitle("Probabilidade de Bloqueio de Serviços por Margem de Admissão\n(Comparação em Escala Logarítmica de $10^{-3}$ até $10^{0}$)", 
             y=0.98, fontsize=14, fontweight="bold")

# Legenda única na parte inferior
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=3, frameon=True, edgecolor="#cccccc", fontsize=10.5)

plt.tight_layout()
plt.subplots_adjust(top=0.84, bottom=0.15)

# Salvar
output_path = SCRIPT_DIR / "blocking_probability_log.png"
fig.savefig(output_path, bbox_inches="tight")
print(f"Salvo: {output_path.name}")
plt.close(fig)

print("Processamento concluído com sucesso!")
