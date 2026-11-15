"""Controlador de execução de simulação em paralelo para a GUI.

Gerencia o pool de subprocessos usando a estratégia 'spawn', permitindo
executar simulações heurísticas de forma assíncrona sem travar a interface Qt.
"""

from __future__ import annotations

import multiprocessing
import random
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from PySide6.QtCore import QObject, Signal, QMutex, QMutexLocker

from optical_networking_gym_v2 import ScenarioConfig, get_modulations, make_env
from optical_networking_gym_v2.contracts.enums import TrafficMode
from optical_networking_gym_v2.gui.models.run_config import RunConfig
from optical_networking_gym_v2.gui.controllers.progress_tracker import ProgressTracker


POLICY_NAME_MAP: dict[str, str] = {
    "select_first_fit_action": "First_Fit",
    "select_random_action": "Random",
    "select_highest_snr_first_fit_action": "Highest_SNR",
    "select_load_balancing_action": "Load_Balancing",
    "select_lowest_fragmentation_action": "Lowest_Fragmentation",
    "select_ksp_best_mod_last_fit_action": "KSP_Best_Mod_Last_Fit",
}


def _run_single_simulation_task(task_params: dict[str, Any]) -> dict[str, Any]:
    """Executa uma única rodada de simulação em um processo separado (picklable).

    Parameters
    ----------
    task_params : dict[str, Any]
        Parâmetros configurados para a tarefa de simulação.

    Returns
    -------
    dict[str, Any]
        Dicionário contendo as métricas de desempenho e status da rodada.
    """
    start_time = time.perf_counter()
    try:
        # Resolve as modulações a partir dos nomes fornecidos
        modulations_list = task_params.get("modulations", ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"])
        if isinstance(modulations_list, (list, tuple)):
            modulations_str = ",".join(modulations_list)
        else:
            modulations_str = str(modulations_list)
        modulations = get_modulations(modulations_str)

        # Trata o modo de tráfego (Dynamic ou Static)
        traffic_mode_str = task_params.get("traffic_mode", "dynamic")
        traffic_mode = TrafficMode(traffic_mode_str)

        episode_index = int(task_params.get("episode_index", 0))
        exact_seed = task_params.get("exact_seed")
        raw_seed = task_params.get("seed")
        if exact_seed is not None:
            episode_seed = int(exact_seed)
        elif raw_seed is None:
            episode_seed = random.randint(1, 10_000_000)
        else:
            episode_seed = int(raw_seed) + episode_index
        seed_base = episode_seed

        # Instancia as configurações do cenário
        config = ScenarioConfig(
            scenario_id=task_params.get("scenario_id", "gui_run"),
            topology_id=task_params.get("topology_id", "nobel-eu"),
            k_paths=task_params.get("k_paths", 3),
            num_spectrum_resources=task_params.get("num_spectrum_resources", 320),
            episode_length=task_params.get("episode_length", 1000),
            seed=episode_seed,
            max_span_length_km=task_params.get("max_span_length_km", 100.0),
            default_attenuation_db_per_km=task_params.get("default_attenuation_db_per_km", 0.2),
            default_noise_figure_db=task_params.get("default_noise_figure_db", 4.5),
            traffic_mode=traffic_mode,
            bit_rates=tuple(task_params.get("bit_rates", (10, 40, 100, 400))),
            bit_rate_probabilities=tuple(task_params["bit_rate_probabilities"]) if task_params.get("bit_rate_probabilities") is not None else None,
            load=task_params.get("load", 300.0),
            mean_holding_time=task_params.get("mean_holding_time", 100.0),
            qot_constraint=task_params.get("qot_constraint", "ASE+NLI"),
            margin=task_params.get("margin", 0.0),
            modulations=modulations,
            modulations_to_consider=task_params.get("modulations_to_consider"),
            measure_disruptions=task_params.get("measure_disruptions", False),
            drop_on_disruption=task_params.get("drop_on_disruption", False),
            channel_width=task_params.get("channel_width", 12.5),
            frequency_slot_bandwidth=task_params.get("frequency_slot_bandwidth", 12.5e9),
            launch_power_dbm=task_params.get("launch_power_dbm", 0.0),
            enable_observation=False,
        )

        # Inicializa o ambiente do Gym
        env = make_env(config=config)

        # Importa dinamicamente a heurística solicitada
        heuristic_id = task_params.get("heuristic_id", "select_first_fit_action")
        policy_name = POLICY_NAME_MAP.get(heuristic_id, heuristic_id)

        import optical_networking_gym_v2.heuristics.masked_heuristics as masked_heur
        import optical_networking_gym_v2.heuristics.runtime_heuristics as runtime_heur

        heuristic_fn = None
        category = "runtime"

        if hasattr(masked_heur, heuristic_id):
            heuristic_fn = getattr(masked_heur, heuristic_id)
            category = "masked"
        elif hasattr(runtime_heur, heuristic_id):
            heuristic_fn = getattr(runtime_heur, heuristic_id)
            category = "runtime"
        else:
            try:
                import optical_networking_gym_v2.heuristics.runtime_heuristics_test as runtime_test
                if hasattr(runtime_test, heuristic_id):
                    heuristic_fn = getattr(runtime_test, heuristic_id)
                    category = "runtime"
            except ImportError:
                pass

        if heuristic_fn is None:
            import optical_networking_gym_v2 as ong
            if hasattr(ong, heuristic_id):
                heuristic_fn = getattr(ong, heuristic_id)
                if "masked" in heuristic_id or heuristic_id in ["select_first_fit_action", "select_random_action"]:
                    category = "masked"
                else:
                    category = "runtime"

        if heuristic_fn is None:
            raise ValueError(f"Heurística com ID '{heuristic_id}' não encontrada nos módulos.")

        # Loop de simulação do episódio
        _, info = env.reset(seed=episode_seed)
        sim_start = time.perf_counter()

        k_path_counts = [0, 0, 0]
        total_osnr_margin_db = 0.0
        total_entropy = 0.0
        total_route_cuts = 0.0
        total_route_rss = 0.0
        total_initial_slot = 0
        total_slots_allocated = 0

        while True:
            if category == "masked":
                mask = info.get("mask")
                if mask is None:
                    mask = env.action_masks()
                action = int(heuristic_fn(mask))
            else:
                context = env.heuristic_context()
                action = int(heuristic_fn(context))

            _, _, terminated, truncated, info = env.step(action)
            if info.get("accepted", False):
                p_idx = info.get("chosen_path_index")
                if p_idx is not None and 0 <= int(p_idx) < 3:
                    k_path_counts[int(p_idx)] += 1
                c_slot = info.get("chosen_slot")
                if c_slot is not None:
                    total_initial_slot += int(c_slot)
                num_slots = info.get("service_num_slots")
                if num_slots is not None:
                    total_slots_allocated += int(num_slots)
                osnr = float(info.get("osnr", 0.0))
                osnr_req = float(info.get("osnr_req", 0.0))
                if osnr > 0.0 and osnr_req > 0.0:
                    total_osnr_margin_db += (osnr - osnr_req)
                total_entropy += float(info.get("fragmentation_shannon_entropy", 0.0))
                total_route_cuts += float(info.get("fragmentation_route_cuts", 0.0))
                total_route_rss += float(info.get("fragmentation_route_rss", 0.0))
            if terminated or truncated:
                break

        elapsed_time = time.perf_counter() - sim_start

        # Coleta os snapshots de estatísticas ao fim do episódio
        simulator = env.simulator
        if simulator.statistics is None:
            raise RuntimeError("As estatísticas do simulador não estão disponíveis.")

        snapshot = simulator.statistics.snapshot()
        slot_alloc = simulator.state.slot_allocation

        processed = int(snapshot.episode_services_processed)
        accepted = int(snapshot.episode_services_accepted)
        served = int(snapshot.episode_services_served)
        effective_loss_rate = float((processed - served) / processed) if processed > 0 else 0.0

        mod_hist = dict(snapshot.episode_modulation_histogram) if hasattr(snapshot, "episode_modulation_histogram") else {}
        mod_bpsk = int(mod_hist.get(1, 0))
        mod_qpsk = int(mod_hist.get(2, 0))
        mod_8qam = int(mod_hist.get(3, 0))
        mod_16qam = int(mod_hist.get(4, 0))
        mod_32qam = int(mod_hist.get(5, 0))
        mod_64qam = int(mod_hist.get(6, 0))

        total_spectral_bits = (
            1 * mod_bpsk
            + 2 * mod_qpsk
            + 3 * mod_8qam
            + 4 * mod_16qam
            + 5 * mod_32qam
            + 6 * mod_64qam
        )
        avg_se = (total_spectral_bits / accepted) if accepted > 0 else 0.0

        avg_net_occ = (
            float(np.count_nonzero(slot_alloc != -1)) / slot_alloc.size
            if slot_alloc.size > 0
            else 0.0
        )
        max_lnk_occ = (
            float(np.max(np.count_nonzero(slot_alloc != -1, axis=1))) / config.num_spectrum_resources
            if slot_alloc.size > 0 and config.num_spectrum_resources > 0
            else 0.0
        )
        active_at_end = len(simulator.state.active_services_by_id)

        blk_res = int(snapshot.episode_services_blocked_resources)
        blk_qot = int(snapshot.episode_services_blocked_qot)
        blk_agent = int(snapshot.episode_services_rejected_by_agent)
        tot_blocked = blk_res + blk_qot + blk_agent

        br_req = float(snapshot.episode_bit_rate_requested)
        br_prov = float(snapshot.episode_bit_rate_provisioned)
        bbp = float((br_req - br_prov) / br_req) if br_req > 0 else 0.0

        k0 = k_path_counts[0]
        k1 = k_path_counts[1]
        k2 = k_path_counts[2]
        avg_osnr_margin_db = (total_osnr_margin_db / accepted) if accepted > 0 else 0.0

        return {
            "status": "success",
            "policy": policy_name,
            "heuristic_id": heuristic_id,
            "topology_id": str(config.topology_id),
            "load": float(config.load),
            "margin": float(config.margin),
            "seed_base": int(seed_base),
            "episode_index": int(episode_index),
            "episode_seed": int(episode_seed),
            "steps_requested": int(config.episode_length),
            "processed": processed,
            "accepted": accepted,
            "served": served,
            "blocking_rate": float(snapshot.episode_service_blocking_rate),
            "served_rate": float(snapshot.episode_service_served_rate),
            "effective_loss_rate": float(effective_loss_rate),
            "blocked_resources": blk_res,
            "blocked_qot": blk_qot,
            "rejected_by_agent": blk_agent,
            "disrupted": int(snapshot.episode_disrupted_services),
            "dropped_qot": int(snapshot.episode_services_dropped_qot),
            "disruption_rate": float(snapshot.episode_disrupted_services_rate),
            "mod_bpsk": mod_bpsk,
            "mod_qpsk": mod_qpsk,
            "mod_8qam": mod_8qam,
            "mod_16qam": mod_16qam,
            "mod_32qam": mod_32qam,
            "mod_64qam": mod_64qam,
            "avg_spectral_efficiency": float(avg_se),
            "elapsed_s": float(elapsed_time),
            "bit_rate_requested_gbps": br_req,
            "bit_rate_provisioned_gbps": br_prov,
            "bandwidth_blocking_rate": bbp,
            "blocked_resources_rate": (blk_res / processed) if processed > 0 else 0.0,
            "blocked_qot_rate": (blk_qot / processed) if processed > 0 else 0.0,
            "pct_blocked_due_to_resources": (blk_res / tot_blocked * 100.0) if tot_blocked > 0 else 0.0,
            "pct_blocked_due_to_qot": (blk_qot / tot_blocked * 100.0) if tot_blocked > 0 else 0.0,
            "avg_network_occupancy": float(avg_net_occ),
            "max_link_occupancy": float(max_lnk_occ),
            "active_services_at_end": int(active_at_end),
            "k0_count": k0,
            "k1_count": k1,
            "k2_count": k2,
            "k0_pct": (k0 / accepted * 100.0) if accepted > 0 else 0.0,
            "k1_pct": (k1 / accepted * 100.0) if accepted > 0 else 0.0,
            "k2_pct": (k2 / accepted * 100.0) if accepted > 0 else 0.0,
            "avg_osnr_margin_db": float(avg_osnr_margin_db),
            "avg_fragmentation_shannon_entropy": (total_entropy / accepted) if accepted > 0 else 0.0,
            "avg_fragmentation_route_cuts": (total_route_cuts / accepted) if accepted > 0 else 0.0,
            "avg_fragmentation_route_rss": (total_route_rss / accepted) if accepted > 0 else 0.0,
            "avg_slots_per_service": (total_slots_allocated / accepted) if accepted > 0 else 0.0,
            "avg_initial_slot_index": (total_initial_slot / accepted) if accepted > 0 else 0.0,
            # Aliases de compatibilidade interna
            "seed": int(episode_seed),
            "requests_per_episode": int(config.episode_length),
            "services_processed": processed,
            "services_accepted": accepted,
            "services_served": served,
            "service_blocking_rate": float(snapshot.episode_service_blocking_rate),
            "service_served_rate": float(snapshot.episode_service_served_rate),
            "bit_rate_blocking_rate": bbp,
            "services_blocked_resources": blk_res,
            "services_blocked_qot": blk_qot,
            "services_rejected_by_agent": blk_agent,
            "bit_rate_requested": br_req,
            "bit_rate_provisioned": br_prov,
            "disrupted_services": int(snapshot.episode_disrupted_services),
            "services_dropped_qot": int(snapshot.episode_services_dropped_qot),
            "disrupted_services_rate": float(snapshot.episode_disrupted_services_rate),
            "mean_accepted_osnr": float(avg_osnr_margin_db),
            "modulation_histogram": list(snapshot.episode_modulation_histogram),
            "episode_time_s": float(elapsed_time),
            "error": None,
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "policy": POLICY_NAME_MAP.get(task_params.get("heuristic_id", "unknown"), task_params.get("heuristic_id", "unknown")),
            "load": task_params.get("load", 0.0),
            "margin": task_params.get("margin", 0.0),
            "heuristic_id": task_params.get("heuristic_id", "unknown"),
            "seed": task_params.get("seed", 42),
            "episode_index": int(task_params.get("episode_index", 0)),
            "services_processed": 0,
            "services_accepted": 0,
            "services_blocked_resources": 0,
            "services_blocked_qot": 0,
            "services_rejected_by_agent": 0,
            "bit_rate_requested": 0.0,
            "bit_rate_provisioned": 0.0,
            "disrupted_services": 0,
            "services_dropped_qot": 0,
            "service_blocking_rate": 1.0,
            "service_served_rate": 0.0,
            "bit_rate_blocking_rate": 1.0,
            "disrupted_services_rate": 0.0,
            "modulation_histogram": [],
            "episode_time_s": time.perf_counter() - start_time,
            "elapsed_s": time.perf_counter() - start_time,
            "error": f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
        }


class SimulationRunner(QObject):
    """Controlador que delega e gerencia simulações paralelizadas.

    Utiliza ProcessPoolExecutor para escalonar tarefas e reporta o progresso
    em tempo real através de sinais Qt customizados.
    """

    sweep_started = Signal(int)  # total_tasks
    task_completed = Signal(dict)  # resultado individual
    progress_updated = Signal(int, int, float)  # concluidas, total, eta_seconds
    sweep_finished = Signal(list)  # lista de resultados individuais
    all_completed = sweep_finished  # Alias para compatibilidade com MainWindow
    sweep_cancelled = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._executor: ProcessPoolExecutor | None = None
        self._progress_tracker: ProgressTracker | None = None
        self._active_futures: list[Any] = []
        self._results: list[dict[str, Any]] = []
        self._is_running: bool = False
        self._mutex: QMutex = QMutex()
        self._total_tasks: int = 0
        self._completed_tasks: int = 0

    def start(self, config: RunConfig) -> None:
        """Inicia o sweep de simulações (alias de start_sweep)."""
        self.start_sweep(config)

    def cancel(self) -> None:
        """Cancela o sweep de simulações (alias de cancel_sweep)."""
        self.cancel_sweep()

    def start_sweep(self, config: RunConfig) -> None:
        """Inicia a execução em lote das tarefas de simulação configuradas.

        Parameters
        ----------
        config : RunConfig
            Objeto contendo a configuração completa da varredura.
        """
        with QMutexLocker(self._mutex):
            if self._is_running:
                self.error_occurred.emit("Já existe uma varredura de simulações ativa.")
                return

            tasks = config.iter_tasks()
            self._total_tasks = len(tasks)
            if self._total_tasks == 0:
                self.error_occurred.emit("Nenhuma tarefa válida para executar.")
                return

            self._results.clear()
            self._active_futures.clear()
            self._completed_tasks = 0
            self._is_running = True
            self._progress_tracker = ProgressTracker(self._total_tasks)

        self.sweep_started.emit(self._total_tasks)

        num_workers = config.num_workers
        if num_workers is None or num_workers <= 0:
            num_workers = max(1, multiprocessing.cpu_count() - 1)

        ctx = multiprocessing.get_context("spawn")
        self._executor = ProcessPoolExecutor(
            max_workers=num_workers,
            mp_context=ctx
        )

        for task in tasks:
            if not self.is_running():
                break
            future = self._executor.submit(_run_single_simulation_task, task)
            self._active_futures.append(future)
            future.add_done_callback(self._on_future_done)

    def _on_future_done(self, future: Any) -> None:
        """Callback executado na conclusão de cada tarefa."""
        self._mutex.lock()
        if not self._is_running:
            self._mutex.unlock()
            return

        if future.cancelled():
            self._mutex.unlock()
            return

        try:
            result = future.result()
        except Exception as e:
            result = {
                "status": "error",
                "load": 0.0,
                "margin": 0.0,
                "heuristic_id": "unknown",
                "seed": 42,
                "error": f"Crash no subprocesso: {str(e)}",
                "episode_time_s": 0.0,
            }

        self._results.append(result)
        self._completed_tasks += 1

        duration = result.get("episode_time_s", 0.0)
        if self._progress_tracker:
            self._progress_tracker.record_task_completion(duration)
            eta = self._progress_tracker.estimate_remaining_time()
        else:
            eta = 0.0

        completed = self._completed_tasks
        total = self._total_tasks
        self._mutex.unlock()

        # Emite os sinais fora da zona de exclusão mútua
        self.task_completed.emit(result)
        self.progress_updated.emit(completed, total, eta)

        if completed >= total:
            self.finish_sweep()

    def finish_sweep(self) -> None:
        """Conclui a varredura ativa coletando os resultados finais."""
        self._mutex.lock()
        if not self._is_running:
            self._mutex.unlock()
            return

        self._is_running = False
        results = list(self._results)
        executor = self._executor
        self._cleanup()
        self._mutex.unlock()

        if executor is not None:
            try:
                executor.shutdown(wait=False)
            except Exception:
                pass

        self.sweep_finished.emit(results)

    def cancel_sweep(self) -> None:
        """Solicita o cancelamento de todas as tarefas da varredura em execução."""
        self._mutex.lock()
        if not self._is_running:
            self._mutex.unlock()
            return

        self._is_running = False

        for future in self._active_futures:
            future.cancel()

        executor = self._executor
        self._cleanup()
        self._mutex.unlock()

        if executor is not None:
            processes = getattr(executor, "_processes", None)
            if isinstance(processes, dict):
                for proc in list(processes.values()):
                    try:
                        if proc is not None and proc.is_alive():
                            proc.kill()
                    except Exception:
                        pass
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

        self.sweep_cancelled.emit()

    def _cleanup(self) -> None:
        """Limpa referências internas aos futuros e executors."""
        self._executor = None
        self._active_futures.clear()
        self._completed_tasks = 0

    def is_running(self) -> bool:
        """Informa se a simulação está ativa."""
        with QMutexLocker(self._mutex):
            return self._is_running
