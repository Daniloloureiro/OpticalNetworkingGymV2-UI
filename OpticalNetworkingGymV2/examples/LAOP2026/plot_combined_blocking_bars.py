import pandas as pd
import numpy as np
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
x_positions = np.arange(len(loads))
width = 0.35

# Extrair bloqueados com NLI
nli_blocked_0 = df_nli[df_nli["margin"] == 0.0].sort_values("load")["rejected_by_agent"].values
nli_blocked_3 = df_nli[df_nli["margin"] == 3.0].sort_values("load")["rejected_by_agent"].values

# Extrair bloqueados sem NLI
ase_blocked_0 = df_ase[df_ase["margin"] == 0.0].sort_values("load")["rejected_by_agent"].values
ase_blocked_3 = df_ase[df_ase["margin"] == 3.0].sort_values("load")["rejected_by_agent"].values

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

# Grid 1x2 com eixo Y compartilhado para comparação honesta de escala
fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), sharey=True, dpi=200)

# --- Subplot 0 (Esquerda): Com NLI ---
ax0 = axes[0]
rects_nli0 = ax0.bar(x_positions - width/2, nli_blocked_0, width, label="Margem = 0.0 dB", color="#2ca02c", alpha=0.9, edgecolor="none")
rects_nli3 = ax0.bar(x_positions + width/2, nli_blocked_3, width, label="Margem = 3.0 dB", color="#d62728", alpha=0.9, edgecolor="none")

for i in range(len(loads)):
    ax0.text(i - width/2, nli_blocked_0[i] + 10, f"{int(nli_blocked_0[i])}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")
    ax0.text(i + width/2, nli_blocked_3[i] + 10, f"{int(nli_blocked_3[i])}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")

ax0.set_title("Cenário com NLI (ASE+NLI)\nAlgoritmo: FFQoT_Aware ($k=3$)", pad=12, fontsize=12, fontweight="bold")
ax0.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax0.set_ylabel("Quantidade de conexões bloqueadas (de 1000)", labelpad=8)
ax0.set_xticks(x_positions)
ax0.set_xticklabels([f"{int(l)}" for l in loads])
ax0.grid(True, axis="y", linestyle="--", alpha=0.5)
ax0.spines["top"].set_visible(False)
ax0.spines["right"].set_visible(False)
ax0.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="upper left")

# --- Subplot 1 (Direita): Sem NLI ---
ax1 = axes[1]
rects_ase0 = ax1.bar(x_positions - width/2, ase_blocked_0, width, label="Margem = 0.0 dB (sem NLI)", color="#17becf", alpha=0.9, edgecolor="none")
rects_ase3 = ax1.bar(x_positions + width/2, ase_blocked_3, width, label="Margem = 3.0 dB (sem NLI)", color="#ff7f0e", alpha=0.9, edgecolor="none")

for i in range(len(loads)):
    ax1.text(i - width/2, ase_blocked_0[i] + 10, f"{int(ase_blocked_0[i])}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")
    ax1.text(i + width/2, ase_blocked_3[i] + 10, f"{int(ase_blocked_3[i])}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")

ax1.set_title("Cenário sem NLI (ASE-only / DIST)\nAlgoritmo: FFQoT_Aware ($k=3$)", pad=12, fontsize=12, fontweight="bold")
ax1.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax1.set_xticks(x_positions)
ax1.set_xticklabels([f"{int(l)}" for l in loads])
ax1.grid(True, axis="y", linestyle="--", alpha=0.5)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="upper left")

# Formatação Geral da Figura
ax0.set_ylim(0, 1000)
fig.suptitle("Comparativo de Conexões Bloqueadas (FFQoT_Aware): Com NLI vs Sem NLI\nTopologia Nobel-EU | k=3 | Cargas 50–150 Erlang", 
             y=0.98, fontsize=14, fontweight="bold")

plt.tight_layout()
plt.subplots_adjust(top=0.84, bottom=0.15)

# Salvar
output_path = SCRIPT_DIR / "combined_blocking_medium.png"
fig.savefig(output_path, bbox_inches="tight")
print(f"Salvo: {output_path.name}")
plt.close(fig)

print("Processamento concluído com sucesso!")
