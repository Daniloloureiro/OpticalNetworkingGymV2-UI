import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.ticker as ticker

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ff_dir = SCRIPT_DIR / "results_medium_ff"
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Encontrar o CSV consolidado de FF Legada mais recente
ff_files = sorted(list(ff_dir.glob("*-medium-ff-summary.csv")), reverse=True)
if not ff_files:
    raise FileNotFoundError("Nenhum CSV consolidado *-medium-ff-summary.csv encontrado em results_medium_ff!")
ff_csv = ff_files[0]
print(f"Lendo dados de: {ff_csv.name}")
df = pd.read_csv(ff_csv).sort_values(by=["load", "margin"])

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

fig, ax = plt.subplots(figsize=(8.0, 5.5), dpi=150)

loads = sorted(df["load"].unique())
margins = [0.0, 3.0]

# Cores e estilos: Azul para Margem 0.0 dB e Laranja para Margem 3.0 dB
styles = {
    0.0: {"color": "#1f77b4", "marker": "o", "linestyle": "-", "label": "Margem = 0.0 dB"},
    3.0: {"color": "#ff7f0e", "marker": "s", "linestyle": "-", "label": "Margem = 3.0 dB"}
}

# Plotar as curvas de blocking_rate (probabilidade de bloqueio na admissão)
for margin in margins:
    sub = df[df["margin"] == margin].sort_values("load")
    
    # Filtrar valores zerados (bloqueio = 0) na escala logarítmica para evitar bugs visuais de linhas verticais infinitas
    sub_log = sub[sub["blocking_rate"] > 0]
    
    x = sub_log["load"]
    y = sub_log["blocking_rate"]
    st = styles[margin]
    
    if not sub_log.empty:
        ax.plot(x, y, **st, linewidth=2.2, markersize=8, clip_on=False)
        
        # Anotações dos valores como porcentagem (apenas >= 10^-3)
        for val_x, val_y in zip(x, y):
            if val_y >= 1e-3:
                # offset multiplicativo para escala log Y
                offset = 1.15 if val_y < 0.01 else 1.08
                ax.text(val_x, val_y * offset, f"{val_y*100:.1f}%", 
                        ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#333333")
    else:
        # Plot de linha vazia apenas para constar na legenda
        ax.plot([], [], **st)

# Formatação do painel
ax.set_title("Probabilidade de Bloqueio (Requisições Não Alocadas)\nFirst Fit Legada (Nobel-EU | k=3 | ASE+NLI)", pad=15, fontsize=12, fontweight="bold")
ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax.set_ylabel("Probabilidade de Bloqueio (Admissão)", labelpad=8)
ax.set_xticks(loads)
ax.set_xticklabels([str(int(l)) for l in loads])

# Escala logarítmica (base 10^-3 a 10^0 conforme solicitado)
ax.set_yscale('log')
ax.set_ylim(1e-3, 1.0)
ax.get_yaxis().set_major_formatter(ticker.LogFormatterMathtext())

# Remover bordas desnecessárias
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Adicionar grid para escala logarítmica
ax.grid(True, which="both", linestyle="--", alpha=0.45)

# Legenda
ax.legend(title="Margem de Admissão", frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="lower right")

plt.tight_layout()

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "legacy_ff_blocking_only.png"
out_path_local = ff_dir / "legacy_ff_blocking_only.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")

print(f"Gráfico salvo com sucesso em:\n  - Artifacts: {out_path_artifact.name}\n  - Local: {out_path_local.name}")
plt.close(fig)
