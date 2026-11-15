"""Painel de Orquestração e Execução Paralela de Simulações.

Permite configurar o plano de simulação (Simulação Simples, Varredura de
Carga, Varredura de Margem ou Grade Fatorial 2D), dimensionar o paralelismo em
núcleos de CPU, inspecionar o resumo pré-execução e monitorar o progresso em
tempo real com estimativa de término (ETA) e console de eventos.
"""

from __future__ import annotations

import multiprocessing
import time
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSlider, QPushButton, QPlainTextEdit, QGroupBox, QSplitter, QFrame,
    QScrollArea, QSizePolicy
)

from optical_networking_gym_v2.gui import theme
from optical_networking_gym_v2.gui.theme import create_academic_header
from optical_networking_gym_v2.gui.models.gui_config import GUIState
from optical_networking_gym_v2.gui.models.run_config import HEURISTIC_CATALOG
from optical_networking_gym_v2.gui.controllers.simulation_runner import SimulationRunner
from optical_networking_gym_v2.gui.controllers.results_manager import ResultsManager
from optical_networking_gym_v2.gui.widgets.progress_widget import ProgressWidget


def parse_float_list(text: str) -> list[float]:
    """Converte uma string separada por vírgulas ou espaços em uma lista de floats."""
    cleaned = text.replace(",", " ")
    parts = cleaned.split()
    if not parts:
        raise ValueError("Lista vazia")
    return [float(p) for p in parts]


class ExecutionPanel(QWidget):
    """Painel responsável por disparar e monitorar o lote de simulações."""

    simulation_finished = Signal()
    start_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.runner: SimulationRunner | None = None
        self.results_manager: ResultsManager | None = None
        self.state_provider: Callable[[], GUIState] | None = None
        self.latest_state: GUIState = GUIState()

        self._max_cores = multiprocessing.cpu_count()

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.header_banner = create_academic_header(
            title="Executar Simulação — Orquestração e Execução Multiprocessada",
            subtitle=(
                "Configure o plano de simulações (Simulação Simples, Varredura de Carga/Margem ou Grade 2D), "
                "dimensione o pool de subprocessos paralelos e acompanhe a telemetria em tempo real."
            ),
            badge_text="MULTIPROCESSING SPAWN • TELEMETRIA EM TEMPO REAL",
            parent=self,
        )
        root_layout.addWidget(self.header_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        # ── Coluna da Esquerda: Configuração da Execução ──────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.config_container = QWidget()
        config_layout = QVBoxLayout(self.config_container)
        config_layout.setContentsMargins(0, 0, 6, 0)
        config_layout.setSpacing(12)

        # Grupo 1: Parâmetros do Plano de Simulação
        self.run_group = QGroupBox("Plano de Simulação e Paralelismo")
        run_layout = QVBoxLayout(self.run_group)
        run_layout.setContentsMargins(14, 22, 14, 14)
        run_layout.setSpacing(10)

        mode_row = QWidget()
        mode_row_layout = QHBoxLayout(mode_row)
        mode_row_layout.setContentsMargins(0, 2, 0, 2)
        mode_row_layout.setSpacing(10)

        mode_label = QLabel("Modo de Simulação")
        mode_label.setMinimumWidth(145)
        mode_label.setStyleSheet("font-weight: 600; font-size: 11px;")
        mode_row_layout.addWidget(mode_label)

        self.run_mode_combo = QComboBox()
        self.run_mode_combo.setMinimumWidth(160)
        self.run_mode_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.run_mode_combo.addItems([
            "Simulação Simples",
            "Varredura de Carga (Sweep Load)",
            "Varredura de Margem (Sweep Margin)",
            "Grade de Parâmetros (Grid Sweep)"
        ])
        self.run_mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_row_layout.addWidget(self.run_mode_combo, 1)
        run_layout.addWidget(mode_row)

        # Varredura de Cargas (Loads)
        self.loads_row = QWidget()
        loads_row_layout = QHBoxLayout(self.loads_row)
        loads_row_layout.setContentsMargins(0, 2, 0, 2)
        loads_row_layout.setSpacing(10)

        loads_label = QLabel("Vetor de Cargas (Erlang)")
        loads_label.setMinimumWidth(145)
        loads_label.setStyleSheet("font-weight: 600; font-size: 11px;")
        loads_row_layout.addWidget(loads_label)

        self.loads_input = QLineEdit()
        self.loads_input.setPlaceholderText("Ex: 50, 100, 150, 200, 250, 300")
        self.loads_input.textChanged.connect(self._on_sweep_inputs_changed)
        loads_row_layout.addWidget(self.loads_input, 1)
        run_layout.addWidget(self.loads_row)

        # Varredura de Margens (Margins)
        self.margins_row = QWidget()
        margins_row_layout = QHBoxLayout(self.margins_row)
        margins_row_layout.setContentsMargins(0, 2, 0, 2)
        margins_row_layout.setSpacing(10)

        margins_label = QLabel("Vetor de Margens (dB)")
        margins_label.setMinimumWidth(145)
        margins_label.setStyleSheet("font-weight: 600; font-size: 11px;")
        margins_row_layout.addWidget(margins_label)

        self.margins_input = QLineEdit()
        self.margins_input.setPlaceholderText("Ex: 0.0, 0.5, 1.0, 1.5, 2.0")
        self.margins_input.textChanged.connect(self._on_sweep_inputs_changed)
        margins_row_layout.addWidget(self.margins_input, 1)
        run_layout.addWidget(self.margins_row)

        self.validation_warning = QLabel("")
        self.validation_warning.setWordWrap(True)
        self.validation_warning.setStyleSheet(f"color: {theme.COLORS.error}; font-size: 10.5px; font-weight: 700;")
        self.validation_warning.setVisible(False)
        run_layout.addWidget(self.validation_warning)

        # Paralelismo (Cores Slider)
        cores_row = QWidget()
        cores_row_layout = QVBoxLayout(cores_row)
        cores_row_layout.setContentsMargins(0, 4, 0, 0)
        cores_row_layout.setSpacing(6)

        cores_header = QHBoxLayout()
        cores_label = QLabel("Trabalhadores Paralelos (Workers CPU)")
        cores_label.setStyleSheet("font-weight: 600; font-size: 11px;")
        cores_header.addWidget(cores_label)

        self.cores_val_label = QLabel("")
        self.cores_val_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.cores_val_label.setStyleSheet(f"color: {theme.COLORS.primary_light}; font-weight: 700;")
        cores_header.addWidget(self.cores_val_label)
        cores_row_layout.addLayout(cores_header)

        self.cores_slider = QSlider(Qt.Orientation.Horizontal)
        self.cores_slider.setMinimum(1)
        self.cores_slider.setMaximum(self._max_cores)
        self.cores_slider.setValue(max(1, self._max_cores - 1))
        self.cores_slider.valueChanged.connect(self._on_cores_changed)
        cores_row_layout.addWidget(self.cores_slider)

        self.cores_warning = QLabel(
            "Nota: Alocar 100% dos núcleos lógicos pode reduzir temporariamente a fluidez da interface gráfica."
        )
        self.cores_warning.setWordWrap(True)
        self.cores_warning.setStyleSheet(f"color: {theme.COLORS.warning}; font-size: 10px;")
        self.cores_warning.setVisible(False)
        cores_row_layout.addWidget(self.cores_warning)
        run_layout.addWidget(cores_row)

        config_layout.addWidget(self.run_group)

        # Grupo 2: Resumo Pré-Execução
        self.plan_group = QGroupBox("Checklist do Plano de Simulação")
        plan_layout = QVBoxLayout(self.plan_group)
        plan_layout.setContentsMargins(14, 20, 14, 12)
        self.plan_summary_label = QLabel()
        self.plan_summary_label.setWordWrap(True)
        plan_layout.addWidget(self.plan_summary_label)
        config_layout.addWidget(self.plan_group)

        # Grupo 3: Painel de Controle de Execução (Botões e Progresso)
        self.control_group = QGroupBox("Controle e Progresso da Execução")
        control_layout = QVBoxLayout(self.control_group)
        control_layout.setContentsMargins(14, 22, 14, 14)
        control_layout.setSpacing(12)

        self.progress_widget = ProgressWidget()
        control_layout.addWidget(self.progress_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("Iniciar Simulação")
        self.start_btn.setProperty("class", "success")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.start_btn, 1)

        self.cancel_btn = QPushButton("Interromper")
        self.cancel_btn.setProperty("class", "danger")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.cancel_btn)

        control_layout.addLayout(btn_layout)
        config_layout.addWidget(self.control_group)
        config_layout.addStretch(1)
        left_scroll.setWidget(self.config_container)
        left_scroll.setMinimumWidth(380)

        # ── Coluna da Direita: Terminal de Log de Eventos ─────────────────
        self.terminal_group = QGroupBox("Console de Telemetria e Eventos de Simulação")
        self.terminal_group.setMinimumWidth(260)
        terminal_layout = QVBoxLayout(self.terminal_group)
        terminal_layout.setContentsMargins(12, 22, 12, 12)
        terminal_layout.setSpacing(8)

        self.log_terminal = QPlainTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setPlaceholderText(
            "Aguardando disparo da simulação...\n"
            "Os resultados parciais de cada tarefa (SBR, BBR, Disrupções e Tempo de CPU) aparecerão aqui."
        )
        terminal_layout.addWidget(self.log_terminal)

        self.clear_log_btn = QPushButton("Limpar Console")
        self.clear_log_btn.setProperty("class", "flat")
        self.clear_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_log_btn.clicked.connect(self.log_terminal.clear)
        terminal_layout.addWidget(self.clear_log_btn, alignment=Qt.AlignmentFlag.AlignRight)

        splitter.addWidget(left_scroll)
        splitter.addWidget(self.terminal_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([470, 490])

        self._on_cores_changed(self.cores_slider.value())
        self._update_plan_summary()

    def setup_controllers(
        self,
        runner: SimulationRunner,
        results_manager: ResultsManager,
        state_provider: Callable[[], GUIState]
    ) -> None:
        self.runner = runner
        self.results_manager = results_manager
        self.state_provider = state_provider

        self.runner.sweep_started.connect(self._on_runner_started)
        self.runner.task_completed.connect(self._on_task_completed)
        self.runner.progress_updated.connect(self._on_progress_updated)
        self.runner.sweep_finished.connect(self._on_runner_finished)
        self.runner.sweep_cancelled.connect(self._on_runner_cancelled)
        self.runner.error_occurred.connect(self._on_runner_error)

    def _on_cores_changed(self, value: int) -> None:
        self.cores_val_label.setText(f"{value} / {self._max_cores} núcleos")
        self.cores_warning.setVisible(value == self._max_cores)
        self._update_plan_summary()

    def _on_mode_changed(self, text: str) -> None:
        if text in ("Simulação Simples", "Simulação Única"):
            self.loads_row.setEnabled(False)
            self.margins_row.setEnabled(False)
        elif text == "Varredura de Carga (Sweep Load)":
            self.loads_row.setEnabled(True)
            self.margins_row.setEnabled(False)
        elif text == "Varredura de Margem (Sweep Margin)":
            self.margins_row.setEnabled(True)
            self.loads_row.setEnabled(False)
        elif text == "Grade de Parâmetros (Grid Sweep)":
            self.loads_row.setEnabled(True)
            self.margins_row.setEnabled(True)
        self._on_sweep_inputs_changed()

    def _on_sweep_inputs_changed(self, *args) -> None:
        self._validate_loads(self.loads_input.text())
        self._validate_margins(self.margins_input.text())
        self._update_plan_summary()

    def _update_plan_summary(self) -> None:
        c = theme.COLORS
        st = self.latest_state
        n_heur = max(1, len(st.selected_heuristics))
        mode_text = self.run_mode_combo.currentText()

        try:
            n_loads = len(parse_float_list(self.loads_input.text())) if self.loads_row.isEnabled() else 1
        except ValueError:
            n_loads = 0
        try:
            n_margins = len(parse_float_list(self.margins_input.text())) if self.margins_row.isEnabled() else 1
        except ValueError:
            n_margins = 0

        n_ep = max(1, int(getattr(st, "episodes_per_point", 1)))
        if mode_text in ("Simulação Simples", "Simulação Única"):
            total_tasks = n_heur * n_ep
        elif mode_text == "Varredura de Carga (Sweep Load)":
            total_tasks = n_heur * n_loads * n_ep
        elif mode_text == "Varredura de Margem (Sweep Margin)":
            total_tasks = n_heur * n_margins * n_ep
        else:
            total_tasks = n_heur * n_loads * n_margins * n_ep

        total_reqs = total_tasks * st.episode_length

        self.plan_summary_label.setText(
            f"<table style='width:100%; font-size:11px;'>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Topologia &amp; Restrição QoT:</td>"
            f"<td style='text-align:right; font-weight:700;'>{st.topology_id.upper()} ({st.qot_constraint})</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Algoritmos Selecionados:</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.primary_light};'>{n_heur} heurística(s)</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Total de Episódios (Tarefas):</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.accent};'>{total_tasks} episódio(s)</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Total de Requisições Ópticas:</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.success};'>{total_reqs:,} conexões</td></tr>"
            f"</table>"
        )

    def _validate_loads(self, text: str) -> bool:
        if not self.loads_row.isEnabled():
            self.loads_input.setStyleSheet("")
            self.validation_warning.setVisible(False)
            return True
        try:
            parse_float_list(text)
            self.loads_input.setStyleSheet("")
            self.validation_warning.setVisible(False)
            return True
        except ValueError:
            self.loads_input.setStyleSheet(f"border: 1.5px solid {theme.COLORS.error};")
            self.validation_warning.setText(
                "Valores de carga inválidos. Informe números separados por vírgula ou espaço (ex: 100, 200, 300)."
            )
            self.validation_warning.setVisible(True)
            return False

    def _validate_margins(self, text: str) -> bool:
        if not self.margins_row.isEnabled():
            self.margins_input.setStyleSheet("")
            self.validation_warning.setVisible(False)
            return True
        try:
            parse_float_list(text)
            self.margins_input.setStyleSheet("")
            self.validation_warning.setVisible(False)
            return True
        except ValueError:
            self.margins_input.setStyleSheet(f"border: 1.5px solid {theme.COLORS.error};")
            self.validation_warning.setText(
                "Valores de margem inválidos. Informe números separados por vírgula ou espaço (ex: 0.0, 1.0, 2.0)."
            )
            self.validation_warning.setVisible(True)
            return False

    def log(self, text: str, color: str | None = None) -> None:
        c = theme.COLORS
        use_color = color or c.text
        timestamp = time.strftime("[%H:%M:%S]")
        html_msg = (
            f"<span style='color: {c.text_secondary}; font-weight: bold;'>{timestamp}</span> "
            f"<span style='color: {use_color};'>{text}</span>"
        )
        self.log_terminal.appendHtml(html_msg)
        self.log_terminal.ensureCursorVisible()

    def _on_start_clicked(self) -> None:
        if not self._validate_loads(self.loads_input.text()) or not self._validate_margins(self.margins_input.text()):
            self.log("Falha ao iniciar: corrija a sintaxe dos vetores de varredura.", theme.COLORS.error)
            return
        self.start_requested.emit()

    def _on_cancel_clicked(self) -> None:
        if self.runner and self.runner.is_running():
            self.log("Solicitando interrupção imediata dos subprocessos...", theme.COLORS.warning)
            self.runner.cancel_sweep()

    def on_simulation_started(self, total_tasks: int) -> None:
        self._on_runner_started(total_tasks)

    def on_simulation_finished(self) -> None:
        self._reset_ui_after_run()

    def log_message(self, message: str, color: str | None = None, success: bool = True) -> None:
        c = theme.COLORS
        if color is None:
            color = c.text if success else c.error
        self.log(message.replace("\n", "<br/>"), color)

    def _on_runner_started(self, total_tasks: int) -> None:
        c = theme.COLORS
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.run_group.setEnabled(False)
        self.progress_widget.reset()
        self.progress_widget.update_progress(0, total_tasks, "Inicializando pool de processos...")
        self.log(
            f"<b>Iniciando bateria de simulação:</b> {total_tasks} tarefa(s) agendada(s) "
            f"em {self.cores_slider.value()} processo(s) paralelo(s).",
            c.primary_light,
        )

    def _on_task_completed(self, result: dict) -> None:
        c = theme.COLORS
        heur_id = result.get("heuristic_id", "unknown")
        h_name = next((h.name for h in HEURISTIC_CATALOG if h.id == heur_id), heur_id)
        load = result.get("load", 0.0)
        margin = result.get("margin", 0.0)

        if result.get("status") == "success":
            sbr = result.get("service_blocking_rate", 0.0) * 100.0
            bbr = result.get("bit_rate_blocking_rate", 0.0) * 100.0
            served = result.get("service_served_rate", 0.0) * 100.0
            disrupt = result.get("disrupted_services", 0)
            elapsed = result.get("episode_time_s", result.get("elapsed_s", 0.0))
            self.log(
                f"<b>[OK] [{h_name}]</b> Carga={load:.1f} Erl | Margem={margin:.2f} dB &rarr; "
                f"Bloq.Serv=<b>{sbr:.2f}%</b> | Bloq.Bits={bbr:.2f}% | "
                f"Entrega=<b>{served:.2f}%</b> | Disrupções={disrupt} | Tempo={elapsed:.2f}s",
                c.success,
            )
        else:
            err = result.get("error", "Erro desconhecido")
            self.log(
                f"<b>[FALHA] [{h_name}]</b> Carga={load:.1f} | Margem={margin:.2f} | Erro: {err}",
                c.error,
            )

    def _on_progress_updated(self, completed: int, total: int, eta_seconds: float) -> None:
        status_text = f"Computando episódios: {completed} de {total} concluídos"
        self.progress_widget.update_progress(completed, total, status_text)

    def _on_runner_finished(self, results: list) -> None:
        self._reset_ui_after_run()
        csv_msg = ""
        if self.results_manager:
            self.results_manager.set_results(results)
            try:
                scenario_id = getattr(self.latest_state, "scenario_id", "simulacao")
                saved_paths = self.results_manager.auto_save_legacy_csvs(scenario_id=scenario_id)
                if saved_paths:
                    paths_str = "<br/>".join(f"&nbsp;&nbsp;- <code>{p}</code>" for p in saved_paths)
                    csv_msg = f"<br/><b>Arquivos CSV gerados automaticamente (Padrão Legado):</b><br/>{paths_str}"
            except Exception as exc:
                csv_msg = f"<br/>Aviso ao gerar CSV automático: {exc}"

        self.log(
            f"<b>Bateria de simulação concluída.</b> Todas as {len(results)} tarefas finalizaram. "
            f"Resultados disponíveis na etapa '6. Resultados e Histórico'.{csv_msg}",
            theme.COLORS.primary_light,
        )
        self.simulation_finished.emit()

    def _on_runner_cancelled(self) -> None:
        partial_msg = ""
        if self.results_manager and self.results_manager.get_raw_results():
            try:
                scenario_id = getattr(self.latest_state, "scenario_id", "simulacao")
                saved_paths = self.results_manager.auto_save_legacy_csvs(scenario_id=f"{scenario_id}_parcial")
                if saved_paths:
                    paths_str = "<br/>".join(f"&nbsp;&nbsp;- <code>{p}</code>" for p in saved_paths)
                    partial_msg = f"<br/><b>Resultados parciais salvos automaticamente:</b><br/>{paths_str}"
            except Exception:
                pass
        self.log(f"Execução interrompida pelo usuário.{partial_msg}", theme.COLORS.warning)
        self._reset_ui_after_run()

    def _on_runner_error(self, err_msg: str) -> None:
        self.log(f"Erro Crítico do Executor: {err_msg}", theme.COLORS.error)
        self._reset_ui_after_run()

    def _reset_ui_after_run(self) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.run_group.setEnabled(True)

    def load_state(self, state: GUIState) -> None:
        self.latest_state = state

        mode_str = state.run_mode.lower()
        if mode_str in ("single", "simple", "simples"):
            self.run_mode_combo.setCurrentText("Simulação Simples")
        elif mode_str == "load_sweep":
            self.run_mode_combo.setCurrentText("Varredura de Carga (Sweep Load)")
        elif mode_str == "margin_sweep":
            self.run_mode_combo.setCurrentText("Varredura de Margem (Sweep Margin)")
        elif mode_str == "grid":
            self.run_mode_combo.setCurrentText("Grade de Parâmetros (Grid Sweep)")

        self.loads_input.setText(", ".join(map(str, state.sweep_loads)))
        self.margins_input.setText(", ".join(map(str, state.sweep_margins)))

        workers = state.num_workers if state.num_workers is not None else max(1, self._max_cores - 1)
        self.cores_slider.setValue(workers)

        self._on_mode_changed(self.run_mode_combo.currentText())
        self._update_plan_summary()

    def update_state(self, state: GUIState) -> None:
        combo_text = self.run_mode_combo.currentText()
        if combo_text in ("Simulação Simples", "Simulação Única"):
            state.run_mode = "single"
        elif combo_text == "Varredura de Carga (Sweep Load)":
            state.run_mode = "load_sweep"
        elif combo_text == "Varredura de Margem (Sweep Margin)":
            state.run_mode = "margin_sweep"
        elif combo_text == "Grade de Parâmetros (Grid Sweep)":
            state.run_mode = "grid"

        if self.loads_row.isEnabled():
            try:
                state.sweep_loads = parse_float_list(self.loads_input.text())
            except ValueError:
                pass

        if self.margins_row.isEnabled():
            try:
                state.sweep_margins = parse_float_list(self.margins_input.text())
            except ValueError:
                pass

        state.num_workers = int(self.cores_slider.value())
        self.latest_state = state
        self._update_plan_summary()
