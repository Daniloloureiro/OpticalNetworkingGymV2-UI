import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.ticker as ticker

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
smart_dir = SCRIPT_DIR / "results_smart"
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Encontrar o CSV consolidado mais recente do DAFF Original em results_smart
csv_files = sorted(list(smart_dir.glob("*-smart-scenario-summary.csv")), reverse=True)
if not csv_files:
    raise FileNotFoundError("Nenhum CSV consolidado *-smart-scenario-summary.csv encontrado em results_smart!")
csv_file = csv_files[0]
print(f"Lendo dados de: {csv_file.name}")
df = pd.read_csv(csv_file).sort_values(by=["load", "margin"])
df["policy"] = df["policy"].replace({"disruption_aware_first_fit": "FFQoT_Aware"})

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
margins = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# Cores e marcadores para as cargas do Gráfico 1
load_styles = {
    250.0: {"color": "#2166ac", "marker": "o", "linestyle": "-", "label": "Carga = 250 Erl"},
    275.0: {"color": "#1a9850", "marker": "s", "linestyle": "-", "label": "Carga = 275 Erl"},
    300.0: {"color": "#d73027", "marker": "^", "linestyle": "-", "label": "Carga = 300 Erl"}
}

# ===========================================================================
# GRÁFICO 1: Taxa de Perda Efetiva vs Margem de Admissão (Cargas Altas)
# ===========================================================================
fig1, ax1 = plt.subplots(figsize=(8.0, 5.5), dpi=150)

for load in loads:
    sub = df[df["load"] == load].sort_values("margin")
    x = sub["margin"]
    y = sub["effective_loss_rate"]
    st = load_styles[load]
    
    ax1.plot(x, y * 100, **st, linewidth=2.0, markersize=7, clip_on=False)
    
    # Adicionar anotações textuais
    for val_x, val_y in zip(x, y):
        ax1.text(val_x, val_y * 100 + 1.2, f"{val_y*100:.1f}%", 
                 ha="center", va="bottom", fontsize=8.0, color="#333333")

ax1.set_title("Taxa de Perda Efetiva vs Margem de Admissão\nFFQoT_Aware (Cargas Altas | Nobel-EU | k=3 | ASE+NLI)", pad=15, fontsize=12, fontweight="bold")
ax1.set_xlabel("Margem de admissão (dB)", labelpad=8)
ax1.set_ylabel("Taxa de Perda Efetiva (%)", labelpad=8)
ax1.set_xticks(margins)
ax1.set_xticklabels([f"{m:g}" for m in margins])
ax1.set_ylim(40, 80)  # Foco nos valores altos (58% a 71%)
ax1.grid(True, which="both", linestyle="--", alpha=0.45)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.legend(title="Carga de Tráfego", frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="lower right")

plt.tight_layout()

out_path1_artifact = ARTIFACT_DIR / "smart_ff_qot_aware_effective_loss.png"
out_path1_local = smart_dir / "smart_ff_qot_aware_effective_loss.png"
fig1.savefig(out_path1_artifact, bbox_inches="tight")
fig1.savefig(out_path1_local, bbox_inches="tight")
plt.close(fig1)

# ===========================================================================
# GRÁFICO 2: Decomposição da Perda Efetiva (Bloqueio vs Queda QoT)
# ===========================================================================
fig2, axes2 = plt.subplots(1, 3, figsize=(16, 6.0), sharey=True, dpi=150)

# Estilos das componentes
comp_styles = {
    "blocking": {"color": "#3b82f6", "marker": "s", "linestyle": "--", "label": "Bloqueio Admissão"},
    "disruption": {"color": "#ef4444", "marker": "x", "linestyle": ":", "label": "Queda QoT (Derrubado)"},
    "total": {"color": "#10b981", "marker": "o", "linestyle": "-", "label": "Perda Efetiva Total"}
}

for idx, load in enumerate(loads):
    ax = axes2[idx]
    sub = df[df["load"] == load].sort_values("margin")
    x = sub["margin"]
    
    # Plotar as três curvas (no DAFF, bloqueio e total sobrepõem pois queda=0)
    ax.plot(x, sub["blocking_rate"] * 100, **comp_styles["blocking"], linewidth=1.6, markersize=5)
    ax.plot(x, sub["drop_rate"] * 100, **comp_styles["disruption"], linewidth=1.4, markersize=6)
    ax.plot(x, sub["effective_loss_rate"] * 100, **comp_styles["total"], linewidth=2.2, markersize=6)
    
    # Rótulos de dados no topo (escrever apenas o total para não poluir)
    for val_x, val_y in zip(x, sub["effective_loss_rate"].values):
        ax.text(val_x, val_y * 100 + 1.5, f"{val_y*100:.1f}%", ha="center", va="bottom", fontsize=8.0, color="#333333")

    ax.set_title(f"Carga: {int(load)} Erl", fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel("Margem (dB)", labelpad=6)
    ax.set_xticks(margins)
    ax.set_xticklabels([f"{m:g}" for m in margins])
    ax.grid(True, linestyle="--", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if idx == 0:
        ax.set_ylabel("Taxa (%)", labelpad=8)
        ax.set_ylim(-5, 85)

fig2.suptitle("Decomposição da Perda Efetiva (FFQoT_Aware): Bloqueio vs Queda QoT\n(Topologia Nobel-EU | k=3 | NLI Ativo | Cargas Altas)", 
             y=0.98, fontsize=13, fontweight="bold")

# Legenda unificada na parte inferior
from matplotlib.patches import Patch
import matplotlib.lines as mlines
handles2 = [
    mlines.Line2D([], [], color="#3b82f6", marker="s", linestyle="--", label="Bloqueio na Admissão"),
    mlines.Line2D([], [], color="#ef4444", marker="x", linestyle=":", label="Queda QoT (Disrompidos)"),
    mlines.Line2D([], [], color="#10b981", marker="o", linestyle="-", linewidth=2.2, label="Perda Efetiva Total")
]
fig2.legend(handles=handles2, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=3, frameon=True, edgecolor="#cccccc", fontsize=10.5)

plt.tight_layout()
plt.subplots_adjust(top=0.86, bottom=0.14, wspace=0.12)

out_path2_artifact = ARTIFACT_DIR / "smart_ff_qot_aware_loss_decomposition.png"
out_path2_local = smart_dir / "smart_ff_qot_aware_loss_decomposition.png"
fig2.savefig(out_path2_artifact, bbox_inches="tight")
fig2.savefig(out_path2_local, bbox_inches="tight")
plt.close(fig2)

print("Processamento concluído com sucesso!")
print(f"Arquivos salvos localmente em {smart_dir.name}/")
