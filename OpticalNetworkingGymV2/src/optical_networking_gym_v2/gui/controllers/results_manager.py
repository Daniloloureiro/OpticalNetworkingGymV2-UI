"""Gerenciador e exportador de resultados de simulação no padrão exclusivo (episodes.csv e summary.csv).

Agrega e processa os dicionários de resultados retornados pelo executor de simulações,
calculando exatamente as 28 colunas de episodes.csv e as 45 colunas de summary.csv.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import statistics
from typing import Any

from optical_networking_gym_v2.gui.controllers.simulation_runner import POLICY_NAME_MAP


EPISODES_FIELDNAMES: list[str] = [
    "policy",
    "topology_id",
    "load",
    "margin",
    "seed_base",
    "episode_index",
    "episode_seed",
    "steps_requested",
    "processed",
    "accepted",
    "served",
    "blocking_rate",
    "served_rate",
    "effective_loss_rate",
    "blocked_resources",
    "blocked_qot",
    "rejected_by_agent",
    "disrupted",
    "dropped_qot",
    "disruption_rate",
    "mod_bpsk",
    "mod_qpsk",
    "mod_8qam",
    "mod_16qam",
    "mod_32qam",
    "mod_64qam",
    "avg_spectral_efficiency",
    "elapsed_s",
]

SUMMARY_FIELDNAMES: list[str] = [
    "policy",
    "topology_id",
    "load",
    "margin",
    "episodes",
    "requests_per_episode",
    "total_requests",
    "blocking_rate_mean",
    "blocking_rate_std",
    "served_rate_mean",
    "served_rate_std",
    "effective_loss_rate_mean",
    "effective_loss_rate_std",
    "disrupted_mean",
    "disrupted_std",
    "disruption_rate_mean",
    "disruption_rate_std",
    "bandwidth_blocking_rate_mean",
    "bandwidth_blocking_rate_std",
    "pct_blocked_due_to_resources_mean",
    "pct_blocked_due_to_qot_mean",
    "avg_network_occupancy_mean",
    "max_link_occupancy_mean",
    "k0_pct_mean",
    "k1_pct_mean",
    "k2_pct_mean",
    "avg_osnr_margin_db_mean",
    "avg_fragmentation_shannon_entropy_mean",
    "avg_slots_per_service_mean",
    "mod_bpsk_mean",
    "mod_qpsk_mean",
    "mod_8qam_mean",
    "mod_16qam_mean",
    "mod_32qam_mean",
    "mod_64qam_mean",
    "mod_bpsk_pct",
    "mod_qpsk_pct",
    "mod_8qam_pct",
    "mod_16qam_pct",
    "mod_32qam_pct",
    "mod_64qam_pct",
    "avg_spectral_efficiency_mean",
    "avg_spectral_efficiency_std",
    "elapsed_s_mean",
    "elapsed_s_total",
]

# Aliases para compatibilidade de importação
LEGACY_CSV_FIELDNAMES = EPISODES_FIELDNAMES


def default_results_dir() -> Path:
    """Pasta padrão dos CSVs: ~/Documentos/OpticalNetworkingGym/results_csv.

    Usa a pasta de documentos do usuário (Windows e Linux) para funcionar
    também nos executáveis empacotados, onde o diretório atual pode ser
    somente leitura (ex.: C:\\Program Files).
    """
    docs: Path | None = None
    try:
        from PySide6.QtCore import QStandardPaths

        loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if loc:
            docs = Path(loc)
    except Exception:
        docs = None
    if docs is None:
        docs = Path.home() / "Documents"
    return docs / "OpticalNetworkingGym" / "results_csv"


def _normalize_policy_name(res: dict[str, Any]) -> str:
    raw_policy = str(res.get("policy", res.get("heuristic_id", "First_Fit")))
    return POLICY_NAME_MAP.get(raw_policy, raw_policy)


def _extract_mod_counts(res: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    if "mod_bpsk" in res:
        return (
            int(res.get("mod_bpsk", 0)),
            int(res.get("mod_qpsk", 0)),
            int(res.get("mod_8qam", 0)),
            int(res.get("mod_16qam", 0)),
            int(res.get("mod_32qam", 0)),
            int(res.get("mod_64qam", 0)),
        )
    hist_raw = res.get("modulation_histogram", [])
    mod_hist: dict[int, int] = {}
    if isinstance(hist_raw, dict):
        mod_hist = {int(k): int(v) for k, v in hist_raw.items()}
    elif isinstance(hist_raw, (list, tuple)):
        for item in hist_raw:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                mod_hist[int(item[0])] = int(item[1])
    return (
        int(mod_hist.get(1, 0)),
        int(mod_hist.get(2, 0)),
        int(mod_hist.get(3, 0)),
        int(mod_hist.get(4, 0)),
        int(mod_hist.get(5, 0)),
        int(mod_hist.get(6, 0)),
    )


def format_episode_csv_row(res: dict[str, Any]) -> dict[str, Any]:
    """Converte um dicionário de resultado de simulação para uma linha exata de episodes.csv (28 colunas)."""
    processed = int(res.get("processed", res.get("services_processed", 0)))
    accepted = int(res.get("accepted", res.get("services_accepted", 0)))
    served = int(res.get("served", res.get("services_served", accepted - int(res.get("services_dropped_qot", 0)))))
    disruption_rate = float(res.get("disruption_rate", res.get("disrupted_services_rate", 0.0)))
    effective_loss_rate = float(
        res.get(
            "effective_loss_rate",
            ((processed - served) / processed) if processed > 0 else 0.0,
        )
    )
    seed_val = int(res.get("seed_base", res.get("seed", 10)))
    episode_index = int(res.get("episode_index", 0))
    episode_seed = int(res.get("episode_seed", seed_val))

    mod_bpsk, mod_qpsk, mod_8qam, mod_16qam, mod_32qam, mod_64qam = _extract_mod_counts(res)
    total_spectral_bits = (
        1 * mod_bpsk
        + 2 * mod_qpsk
        + 3 * mod_8qam
        + 4 * mod_16qam
        + 5 * mod_32qam
        + 6 * mod_64qam
    )
    avg_se = float(
        res.get(
            "avg_spectral_efficiency",
            (total_spectral_bits / accepted) if accepted > 0 else 0.0,
        )
    )

    return {
        "policy": _normalize_policy_name(res),
        "topology_id": str(res.get("topology_id", "nobel-eu")),
        "load": float(res.get("load", 0.0)),
        "margin": float(res.get("margin", 0.0)),
        "seed_base": seed_val,
        "episode_index": episode_index,
        "episode_seed": episode_seed,
        "steps_requested": int(res.get("steps_requested", res.get("requests_per_episode", processed))),
        "processed": processed,
        "accepted": accepted,
        "served": served,
        "blocking_rate": float(res.get("blocking_rate", res.get("service_blocking_rate", 0.0))),
        "served_rate": float(res.get("served_rate", res.get("service_served_rate", 0.0))),
        "effective_loss_rate": effective_loss_rate,
        "blocked_resources": int(res.get("blocked_resources", res.get("services_blocked_resources", 0))),
        "blocked_qot": int(res.get("blocked_qot", res.get("services_blocked_qot", 0))),
        "rejected_by_agent": int(res.get("rejected_by_agent", res.get("services_rejected_by_agent", 0))),
        "disrupted": int(res.get("disrupted", res.get("disrupted_services", 0))),
        "dropped_qot": int(res.get("dropped_qot", res.get("services_dropped_qot", 0))),
        "disruption_rate": disruption_rate,
        "mod_bpsk": mod_bpsk,
        "mod_qpsk": mod_qpsk,
        "mod_8qam": mod_8qam,
        "mod_16qam": mod_16qam,
        "mod_32qam": mod_32qam,
        "mod_64qam": mod_64qam,
        "avg_spectral_efficiency": avg_se,
        "elapsed_s": float(res.get("elapsed_s", res.get("episode_time_s", 0.0))),
    }


# Alias para compatibilidade
format_legacy_csv_row = format_episode_csv_row


def build_summary_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrega os episódios por (policy, topology_id, load, margin) gerando as 45 colunas de summary.csv."""
    valid_results = [r for r in results if r.get("status", "success") != "error"]
    if not valid_results:
        return []

    grouped: dict[tuple[str, str, float, float], list[dict[str, Any]]] = {}
    for res in valid_results:
        policy = _normalize_policy_name(res)
        topo = str(res.get("topology_id", "nobel-eu"))
        load = float(res.get("load", 0.0))
        margin = float(res.get("margin", 0.0))
        grouped.setdefault((policy, topo, load, margin), []).append(res)

    summary_rows: list[dict[str, Any]] = []
    for (policy, topo, load, margin), rows in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3])
    ):
        ep_rows = [format_episode_csv_row(r) for r in rows]
        episodes_count = len(ep_rows)

        blocking_rates = [float(r["blocking_rate"]) for r in ep_rows]
        served_rates = [float(r["served_rate"]) for r in ep_rows]
        loss_rates = [float(r["effective_loss_rate"]) for r in ep_rows]
        disrupted_counts = [int(r["disrupted"]) for r in ep_rows]
        disruption_rates = [float(r["disruption_rate"]) for r in ep_rows]
        elapsed_times = [float(r["elapsed_s"]) for r in ep_rows]

        bpsk_counts = [int(r["mod_bpsk"]) for r in ep_rows]
        qpsk_counts = [int(r["mod_qpsk"]) for r in ep_rows]
        qam8_counts = [int(r["mod_8qam"]) for r in ep_rows]
        qam16_counts = [int(r["mod_16qam"]) for r in ep_rows]
        qam32_counts = [int(r["mod_32qam"]) for r in ep_rows]
        qam64_counts = [int(r["mod_64qam"]) for r in ep_rows]
        avg_se_list = [float(r["avg_spectral_efficiency"]) for r in ep_rows]

        total_acc = sum(int(r["accepted"]) for r in ep_rows)
        tot_bpsk = sum(bpsk_counts)
        tot_qpsk = sum(qpsk_counts)
        tot_8qam = sum(qam8_counts)
        tot_16qam = sum(qam16_counts)
        tot_32qam = sum(qam32_counts)
        tot_64qam = sum(qam64_counts)

        bbp_list: list[float] = []
        blk_res_pct: list[float] = []
        blk_qot_pct: list[float] = []
        net_occ_list: list[float] = []
        max_occ_list: list[float] = []
        k0_pct_list: list[float] = []
        k1_pct_list: list[float] = []
        k2_pct_list: list[float] = []
        osnr_marg_list: list[float] = []
        entropy_list: list[float] = []
        slots_list: list[float] = []

        for raw_r, ep_r in zip(rows, ep_rows):
            if "bandwidth_blocking_rate" in raw_r:
                bbp_val = float(raw_r["bandwidth_blocking_rate"])
            else:
                br_req = float(raw_r.get("bit_rate_requested", 0.0))
                br_prov = float(raw_r.get("bit_rate_provisioned", 0.0))
                bbp_val = float((br_req - br_prov) / br_req) if br_req > 0 else float(raw_r.get("bit_rate_blocking_rate", 0.0))
            bbp_list.append(bbp_val)

            blk_res = int(ep_r["blocked_resources"])
            blk_qot = int(ep_r["blocked_qot"])
            blk_agent = int(ep_r["rejected_by_agent"])
            tot_blk = blk_res + blk_qot + blk_agent

            blk_res_pct.append(
                float(raw_r.get("pct_blocked_due_to_resources", (blk_res / tot_blk * 100.0) if tot_blk > 0 else 0.0))
            )
            blk_qot_pct.append(
                float(raw_r.get("pct_blocked_due_to_qot", (blk_qot / tot_blk * 100.0) if tot_blk > 0 else 0.0))
            )
            net_occ_list.append(float(raw_r.get("avg_network_occupancy", 0.0)))
            max_occ_list.append(float(raw_r.get("max_link_occupancy", 0.0)))
            k0_pct_list.append(float(raw_r.get("k0_pct", 0.0)))
            k1_pct_list.append(float(raw_r.get("k1_pct", 0.0)))
            k2_pct_list.append(float(raw_r.get("k2_pct", 0.0)))
            osnr_marg_list.append(float(raw_r.get("avg_osnr_margin_db", raw_r.get("mean_accepted_osnr", 0.0))))
            entropy_list.append(float(raw_r.get("avg_fragmentation_shannon_entropy", 0.0)))
            slots_list.append(float(raw_r.get("avg_slots_per_service", 0.0)))

        summary_rows.append({
            "policy": policy,
            "topology_id": topo,
            "load": load,
            "margin": margin,
            "episodes": episodes_count,
            "requests_per_episode": int(ep_rows[0]["steps_requested"]),
            "total_requests": sum(int(r["processed"]) for r in ep_rows),
            "blocking_rate_mean": statistics.fmean(blocking_rates),
            "blocking_rate_std": statistics.stdev(blocking_rates) if len(blocking_rates) > 1 else 0.0,
            "served_rate_mean": statistics.fmean(served_rates),
            "served_rate_std": statistics.stdev(served_rates) if len(served_rates) > 1 else 0.0,
            "effective_loss_rate_mean": statistics.fmean(loss_rates),
            "effective_loss_rate_std": statistics.stdev(loss_rates) if len(loss_rates) > 1 else 0.0,
            "disrupted_mean": statistics.fmean(disrupted_counts),
            "disrupted_std": statistics.stdev(disrupted_counts) if len(disrupted_counts) > 1 else 0.0,
            "disruption_rate_mean": statistics.fmean(disruption_rates),
            "disruption_rate_std": statistics.stdev(disruption_rates) if len(disruption_rates) > 1 else 0.0,
            "bandwidth_blocking_rate_mean": statistics.fmean(bbp_list),
            "bandwidth_blocking_rate_std": statistics.stdev(bbp_list) if len(bbp_list) > 1 else 0.0,
            "pct_blocked_due_to_resources_mean": statistics.fmean(blk_res_pct),
            "pct_blocked_due_to_qot_mean": statistics.fmean(blk_qot_pct),
            "avg_network_occupancy_mean": statistics.fmean(net_occ_list),
            "max_link_occupancy_mean": statistics.fmean(max_occ_list),
            "k0_pct_mean": statistics.fmean(k0_pct_list),
            "k1_pct_mean": statistics.fmean(k1_pct_list),
            "k2_pct_mean": statistics.fmean(k2_pct_list),
            "avg_osnr_margin_db_mean": statistics.fmean(osnr_marg_list),
            "avg_fragmentation_shannon_entropy_mean": statistics.fmean(entropy_list),
            "avg_slots_per_service_mean": statistics.fmean(slots_list),
            "mod_bpsk_mean": statistics.fmean(bpsk_counts),
            "mod_qpsk_mean": statistics.fmean(qpsk_counts),
            "mod_8qam_mean": statistics.fmean(qam8_counts),
            "mod_16qam_mean": statistics.fmean(qam16_counts),
            "mod_32qam_mean": statistics.fmean(qam32_counts),
            "mod_64qam_mean": statistics.fmean(qam64_counts),
            "mod_bpsk_pct": (tot_bpsk / total_acc * 100.0) if total_acc > 0 else 0.0,
            "mod_qpsk_pct": (tot_qpsk / total_acc * 100.0) if total_acc > 0 else 0.0,
            "mod_8qam_pct": (tot_8qam / total_acc * 100.0) if total_acc > 0 else 0.0,
            "mod_16qam_pct": (tot_16qam / total_acc * 100.0) if total_acc > 0 else 0.0,
            "mod_32qam_pct": (tot_32qam / total_acc * 100.0) if total_acc > 0 else 0.0,
            "mod_64qam_pct": (tot_64qam / total_acc * 100.0) if total_acc > 0 else 0.0,
            "avg_spectral_efficiency_mean": statistics.fmean(avg_se_list),
            "avg_spectral_efficiency_std": statistics.stdev(avg_se_list) if len(avg_se_list) > 1 else 0.0,
            "elapsed_s_mean": statistics.fmean(elapsed_times),
            "elapsed_s_total": sum(elapsed_times),
        })

    return summary_rows


def write_episodes_csv(results: list[dict[str, Any]], file_path: Path) -> None:
    """Grava episodes.csv com exatamente as 28 colunas padrão."""
    rows = [
        format_episode_csv_row(res)
        for res in results
        if res.get("status", "success") != "error"
    ]
    if not rows:
        raise ValueError("Nenhuma simulação concluída com sucesso para exportar em episodes.csv.")

    rows.sort(key=lambda x: (str(x["policy"]), float(x["load"]), float(x["margin"]), int(x["episode_index"])))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EPISODES_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_csv(results: list[dict[str, Any]], file_path: Path) -> None:
    """Grava summary.csv com exatamente as 45 colunas padrão."""
    summary_rows = build_summary_rows(results)
    if not summary_rows:
        raise ValueError("Nenhuma simulação concluída com sucesso para exportar em summary.csv.")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(summary_rows)


class ResultsManager:
    """Gerencia a agregação, formatação e persistência exclusiva de episodes.csv e summary.csv."""

    def __init__(self) -> None:
        self._raw_results: list[dict[str, Any]] = []
        self.last_generated_csv_paths: list[Path] = []

    def add_result(self, result: dict[str, Any]) -> None:
        """Adiciona um resultado individual à lista de resultados."""
        self._raw_results.append(result)

    def clear(self) -> None:
        """Limpa todos os resultados armazenados."""
        self._raw_results.clear()

    def set_results(self, results: list[dict[str, Any]]) -> None:
        """Armazena a lista de resultados brutos obtida das simulações."""
        self._raw_results = results

    def get_raw_results(self) -> list[dict[str, Any]]:
        """Retorna a lista bruta de resultados."""
        return self._raw_results

    def get_episode_rows(self) -> list[dict[str, Any]]:
        """Retorna as linhas formatadas de episodes.csv (28 colunas)."""
        rows = [
            format_episode_csv_row(res)
            for res in self._raw_results
            if res.get("status", "success") != "error"
        ]
        rows.sort(key=lambda x: (str(x["policy"]), float(x["load"]), float(x["margin"]), int(x["episode_index"])))
        return rows

    def get_summary_rows(self) -> list[dict[str, Any]]:
        """Retorna as linhas consolidadas de summary.csv (45 colunas)."""
        return build_summary_rows(self._raw_results)

    def export_episodes_csv(self, file_path: Path) -> None:
        """Exporta o arquivo episodes.csv (28 colunas)."""
        if not self._raw_results:
            raise ValueError("Não há resultados para exportar.")
        write_episodes_csv(self._raw_results, file_path)

    def export_summary_csv(self, file_path: Path) -> None:
        """Exporta o arquivo summary.csv (45 colunas)."""
        if not self._raw_results:
            raise ValueError("Não há resultados para exportar.")
        write_summary_csv(self._raw_results, file_path)

    def export_csv(self, file_path: Path) -> None:
        """Exporta CSV escolhendo summary.csv ou episodes.csv conforme o nome do arquivo."""
        if "episode" in file_path.stem.lower():
            self.export_episodes_csv(file_path)
        else:
            self.export_summary_csv(file_path)

    def save_pair_in_directory(self, target_dir: Path) -> list[Path]:
        """Grava exatamente episodes.csv e summary.csv dentro de target_dir."""
        if not self._raw_results:
            raise ValueError("Não há resultados para exportar.")
        target_dir.mkdir(parents=True, exist_ok=True)
        episodes_csv_path = target_dir / "episodes.csv"
        summary_csv_path = target_dir / "summary.csv"
        self.export_episodes_csv(episodes_csv_path)
        self.export_summary_csv(summary_csv_path)
        self.last_generated_csv_paths = [episodes_csv_path, summary_csv_path]
        return self.last_generated_csv_paths

    def auto_save_legacy_csvs(self, scenario_id: str = "simulacao", output_dir: Path | None = None) -> list[Path]:
        """Gera automaticamente exclusivamente os arquivos episodes.csv e summary.csv."""
        if not self._raw_results:
            return []

        if output_dir is not None:
            return self.save_pair_in_directory(output_dir)

        root_dir = default_results_dir()
        root_dir.mkdir(parents=True, exist_ok=True)

        now_str = datetime.now().strftime("%d-%m-%Y_%Hh%Mm%Ss")
        safe_id = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in scenario_id).strip("_") or "simulacao"

        run_dir = root_dir / f"{safe_id}_{now_str}"
        suffix = 1
        while run_dir.exists():
            suffix += 1
            run_dir = root_dir / f"{safe_id}_{now_str}_{suffix}"

        return self.save_pair_in_directory(run_dir)
