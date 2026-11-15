import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
nli_dir = SCRIPT_DIR / "results_medium"
ase_dir = SCRIPT_DIR / "results_medium_ase_only"

# 1. Encontrar e carregar o CSV mais recente com NLI
nli_csvs = sorted(list(nli_dir.glob("*-medium-scenario-summary.csv")), reverse=True)
if not nli_csvs:
    raise FileNotFoundError("Nenhum CSV encontrado em results_medium/")
nli_csv = nli_csvs[0]
print(f"Lendo dados com NLI de: {nli_csv.name}")
df_nli = pd.read_csv(nli_csv).sort_values(by=["load", "margin"])
df_nli["policy"] = df_nli["policy"].replace({"disruption_aware_first_fit": "FFQoT_Aware"})

# 2. Encontrar e carregar o CSV mais recente sem NLI
ase_csvs = sorted(list(ase_dir.glob("*-medium-ase-only-summary.csv")), reverse=True)
if not ase_csvs:
    raise FileNotFoundError("Nenhum CSV encontrado em results_medium_ase_only/")
ase_csv = ase_csvs[0]
print(f"Lendo dados sem NLI de: {ase_csv.name}")
df_ase = pd.read_csv(ase_csv).sort_values(by=["load", "margin"])
df_ase["policy"] = df_ase["policy"].replace({"disruption_aware_first_fit": "FFQoT_Aware"})

# Definições
loads = sorted(df_nli["load"].unique())
margins = [0.0, 3.0]

# Configurações globais do Matplotlib para visual premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

# Grid 1x2 sem sharey para garantir que ambos tenham o eixo Y visível de forma independente
fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=200)

# Cores e estilos
colors_nli = {0.0: "#2ca02c", 3.0: "#d62728"}  # Verde/Vermelho
colors_ase = {0.0: "#17becf", 3.0: "#ff7f0e"}  # Ciano/Laranja
markers_nli = {0.0: "o", 3.0: "s"}
markers_ase = {0.0: "^", 3.0: "D"}

# --- Subplot 0 (Esquerda): Com NLI ---
ax0 = axes[0]
for margin in margins:
    sub = df_nli[df_nli["margin"] == margin].sort_values("load")
    x = sub["load"]
    y = sub["blocking_rate"]
    
    ax0.plot(
        x, y,
        label=f"Margem = {margin:g} dB",
        color=colors_nli[margin],
        marker=markers_nli[margin],
        linestyle="-",
        linewidth=2.0,
        markersize=7,
        clip_on=False
    )
    
    for val_x, val_y in zip(x, y):
        ax0.text(val_x, val_y + (val_y * 0.08), f"{val_y*100:.1f}%", 
                 ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")

ax0.set_title("Cenário com NLI (ASE+NLI)\nAlgoritmo: FFQoT_Aware ($k=3$)", pad=12, fontsize=12, fontweight="bold")
ax0.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax0.set_ylabel("Probabilidade de Bloqueio (Escala Log)", labelpad=8)
ax0.set_xticks(loads)
ax0.set_xticklabels([str(int(l)) for l in loads])
ax0.set_yscale('log')
ax0.set_ylim(1e-3, 1.0)
ax0.grid(True, which="both", linestyle="--", alpha=0.45)
ax0.spines["top"].set_visible(False)
ax0.spines["right"].set_visible(False)
ax0.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="upper left")

# --- Subplot 1 (Direita): Sem NLI ---
ax1 = axes[1]
for margin in margins:
    sub = df_ase[df_ase["margin"] == margin].sort_values("load")
    x = sub["load"]
    y = sub["blocking_rate"]
    
    ax1.plot(
        x, y,
        label=f"Margem = {margin:g} dB (sem NLI)",
        color=colors_ase[margin],
        marker=markers_ase[margin],
        linestyle="-",
        linewidth=2.0,
        markersize=7,
        clip_on=False
    )
    
    for val_x, val_y in zip(x, y):
        ax1.text(val_x, val_y + (val_y * 0.08), f"{val_y*100:.1f}%", 
                 ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")

ax1.set_title("Cenário sem NLI (ASE-only / DIST)\nAlgoritmo: FFQoT_Aware ($k=3$)", pad=12, fontsize=12, fontweight="bold")
ax1.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax1.set_ylabel("Probabilidade de Bloqueio (Escala Log)", labelpad=8)  # Eixo Y visível no segundo gráfico também
ax1.set_xticks(loads)
ax1.set_xticklabels([str(int(l)) for l in loads])
ax1.set_yscale('log')
ax1.set_ylim(1e-3, 1.0)  # Eixos perfeitamente idênticos
ax1.grid(True, which="both", linestyle="--", alpha=0.45)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="upper left")

# Formatação Geral da Figura (Aplicar formatador em ambos os eixos Y)
import matplotlib.ticker as ticker
ax0.get_yaxis().set_major_formatter(ticker.LogFormatterMathtext())
ax1.get_yaxis().set_major_formatter(ticker.LogFormatterMathtext())

fig.suptitle("Comparativo de Probabilidade de Bloqueio (FFQoT_Aware): Com NLI vs Sem NLI\nTopologia Nobel-EU | k=3 | Cargas 50–150 Erlang (Escala Logarítmica)", 
             y=0.98, fontsize=14, fontweight="bold")

plt.tight_layout()
plt.subplots_adjust(top=0.84, bottom=0.15, wspace=0.22)

# Salvar
output_path = SCRIPT_DIR / "combined_blocking_medium_log.png"
fig.savefig(output_path, bbox_inches="tight")
print(f"Salvo: {output_path.name}")
plt.close(fig)

print("Processamento concluído com sucesso!")
