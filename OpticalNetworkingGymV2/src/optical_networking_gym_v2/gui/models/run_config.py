"""
Modelo de configuração de execução de simulação.

Define a configuração completa para uma rodada de simulação,
incluindo modo de execução, heurísticas selecionadas e paralelismo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RunMode(StrEnum):
    """Modos de execução de simulação."""

    SINGLE = "single"
    """Simulação simples com os parâmetros configurados."""

    LOAD_SWEEP = "load_sweep"
    """Varredura sobre múltiplos valores de carga."""

    MARGIN_SWEEP = "margin_sweep"
    """Varredura sobre múltiplos valores de margem."""

    GRID = "grid"
    """Grade completa: carga × margem."""


@dataclass(frozen=True, slots=True)
class HeuristicEntry:
    """Metadados de uma heurística disponível.

    Attributes
    ----------
    id : str
        Nome da função da heurística (ex: ``select_first_fit_action``).
    name : str
        Nome exibido na interface.
    description : str
        Descrição detalhada do algoritmo.
    category : str
        Categoria (``masked`` ou ``runtime``).
    complexity : str
        Nível de complexidade (``low``, ``medium``, ``high``).
    """

    id: str
    name: str
    description: str
    category: str = "runtime"
    complexity: str = "low"


# ── Catálogo de heurísticas ──────────────────────────────────────

HEURISTIC_CATALOG: tuple[HeuristicEntry, ...] = (
    HeuristicEntry(
        id="select_first_fit_action",
        name="First Fit",
        description=(
            "Atribui o primeiro caminho, modulação e slot disponível "
            "na ordem sequencial. É a heurística mais rápida e simples, "
            "servindo como referência base (baseline) para comparação. "
            "Percorre path → modulação → slot e retorna o primeiro "
            "candidato válido que satisfaz restrições de recurso e QoT."
        ),
        category="runtime",
        complexity="low",
    ),
    HeuristicEntry(
        id="select_random_action",
        name="Random",
        description=(
            "Seleciona aleatoriamente entre todos os candidatos válidos "
            "usando reservoir sampling uniforme. Útil como baseline "
            "estatístico e para avaliar o ganho das heurísticas "
            "inteligentes em relação à escolha puramente aleatória."
        ),
        category="runtime",
        complexity="low",
    ),
    HeuristicEntry(
        id="select_highest_snr_first_fit_action",
        name="Highest SNR",
        description=(
            "Seleciona o candidato com a maior margem de OSNR "
            "(relação sinal-ruído óptica). Maximiza a robustez da "
            "transmissão, priorizando qualidade do sinal. Útil para "
            "cenários onde a confiabilidade é mais importante que "
            "eficiência espectral."
        ),
        category="runtime",
        complexity="medium",
    ),
    HeuristicEntry(
        id="select_load_balancing_action",
        name="Load Balancing",
        description=(
            "Minimiza a utilização máxima dos links do caminho, "
            "distribuindo o tráfego uniformemente pela rede. "
            "Evita gargalos em enlaces específicos e reduz a "
            "fragmentação espectral. Usa como critério secundário "
            "a fragmentação local."
        ),
        category="runtime",
        complexity="medium",
    ),
    HeuristicEntry(
        id="select_lowest_fragmentation_action",
        name="Lowest Fragmentation",
        description=(
            "Minimiza o dano de fragmentação espectral causado pela "
            "alocação. Avalia: número de blocos livres, tamanho do "
            "maior bloco, fragmentação local e cortes no espectro. "
            "Preserva blocos contíguos grandes para futuras "
            "requisições de alta demanda."
        ),
        category="runtime",
        complexity="high",
    ),
    HeuristicEntry(
        id="select_ksp_best_mod_last_fit_action",
        name="KSP + Best Mod + Last Fit",
        description=(
            "K-Shortest Path com melhor modulação (maior eficiência "
            "espectral) e alocação Last-Fit (último slot disponível). "
            "Combina roteamento otimizado com alocação que agrupa "
            "slots livres no início do espectro, facilitando "
            "alocações futuras."
        ),
        category="runtime",
        complexity="medium",
    ),
)


@dataclass
class RunConfig:
    """Configuração completa para execução de simulação.

    Combina os parâmetros do cenário com as opções de execução
    como modo, heurísticas selecionadas e paralelismo.
    """

    # ── Cenário (mapeamento direto para ScenarioConfig) ─
    scenario_id: str = "gui_run"
    topology_id: str = "nobel-eu"
    k_paths: int = 3
    num_spectrum_resources: int = 320
    episode_length: int = 1000
    episodes_per_point: int = 1
    seed: int | None = 10
    seed_schedule: dict[str, int] | None = None

    # Parâmetros físicos
    max_span_length_km: float = 100.0
    default_attenuation_db_per_km: float = 0.2
    default_noise_figure_db: float = 4.5
    channel_width: float = 12.5
    frequency_slot_bandwidth: float = 12.5e9
    launch_power_dbm: float = 0.0

    # Tráfego
    traffic_mode: str = "dynamic"
    bit_rates: tuple[int, ...] = (10, 40, 100, 400)
    bit_rate_probabilities: tuple[float, ...] | None = None
    load: float = 300.0
    mean_holding_time: float = 100.0

    # QoT
    qot_constraint: str = "ASE+NLI"
    margin: float = 0.0
    modulations: list[str] = field(
        default_factory=lambda: ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"]
    )
    modulations_to_consider: int | None = None
    measure_disruptions: bool = False
    drop_on_disruption: bool = False

    # ── Execução ────────────────────────────────────────
    mode: RunMode = RunMode.SINGLE
    heuristic_ids: list[str] = field(
        default_factory=lambda: ["select_first_fit_action"]
    )
    sweep_loads: list[float] = field(
        default_factory=lambda: [50.0, 100.0, 150.0, 200.0, 250.0, 300.0]
    )
    sweep_margins: list[float] = field(
        default_factory=lambda: [0.0, 1.0, 2.0, 3.0]
    )
    num_workers: int | None = None

    @property
    def total_tasks(self) -> int:
        """Número total de simulações a serem executadas."""
        n_heuristics = len(self.heuristic_ids)
        n_ep = max(1, int(self.episodes_per_point))
        if self.mode == RunMode.SINGLE:
            return n_heuristics * n_ep
        elif self.mode == RunMode.LOAD_SWEEP:
            return len(self.sweep_loads) * n_heuristics * n_ep
        elif self.mode == RunMode.MARGIN_SWEEP:
            return len(self.sweep_margins) * n_heuristics * n_ep
        elif self.mode == RunMode.GRID:
            return len(self.sweep_loads) * len(self.sweep_margins) * n_heuristics * n_ep
        return n_ep

    def iter_tasks(self) -> list[dict]:
        """Gera a lista de tarefas individuais para execução.

        Returns
        -------
        list[dict]
            Cada dicionário contém ``load``, ``margin``, ``heuristic_id``,
            ``episode_index`` e demais parâmetros necessários para criar um ScenarioConfig.
        """
        base = {
            "scenario_id": self.scenario_id,
            "topology_id": self.topology_id,
            "k_paths": self.k_paths,
            "num_spectrum_resources": self.num_spectrum_resources,
            "episode_length": self.episode_length,
            "seed": self.seed,
            "max_span_length_km": self.max_span_length_km,
            "default_attenuation_db_per_km": self.default_attenuation_db_per_km,
            "default_noise_figure_db": self.default_noise_figure_db,
            "channel_width": self.channel_width,
            "frequency_slot_bandwidth": self.frequency_slot_bandwidth,
            "launch_power_dbm": self.launch_power_dbm,
            "traffic_mode": self.traffic_mode,
            "bit_rates": self.bit_rates,
            "bit_rate_probabilities": self.bit_rate_probabilities,
            "qot_constraint": self.qot_constraint,
            "modulations": self.modulations,
            "modulations_to_consider": self.modulations_to_consider,
            "measure_disruptions": self.measure_disruptions,
            "drop_on_disruption": self.drop_on_disruption,
            "mean_holding_time": self.mean_holding_time,
        }

        tasks = []
        n_ep = max(1, int(self.episodes_per_point))

        def _make_task(load_val: float, margin_val: float, hid: str, ep_idx: int) -> dict:
            key = f"{float(load_val):.1f}_{float(margin_val):.1f}_{int(ep_idx)}"
            exact_seed = (
                self.seed_schedule.get(key)
                if (self.seed_schedule and self.seed is None)
                else None
            )
            return {
                **base,
                "load": load_val,
                "margin": margin_val,
                "heuristic_id": hid,
                "episode_index": ep_idx,
                "exact_seed": exact_seed,
            }

        if self.mode == RunMode.SINGLE:
            for hid in self.heuristic_ids:
                for ep_idx in range(n_ep):
                    tasks.append(_make_task(self.load, self.margin, hid, ep_idx))

        elif self.mode == RunMode.LOAD_SWEEP:
            for load_val in self.sweep_loads:
                for hid in self.heuristic_ids:
                    for ep_idx in range(n_ep):
                        tasks.append(_make_task(load_val, self.margin, hid, ep_idx))

        elif self.mode == RunMode.MARGIN_SWEEP:
            for margin_val in self.sweep_margins:
                for hid in self.heuristic_ids:
                    for ep_idx in range(n_ep):
                        tasks.append(_make_task(self.load, margin_val, hid, ep_idx))

        elif self.mode == RunMode.GRID:
            for load_val in self.sweep_loads:
                for margin_val in self.sweep_margins:
                    for hid in self.heuristic_ids:
                        for ep_idx in range(n_ep):
                            tasks.append(_make_task(load_val, margin_val, hid, ep_idx))

        return tasks
