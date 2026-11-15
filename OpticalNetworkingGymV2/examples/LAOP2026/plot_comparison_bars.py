import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
import glob
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
SMART_CSV = SCRIPT_DIR / "results_smart" / "15-06-00h26-smart-scenario-summary.csv"
RELAXED_DIR = SCRIPT_DIR / "results_test"

# 1. Carregar dados FFQoT_Aware
if not SMART_CSV.exists():
    raise FileNotFoundError(f"CSV original não encontrado: {SMART_CSV}")
df_smart = pd.read_csv(SMART_CSV)

original_data = {}
for _, row in df_smart.iterrows():
    l = float(row["load"])
    m = float(row["margin"])
    original_data[(l, m)] = {
        "blocked": int(row["rejected_by_agent"]),
        "dropped": int(row["disrupted"])
    }

# 2. Carregar dados FFQoTA_Otimizada
relaxed_files = glob.glob(str(RELAXED_DIR / "*.summary.json"))
relaxed_data = {}
for f in relaxed_files:
    try:
        with open(f, 'r') as file:
            d = json.load(file)
            l = float(d.get("load"))
            m = float(d.get("margin"))
            relaxed_data[(l, m)] = {
                "blocked": int(d.get("rejected", 0)),
                "dropped": int(d.get("episode_disrupted_services_count", 0))
            }
    except Exception as e:
        print(f"Erro ao ler {f}: {e}")

# Definições
loads = [250.0, 275.0, 300.0]
margins = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# Configurações do matplotlib
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 10,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

# Grid 2x3 (Linha 0: Bloqueios, Linha 1: Quedas | Coluna 0,1,2: Cargas)
fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), dpi=200)

# Estilos de cores
color_orig = "#d62728"  # Vermelho para FFQoT_Aware
color_relax = "#1f77b4"  # Azul para FFQoTA_Otimizada

width = 0.35  # Largura de cada barra
x_positions = np.arange(len(margins))

for row_idx, metric in enumerate(["blocked", "dropped"]):
    for col_idx, load in enumerate(loads):
        ax = axes[row_idx, col_idx]
        
        orig_vals = []
        relax_vals = []
        missing_relax_indices = []
        
        for m_idx, margin in enumerate(margins):
            # Original (FFQoT_Aware)
            key = (load, margin)
            orig_vals.append(original_data.get(key, {"blocked": 0, "dropped": 0})[metric])
            
            # Relaxada (FFQoTA_Otimizada)
            if key in relaxed_data:
                relax_vals.append(relaxed_data[key][metric])
            else:
                relax_vals.append(0)
                missing_relax_indices.append(m_idx)
        
        # Plotar as barras agrupadas
        rects_orig = ax.bar(x_positions - width/2, orig_vals, width, label="FFQoT_Aware", color=color_orig, alpha=0.9)
        rects_relax = ax.bar(x_positions + width/2, relax_vals, width, label="FFQoTA_Otimizada", color=color_relax, alpha=0.9)
        
        # Adicionar os valores numéricos no topo das barras
        for i in range(len(margins)):
            # Valor do Original (sempre existe)
            val_orig = orig_vals[i]
            ax.text(i - width/2, val_orig + (2 if row_idx == 1 else 8), f"{val_orig}", 
                    ha="center", va="bottom", fontsize=7.5, color="#333333", fontweight="bold")
            
            # Valor do Relaxado
            if i in missing_relax_indices:
                ax.text(i + width/2, 2 if row_idx == 1 else 10, "N/A", 
                        ha="center", va="bottom", fontsize=7.5, color="#999999", fontstyle="italic", fontweight="bold")
            else:
                val_relax = relax_vals[i]
                ax.text(i + width/2, val_relax + (2 if row_idx == 1 else 8), f"{val_relax}", 
                        ha="center", va="bottom", fontsize=7.5, color="#333333", fontweight="bold")
        
        # Títulos e formatação específicos de cada subplot
        if row_idx == 0:
            ax.set_title(f"Bloqueios | Carga: {int(load)} Erl", fontsize=11, fontweight="bold", pad=10)
            ax.set_ylim(0, 750)
            if col_idx == 0:
                ax.set_ylabel("Quantidade Bloqueada (de 1000)", fontsize=10, fontweight="bold")
        else:
            ax.set_title(f"Quedas (Disrupção) | Carga: {int(load)} Erl", fontsize=11, fontweight="bold", pad=10)
            ax.set_ylim(0, 160)
            ax.set_xlabel("Margem de Admissão (dB)", labelpad=8)
            if col_idx == 0:
                ax.set_ylabel("Quantidade Derrubada (de 1000)", fontsize=10, fontweight="bold")
        
        ax.set_xticks(x_positions)
        ax.set_xticklabels([f"{m:g}" for m in margins])
        ax.grid(True, axis="y", linestyle="--", alpha=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

# Título Principal da Figura
fig.suptitle("Comparativo das Heurísticas: FFQoT_Aware × FFQoTA_Otimizada\nQuantidade de Serviços Bloqueados e Quedas de Serviços Ativos", 
             y=0.98, fontsize=14, fontweight="bold")

# Legenda unificada na parte inferior
handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=2, frameon=True, edgecolor="#cccccc", fontsize=11)

plt.tight_layout()
plt.subplots_adjust(top=0.89, bottom=0.10, hspace=0.32, wspace=0.18)

# Salvar a imagem no diretório LAOP2026
output_path = SCRIPT_DIR / "comparison_blocking_and_disruptions.png"
fig.savefig(output_path, bbox_inches="tight")
print(f"Salvo: {output_path.name}")
plt.close(fig)

print("Processamento concluído com sucesso!")
