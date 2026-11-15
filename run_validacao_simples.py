import sys
import os
import time
import json
from pathlib import Path
import pandas as pd
import argparse

PROJECT_ROOT = Path("/home/eclipse/Projects/ONG-UI/OpticalNetworkingGymV2")
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_DIR))

from examples.LAOP2026.trace_disruptions import run_trace as run_trace_baseline
from examples.LAOP2026.trace_disruptions_test import run_trace as run_trace_daff

def run_simulation(num_requests=250, load=250.0, margin_db=1.0, seed=10):
    print("="*75)
    print(f"[*] EXECUTANDO SIMULADOR V2: Nobel-EU | Carga: {load} Erl | Margem: {margin_db} dB")
    print(f"[*] Total de Requisições por Heurística: {num_requests}")
    print("="*75)
    
    out_dir = Path("/home/eclipse/Projects/ONG-UI/results_validacao")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Baseline First-Fit
    print(f"\n[1/2] Executando Baseline First-Fit (FF)... Por favor aguarde...")
    t0 = time.time()
    args_ff = argparse.Namespace(
        topology_id="nobel-eu",
        load=load,
        margin=margin_db,
        seed=seed,
        episode_length=num_requests,
        mean_holding_time=10800.0,
        num_spectrum_resources=320,
        k_paths=3,
        launch_power_dbm=0.0,
        modulations_to_consider=6,
        drop_on_disruption=True,
        stop_after_disruptions=0,
        stop_on_first_disruption=False,
        output_dir=out_dir,
        write_step_trace=False,
    )
    res_ff = run_trace_baseline(args_ff)
    elapsed_ff = time.time() - t0
    
    with open(res_ff.summary_path, "r", encoding="utf-8") as f:
        data_ff = json.load(f)
        
    pb_ff = data_ff["service_blocking_rate"] * 100
    pdis_ff = data_ff["episode_disrupted_services_rate"] * 100
    pserv_ff = data_ff["service_served_rate"] * 100
    
    print(f"    [+] FF Concluído em {elapsed_ff:.2f}s | Bloq: {pb_ff:.2f}% | Disrup: {pdis_ff:.2f}% | Entrega: {pserv_ff:.2f}%")
    
    # 2. DAFF (FF_QoT Proposto)
    print(f"\n[2/2] Executando DAFF (FF_QoT Proposto)... Por favor aguarde...")
    t0 = time.time()
    args_daff = argparse.Namespace(
        topology_id="nobel-eu",
        load=load,
        margin=margin_db,
        seed=seed,
        episode_length=num_requests,
        mean_holding_time=10800.0,
        num_spectrum_resources=320,
        k_paths=3,
        launch_power_dbm=0.0,
        modulations_to_consider=6,
        drop_on_disruption=True,
        stop_after_disruptions=0,
        stop_on_first_disruption=False,
        output_dir=out_dir,
        write_step_trace=False,
        no_fallback=False,
    )
    res_daff = run_trace_daff(args_daff)
    elapsed_daff = time.time() - t0
    
    with open(res_daff.summary_path, "r", encoding="utf-8") as f:
        data_daff = json.load(f)
        
    pb_daff = data_daff["service_blocking_rate"] * 100
    pdis_daff = data_daff["episode_disrupted_services_rate"] * 100
    pserv_daff = data_daff["service_served_rate"] * 100
    
    print(f"    [+] DAFF Concluído em {elapsed_daff:.2f}s | Bloq: {pb_daff:.2f}% | Disrup: {pdis_daff:.2f}% | Entrega: {pserv_daff:.2f}%")
    
    tabela = [
        {
            "Algoritmo": "Baseline First-Fit (FF)",
            "Taxa Bloqueio (%)": round(pb_ff, 2),
            "Taxa Disrupção (%)": round(pdis_ff, 2),
            "Taxa Entrega Real (%)": round(pserv_ff, 2),
            "Tempo (s)": round(elapsed_ff, 2)
        },
        {
            "Algoritmo": "DAFF (FF_QoT Proposto)",
            "Taxa Bloqueio (%)": round(pb_daff, 2),
            "Taxa Disrupção (%)": round(pdis_daff, 2),
            "Taxa Entrega Real (%)": round(pserv_daff, 2),
            "Tempo (s)": round(elapsed_daff, 2)
        }
    ]
    
    df = pd.DataFrame(tabela)
    csv_path = out_dir / "resumo_validacao.csv"
    df.to_csv(csv_path, index=False)
    
    print("\n" + "="*75)
    print("               QUADRO COMPARATIVO CONSOLIDADO (BENCHMARK)")
    print("="*75)
    print(df.to_string(index=False))
    print("="*75)
    
    ganho = pserv_daff - pserv_ff
    reduc_dis = ((pdis_ff - pdis_daff) / pdis_ff * 100) if pdis_ff > 0 else 0.0
    print(f"\n🏆 SÍNTESE DA VALIDAÇÃO FÍSICA:")
    print(f"   • Redução relativa de conexões ativas derrubadas: {reduc_dis:.1f}%")
    print(f"   • Ganho líquido absoluto de conexões entregues: +{ganho:.2f} pontos percentuais")
    print(f"   • Arquivo salvo: {csv_path}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=250)
    args = parser.parse_args()
    run_simulation(num_requests=args.requests, load=250.0, margin_db=1.0, seed=10)
