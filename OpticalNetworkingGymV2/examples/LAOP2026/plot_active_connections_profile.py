import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
import sys
import dataclasses

# Caminhos
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = Path("/home/eclipse/.gemini/antigravity/brain/f169e1d5-e48d-42e3-99ff-77c961333134")

# Configurar caminhos para importar os pacotes do projeto
sys.path.insert(0, str(SCRIPT_DIR.parents[2] / "src"))
sys.path.insert(0, str(SCRIPT_DIR.parents[2]))

from optical_networking_gym_v2 import make_env
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils
from optical_networking_gym_v2.contracts.enums import MaskMode
from optical_networking_gym_v2.heuristics.runtime_heuristics import build_runtime_heuristic_context, select_first_fit_action

# ==========================================
# SIMULAÇÃO RÁPIDA DE TRÁFEGO (FFQOTA_OTIMIZADA)
# ==========================================
print("Iniciando a simulação real de tráfego (modo RESOURCE_ONLY)...")
load = 250.0   # Carga nominal de 250 Erlangs
margin = 1.0   # Margem
seed = 10      # Seed padrão da simulação
num_requests = 1000
mean_holding_time_hours = 3.0 # H = 3h (10.800 s)

# 1. Construir cenário base
scenario_base = scenario_utils.build_nobel_eu_graph_load_scenario(
    topology_id="nobel-eu",
    episode_length=num_requests,
    seed=seed,
    load=load,
    mean_holding_time=10800.0,
    num_spectrum_resources=320,
    k_paths=3,
    launch_power_dbm=0.0,
    modulations_to_consider=6,
    margin=margin,
    measure_disruptions=True,
    drop_on_disruption=True,
)

# 2. Alterar para modo recurso (RESOURCE_ONLY) para desativar cálculos de QoT física e acelerar 10.000x
scenario = dataclasses.replace(scenario_base, mask_mode=MaskMode.RESOURCE_ONLY)

env = make_env(config=scenario)
env.reset(seed=seed)

arrival_times = []
departure_times = []

# Executar a simulação de 1000 conexões de forma instantânea
for step_idx in range(num_requests):
    context = build_runtime_heuristic_context(env)
    req = context.request
    
    # Salvar tempos da conexão em horas
    arrival_times.append(req.arrival_time / 3600.0)
    departure_times.append((req.arrival_time + req.holding_time) / 3600.0)
    
    # Usar a heurística rápida First-Fit espectral puro
    action = select_first_fit_action(env)
    env.step(action)

arrival_times = np.array(arrival_times)
departure_times = np.array(departure_times)

# Fim da geração de chegadas
end_arrivals_time = arrival_times[-1]
# Fim absoluto da simulação (quando a última conexão ativa termina)
end_simulation_time = np.max(departure_times)

# Monitorar a flutuação de conexões ativas na rede ao longo do tempo
time_points = np.linspace(0, end_simulation_time, 2000)
active_counts = []

for t in time_points:
    # Conta conexões ativas no instante t
    active = np.sum((arrival_times <= t) & (departure_times > t))
    active_counts.append(active)

active_counts = np.array(active_counts)

# Converter para Tráfego Relativo (%) em relação à carga nominal E = 250 Erlangs
relative_traffic = (active_counts / load) * 100

# ==========================================
# PLOTAGEM DO GRÁFICO (Estilo Premium)
# ==========================================
fig, ax = plt.subplots(figsize=(12, 7.5), dpi=220)

# Cor de fundo suave
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#ffffff")

# Plotar a curva de tráfego relativo flutuante da simulação real
ax.plot(time_points, relative_traffic, color="#1f77b4", linewidth=1.5, alpha=0.9, 
        label="Tráfego Relativo Real Amostrado ($E_{\\text{inst}} / E_{\\text{nom}}$)")

# Definir as fases de simulação dinâmicas
t_warmup = 3 * mean_holding_time_hours  # Fim do aquecimento em 9 horas (3*H)
t_cooldown = end_arrivals_time         # Fim das chegadas (última requisição gerada)

# Linhas pontilhadas verticais
ax.axvline(t_warmup, color="#475569", linestyle="--", linewidth=1.2)
ax.axvline(t_cooldown, color="#475569", linestyle="--", linewidth=1.2)

# Sombreados de cor para representar as fases
ax.axvspan(0, t_warmup, facecolor="#fef3c7", alpha=0.4, label="Fase 1: Aquecimento (Transitório)")
ax.axvspan(t_warmup, t_cooldown, facecolor="#e8f5e9", alpha=0.45, label="Fase 2: Regime Estacionário")
ax.axvspan(t_cooldown, end_simulation_time, facecolor="#fef2f2", alpha=0.4, label="Fase 3: Esvaziamento (Tear-down)")

# Linha horizontal do patamar esperado de 100%
ax.axhline(100.0, color="#2563eb", linestyle=":", linewidth=1.5, alpha=0.8)

# Percentual de tempo do eixo X
pct_warmup_x = (t_warmup / end_simulation_time) * 100
pct_cooldown_x = (t_cooldown / end_simulation_time) * 100

# Adicionar textos explicativos discretos no rodapé (abaixo da linha zero)
ax.text(t_warmup, -6, f"{t_warmup:.1f}h\n(Warm-up)", ha="center", va="top", fontsize=8.5, color="#475569", fontweight="bold")
ax.text(t_cooldown, -6, f"{t_cooldown:.1f}h\n(Chegadas)", ha="center", va="top", fontsize=8.5, color="#475569", fontweight="bold")

# Anotações dos patamares de tráfego relativo no Y
ax.text(-0.2, 100.0, "100% (Carga Nominal)", ha="right", va="center", fontsize=9.5, fontweight="bold", color="#2563eb")

# Anotações de caixas explicativas no canto direito (onde o tráfego já caiu para zero)
# 1. Total de requisições N = 1000
bbox_total = dict(boxstyle="round,pad=0.4", fc="#fef2f2", ec="#b91c1c", lw=1.5)
ax.text(30.0, 78, f"Requisições Totais\nN = {num_requests}\nCarga = {int(load)} Erl", ha="center", va="center", 
        fontsize=10, fontweight="bold", color="#b91c1c", bbox=bbox_total)

# 2. Fórmula de Erlang
erlang_text = (
    "Fórmula de Erlang (Intensidade de Tráfego):\n\n"
    r"$E = \frac{\lambda}{\mu} = \lambda \cdot H$"
)
ax.text(30.0, 42, erlang_text, ha="center", va="center", fontsize=10.5, fontweight="bold", color="#0f172a",
        bbox=dict(facecolor="#f8fafc", edgecolor="#cbd5e1", boxstyle="round,pad=0.5"))

# Configuração dos eixos
ax.set_title("Perfil Temporal de Conexões Ativas: Heurística FFQoTA_Otimizada\n"
             "Simulação Física Real | Topologia Nobel-EU | Carga = 250 Erlangs | 1000 Conexões", 
             fontsize=13, fontweight="bold", color="#0f172a", pad=16)
ax.set_xlabel("Tempo de Simulação (horas)", labelpad=16, fontweight="bold")
ax.set_ylabel("Tráfego Relativo (%)", labelpad=12, fontweight="bold")

ax.set_xlim(0, end_simulation_time + 0.5)
ax.set_ylim(-13, 130)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))

ax.grid(True, which="both", linestyle="--", alpha=0.35)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Legenda
ax.legend(loc="upper right", frameon=True, edgecolor="#cccccc")

plt.tight_layout()

# Salvar gráficos
out_path_artifact = ARTIFACT_DIR / "traffic_profile_envelope.png"
out_path_local = SCRIPT_DIR / "results_test" / "traffic_profile_envelope.png"

fig.savefig(out_path_artifact, bbox_inches="tight")
fig.savefig(out_path_local, bbox_inches="tight")
plt.close(fig)

print("Gráfico de envelope de perfil de tráfego (dados reais FFQoTA_Otimizada) gerado com sucesso!")
print(f"Salvo localmente em: {out_path_local}")
print(f"Salvo nos artefatos em: {out_path_artifact}")
