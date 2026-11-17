"""
Janela principal (MainWindow) da GUI Acadêmica do Optical Networking Gym v2.

Orquestra todos os painéis da interface em um fluxo científico numerado (etapas 1 a 6),
sincroniza o estado global da GUI, gerencia persistência de configurações e conecta os
controladores multiprocessados aos módulos de análise estatística e exportação CSV.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QStackedWidget,
    QMessageBox,
    QFileDialog,
    QLabel,
    QFrame,
    QPushButton,
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction

from .theme import SIDEBAR_WIDTH, apply_theme
from .models.gui_config import GUIState
from .models.run_config import RunConfig, HEURISTIC_CATALOG
from .controllers.simulation_runner import SimulationRunner
from .controllers.results_manager import ResultsManager
from .controllers.history_manager import HistoryManager
from .panels.scenario_panel import ScenarioPanel
from .panels.physics_panel import PhysicsPanel
from .panels.traffic_panel import TrafficPanel
from .panels.qot_panel import QoTPanel
from .panels.heuristics_panel import HeuristicsPanel
from .panels.execution_panel import ExecutionPanel
from .panels.results_panel import ResultsPanel
from .widgets.parameter_widget import ParameterHelpDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Janela principal da estação de simulação acadêmica Optical Networking Gym v2."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Optical Networking Gym v2 — Ambiente Acadêmico de Simulação RMLSA & QoT"
        )
        self.resize(1260, 780)
        self.setMinimumSize(920, 620)

        # ── Estado e Controladores ────────────────────────────────
        self.state = GUIState()
        self._loading_ui = False
        self.runner = SimulationRunner()
        self.results_manager = ResultsManager()
        self.history_manager = HistoryManager()
        self._last_run_config: RunConfig | None = None

        self._config_dir = Path.home() / ".optical_networking_gym"
        self._config_dir.mkdir(exist_ok=True)
        self._default_config_path = self._config_dir / "gui_default_settings.json"

        if self._default_config_path.exists():
            try:
                self.state = GUIState.load_from_file(self._default_config_path)
                self._sanitize_loaded_state()
            except Exception as e:
                logger.warning(f"Erro ao carregar configurações padrão: {e}")

        from PySide6.QtWidgets import QApplication
        app_inst = QApplication.instance()
        if app_inst:
            apply_theme(app_inst, theme="light")

        # ── Componentes de Interface ─────────────────────────────
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._connect_signals()

        self.write_settings_to_ui()
        initial_row = max(0, min(self.state.last_active_tab, self.sidebar.count() - 1))
        self.sidebar.setCurrentRow(initial_row)

    def _sanitize_loaded_state(self) -> None:
        """Garante que heurísticas e abas carregadas de arquivos antigos sejam válidas."""
        valid_ids = {h.id for h in HEURISTIC_CATALOG}
        filtered = [hid for hid in self.state.selected_heuristics if hid in valid_ids]
        if not filtered:
            filtered = ["select_first_fit_action"]
        self.state.selected_heuristics = filtered
        self.state.theme = "light"

    def _setup_ui(self) -> None:
        """Cria e organiza a barra lateral de fluxo científico e os painéis."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Barra Lateral de Navegação (Sidebar) ──────────────────
        sidebar_widget = QWidget(self)
        sidebar_widget.setFixedWidth(SIDEBAR_WIDTH)
        sidebar_widget.setObjectName("Sidebar")

        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Cabeçalho Institucional / Acadêmico da Barra Lateral
        header_frame = QFrame(sidebar_widget)
        header_frame.setObjectName("SidebarHeader")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 14, 14, 14)
        header_layout.setSpacing(3)

        title_label = QLabel("Optical Gym v2", header_frame)
        title_label.setStyleSheet(
            "font-size: 15px; font-weight: 800; color: #ffffff; background: transparent;"
        )

        subtitle_label = QLabel("Bancada RMLSA & QoT Óptica", header_frame)
        subtitle_label.setStyleSheet(
            "font-size: 10.5px; font-weight: 600; color: #cbd5e1; background: transparent;"
        )

        norm_label = QLabel("UFPA • ITU-T G.694.1 • GN Model", header_frame)
        norm_label.setStyleSheet(
            "font-size: 9.5px; color: #94a3b8; background: transparent;"
        )

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(norm_label)
        sidebar_layout.addWidget(header_frame)

        # Lista de etapas numeradas na barra lateral
        self.sidebar = QListWidget(sidebar_widget)
        self.sidebar.setObjectName("SidebarList")
        self.sidebar.addItems([
            "1. Cenário e Topologia",
            "2. Física da Fibra",
            "3. Tráfego e Demandas",
            "4. Modulação e QoT",
            "5. Heurísticas",
            "6. Resultados e Histórico",
        ])
        sidebar_layout.addWidget(self.sidebar, 1)

        # Rodapé da Barra Lateral com Ações Principais
        footer_frame = QFrame(sidebar_widget)
        footer_frame.setObjectName("SidebarFooter")
        footer_frame.setStyleSheet("QFrame#SidebarFooter { background: transparent; border: none; }")
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(10, 8, 10, 12)
        footer_layout.setSpacing(8)

        self.quick_run_btn = QPushButton("Iniciar Simulação")
        self.quick_run_btn.setProperty("class", "success")
        self.quick_run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_run_btn.setToolTip("Abre a janela de execução e orquestração da simulação")
        self.quick_run_btn.clicked.connect(self.action_open_execution_panel)
        footer_layout.addWidget(self.quick_run_btn)

        self.reset_defaults_btn = QPushButton("Voltar ao Padrão")
        self.reset_defaults_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_defaults_btn.setToolTip("Restaura todos os parâmetros de simulação para os valores padrão")
        self.reset_defaults_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #334155;"
            "  color: #f8fafc;"
            "  border: 1px solid #475569;"
            "  border-radius: 5px;"
            "  padding: 6px 12px;"
            "  font-weight: 600;"
            "  font-size: 10pt;"
            "}"
            "QPushButton:hover {"
            "  background-color: #475569;"
            "  border-color: #64748b;"
            "}"
        )
        self.reset_defaults_btn.clicked.connect(self.action_reset_defaults)
        footer_layout.addWidget(self.reset_defaults_btn)

        sidebar_layout.addWidget(footer_frame)
        main_layout.addWidget(sidebar_widget)

        # ── Área de Conteúdo (StackedWidget) ──────────────────────
        self.container = QStackedWidget(central_widget)

        self.scenario_panel = ScenarioPanel(self)
        self.physics_panel = PhysicsPanel(self)
        self.traffic_panel = TrafficPanel(self)
        self.qot_panel = QoTPanel(self)
        self.heuristics_panel = HeuristicsPanel(self)
        self.results_panel = ResultsPanel(self)
        self.execution_panel = ExecutionPanel(self)

        self.execution_panel.setup_controllers(
            runner=self.runner,
            results_manager=self.results_manager,
            state_provider=self.read_settings_from_ui,
        )
        self.results_panel.setup_controllers(
            results_manager=self.results_manager,
            history_manager=self.history_manager,
        )

        # Índices 0 a 5 correspondem aos itens da barra lateral;
        # Índice 6 corresponde à janela "Executar Simulação" aberta pelo botão "Iniciar Simulação"
        self.container.addWidget(self.scenario_panel)    # 0
        self.container.addWidget(self.physics_panel)     # 1
        self.container.addWidget(self.traffic_panel)     # 2
        self.container.addWidget(self.qot_panel)         # 3
        self.container.addWidget(self.heuristics_panel)  # 4
        self.container.addWidget(self.results_panel)     # 5
        self.container.addWidget(self.execution_panel)   # 6

        main_layout.addWidget(self.container, 1)

    def _setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # ── Menu Arquivo ──────────────────────────────────────────
        file_menu = menu_bar.addMenu("&Arquivo")

        load_action = QAction("&Carregar Configuração (.json)...", self)
        load_action.triggered.connect(self.action_load_settings)
        file_menu.addAction(load_action)

        save_action = QAction("&Salvar Configuração (.json)...", self)
        save_action.triggered.connect(self.action_save_settings)
        file_menu.addAction(save_action)

        reset_action = QAction("&Voltar ao Padrão", self)
        reset_action.triggered.connect(self.action_reset_defaults)
        file_menu.addAction(reset_action)

        file_menu.addSeparator()

        exit_action = QAction("S&air", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ── Menu Simulação ────────────────────────────────────────
        sim_menu = menu_bar.addMenu("&Simulação")

        open_exec_action = QAction("&Abrir Janela de Execução", self)
        open_exec_action.triggered.connect(self.action_open_execution_panel)
        sim_menu.addAction(open_exec_action)

        run_action = QAction("&Iniciar Simulação", self)
        run_action.triggered.connect(self.action_run_simulations)
        sim_menu.addAction(run_action)

        cancel_action = QAction("&Cancelar Simulação", self)
        cancel_action.triggered.connect(self.runner.cancel)
        sim_menu.addAction(cancel_action)

        # ── Menu Ajuda ────────────────────────────────────────────
        help_menu = menu_bar.addMenu("A&juda")

        guide_action = QAction("&Guia Metodológico de Simulação...", self)
        guide_action.triggered.connect(self.action_methodology_guide)
        help_menu.addAction(guide_action)

        about_action = QAction("&Sobre o Simulador...", self)
        about_action.triggered.connect(self.action_about)
        help_menu.addAction(about_action)

    def _setup_status_bar(self) -> None:
        status = self.statusBar()
        self.status_label = QLabel(
            "Pronto — Modo padrão: Simulação Simples (First Fit). Clique em 'Iniciar Simulação'.",
            self,
        )
        status.addWidget(self.status_label)

        self.summary_status_label = QLabel("", self)
        status.addPermanentWidget(self.summary_status_label)
        self._update_status_summary()

    def _update_status_summary(self) -> None:
        n_h = len(self.state.selected_heuristics)
        mode_str = "Simulação Simples" if self.state.run_mode in ("single", "simple", "simples") else self.state.run_mode.upper()
        self.summary_status_label.setText(
            f"Modo: {mode_str} | "
            f"Topologia: {self.state.topology_id.upper()} | "
            f"QoT: {self.state.qot_constraint} (M={self.state.margin:.1f} dB) | "
            f"Carga: {self.state.load:.0f} Erl | "
            f"Heurísticas: {n_h}"
        )

    def _connect_signals(self) -> None:
        self.sidebar.currentRowChanged.connect(self._on_sidebar_row_changed)

        for pnl in (
            self.scenario_panel,
            self.physics_panel,
            self.traffic_panel,
            self.qot_panel,
            self.heuristics_panel,
        ):
            pnl.state_changed.connect(self._on_any_panel_changed)

        self.execution_panel.start_requested.connect(self.action_run_simulations)
        self.results_panel.load_record_to_results.connect(self._on_load_history_to_results)

        self.runner.task_completed.connect(self._on_task_completed)
        self.runner.all_completed.connect(self._on_all_tasks_completed)
        self.runner.sweep_cancelled.connect(self._on_simulation_cancelled)
        self.runner.error_occurred.connect(self._on_runner_error)
        self.runner.progress_updated.connect(self._on_progress_updated)

    def _on_any_panel_changed(self) -> None:
        if getattr(self, "_loading_ui", False):
            return
        self.read_settings_from_ui()
        self._update_status_summary()

    def _on_sidebar_row_changed(self, index: int) -> None:
        if 0 <= index < self.sidebar.count():
            self.container.setCurrentIndex(index)
            self.state.last_active_tab = index
            if index == 5:
                self.read_settings_from_ui()
                self._update_status_summary()

    # ── Sincronização UI <=> GUIState ────────────────────────────

    def read_settings_from_ui(self) -> GUIState:
        self.scenario_panel.update_state(self.state)
        self.physics_panel.update_state(self.state)
        self.traffic_panel.update_state(self.state)
        self.qot_panel.update_state(self.state)
        self.heuristics_panel.update_state(self.state)
        self.execution_panel.update_state(self.state)
        return self.state

    def write_settings_to_ui(self) -> None:
        self._loading_ui = True
        try:
            self.scenario_panel.load_state(self.state)
            self.physics_panel.load_state(self.state)
            self.traffic_panel.load_state(self.state)
            self.qot_panel.load_state(self.state)
            self.heuristics_panel.load_state(self.state)
            self.execution_panel.load_state(self.state)
            self._update_status_summary()
        finally:
            self._loading_ui = False

    def get_run_config(self) -> RunConfig:
        self.read_settings_from_ui()
        seed_value = self.state.seed if self.state.use_seed else None
        from .models.run_config import RunMode
        run_mode = RunMode(self.state.run_mode)

        return RunConfig(
            scenario_id=self.state.scenario_id,
            topology_id=self.state.topology_id,
            k_paths=self.state.k_paths,
            num_spectrum_resources=self.state.num_spectrum_resources,
            episode_length=self.state.episode_length,
            episodes_per_point=self.state.episodes_per_point,
            seed=seed_value,
            seed_schedule=self.state.seed_schedule,
            max_span_length_km=self.state.max_span_length_km,
            default_attenuation_db_per_km=self.state.default_attenuation_db_per_km,
            default_noise_figure_db=self.state.default_noise_figure_db,
            channel_width=self.state.channel_width,
            frequency_slot_bandwidth=self.state.frequency_slot_bandwidth,
            launch_power_dbm=self.state.launch_power_dbm,
            traffic_mode=self.state.traffic_mode,
            bit_rates=tuple(self.state.bit_rates),
            bit_rate_probabilities=tuple(self.state.bit_rate_probabilities) if self.state.bit_rate_probabilities else None,
            load=self.state.load,
            mean_holding_time=self.state.mean_holding_time,
            qot_constraint=self.state.qot_constraint,
            margin=self.state.margin,
            modulations=self.state.modulations,
            modulations_to_consider=self.state.modulations_to_consider,
            measure_disruptions=self.state.measure_disruptions,
            drop_on_disruption=self.state.drop_on_disruption,
            mode=run_mode,
            heuristic_ids=self.state.selected_heuristics,
            sweep_loads=self.state.sweep_loads,
            sweep_margins=self.state.sweep_margins,
            num_workers=self.state.num_workers,
        )

    # ── Ações e Eventos ──────────────────────────────────────────

    @Slot()
    def action_open_execution_panel(self) -> None:
        """Abre a janela de Executar Simulação através do botão 'Iniciar Simulação'."""
        self.read_settings_from_ui()
        self._update_status_summary()
        self.sidebar.blockSignals(True)
        self.sidebar.clearSelection()
        self.sidebar.setCurrentRow(-1)
        self.sidebar.blockSignals(False)
        self.container.setCurrentWidget(self.execution_panel)
        self.status_label.setText("Janela de Execução — Revise o plano de simulação e inicie a execução.")

    @Slot()
    def action_reset_defaults(self) -> None:
        """Restaura todas as configurações da interface para os valores padrão (Simulação Simples)."""
        current_tab = self.sidebar.currentRow()
        self.state = GUIState()
        self.write_settings_to_ui()
        try:
            self.state.save_to_file(self._default_config_path)
        except Exception:
            pass
        if 0 <= current_tab < self.sidebar.count():
            self.sidebar.setCurrentRow(current_tab)
        self.status_label.setText("Configurações restauradas para o padrão: Simulação Simples (First Fit).")

    @Slot()
    def action_run_simulations(self) -> None:
        if self.runner.is_running():
            self.action_open_execution_panel()
            return

        try:
            run_config = self.get_run_config()

            if not run_config.heuristic_ids:
                QMessageBox.warning(
                    self,
                    "Sem Heurísticas Selecionadas",
                    "Selecione pelo menos uma heurística na etapa '5. Heurísticas' para executar a simulação.",
                )
                self.sidebar.setCurrentRow(4)
                return

            self._last_run_config = run_config
            self.status_label.setText("Executando bateria de simulações em background...")
            self.action_open_execution_panel()

            self.results_manager.clear()
            self.runner.start(run_config)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro de Configuração",
                f"Erro ao inicializar as configurações da simulação:\n{str(e)}",
            )
            logger.exception("Erro ao rodar simulações")

    @Slot(dict)
    def _on_task_completed(self, result: dict[str, Any]) -> None:
        self.results_manager.add_result(result)

    @Slot(list)
    def _on_all_tasks_completed(self, results: list[dict[str, Any]]) -> None:
        self.status_label.setText(f"Simulação concluída ({len(results)} tarefas processadas).")
        self.execution_panel.on_simulation_finished()

        self.results_panel.update_results()

        if self._last_run_config:
            config_dict = self.state.to_dict()
            self.history_manager.add_record(
                config=config_dict,
                results=results,
            )
            self.results_panel.refresh_history_list()

        self.sidebar.setCurrentRow(5)

    @Slot(list)
    def _on_load_history_to_results(self, results: list[dict[str, Any]]) -> None:
        self.results_manager.set_results(results)
        self.results_panel.update_results()
        self.sidebar.setCurrentRow(5)
        self.status_label.setText(
            f"Carregados {len(results)} resultados do histórico nos Resultados Atuais."
        )

    @Slot()
    def _on_simulation_cancelled(self) -> None:
        self.status_label.setText("Simulação interrompida pelo usuário.")
        self.quick_run_btn.setEnabled(True)
        self.execution_panel.on_simulation_finished()
        if self.results_manager.get_raw_results():
            self.results_panel.update_results()

    @Slot(str)
    def _on_runner_error(self, err_msg: str) -> None:
        self.status_label.setText("Erro na execução.")
        self.execution_panel.on_simulation_finished()
        self.execution_panel.log_message(f"[ERRO CRÍTICO] {err_msg}", success=False)

        QMessageBox.critical(
            self,
            "Erro de Simulação",
            f"Ocorreu um erro durante a execução do processo:\n{err_msg}",
        )

    @Slot(int, int, float)
    def _on_progress_updated(self, done: int, total: int, eta: float) -> None:
        if hasattr(self.execution_panel, "update_progress"):
            self.execution_panel.update_progress(done, total, eta)
        self.status_label.setText(f"Progresso da simulação: {done}/{total} episódios concluídos")

    # ── Salvar e Carregar Configurações ────────────────────────────

    @Slot()
    def action_save_settings(self) -> None:
        self.read_settings_from_ui()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Configurações da Simulação",
            str(self._config_dir / f"{self.state.scenario_id}.json"),
            "Configuração do Simulador (*.json)",
        )
        if file_path:
            try:
                p = Path(file_path)
                self.state.save_to_file(p)
                self.state.save_to_file(self._default_config_path)
                self.status_label.setText(f"Configurações salvas em {p.name}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{str(e)}"
                )

    @Slot()
    def action_load_settings(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Carregar Configurações da Simulação",
            str(self._config_dir),
            "Configuração do Simulador (*.json)",
        )
        if file_path:
            try:
                p = Path(file_path)
                self.state = GUIState.load_from_file(p)
                self._sanitize_loaded_state()
                self.write_settings_to_ui()
                row = max(0, min(self.state.last_active_tab, self.sidebar.count() - 1))
                self.sidebar.setCurrentRow(row)
                self.status_label.setText(f"Configurações carregadas de {p.name}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro ao Carregar", f"Não foi possível ler o arquivo:\n{str(e)}"
                )

    @Slot()
    def action_methodology_guide(self) -> None:
        html = (
            "<h3>Fluxo Metodológico para Simulações RMLSA &amp; QoT</h3>"
            "<ol>"
            "<li><b>Etapa 1 (Cenário &amp; Topologia):</b> Escolha a topologia de referência (ex: <code>nobel-eu</code> "
            "ou <code>nsfnet_chen</code>), <i>K</i> = 3 ou 5 rotas candidatas e 320 slots espectrais (Banda C — ITU-T G.694.1).</li>"
            "<li><b>Etapa 2 (Física da Fibra):</b> Ajuste o comprimento máximo de span (80 km), atenuação "
            "(0,20 dB/km), figura de ruído EDFA (4,5 dB) e potência de lançamento (0,0 dBm).</li>"
            "<li><b>Etapa 3 (Tráfego &amp; Demandas):</b> Defina a carga em Erlangs e a distribuição de taxas de linha (10G a 400G).</li>"
            "<li><b>Etapa 4 (Modulação &amp; QoT):</b> Configure as modulações habilitadas, selecione o modelo "
            "<code>ASE+NLI</code>, a margem de segurança (dB) e o monitoramento/derrubada por disrupção.</li>"
            "<li><b>Etapa 5 (Heurísticas):</b> Selecione entre as heurísticas <b>Estáticas</b> "
            "(<i>First Fit</i>, <i>Last Fit</i>, <i>Random</i>) e <b>Dinâmicas</b> "
            "(<i>Highest SNR</i>, <i>Load Balancing</i>, <i>Lowest Fragmentation</i>) a comparar.</li>"
            "<li><b>Iniciar Simulação &amp; Etapa 6 (Resultados e Histórico):</b> Clique em <b>Iniciar Simulação</b> para "
            "executar varreduras de carga ou margem em multiprocessamento e inspecione os resultados, histórico e arquivos CSV "
            "no padrão do simulador legado (<code>episodes.csv</code> e <code>summary.csv</code>).</li>"
            "</ol>"
        )
        ParameterHelpDialog("Guia Metodológico de Simulação Óptica", html, self).exec()

    @Slot()
    def action_about(self) -> None:
        QMessageBox.about(
            self,
            "Sobre o Optical Networking Gym v2",
            "<h3>Optical Networking Gym v2 — Suíte Acadêmica</h3>"
            "<p>Ambiente de simulação de eventos discretos e aprendizado por reforço (Gymnasium) "
            "para Redes Ópticas Elásticas (EONs) com camada física Cython de alta performance.</p>"
            "<p><b>Destaques Técnicos:</b></p>"
            "<ul>"
            "  <li>Grade flexível ITU-T G.694.1 (slots de 12.5 GHz na Banda C).</li>"
            "  <li>Avaliação física de QoT em tempo real (Ruído ASE + Interferência Não-Linear NLI).</li>"
            "  <li>Catálogo de heurísticas de alocação espectral (First Fit, Random, Highest SNR, Load Balancing, Lowest Fragmentation).</li>"
            "  <li>Execução paralela multiprocessada e geração de arquivos CSV no padrão legado.</li>"
            "</ul>"
            "<p>Desenvolvido para pesquisa científica e ensino de pós-graduação e graduação (UFPA).</p>",
        )

    def closeEvent(self, event: Any) -> None:
        if self.runner.is_running():
            reply = QMessageBox.question(
                self,
                "Simulação em Andamento",
                "Uma bateria de simulações está em execução. Deseja interrompê-la e sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.runner.cancel()
            else:
                event.ignore()
                return

        self.read_settings_from_ui()
        try:
            self.state.save_to_file(self._default_config_path)
        except Exception:
            pass
        event.accept()
