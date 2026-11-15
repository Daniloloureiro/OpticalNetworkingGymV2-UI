import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# --- Carregar dados sem NLI (ASE-only) ---
ase_dir = SCRIPT_DIR / "results_medium_ase_only"
ase_files = sorted(ase_dir.glob("*-medium-ase-only-summary.csv"), reverse=True)
if not ase_files:
    raise FileNotFoundError("Nenhum CSV em results_medium_ase_only/")
df_ase = pd.read_csv(ase_files[0])

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

margins = [0.0, 3.0]
# Cores e estilos consistentes com os plots anteriores para o modelo ASE-only
policy_styles = {
    0.0: {
        "label": "ASE-only – Margem 0.0 dB",
        "color": "#17becf",
        "marker": "^",
        "linestyle": "--",
        "linewidth": 2.0,
        "markersize": 7,
    },
    3.0: {
        "label": "ASE-only – Margem 3.0 dB",
        "color": "#ff7f0e",
        "marker": "D",
        "linestyle": "--",
        "linewidth": 2.0,
        "markersize": 7,
    }
}

fig, ax = plt.subplots(figsize=(8.0, 5.8), dpi=220)
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#ffffff")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(True, which="both", linestyle="--", alpha=0.35)

ax.set_title("Probabilidade de Bloqueio na Admissão sob Ruído ASE-only\nFFQoT_Aware (Sem Disrupções Físicas | Nobel-EU | k=3)", pad=14, fontsize=11, fontweight="bold")
ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax.set_ylabel("Probabilidade de Bloqueio (Fração)", labelpad=8)

loads = sorted(df_ase["load"].unique())
ax.set_xticks(loads)
ax.set_xticklabels([f"{int(l)}" for l in loads])

for margin in margins:
    sub = df_ase[df_ase["margin"] == margin].sort_values("load")
    x = sub["load"]
    y = sub["blocking_rate"]
    
    # Tratamento para PB zero: plota no limite inferior (1e-3)
    y_log = np.where(y == 0, 1e-3, y)
    
    st = policy_styles[margin]
    ax.plot(x, y_log, **st)

ax.set_yscale("log")
ax.set_ylim(10**-3, 10**1)
ax.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc")

plt.tight_layout()

# Salvar gráficos
out_path_artifact = ARTIFACT_DIR / "blocking_probability_ase_only.png"
out_path_local = SCRIPT_DIR / "results_test" / "blocking_probability_ase_only.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráfico de PB para cenário ASE-only gerado com sucesso!")
print(f"Salvo nos artefatos em: {out_path_artifact}")
print(f"Salvo localmente em: {out_path_local}")
