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

fig, ax = plt.subplots(figsize=(11, 14), dpi=200)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# Cor de fundo suave
fig.patch.set_facecolor("#fcfcfc")

# Título do fluxograma
ax.text(0.5, 0.97, "FLUXOGRAMA DE DECISÃO DO ALGORITMO FFQOTA_OTIMIZADA", 
        ha="center", va="center", fontsize=14, fontweight="bold", color="#0f172a")
ax.text(0.5, 0.945, "Mecanismo em Dois Estágios: Varredura First-Fit (Estágio 1) e Fallback Relaxado (Estágio 2)", 
        ha="center", va="center", fontsize=9.5, color="#64748b", style="italic")

# Estilos de Caixas
arrow_style = dict(arrowstyle="-|>", color="#475569", lw=1.5, mutation_scale=15)
line_style = dict(color="#475569", linestyle="--", lw=1.2)

def draw_oval(x, y, text, color_edge, color_face):
    bbox = dict(boxstyle="round,pad=0.5", facecolor=color_face, edgecolor=color_edge, lw=1.5)
    ax.text(x, y, text, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#0f172a", bbox=bbox)

def draw_rect(x, y, text, color_edge, color_face, w=0.35, h=0.055):
    rect = patches.FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle="round,pad=0.01", edgecolor=color_edge, facecolor=color_face, lw=1.5
    )
    ax.add_patch(rect)
    ax.text(x, y, text, ha="center", va="center", fontsize=9, fontweight="bold", color="#0f172a")

def draw_diamond(x, y, text, color_edge, color_face, w=0.18, h=0.052):
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
# 1. Início (x=0.5, y=0.90)
draw_oval(0.5, 0.90, "Início: Nova Requisição\nde Serviço Recebida", "#16a34a", "#f0fdf4")

# 2. RSA Varredura (x=0.5, y=0.81)
draw_rect(0.5, 0.81, "Estágio 1: Varredura RSA First-Fit\nCandidato (Caminho, Mod, Slot)", "#2563eb", "#eff6ff")

# 3. Decisão QoT Própria (x=0.5, y=0.70)
draw_diamond(0.5, 0.70, "QoT própria\nviável?", "#d97706", "#fef3c7")

# 4. Decisão Disrupção (x=0.5, y=0.58)
draw_diamond(0.5, 0.58, "Causa disrupção\nem ativos?", "#b91c1c", "#fef2f2")

# 5. Armazenar Fallback (x=0.80, y=0.58)
draw_rect(0.80, 0.58, "Salvar candidato no conjunto\nde Fallback com Custo:\nCusto = (Quedas, Déficit, Slot)", "#7c3aed", "#f5f3ff", w=0.28, h=0.065)

# 6. Esgotou Candidatos? (x=0.5, y=0.45)
draw_diamond(0.5, 0.45, "Esgotou todos\ncandidatos?", "#475569", "#f1f5f9")

# 7. Decisão Tem Fallback? (x=0.5, y=0.32)
draw_diamond(0.5, 0.32, "Existe algum\ncandidato salvo?", "#475569", "#f1f5f9")

# 8. Estágio 2: Seleção de Fallback (x=0.5, y=0.20)
draw_rect(0.5, 0.20, "Estágio 2 (Fallback Relaxado):\nEscolher candidato de MENOR CUSTO\n(Menos quedas -> Menor déficit OSNR)", "#7c3aed", "#f5f3ff", w=0.38, h=0.06)

# 9. Rejeição (x=0.20, y=0.32)
draw_oval(0.20, 0.32, "Serviço Rejeitado\nna Admissão", "#dc2626", "#fef2f2")

# 10. Confirmar alocação (x=0.5, y=0.10)
draw_rect(0.5, 0.10, "Confirmar alocação física definitiva\ndo candidato escolhido na rede", "#16a34a", "#f0fdf4")

# 11. Fim Aceito (x=0.5, y=0.035)
draw_oval(0.5, 0.035, "Serviço Aceito e Estabelecido", "#16a34a", "#e8f5e9")


# --- Conectar Caixas com Setas ---
# Início -> Varredura RSA
ax.annotate("", xy=(0.5, 0.845), xytext=(0.5, 0.875), arrowprops=arrow_style)

# Varredura RSA -> Decisão QoT
ax.annotate("", xy=(0.5, 0.755), xytext=(0.5, 0.78), arrowprops=arrow_style)

# Decisão QoT -> Sim
ax.annotate("Sim", xy=(0.5, 0.635), xytext=(0.5, 0.65), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#16a34a")

# Decisão QoT -> Não (candidato inviável - pula direto para ver se esgotou)
ax.annotate("Não", xy=(0.32, 0.70), xytext=(0.42, 0.70), arrowprops=dict(arrowstyle="-", color="#475569", lw=1.5))
ax.plot([0.32, 0.32], [0.45, 0.70], color="#475569", lw=1.5)
ax.annotate("", xy=(0.41, 0.45), xytext=(0.32, 0.45), arrowprops=arrow_style)

# Decisão Disrupção -> Não (Candidato Limpo! Sucesso imediato no Estágio 1)
# Seta vai direto para confirmar alocação e pula o resto
ax.annotate("Não (Limpo)", xy=(0.32, 0.58), xytext=(0.42, 0.58), arrowprops=dict(arrowstyle="-", color="#16a34a", lw=1.5))
ax.plot([0.32, 0.32], [0.10, 0.58], color="#16a34a", lw=1.5)
ax.annotate("", xy=(0.41, 0.10), xytext=(0.32, 0.10), arrowprops=dict(arrowstyle="-|>", color="#16a34a", lw=1.5, mutation_scale=15))

# Decisão Disrupção -> Sim (Causa disrupção em ativos - Vai para salvar em Fallback)
ax.annotate("Sim", xy=(0.66, 0.58), xytext=(0.57, 0.58), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#b91c1c")

# De Salvar Fallback para Esgotou? (conecta por baixo)
ax.plot([0.80, 0.80], [0.45, 0.545], color="#475569", lw=1.5)
ax.annotate("", xy=(0.59, 0.45), xytext=(0.80, 0.45), arrowprops=arrow_style)

# Esgotou? -> Não (Tentar próximo candidato - loop de volta)
ax.annotate("Não", xy=(0.5, 0.505), xytext=(0.5, 0.485), arrowprops=dict(arrowstyle="-|>", color="#2563eb", lw=1.5, mutation_scale=15))
ax.plot([0.5, 0.5], [0.485, 0.505], color="#2563eb", lw=1.5)

# Esgotou? -> Sim
ax.annotate("Sim", xy=(0.5, 0.375), xytext=(0.5, 0.40), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#475569")

# Decisão Tem Fallback? -> Sim
ax.annotate("Sim", xy=(0.5, 0.235), xytext=(0.5, 0.27), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#16a34a")

# Decisão Tem Fallback? -> Não (Nenhum candidato limpo nem com QoT própria viável existiu)
ax.annotate("Não", xy=(0.30, 0.32), xytext=(0.41, 0.32), arrowprops=arrow_style, fontsize=8.5, fontweight="bold", color="#b91c1c")

# Estágio 2 Seleção -> Confirmar alocação
ax.annotate("", xy=(0.5, 0.13), xytext=(0.5, 0.17), arrowprops=arrow_style)

# Confirmar -> Fim Aceito
ax.annotate("", xy=(0.5, 0.065), xytext=(0.5, 0.08), arrowprops=arrow_style)

# Desenhar seta voltando para a varredura do loop principal
# A linha sai do loop de "Não" de esgotou e sobe para o cabeçalho de varredura
ax.plot([0.96, 0.96], [0.45, 0.81], color="#2563eb", lw=1.5)
ax.plot([0.80, 0.96], [0.45, 0.45], color="#2563eb", lw=1.5)
ax.annotate("", xy=(0.69, 0.81), xytext=(0.96, 0.81), arrowprops=dict(arrowstyle="-|>", color="#2563eb", lw=1.5, mutation_scale=15))

plt.tight_layout()

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "flowchart_ff_qota_optimized.png"
out_path_local = SCRIPT_DIR / "results_test" / "flowchart_ff_qota_optimized.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Fluxograma de decisão da FFQoTA_Otimizada gerado com sucesso!")
print(f"Salvo localmente em results_test/flowchart_ff_qota_optimized.png")
