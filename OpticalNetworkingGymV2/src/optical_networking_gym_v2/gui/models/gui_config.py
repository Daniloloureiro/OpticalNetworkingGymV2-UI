"""
Estado serializável da GUI.

Permite salvar e restaurar a configuração completa da interface,
incluindo todos os parâmetros de cenário e preferências do usuário.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class GUIState:
    """Estado completo da GUI, persistível em JSON.

    Agrupa todos os parâmetros de cenário, preferências de interface,
    e últimas configurações utilizadas. Pode ser salvo/carregado
    para reutilização entre sessões.
    """

    # ── Cenário ─────────────────────────────────────────
    scenario_id: str = "custom"
    topology_id: str = "nobel-eu"
    k_paths: int = 3
    num_spectrum_resources: int = 320
    episode_length: int = 1000
    episodes_per_point: int = 1
    seed: int | None = 10
    use_seed: bool = True
    seed_schedule: dict[str, int] | None = None

    # ── Parâmetros Físicos ──────────────────────────────
    max_span_length_km: float = 100.0
    default_attenuation_db_per_km: float = 0.2
    default_noise_figure_db: float = 4.5
    channel_width: float = 12.5
    frequency_slot_bandwidth: float = 12.5e9
    launch_power_dbm: float = 0.0

    # ── Tráfego ─────────────────────────────────────────
    traffic_mode: str = "dynamic"
    bit_rates: list[int] = field(default_factory=lambda: [10, 40, 100, 400])
    bit_rate_probabilities: list[float] | None = None
    load: float = 300.0
    mean_holding_time: float = 100.0

    # ── QoT e Modulações ────────────────────────────────
    qot_constraint: str = "ASE+NLI"
    margin: float = 0.0
    modulations: list[str] = field(
        default_factory=lambda: ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"]
    )
    modulations_to_consider: int | None = None
    measure_disruptions: bool = False
    drop_on_disruption: bool = False

    # ── Heurísticas selecionadas ────────────────────────
    selected_heuristics: list[str] = field(
        default_factory=lambda: ["select_first_fit_action"]
    )

    # ── Execução ────────────────────────────────────────
    run_mode: str = "single"  # single, load_sweep, margin_sweep, grid
    sweep_loads: list[float] = field(
        default_factory=lambda: [50.0, 100.0, 150.0, 200.0, 250.0, 300.0]
    )
    sweep_margins: list[float] = field(
        default_factory=lambda: [0.0, 1.0, 2.0, 3.0]
    )
    num_workers: int | None = None  # None = auto

    # ── Preferências de Interface ───────────────────────
    theme: str = "light"  # light, dark
    last_results_dir: str = ""
    plot_style: str = "academic"  # academic, dark, default
    export_dpi: int = 300
    last_active_tab: int = 0

    def save_to_file(self, path: Path) -> None:
        """Salva o estado em um arquivo JSON.

        Parameters
        ----------
        path : Path
            Caminho do arquivo de destino.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, path: Path) -> "GUIState":
        """Carrega o estado de um arquivo JSON.

        Parameters
        ----------
        path : Path
            Caminho do arquivo JSON.

        Returns
        -------
        GUIState
            Estado restaurado.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return asdict(self)
