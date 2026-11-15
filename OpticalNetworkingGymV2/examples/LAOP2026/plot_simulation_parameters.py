import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Configuração de estilo premium
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "Arial"],
})

# Criar figura e eixo único
fig, ax = plt.subplots(figsize=(14, 9), dpi=220)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# Cor de fundo geral suave
fig.patch.set_facecolor("#fdfdfd")

# 1. Título Geral do Dashboard
ax.text(0.5, 0.95, "DASHBOARD DE PARÂMETROS DA SIMULAÇÃO", 
        ha="center", va="center", fontsize=18, fontweight="bold", color="#0f172a")
ax.text(0.5, 0.91, "Cenário de Varredura Física LAOP 2026 — Topologia Nobel-EU", 
        ha="center", va="center", fontsize=11, color="#64748b", style="italic")

# Linha divisória horizontal abaixo do título
ax.plot([0.05, 0.95], [0.88, 0.88], color="#e2e8f0", linewidth=1.5)

# Função auxiliar para desenhar "cards" de informação
def draw_card(ax, title, x_min, x_max, y_min, y_max, header_color, text_items):
    # Desenhar o retângulo do card
    rect = patches.FancyBboxPatch(
        (x_min, y_min), x_max - x_min, y_max - y_min,
        boxstyle="round,pad=0.015", edgecolor="#cbd5e1", facecolor="#f8fafc", linewidth=1.2
    )
    ax.add_patch(rect)
    
    # Cabeçalho do Card
    ax.text(x_min + 0.02, y_max - 0.035, title, 
            ha="left", va="center", fontsize=12, fontweight="bold", color=header_color)
    
    # Linha interna do cabeçalho
    ax.plot([x_min + 0.02, x_max - 0.02], [y_max - 0.055, y_max - 0.055], color="#cbd5e1", linewidth=0.8)
    
    # Conteúdo de Texto
    y_curr = y_max - 0.08
    for label, val in text_items:
        # Marcador redondo simulado
        ax.plot(x_min + 0.025, y_curr, marker="o", color=header_color, markersize=4)
        # Rótulo em negrito
        ax.text(x_min + 0.035, y_curr, label + ":", 
                ha="left", va="center", fontsize=9.5, fontweight="bold", color="#334155")
        # Valor correspondente
        ax.text(x_min + 0.17, y_curr, val, 
                ha="left", va="center", fontsize=9.5, color="#0f172a")
        y_curr -= 0.032

# Card 1: Topologia & Infraestrutura de Rede
network_items = [
    ("Topologia física", "Nobel-EU (Rede de Tráfego Europeia)"),
    ("Dimensão da rede", "28 nós de comutação / 41 enlaces bidirecionais"),
    ("Algoritmo de Rotas", "k-Shortest Paths (k-SP) com k = 3 caminhos"),
    ("Espectro por Enlace", "320 slots de frequência (Grade flexível ITU-T)"),
    ("Largura de Slot", "12.5 GHz por slot espectral"),
    ("Banda espectral", "4.0 THz (Grade flexível total do enlace C-band)"),
]
draw_card(ax, "1. Topologia & Infraestrutura", 0.05, 0.48, 0.52, 0.85, "#1e3a8a", network_items)

# Card 2: Geração & Perfil de Tráfego
traffic_items = [
    ("Duração do episódio", "1000 conexões de tráfego por simulação"),
    ("Holding Time (Médio)", "10.800 segundos (3 horas de tempo de posse)"),
    ("Taxa de bits solicitada", "48, 120, 240, 480 Gbps (Distribuídos uniformemente)"),
    ("Carga (Varredura Média)", "50, 75, 100, 125, 150 Erlangs"),
    ("Carga (Varredura Alta)", "250, 275, 300 Erlangs"),
    ("Modelo de Chegada", "Processo de Poisson (Chegadas com holding exponencial)"),
]
draw_card(ax, "2. Perfil de Tráfego", 0.52, 0.95, 0.52, 0.85, "#0f766e", traffic_items)

# Card 3: Camada Física & QoT (Quality of Transmission)
physical_items = [
    ("Atenuação de fibra", "0.2 dB / km (Fibra monomodo padrão SMF)"),
    ("Ruído de EDFA (NF)", "4.5 dB (Figura de ruído do amplificador óptico)"),
    ("Comprimento de Span", "Máximo de 80.0 km por vão óptico"),
    ("Potência de Lançamento", "0.0 dBm por canal óptico ativo"),
    ("Margem de QoT", "0.0 a 3.0 dB (Passo incremental de 0.5 dB)"),
    ("Engine de QoT", "Modelo Físico Analítico GN (Gaussian Noise)"),
]
draw_card(ax, "3. Modelo Físico & QoT", 0.05, 0.48, 0.15, 0.48, "#b91c1c", physical_items)

# Card 4: Configurações do Simulador
sim_items = [
    ("Formatos de Modulação", "BPSK, QPSK, 8QAM, 16QAM, 32QAM, 64QAM"),
    ("Heurísticas avaliadas", "First Fit Legada, FFQoT_Aware, FFQoTA_Otimizada"),
    ("Critério de Alocação", "First-Fit por índice de eficiência espectral (SE)"),
    ("NLI Ativo (Não-Linear)", "Ativo no cálculo de ruído total (Self/Cross-Phase)"),
    ("Disrupção Física", "Ativa (Queda automática de serviços com QoT violado)"),
    ("Execução paralela", "Varredura automática distribuída com Multiprocessing"),
]
draw_card(ax, "4. Configurações de Simulação", 0.52, 0.95, 0.15, 0.48, "#6d28d9", sim_items)

# Nota de Rodapé com créditos e metadados
ax.text(0.5, 0.08, "Nota: O simulador calcula a Qualidade de Transmissão (QoT) em tempo real "
                  "considerando efeitos de ruído ASE acumulado e ruído NLI (Interferência Não-Linear).",
        ha="center", va="center", fontsize=8.5, color="#64748b", style="italic")

plt.tight_layout()

# Salvar imagens
out_path_artifact = ARTIFACT_DIR / "simulation_parameters.png"
out_path_local = SCRIPT_DIR / "results_test" / "simulation_parameters.png"

fig.savefig(out_path_artifact, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
fig.savefig(out_path_local, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
plt.close(fig)

print("Dashboard de parâmetros de simulação gerado com sucesso!")
print(f"Salvo localmente em results_test/simulation_parameters.png")
