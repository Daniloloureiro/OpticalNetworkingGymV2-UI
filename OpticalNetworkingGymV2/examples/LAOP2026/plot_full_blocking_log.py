import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

SCRIPT_DIR = Path("/home/eclipse/Documentos/UFPA/Artigo/ONG/optical-networking-gym/examples/LAOP2026")

# Encontrar o CSV mais recente de carga smart e medium
smart_csv = sorted((SCRIPT_DIR / "results_smart").glob("*-smart-scenario-summary.csv"), reverse=True)[0]
medium_csv = sorted((SCRIPT_DIR / "results_medium").glob("*-medium-scenario-summary.csv"), reverse=True)[0]

df_smart = pd.read_csv(smart_csv)
df_medium = pd.read_csv(medium_csv)

df = pd.concat([df_smart, df_medium])

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linewidth": 0.5,
})

fig, ax = plt.subplots(figsize=(9, 6), dpi=200)

margins = sorted(df["margin"].unique())
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2"]
markers = ["o", "s", "^", "v", "D", "p", "*"]

for i, margin in enumerate(margins):
    sub = df[df["margin"] == margin].sort_values("load")
    if sub.empty: continue
    
    # Substituir perda zero por 1e-4 para o eixo logarítmico não sumir com o ponto
    sub["plot_rate"] = sub["effective_loss_rate"].apply(lambda x: max(x, 1e-4))
    
    ax.plot(
        sub["load"],
        sub["plot_rate"],
        label=f"Margin = {margin} dB",
        color=colors[i % len(colors)],
        marker=markers[i % len(markers)],
        linestyle="-",
        linewidth=2.0,
        markersize=6,
    )

ax.set_yscale("log")
ax.set_ylim(5e-5, 1)
ax.axhline(1e-4, color="gray", linestyle=":", alpha=0.5)
ax.text(max(df["load"])*0.02, 1.2e-4, "Bloqueio Nulo (Simulado como 10⁻⁴)", color="gray", alpha=0.8, fontsize=9)

ax.set_title("Probabilidade de Bloqueio vs Carga de Tráfego\n(Potência = 0.0 dBm, Limiares SNR Legados)", pad=14, fontsize=12)
ax.set_xlabel("Carga de tráfego (Erlang)", labelpad=8)
ax.set_ylabel("Probabilidade de Bloqueio (Taxa de Perda Efetiva)", labelpad=8)

# Limiar de referência 10^-1 para mostrar superação do problema anterior
ax.axhline(1e-1, color="red", linestyle="--", alpha=0.4, label="Alvo 10⁻¹")

ax.grid(True, which="both", linestyle="--", alpha=0.5)
ax.legend(frameon=True, edgecolor="#cccccc", facecolor="#fafafa", loc="lower right", ncol=2)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

out_path = SCRIPT_DIR / "final_blocking_probability_log.png"
fig.savefig(out_path, bbox_inches="tight")
print(f"Gráfico completo salvo em: {out_path.name}")
