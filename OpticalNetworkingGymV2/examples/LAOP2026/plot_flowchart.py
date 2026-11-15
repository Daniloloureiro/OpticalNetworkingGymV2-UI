import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Configurações de estilo
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
})

fig, ax = plt.subplots(figsize=(10, 12), dpi=200)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# Cor de fundo suave
fig.patch.set_facecolor("#fcfcfc")

# Título do fluxograma
ax.text(0.5, 0.97, "FLUXOGRAMA DE DECISÃO DO ALGORITMO FFQOT_AWARE", 
        ha="center", va="center", fontsize=14, fontweight="bold", color="#0f172a")
ax.text(0.5, 0.94, "Prevenção Ativa de Disrupção Física em Redes Ópticas (EONs)", 
        ha="center", va="center", fontsize=9.5, color="#64748b", style="italic")

# Estilos de Caixas
arrow_style = dict(arrowstyle="-|>", color="#475569", lw=1.5, mutation_scale=15)
line_style = dict(color="#475569", linestyle="--", lw=1.2)

def draw_oval(x, y, text, color_edge, color_face):
    bbox = dict(boxstyle="round,pad=0.5", facecolor=color_face, edgecolor=color_edge, lw=1.5)
    ax.text(x, y, text, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#0f172a", bbox=bbox)

def draw_rect(x, y, text, color_edge, color_face, w=0.35, h=0.06):
    rect = patches.FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle="round,pad=0.01", edgecolor=color_edge, facecolor=color_face, lw=1.5
    )
    ax.add_patch(rect)
    ax.text(x, y, text, ha="center", va="center", fontsize=9, fontweight="bold", color="#0f172a")

def draw_diamond(x, y, text, color_edge, color_face, w=0.18, h=0.055):
    # Desenhar losango usando Polígono de 4 pontos
    points = np.array([
        [x, y - h],  # inferior
        [x + w, y],  # direita
        [x, y + h],  # superior
        [x - w, y]   # esquerda
    ])
    polygon = patches.Polygon(points, edgecolor=color_edge, facecolor=color_face, lw=1.5, closed=True)
    ax.add_patch(polygon)
    ax.text(x, y, text, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#0f172a")

# --- Desenhar Caixas ---
# 1. Início (x=0.5, y=0.88)
draw_oval(0.5, 0.88, "Início: Nova Requisição\nde Serviço Recebida", "#16a34a", "#f0fdf4")

# 2. RSA Varredura (x=0.5, y=0.77)
draw_rect(0.5, 0.77, "Varredura RSA First-Fit:\nCaminho -> Modulação -> Slot", "#2563eb", "#eff6ff")

# 3. Decisão QoT Própria (x=0.5, y=0.64)
draw_diamond(0.5, 0.64, "QoT própria\nviável?", "#d97706", "#fef3c7")

# 4. Alocação Temporária (x=0.5, y=0.51)
draw_rect(0.5, 0.51, "Aplicar alocação hipotética\ntemporária na rede virtual", "#0d9488", "#f0fdfa")

# 5. Calcular ruído NLI (x=0.5, y=0.40)
draw_rect(0.5, 0.40, "Recalcular ruído NLI e OSNR\nde todos os serviços ativos", "#0d9488", "#f0fdfa")

# 6. Decisão Disrupção (x=0.5, y=0.28)
draw_diamond(0.5, 0.28, "Algum ativo\ndegrada QoT?", "#b91c1c", "#fef2f2")

# 7. Confirmar alocação (x=0.5, y=0.17)
draw_rect(0.5, 0.17, "Confirmar alocação física\ndefinitiva no simulador", "#16a34a", "#f0fdf4")

# 8. Sucesso (x=0.5, y=0.07)
draw_oval(0.5, 0.07, "Serviço Aceito\ne Estabelecido", "#16a34a", "#e8f5e9")

# --- Caminho Alternativo 1: Descartar alocação temporária (x=0.8, y=0.45)
draw_rect(0.8, 0.45, "Liberar alocação temporária\n(Descartar candidato)", "#ea580c", "#fff7ed", w=0.24, h=0.05)

# --- Caminho Alternativo 2: Rejeição final (x=0.2, y=0.50)
draw_oval(0.2, 0.50, "Serviço Rejeitado\nna Admissão", "#dc2626", "#fef2f2")


# --- Conectar Caixas com Setas ---
# Início -> Varredura RSA
ax.annotate("", xy=(0.5, 0.81), xytext=(0.5, 0.85), arrowprops=arrow_style)

# Varredura RSA -> Decisão QoT
ax.annotate("", xy=(0.5, 0.70), xytext=(0.5, 0.74), arrowprops=arrow_style)

# Decisão QoT -> Não (lado esquerdo para loop ou fim)
ax.annotate("Não", xy=(0.32, 0.64), xytext=(0.42, 0.64), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#b91c1c")

# Decisão QoT -> Sim
ax.annotate("Sim", xy=(0.5, 0.55), xytext=(0.5, 0.58), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#16a34a")

# Alocação Temp -> Calcular NLI
ax.annotate("", xy=(0.5, 0.44), xytext=(0.5, 0.48), arrowprops=arrow_style)

# Calcular NLI -> Decisão Disrupção
ax.annotate("", xy=(0.5, 0.34), xytext=(0.5, 0.37), arrowprops=arrow_style)

# Decisão Disrupção -> Sim (Causa disrupção - Vai para liberar temporária)
# Seta vai para a direita e sobe até a caixa de descarte
ax.annotate("Sim", xy=(0.68, 0.28), xytext=(0.57, 0.28), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#b91c1c")
ax.annotate("", xy=(0.8, 0.42), xytext=(0.8, 0.28), arrowprops=dict(arrowstyle="-", color="#475569", lw=1.5))
ax.plot([0.68, 0.8], [0.28, 0.28], color="#475569", lw=1.5)

# Decisão Disrupção -> Não (Não causa disrupção - Vai para confirmar)
ax.annotate("Não", xy=(0.5, 0.21), xytext=(0.5, 0.245), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#16a34a")

# Confirmar -> Sucesso
ax.annotate("", xy=(0.5, 0.11), xytext=(0.5, 0.14), arrowprops=arrow_style)

# De Liberar Temp para Varredura (seta volta)
ax.annotate("", xy=(0.68, 0.77), xytext=(0.8, 0.77), arrowprops=arrow_style)
ax.plot([0.8, 0.8], [0.48, 0.77], color="#475569", lw=1.5)

# De Decisão QoT Não para Liberar Temp (linha)
ax.plot([0.32, 0.32], [0.64, 0.77], color="#475569", lw=1.5)
ax.plot([0.32, 0.325], [0.77, 0.77], color="#475569", lw=1.5) # conecta de volta

# Se esgotarem todas as opções (de Varredura RSA para Rejeição final)
ax.annotate("Sem recursos /\nQoT inviável", xy=(0.2, 0.54), xytext=(0.325, 0.77), 
            arrowprops=dict(arrowstyle="-|>", color="#dc2626", lw=1.2, connectionstyle="angle,angleA=0,angleB=90"),
            fontsize=8.5, color="#dc2626")

plt.tight_layout()

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "flowchart_ff_qot_aware.png"
out_path_local = SCRIPT_DIR / "results_test" / "flowchart_ff_qot_aware.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Fluxograma de decisão da FFQoT_Aware gerado com sucesso!")
print(f"Salvo localmente em results_test/flowchart_ff_qot_aware.png")
