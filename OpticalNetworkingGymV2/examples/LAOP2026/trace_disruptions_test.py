"""
trace_disruptions_test.py
=========================
Versão de teste do trace_disruptions.py, usando a heurística
**FFQoTA_Otimizada** (select_ff_qota_optimized_action).

Esta heurística tem dois estágios:
  1. Busca candidato que não cause disrupção (igual ao FFQoT_Aware).
  2. Se nenhum existe, escolhe o "menos pior" em vez de rejeitar
     (comportamento NOVO — reduz rigidez e conservadorismo).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime
import json
from pathlib import Path
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from optical_networking_gym_v2 import make_env
from optical_networking_gym_v2.instrumentation.traces import write_step_trace_jsonl
from optical_networking_gym_v2.utils import experiment_scenarios as scenario_utils

# Importa a nova heurística relaxada
from optical_networking_gym_v2.heuristics.runtime_heuristics_test import (
    select_ff_qota_optimized_action,
)


SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class TraceDisruptionsRun:
    summary_path: Path
    trace_path: Path | None
    disruptions_path: Path
    summary: dict[str, object]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run LAOP2026 FFQoTA_Otimizada (dois estágios) com rastreamento de "
            "disrupções na v2 environment."
        )
    )
    parser.add_argument("--topology-id", default="nobel-eu")
    parser.add_argument("--load", type=float, required=True)
    parser.add_argument("--margin", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=10)
    parser.add_argument("--episode-length", type=int, default=150)
    parser.add_argument("--mean-holding-time", type=float, default=10800.0)
    parser.add_argument("--num-spectrum-resources", type=int, default=320)
    parser.add_argument("--k-paths", type=int, default=5)
    parser.add_argument("--launch-power-dbm", type=float, default=0.0)
    parser.add_argument("--modulations-to-consider", type=int, default=3)
    parser.add_argument("--drop-on-disruption", action="store_true")
    parser.add_argument("--stop-after-disruptions", type=int, default=0)
    parser.add_argument("--stop-on-first-disruption", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR / "results_test")
    parser.add_argument(
        "--write-step-trace",
        action="store_true",
        help="Salva o trace detalhado por passo (JSONL). Desabilitado por padrão.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        default=False,
        help="Desabilita o Estágio 2 (fallback relaxado). Comportamento idêntico ao FFQoT_Aware.",
    )
    return parser


def build_scenario(args: argparse.Namespace):
    return scenario_utils.build_nobel_eu_graph_load_scenario(
        topology_id=str(args.topology_id),
        episode_length=int(args.episode_length),
        seed=int(args.seed),
        load=float(args.load),
        mean_holding_time=float(args.mean_holding_time),
        num_spectrum_resources=int(args.num_spectrum_resources),
        k_paths=int(args.k_paths),
        launch_power_dbm=float(args.launch_power_dbm),
        modulations_to_consider=int(args.modulations_to_consider),
        margin=float(args.margin),
        measure_disruptions=True,
        drop_on_disruption=bool(args.drop_on_disruption),
    )


def _build_output_base_name(*, now: datetime, args: argparse.Namespace) -> str:
    return (
        f"{now.strftime('%d-%m-%Hh%M')}"
        f"-trace-relaxed"
        f"-{args.topology_id}"
        f"-load{int(args.load) if float(args.load).is_integer() else args.load}"
        f"-margin{args.margin:g}"
        f"-seed{args.seed}"
    )


def run_trace(args: argparse.Namespace) -> TraceDisruptionsRun:
    allow_fallback = not getattr(args, "no_fallback", False)
    scenario = replace(build_scenario(args), capture_step_trace=bool(args.write_step_trace))
    env = make_env(config=scenario)
    _, info = env.reset(seed=int(args.seed))

    first_disruption_step: int | None = None
    statuses: list[str] = []
    disruption_events: list[dict[str, object]] = []
    started_at = time.perf_counter()

    while True:
        disrupted_before = set(env.simulator.state.disrupted_services_by_id)
        active_before = {
            service_id: {
                "osnr": float(service.osnr),
                "ase": float(service.ase),
                "nli": float(service.nli),
                "established_osnr": float(service.established_osnr),
                "shared_link_service_count_at_establishment": int(
                    service.shared_link_service_count_at_establishment
                ),
            }
            for service_id, service in env.simulator.state.active_services_by_id.items()
        }
        trigger_request = env.simulator.current_request

        # ------------------------------------------------------------------
        # NOVA HEURÍSTICA: FFQoTA_Otimizada (dois estágios)
        # ------------------------------------------------------------------
        action = int(
            select_ff_qota_optimized_action(
                env.heuristic_context(),
                allow_disruption_fallback=allow_fallback,
            )
        )
        # ------------------------------------------------------------------

        _, _, terminated, truncated, info = env.step(action)
        statuses.append(str(info.get("status", "unknown")))

        disrupted_count = int(env.simulator.statistics.episode_disrupted_services)
        disrupted_after = set(env.simulator.state.disrupted_services_by_id)
        new_disrupted_ids = sorted(disrupted_after - disrupted_before)
        if new_disrupted_ids:
            dropped_services = []
            for service_id in new_disrupted_ids:
                disrupted_service = env.simulator.state.disrupted_services_by_id[service_id]
                previous_service = active_before.get(service_id, disrupted_service)
                modulation = disrupted_service.modulation
                required_osnr = 0.0 if modulation is None else float(modulation.minimum_osnr + scenario.margin)
                shared_services_now = set()
                for link_id in disrupted_service.path.link_ids:
                    shared_services_now.update(env.simulator.state.link_active_service_ids[link_id])
                shared_services_now.discard(service_id)
                dropped_services.append(
                    {
                        "service_id": int(service_id),
                        "source_id": int(disrupted_service.request.source_id),
                        "destination_id": int(disrupted_service.request.destination_id),
                        "bit_rate": int(disrupted_service.request.bit_rate),
                        "path_k": int(disrupted_service.path.k),
                        "path_node_names": [str(name) for name in disrupted_service.path.node_names],
                        "service_slot_start": int(disrupted_service.service_slot_start),
                        "service_slot_end_exclusive": int(disrupted_service.service_slot_end_exclusive),
                        "modulation_name": None if modulation is None else str(modulation.name),
                        "osnr_before_refresh": float(previous_service["osnr"]),
                        "osnr_after_refresh": float(disrupted_service.osnr),
                        "delta_osnr_db": float(disrupted_service.osnr - previous_service["osnr"]),
                        "osnr_requirement": required_osnr,
                        "margin_to_requirement_db": float(disrupted_service.osnr - required_osnr),
                        "established_osnr": float(previous_service["established_osnr"]),
                        "shared_link_service_count_at_establishment": int(
                            previous_service["shared_link_service_count_at_establishment"]
                        ),
                        "shared_link_service_count_after_drop": int(len(shared_services_now)),
                        "disruption_count": int(disrupted_service.disruption_count),
                        "drop_reason": "osnr_below_required_margin",
                    }
                )

            disruption_events.append(
                {
                    "step_index": int(env.simulator.steps_completed),
                    "trigger_request": {
                        "service_id": int(trigger_request.service_id),
                        "source_id": int(trigger_request.source_id),
                        "destination_id": int(trigger_request.destination_id),
                        "bit_rate": int(trigger_request.bit_rate),
                    },
                    "trigger_action": int(action),
                    "trigger_outcome": {
                        "status": str(info.get("status", "unknown")),
                        "accepted": bool(info.get("accepted", False)),
                        "osnr": float(info.get("osnr", 0.0)),
                        "osnr_req": float(info.get("osnr_req", 0.0)),
                    },
                    "dropped_services": dropped_services,
                    "dropped_count_in_step": len(dropped_services),
                    "dropped_count_cumulative": int(env.simulator.statistics.episode_services_dropped_qot),
                    "disrupted_count_cumulative": disrupted_count,
                }
            )

        if disrupted_count > 0 and first_disruption_step is None:
            first_disruption_step = int(env.simulator.steps_completed)
            if args.stop_on_first_disruption:
                break
        if args.stop_after_disruptions > 0 and disrupted_count >= int(args.stop_after_disruptions):
            break

        if terminated or truncated:
            break

    elapsed_s = time.perf_counter() - started_at
    snapshot = env.simulator.statistics.snapshot()
    now = datetime.now()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = _build_output_base_name(now=now, args=args)
    summary_path = output_dir / f"{base_name}.summary.json"
    trace_path = output_dir / f"{base_name}.trace.jsonl" if args.write_step_trace else None
    disruptions_path = output_dir / f"{base_name}.disruptions.json"

    summary = {
        "date": now.isoformat(),
        "heuristic": "FFQoTA_Otimizada",
        "allow_disruption_fallback": allow_fallback,
        "topology_id": scenario.topology_id,
        "load": float(scenario.load),
        "margin": float(scenario.margin),
        "seed": int(scenario.seed or 0),
        "episode_length_requested": int(scenario.episode_length),
        "steps_executed": int(env.simulator.steps_completed),
        "stopped_on_first_disruption": bool(args.stop_on_first_disruption and first_disruption_step is not None),
        "stop_after_disruptions": int(args.stop_after_disruptions),
        "stopped_after_requested_disruptions": bool(
            args.stop_after_disruptions > 0
            and int(snapshot.episode_disrupted_services) >= int(args.stop_after_disruptions)
        ),
        "first_disruption_step": first_disruption_step,
        "measure_disruptions": bool(scenario.measure_disruptions),
        "drop_on_disruption": bool(scenario.drop_on_disruption),
        "service_blocking_rate": float(snapshot.episode_service_blocking_rate),
        "service_served_rate": float(snapshot.episode_service_served_rate),
        "bit_rate_blocking_rate": float(snapshot.episode_bit_rate_blocking_rate),
        "services_processed": int(snapshot.episode_services_processed),
        "services_accepted": int(snapshot.episode_services_accepted),
        "services_served": int(snapshot.episode_services_served),
        "blocked_due_to_resources": int(snapshot.episode_services_blocked_resources),
        "blocked_due_to_osnr": int(snapshot.episode_services_blocked_qot),
        "rejected": int(snapshot.episode_services_rejected_by_agent),
        "episode_disrupted_services_count": int(snapshot.episode_disrupted_services),
        "episode_disrupted_services_rate": float(snapshot.episode_disrupted_services_rate),
        "disrupted_or_dropped_services": int(snapshot.episode_services_dropped_qot),
        "disruption_event_count": len(disruption_events),
        "elapsed_s": float(elapsed_s),
        "status_sequence_tail": statuses[-10:],
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    disruptions_path.write_text(json.dumps(disruption_events, indent=2), encoding="utf-8")
    if trace_path is not None:
        write_step_trace_jsonl(env.export_step_trace(), trace_path)
    return TraceDisruptionsRun(
        summary_path=summary_path,
        trace_path=trace_path,
        disruptions_path=disruptions_path,
        summary=summary,
    )


def main() -> None:
    args = build_parser().parse_args()
    result = run_trace(args)
    print(f"Summary saved to: {result.summary_path}")
    if result.trace_path is None:
        print("Step trace disabled. Use --write-step-trace to save the heavy JSONL trace.")
    else:
        print(f"Trace saved to: {result.trace_path}")
    print(f"Disruption report saved to: {result.disruptions_path}")
    print(
        "Disruptions:"
        f" {result.summary['episode_disrupted_services_count']}"
        f" | dropped={result.summary['disrupted_or_dropped_services']}"
        f" | first_step={result.summary['first_disruption_step']}"
        f" | steps={result.summary['steps_executed']}"
    )


if __name__ == "__main__":
    main()
