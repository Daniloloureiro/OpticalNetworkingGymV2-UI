from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gnpy.core.elements import Fiber
from gnpy.core.info import create_arbitrary_spectral_information
from gnpy.core.science_utils import NliSolver, RamanSolver

from optical_networking_gym_v2 import BUILTIN_TOPOLOGY_DIR, make_env
from optical_networking_gym_v2.optical.kernels.qot_kernel import accumulate_link_noise
from optical_networking_gym_v2.utils import select_masked_first_fit_policy


PHI_MODULATION_BY_SE = {
    1: 1.0,
    2: 1.0,
    3: 2.0 / 3.0,
    4: 17.0 / 25.0,
    5: 69.0 / 100.0,
    6: 13.0 / 21.0,
}


def _ratio_to_db(value: float) -> float:
    return 10.0 * math.log10(1.0 / value) if value > 0.0 else 0.0


def _active_channels_for_link(state: object, link_id: int) -> list[object]:
    return [
        state.active_services_by_id[service_id]
        for service_id in sorted(state.link_active_service_ids[link_id])
        if service_id in state.active_services_by_id
    ]


def _ong_link_noise(topology: object, target: object, channels: list[object], link_id: int) -> tuple[float, float]:
    link = topology.links[link_id]
    _, ase_ratio, nli_ratio = accumulate_link_noise(
        np.array([span.length_km for span in link.spans], dtype=np.float64),
        np.array([span.attenuation_normalized for span in link.spans], dtype=np.float64),
        np.array([span.noise_figure_normalized for span in link.spans], dtype=np.float64),
        np.array([service.service_id for service in channels], dtype=np.int32),
        np.array([service.center_frequency for service in channels], dtype=np.float64),
        np.array([service.bandwidth for service in channels], dtype=np.float64),
        np.array(
            [PHI_MODULATION_BY_SE[service.modulation.spectral_efficiency] for service in channels],
            dtype=np.float64,
        ),
        current_service_id=target.service_id,
        center_frequency=target.center_frequency,
        bandwidth=target.bandwidth,
        launch_power=target.launch_power,
        include_nli=True,
    )
    return float(ase_ratio), float(nli_ratio)


def _gnpy_link_nli_ratio(topology: object, target: object, channels: list[object], link_id: int) -> float:
    ordered_channels = sorted(channels, key=lambda service: service.center_frequency)
    labels = np.array([str(service.service_id) for service in ordered_channels])
    spectral_info = create_arbitrary_spectral_information(
        frequency=np.array([service.center_frequency for service in ordered_channels], dtype=float),
        pch=np.array([service.launch_power for service in ordered_channels], dtype=float),
        baud_rate=np.array([service.bandwidth for service in ordered_channels], dtype=float),
        tx_osnr=np.full(len(ordered_channels), 100.0, dtype=float),
        slot_width=np.array([service.bandwidth for service in ordered_channels], dtype=float),
        roll_off=0.0,
        label=labels,
    )
    target_pos = int(np.where(labels == str(target.service_id))[0][0])

    total_ratio = 0.0
    for span_index, span in enumerate(topology.links[link_id].spans):
        fiber = Fiber(
            uid=f"link{link_id}_span{span_index}",
            params={
                "length": float(span.length_km),
                "length_units": "km",
                "loss_coef": float(span.attenuation_db_per_km),
                "pmd_coef": 0.0,
                "gamma": 1.3e-3,
                "dispersion": 1.67e-05,
                "con_in": 0.0,
                "con_out": 0.0,
                "att_in": 0.0,
            },
        )
        srs = RamanSolver.calculate_stimulated_raman_scattering(spectral_info, fiber)
        nli_power = NliSolver.compute_nli(spectral_info, srs, fiber)
        total_ratio += float(nli_power[target_pos] / target.launch_power)
    return total_ratio


def _print_link_trace(state: object, topology: object) -> None:
    print("  link trace:")
    for link in topology.links:
        channels = _active_channels_for_link(state, link.id)
        payload = [
            f"svc={service.service_id}:slots={service.service_slot_start}-{service.service_slot_end_exclusive}"
            for service in channels
        ]
        print(f"    link {link.id} {link.source_name}-{link.target_name}: channels={len(channels)} {payload}")


def run_validation(args: argparse.Namespace) -> None:
    env = make_env(
        "ring_4",
        topology_dir=BUILTIN_TOPOLOGY_DIR,
        seed=args.seed,
        load=args.load,
        margin=args.margin,
        episode_length=args.steps,
        k_paths=2,
        num_spectrum_resources=args.spectrum_slots,
        bit_rates=(args.bit_rate,),
        bit_rate_probabilities=(1.0,),
        measure_disruptions=True,
        drop_on_disruption=False,
    )
    _, info = env.reset(seed=args.seed)
    topology = env.simulator.topology

    for step in range(1, args.steps + 1):
        request = env.simulator.current_request
        action = select_masked_first_fit_policy(env, info)
        _, _, _, _, info = env.step(action)
        state = env.simulator.state

        print(
            f"step {step:02d} request svc={request.service_id} "
            f"{request.source_id}->{request.destination_id} bit_rate={request.bit_rate}"
        )
        if args.trace_links:
            _print_link_trace(state, topology)

        if request.service_id not in state.active_services_by_id:
            print("  allocation: BLOCKED")
            continue

        target = state.active_services_by_id[request.service_id]
        ong_ase_ratio = 0.0
        ong_nli_ratio = 0.0
        gnpy_nli_ratio = 0.0
        print(
            "  allocation: ACCEPTED "
            f"path={list(target.path.link_ids)} slots={target.service_slot_start}-{target.service_slot_end_exclusive} "
            f"f={target.center_frequency / 1e12:.6f}THz bw={target.bandwidth / 1e9:.1f}GHz"
        )

        for link_id in target.link_ids:
            channels = _active_channels_for_link(state, link_id)
            link_ase, link_ong_nli = _ong_link_noise(topology, target, channels, link_id)
            link_gnpy_nli = _gnpy_link_nli_ratio(topology, target, channels, link_id)
            ong_ase_ratio += link_ase
            ong_nli_ratio += link_ong_nli
            gnpy_nli_ratio += link_gnpy_nli
            print(
                f"    qot link {link_id}: shared_channels={len(channels)} "
                f"ASEratio={link_ase:.3e} ONG_NLIratio={link_ong_nli:.3e} "
                f"GNPy_NLIratio={link_gnpy_nli:.3e}"
            )

        ong_recalc_osnr = _ratio_to_db(ong_ase_ratio + ong_nli_ratio)
        gnpy_hybrid_osnr = _ratio_to_db(ong_ase_ratio + gnpy_nli_ratio)
        factor = gnpy_nli_ratio / ong_nli_ratio if ong_nli_ratio > 0.0 else 0.0
        print(
            f"  summary: ONG_osnr={target.osnr:.3f}dB ONG_recalc={ong_recalc_osnr:.3f}dB "
            f"GNPy_NLI_plus_ONG_ASE={gnpy_hybrid_osnr:.3f}dB "
            f"delta={gnpy_hybrid_osnr - ong_recalc_osnr:+.3f}dB"
        )
        print(
            f"  nli_only: ONG={_ratio_to_db(ong_nli_ratio):.3f}dB "
            f"GNPy={_ratio_to_db(gnpy_nli_ratio):.3f}dB factor={factor:.3g}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ONG v2 ring_4 QoT NLI against GNPy.")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--load", type=float, default=500.0)
    parser.add_argument("--margin", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=10)
    parser.add_argument("--spectrum-slots", type=int, default=24)
    parser.add_argument("--bit-rate", type=int, default=40)
    parser.add_argument(
        "--trace-links",
        action="store_true",
        help="Print the full per-link occupancy trace. Disabled by default for normal runs.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run_validation(parse_args())
