import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
import glob
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
RELAXED_DIR = SCRIPT_DIR / "results_test"

# 1. Carregar dados FFQoT_Aware
smart_files = sorted(list((SCRIPT_DIR / "results_smart").glob("*-smart-scenario-summary.csv")), reverse=True)
if not smart_files:
    raise FileNotFoundError("Nenhum CSV original encontrado em results_smart!")
df_smart = pd.read_csv(smart_files[0])

original_served = {}
for _, row in df_smart.iterrows():
    l = float(row["load"])
    m = float(row["margin"])
    original_served[(l, m)] = int(row["served"])

# 2. Carregar dados FFQoTA_Otimizada
relaxed_files = glob.glob(str(RELAXED_DIR / "*.summary.json"))
relaxed_served = {}
for f in relaxed_files:
    try:
        with open(f, 'r') as file:
            d = json.load(file)
            l = float(d.get("load"))
            m = float(d.get("margin"))
            relaxed_served[(l, m)] = int(d.get("services_served", 0))
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

# Grid 1x3 (3 subplots para as cargas 250, 275 e 300 Erl)
fig, axes = plt.subplots(1, 3, figsize=(16, 6.0), sharey=True, dpi=200)

color_orig = "#d62728"  # Vermelho para FFQoT_Aware
color_relax = "#1f77b4"  # Azul para FFQoTA_Otimizada

width = 0.35  # Largura de cada barra
x_positions = np.arange(len(margins))

for col_idx, load in enumerate(loads):
    ax = axes[col_idx]
    
    orig_vals = []
    relax_vals = []
    missing_relax_indices = []
    
    for m_idx, margin in enumerate(margins):
        key = (load, margin)
        # Original (FFQoT_Aware)
        orig_vals.append(original_served.get(key, 0))
        
        # Relaxada (FFQoTA_Otimizada)
        if key in relaxed_served:
            relax_vals.append(relaxed_served[key])
        else:
            relax_vals.append(0)
            missing_relax_indices.append(m_idx)
            
    # Plotar as barras agrupadas
    rects_orig = ax.bar(x_positions - width/2, orig_vals, width, label="FFQoT_Aware", color=color_orig, alpha=0.9, edgecolor="none")
    rects_relax = ax.bar(x_positions + width/2, relax_vals, width, label="FFQoTA_Otimizada", color=color_relax, alpha=0.9, edgecolor="none")
    
    # Adicionar os valores numéricos no topo das barras
    for i in range(len(margins)):
        # Valor do Original
        val_orig = orig_vals[i]
        if val_orig > 0:
            ax.text(i - width/2, val_orig + 10, f"{val_orig}", 
                    ha="center", va="bottom", fontsize=8.0, color="#333333", fontweight="bold")
        
        # Valor do Relaxado
        if i in missing_relax_indices:
            ax.text(i + width/2, 15, "N/A", 
                    ha="center", va="bottom", fontsize=8.0, color="#999999", fontstyle="italic", fontweight="bold")
        else:
            val_relax = relax_vals[i]
            if val_relax > 0:
                ax.text(i + width/2, val_relax + 10, f"{val_relax}", 
                        ha="center", va="bottom", fontsize=8.0, color="#333333", fontweight="bold")
                
    # Títulos e formatações dos eixos
    ax.set_title(f"Carga: {int(load)} Erl", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Margem de admissão (dB)", labelpad=8)
    ax.set_xticks(x_positions)
    ax.set_xticklabels([f"{m:g}" for m in margins])
    ax.set_ylim(0, 1100)  # Total de requisitados é 1000
    
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    if col_idx == 0:
        ax.set_ylabel("Serviços atendidos com sucesso (de 1000)", fontsize=11, fontweight="bold", labelpad=8)
        ticks = range(0, 1001, 100)
        ax.set_yticks(ticks)
        ax.set_yticklabels([str(t) for t in ticks])

fig.suptitle("Desempenho de Atendimento de Tráfego: FFQoT_Aware × FFQoTA_Otimizada\nQuantidade de Serviços Estabelecidos e Concluídos com Sucesso", 
             y=0.98, fontsize=14, fontweight="bold")

# Legenda unificada na parte inferior
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=2, frameon=True, edgecolor="#cccccc", fontsize=11)

plt.tight_layout()
plt.subplots_adjust(top=0.84, bottom=0.15)

# Salvar
output_path = SCRIPT_DIR / "performance_served_comparison.png"
fig.savefig(output_path, bbox_inches="tight")
print(f"Salvo: {output_path.name}")
plt.close(fig)

print("Processamento concluído com sucesso!")
