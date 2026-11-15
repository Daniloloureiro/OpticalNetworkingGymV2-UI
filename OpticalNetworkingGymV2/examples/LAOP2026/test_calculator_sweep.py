"""
test_calculator_sweep.py
========================
Demonstração didática e física do QoTEngine (calculadora de QoT).
Modela um enlace óptico padrão e faz uma varredura de potência de lançamento 
(Launch Power Sweep) mostrando o comportamento de:
  • Ruído ASE (linear com a potência de lançamento, ou seja, OSNR_ase cresce linearmente em dB)
  • Ruído NLI (proporcional ao cubo da potência, ou seja, OSNR_nli decai com o quadrado em dB)
  • OSNR Total (mostrando a curva em U e a potência ótima de transmissão)

Avalia também três cenários de ocupação espectral:
  1. Apenas o canal sob teste (apenas SPM - Auto-modulação de fase)
  2. Carga Média (10 canais interferentes vizinhos)
  3. Carga Alta (50 canais interferentes vizinhos)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Ajusta path para importar o kernel do qot
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import numpy as np
from optical_networking_gym_v2.optical.kernels.qot_kernel import accumulate_link_noise

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def db(x: float) -> float:
    return 10.0 * math.log10(max(x, 1e-300))

def main():
    # ── Parâmetros do Enlace Óptico de Teste ───────────────────────
    # Simula um enlace de 3 spans de 80 km (240 km total)
    n_spans = 3
    span_length_km = 80.0
    lengths = np.array([span_length_km] * n_spans, dtype=np.float64)
    
    # Atenuação: 0.2 dB/km -> convertida para Np/m (escala de amplitude)
    att_db_km = 0.2
    att_np_m = att_db_km / (20.0 * math.log10(math.exp(1)) * 1000.0)
    attenuations = np.array([att_np_m] * n_spans, dtype=np.float64)
    
    # Amplificador (EDFA): Noise Figure de 6.0 dB -> convertido para linear
    nf_db = 6.0
    nf_linear = 10.0 ** (nf_db / 10.0)
    noise_figures = np.array([nf_linear] * n_spans, dtype=np.float64)

    # ── Parâmetros do Canal Sob Teste ──────────────────────────────
    current_id = 999
    f_center = 193.1e12  # 193.1 THz (Banda C)
    bw = 37.5e9          # 37.5 GHz de largura de banda (3 slots de 12.5 GHz)
    
    # Varredura de potência de lançamento: -15 dBm a +8 dBm
    p_dbm_sweep = np.arange(-15.0, 9.0, 1.0)
    
    # ── Definição dos Cenários de Interferentes ─────────────────────
    # Vamos gerar interferentes espaçados por 50 GHz
    channel_spacing = 50.0e9 # 50 GHz
    
    scenarios = {
        "Sem interferentes (Apenas SPM)": 0,
        "Carga Média (10 interferentes)": 10,
        "Carga Alta (50 interferentes)": 50
    }
    
    results = {}
    
    for sc_name, num_interferers in scenarios.items():
        results[sc_name] = {
            "p_dbm": [],
            "osnr_ase": [],
            "osnr_nli": [],
            "osnr_total": [],
        }
        
        # Cria os vetores de interferentes
        if num_interferers == 0:
            run_ids = np.empty(0, dtype=np.int32)
            run_freqs = np.empty(0, dtype=np.float64)
            run_bws = np.empty(0, dtype=np.float64)
            run_phis = np.empty(0, dtype=np.float64)
        else:
            # Distribui metade à esquerda e metade à direita da frequência sob teste
            ids = []
            freqs = []
            bws = []
            phis = []
            
            half = num_interferers // 2
            indices = [i for i in range(-half, half + 1) if i != 0]
            # Caso num_interferers seja ímpar e sobrou
            if len(indices) < num_interferers:
                indices.append(half + 1)
                
            for idx, i in enumerate(indices):
                ids.append(i)  # ID diferente do canal sob teste (999)
                freqs.append(f_center + i * channel_spacing)
                bws.append(37.5e9)
                phis.append(1.0)  # QPSK (Phi = 1.0)
                
            run_ids = np.array(ids, dtype=np.int32)
            run_freqs = np.array(freqs, dtype=np.float64)
            run_bws = np.array(bws, dtype=np.float64)
            run_phis = np.array(phis, dtype=np.float64)

        # Roda a calculadora para cada nível de potência
        for p_dbm in p_dbm_sweep:
            p_linear_w = 10.0 ** ((p_dbm - 30.0) / 10.0)
            
            # 1. OSNR Apenas ASE (NLI desativado no kernel)
            _, ase_only, _ = accumulate_link_noise(
                lengths, attenuations, noise_figures,
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.float64),
                np.empty(0, dtype=np.float64),
                np.empty(0, dtype=np.float64),
                current_service_id=current_id,
                center_frequency=f_center,
                bandwidth=bw,
                launch_power=p_linear_w,
                include_nli=False
            )
            osnr_ase_db = db(1.0 / ase_only) if ase_only > 0 else float("inf")
            
            # 2. OSNR com ASE + NLI
            gsnr_linear, _, nli_linear = accumulate_link_noise(
                lengths, attenuations, noise_figures,
                run_ids, run_freqs, run_bws, run_phis,
                current_service_id=current_id,
                center_frequency=f_center,
                bandwidth=bw,
                launch_power=p_linear_w,
                include_nli=True
            )
            
            # nli_linear é acumulado como Power_nli / Launch_Power.
            # Então a potência de ruído NLI absoluta é nli_linear * launch_power.
            # Logo, OSNR_nli = P_launch / P_nli = 1.0 / nli_linear
            osnr_nli_db = db(1.0 / nli_linear) if nli_linear > 0 else float("inf")
            osnr_total_db = db(1.0 / gsnr_linear) if gsnr_linear > 0 else float("inf")
            
            results[sc_name]["p_dbm"].append(p_dbm)
            results[sc_name]["osnr_ase"].append(osnr_ase_db)
            results[sc_name]["osnr_nli"].append(osnr_nli_db)
            results[sc_name]["osnr_total"].append(osnr_total_db)

    # ── Apresenta Amostra no Terminal ──────────────────────────────
    print(f"\n{'='*72}")
    # Tradução: AMOSTRAGEM DO COMPORTAMENTO DO QOTENGINE (ASE vs NLI)
    print(f"  AMOSTRAGEM DO COMPORTAMENTO DO QOTENGINE (ASE vs NLI)")
    print(f"{'='*72}")
    print(f"  Enlace: {n_spans} spans de {span_length_km} km SSMF (Total: {n_spans*span_length_km} km)")
    print(f"  EDFA NF: {nf_db} dB | Atenuação: {att_db_km} dB/km | Canal: {f_center/1e12:.2f} THz")
    print(f"{'-'*72}")
    
    # Amostra de tabela com o cenário de Carga Média
    print(f"\n  [Tabela de Amostragem: Cenário - Carga Média (10 interferentes)]")
    print(f"  {'P_tx (dBm)':^12} | {'OSNR ASE (dB)':^15} | {'OSNR NLI (dB)':^15} | {'OSNR Total (dB)':^16}")
    print(f"  {'-'*68}")
    
    sc_mid = "Carga Média (10 interferentes)"
    for idx, p_dbm in enumerate(results[sc_mid]["p_dbm"]):
        # Mostra apenas alguns pontos para caber legível no terminal
        if p_dbm in [-15.0, -10.0, -5.0, -2.0, 0.0, 2.0, 5.0, 8.0]:
            ase_v = results[sc_mid]["osnr_ase"][idx]
            nli_v = results[sc_mid]["osnr_nli"][idx]
            tot_v = results[sc_mid]["osnr_total"][idx]
            print(f"  {p_dbm:>10.1f}   |   {ase_v:>11.2f}   |   {nli_v:>11.2f}   |   {tot_v:>12.2f}")
            
    # Encontra o ponto de potência ótima para cada cenário
    print(f"\n  [Potência Ótima de Transmissão por Cenário]")
    print(f"  {'-'*68}")
    for sc_name in scenarios:
        tots = results[sc_name]["osnr_total"]
        dbms = results[sc_name]["p_dbm"]
        opt_idx = np.argmax(tots)
        opt_p = dbms[opt_idx]
        opt_osnr = tots[opt_idx]
        print(f"  • {sc_name:<32} -> P_ot = {opt_p:>5.1f} dBm (OSNR_max = {opt_osnr:>5.2f} dB)")
        
    # ── Gera o Gráfico da Curva em U ────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=160)
    
    # Curva ASE pura (igual para todos os cenários porque o ASE não depende dos canais vizinhos)
    # Pegamos do primeiro cenário
    ax.plot(p_dbm_sweep, results["Sem interferentes (Apenas SPM)"]["osnr_ase"], 
            "--", color="#1f77b4", linewidth=1.8, label="Apenas Ruído ASE (Teórico)")
    
    # Plot de cada cenário
    colors = {
        "Sem interferentes (Apenas SPM)": "#2ca02c",
        "Carga Média (10 interferentes)": "#ff7f0e",
        "Carga Alta (50 interferentes)": "#d62728"
    }
    
    for sc_name in scenarios:
        # Plota OSNR Total
        ax.plot(p_dbm_sweep, results[sc_name]["osnr_total"], 
                "-", color=colors[sc_name], linewidth=2.5, 
                label=f"OSNR Total ({sc_name})")
        
        # Plota OSNR NLI correspondente (curva pontilhada)
        ax.plot(p_dbm_sweep, results[sc_name]["osnr_nli"], 
                ":", color=colors[sc_name], linewidth=1.5, alpha=0.75,
                label=f"OSNR NLI ({sc_name})")
        
        # Marca o ponto ótimo
        tots = results[sc_name]["osnr_total"]
        opt_idx = np.argmax(tots)
        ax.scatter(p_dbm_sweep[opt_idx], tots[opt_idx], 
                   color=colors[sc_name], edgecolors="black", 
                   s=80, zorder=5)
        ax.annotate(f" {p_dbm_sweep[opt_idx]:.0f} dBm", 
                    xy=(p_dbm_sweep[opt_idx], tots[opt_idx]), 
                    xytext=(0, 5), textcoords="offset points",
                    fontweight="bold", color=colors[sc_name], fontsize=8.5)

    ax.set_xlabel("Potência de Lançamento no Canal (Launch Power, dBm)", labelpad=10, fontsize=10.5)
    ax.set_ylabel("OSNR Efetiva (dB)", labelpad=10, fontsize=10.5)
    ax.set_title("Curva em U de OSNR: Limitações por Ruído ASE vs Ruído NLI\n"
                 "(Parâmetros: Enlace de 240 km SSMF, 3 spans, EDFA NF = 6 dB)", 
                 pad=15, fontsize=11, fontweight="bold")
    
    ax.set_ylim([5.0, 32.0])
    ax.set_xlim([-15.0, 8.0])
    ax.grid(linestyle="--", alpha=0.5)
    ax.legend(loc="lower left", frameon=True, framealpha=0.95, fontsize=8.5, ncol=2)
    
    # Adiciona anotações explicativas no gráfico
    ax.text(-12.0, 10.0, "← Limitado por ASE\n(Sinal fraco)", 
            color="#1f77b4", fontsize=9.5, fontweight="bold")
    ax.text(2.0, 8.0, "Limitado por NLI →\n(Efeitos não lineares)", 
            color="#d62728", fontsize=9.5, fontweight="bold")
    
    out_path = OUTPUT_DIR / "calculator_sweep_ase_nli.png"
    fig.savefig(out_path, bbox_inches="tight")
    print(f"\n  Gráfico gerado com sucesso!")
    print(f"  Salvo em: {out_path.name}")
    plt.close(fig)
    print("✅ Concluído!")

if __name__ == "__main__":
    main()
