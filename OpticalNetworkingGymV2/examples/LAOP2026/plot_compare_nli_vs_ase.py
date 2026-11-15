import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# --- Carregar dados com NLI ---
nli_dir = SCRIPT_DIR / "results_medium"
nli_files = sorted(nli_dir.glob("*-medium-scenario-summary.csv"), reverse=True)
if not nli_files:
    raise FileNotFoundError("Nenhum CSV em results_medium/")
df_nli = pd.read_csv(nli_files[0])
df_nli["mode"] = "ASE+NLI"

# --- Carregar dados sem NLI ---
ase_dir = SCRIPT_DIR / "results_medium_ase_only"
ase_files = sorted(ase_dir.glob("*-medium-ase-only-summary.csv"), reverse=True)
if not ase_files:
    raise FileNotFoundError("Nenhum CSV em results_medium_ase_only/")
df_ase = pd.read_csv(ase_files[0])
df_ase["mode"] = "ASE-only (sem NLI)"

# --- Estilo ---
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

margins = [0.0, 3.0]
colors_nli  = {0.0: "#2ca02c", 3.0: "#d62728"}   # verde/vermelho para ASE+NLI
colors_ase  = {0.0: "#17becf", 3.0: "#ff7f0e"}   # ciano/laranja para ASE-only
markers_nli = {0.0: "o", 3.0: "s"}
markers_ase = {0.0: "^", 3.0: "D"}

fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), dpi=220, sharey=True)
fig.patch.set_facecolor("#fafafa")

# === Painel 1: Taxa de Perda Efetiva ===
ax1 = axes[0]
ax1.set_facecolor("#ffffff")

for margin in margins:
    sub_nli = df_nli[df_nli["margin"] == margin].sort_values("load")
    sub_ase = df_ase[df_ase["margin"] == margin].sort_values("load")

    # Tratamento para zero no log Y
    y_nli = np.where(sub_nli["effective_loss_rate"] == 0, 1e-3, sub_nli["effective_loss_rate"])
    y_ase = np.where(sub_ase["effective_loss_rate"] == 0, 1e-3, sub_ase["effective_loss_rate"])

    ax1.plot(sub_nli["load"], y_nli,
             color=colors_nli[margin], marker=markers_nli[margin],
             linestyle="-", linewidth=2.0, markersize=7,
             label=f"ASE+NLI – Margem {margin} dB")
    ax1.plot(sub_ase["load"], y_ase,
             color=colors_ase[margin], marker=markers_ase[margin],
             linestyle="--", linewidth=1.8, markersize=7,
             label=f"ASE-only – Margem {margin} dB")

ax1.set_title("Taxa de Perda Efetiva (Fração | Escala Log)\nASE+NLI vs ASE-only (FFQoT_Aware, k=3)", pad=12, fontsize=11, fontweight="bold")
ax1.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax1.set_ylabel("Taxa de Perda Efetiva (Fração)", labelpad=8)
ax1.set_xticks(sorted(df_nli["load"].unique()))
ax1.grid(True, which="both", linestyle="--", alpha=0.35)
ax1.legend(fontsize=8.5, frameon=True, edgecolor="#cccccc", loc="lower right")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.set_yscale('log')
ax1.set_ylim(10**-3, 10**1)

# === Painel 2: Disrupções ===
ax2 = axes[1]
ax2.set_facecolor("#ffffff")

for margin in margins:
    sub_ase = df_ase[df_ase["margin"] == margin].sort_values("load")
    # Tratamento para zero no log Y
    y_disrupt_ase = np.where(sub_ase["disruption_rate"] == 0, 1e-3, sub_ase["disruption_rate"])
    
    ax2.plot(sub_ase["load"], y_disrupt_ase,
             color=colors_ase[margin], marker=markers_ase[margin],
             linestyle="--", linewidth=1.8, markersize=7,
             label=f"ASE-only – Margem {margin} dB")

# NLI tem 0 disrupções — plota na linha de base inferior 1e-3
ax2.axhline(1e-3, color="#999999", linestyle=":", linewidth=1.5, label="ASE+NLI – 0 (todas as margens)")

ax2.set_title("Taxa de Disrupção (Fração | Escala Log)\n(ASE-only pode causar disrupções — sem verificação de NLI)", pad=12, fontsize=11, fontweight="bold")
ax2.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax2.set_ylabel("Taxa de Disrupção (Fração)", labelpad=8)
ax2.set_xticks(sorted(df_ase["load"].unique()))
ax2.grid(True, which="both", linestyle="--", alpha=0.35)
ax2.legend(fontsize=8.5, frameon=True, edgecolor="#cccccc", loc="upper left")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.set_yscale('log')
ax2.set_ylim(10**-3, 10**1)

fig.suptitle("Comparação: FFQoT_Aware com NLI (ASE+NLI) vs sem NLI (ASE-only)\nTopologia Nobel-EU | k=3 | Cargas 50–150 Erlang (Escala Logarítmica)",
             y=1.02, fontsize=12, fontweight="bold")
plt.tight_layout()

# Salvar no diretório de artifacts e também na pasta results_medium_ase_only
out_path_artifact = ARTIFACT_DIR / "plot_nli_vs_ase_comparison.png"
out_path_local = ase_dir / "plot_nli_vs_ase_comparison.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráfico comparativo NLI vs ASE (exclusivo logarítmico em fração) gerado com sucesso!")
