"""Painel Unificado de Resultados (episodes.csv e summary.csv) e Histórico de Simulações.

Exibe exclusivamente o padrão de resultados consolidado em summary.csv (45 colunas)
e detalhado por episódio em episodes.csv (28 colunas), integrando também o histórico
persistente de simulações em uma única janela.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextBrowser, QFrame,
    QFileDialog, QMessageBox, QGroupBox, QTabWidget, QListWidget,
    QListWidgetItem, QSplitter, QInputDialog,
)

from optical_networking_gym_v2.gui import theme
from optical_networking_gym_v2.gui.theme import create_academic_header
from optical_networking_gym_v2.gui.models.gui_config import GUIState
from optical_networking_gym_v2.gui.controllers.results_manager import (
    ResultsManager,
    EPISODES_FIELDNAMES,
    SUMMARY_FIELDNAMES,
    default_results_dir,
    format_episode_csv_row,
)
from optical_networking_gym_v2.gui.controllers.history_manager import (
    HistoryManager,
    SimulationRecord,
)


METRIC_EXPLANATIONS: dict[str, tuple[str, str]] = {
    "policy": (
        "Política / Heurística (policy)",
        "Identificador padronizado da heurística RMLSA executada (ex: First_Fit, Random, Highest_SNR).",
    ),
    "topology_id": (
        "Topologia Física (topology_id)",
        "Identificador da malha óptica avaliada na simulação (ex: nobel-eu, nsfnet_chen, germany50).",
    ),
    "load": (
        "Carga Oferecida em Erlangs (load)",
        "Intensidade de tráfego oferecida à rede (A = taxa de chegada × tempo médio de retenção).",
    ),
    "margin": (
        "Margem de OSNR em dB (margin)",
        "Folga adicional de OSNR exigida na admissão de cada conexão óptica.",
    ),
    "seed_base": (
        "Semente Base (seed_base)",
        "Semente base do gerador pseudo-aleatório utilizada no episódio.",
    ),
    "episode_index": (
        "Índice do Episódio (episode_index)",
        "Índice sequencial da repetição para o ponto (carga, margem) avaliado (0..N-1).",
    ),
    "episode_seed": (
        "Semente do Episódio (episode_seed)",
        "Semente efetiva aplicada em env.reset(seed=episode_seed).",
    ),
    "steps_requested": (
        "Requisições Solicitadas (steps_requested)",
        "Quantidade total de requisições configuradas para o episódio.",
    ),
    "processed": (
        "Serviços Processados (processed)",
        "Total de requisições de conexão óptica geradas e avaliadas pelo simulador durante o episódio.",
    ),
    "accepted": (
        "Serviços Aceitos na Admissão (accepted)",
        "Requisições alocadas na malha óptica que encontraram rota, modulação e slots livres com GSNR suficiente.",
    ),
    "served": (
        "Serviços Entregues com Sucesso (served)",
        "Requisições aceitas que permaneceram íntegras até o fim sem queda por violação de QoT.",
    ),
    "blocking_rate": (
        "Taxa de Bloqueio de Serviço (blocking_rate)",
        "Fração de requisições bloqueadas na admissão sobre o total processado: (processed - accepted) / processed.",
    ),
    "served_rate": (
        "Taxa Líquida de Entrega de Serviço (served_rate)",
        "Fração de requisições efetivamente entregues com sucesso: served / processed.",
    ),
    "effective_loss_rate": (
        "Taxa de Perda Efetiva Total (effective_loss_rate)",
        "Fração total de requisições não entregues (bloqueios + quedas por QoT): (processed - served) / processed.",
    ),
    "blocked_resources": (
        "Bloqueados por Falta de Espectro (blocked_resources)",
        "Requisições rejeitadas por indisponibilidade de slots espectrais contíguos e contínuos.",
    ),
    "blocked_qot": (
        "Bloqueados por Limiar de QoT (blocked_qot)",
        "Requisições rejeitadas porque a GSNR estimada (ASE + NLI) ficou abaixo do limiar exigido.",
    ),
    "rejected_by_agent": (
        "Rejeitados pela Política (rejected_by_agent)",
        "Requisições rejeitadas por ação de bloqueio da política quando nenhum candidato satisfaz recursos e QoT.",
    ),
    "disrupted": (
        "Serviços Afetados por Disrupção (disrupted)",
        "Conexões ativas cuja GSNR caiu abaixo do limiar devido ao ruído não-linear (NLI) de novas alocações.",
    ),
    "dropped_qot": (
        "Serviços Derrubados por Violação de QoT (dropped_qot)",
        "Conexões ativas desconectadas quando drop_on_disruption está habilitado.",
    ),
    "disruption_rate": (
        "Taxa de Disrupção de Serviços (disruption_rate)",
        "Fração de serviços aceitos afetados por degradação severa de QoT pós-admissão.",
    ),
    "mod_bpsk": ("Conexões em BPSK (mod_bpsk)", "Quantidade de conexões aceitas moduladas em BPSK (1 bit/símbolo)."),
    "mod_qpsk": ("Conexões em QPSK (mod_qpsk)", "Quantidade de conexões aceitas moduladas em QPSK (2 bits/símbolo)."),
    "mod_8qam": ("Conexões em 8QAM (mod_8qam)", "Quantidade de conexões aceitas moduladas em 8QAM (3 bits/símbolo)."),
    "mod_16qam": ("Conexões em 16QAM (mod_16qam)", "Quantidade de conexões aceitas moduladas em 16QAM (4 bits/símbolo)."),
    "mod_32qam": ("Conexões em 32QAM (mod_32qam)", "Quantidade de conexões aceitas moduladas em 32QAM (5 bits/símbolo)."),
    "mod_64qam": ("Conexões em 64QAM (mod_64qam)", "Quantidade de conexões aceitas moduladas em 64QAM (6 bits/símbolo)."),
    "avg_spectral_efficiency": (
        "Eficiência Espectral Média (avg_spectral_efficiency)",
        "Média ponderada de bits/símbolo das conexões aceitas no episódio.",
    ),
    "elapsed_s": (
        "Tempo de Execução em Segundos (elapsed_s)",
        "Tempo de parede (wall-clock) gasto para processar o episódio.",
    ),
    "episodes": (
        "Total de Episódios Agregados (episodes)",
        "Quantidade de episódios agrupados para o ponto (policy, topology_id, load, margin).",
    ),
    "requests_per_episode": (
        "Requisições por Episódio (requests_per_episode)",
        "Número de requisições avaliadas em cada episódio individual.",
    ),
    "total_requests": (
        "Total Acumulado de Requisições (total_requests)",
        "Soma de todas as requisições processadas nos episódios agrupados.",
    ),
    "bandwidth_blocking_rate_mean": (
        "Média da Taxa de Bloqueio de Banda (bandwidth_blocking_rate_mean)",
        "Fração média da taxa de bits total solicitada (Gbps) que não pôde ser provisionada.",
    ),
    "avg_network_occupancy_mean": (
        "Ocupação Espectral Média da Malha (avg_network_occupancy_mean)",
        "Fração média de slots ocupados em todos os enlaces da topologia ao final do episódio.",
    ),
    "max_link_occupancy_mean": (
        "Ocupação Máxima de Enlace (max_link_occupancy_mean)",
        "Fração média de ocupação do enlace mais congestionado da rede.",
    ),
    "k0_pct_mean": ("Uso da 1ª Rota K-SP em % (k0_pct_mean)", "Percentual médio de conexões aceitas no caminho mais curto k=0."),
    "k1_pct_mean": ("Uso da 2ª Rota K-SP em % (k1_pct_mean)", "Percentual médio de conexões aceitas no segundo caminho k=1."),
    "k2_pct_mean": ("Uso da 3ª Rota K-SP em % (k2_pct_mean)", "Percentual médio de conexões aceitas no terceiro caminho k=2."),
    "avg_osnr_margin_db_mean": (
        "Folga Média de OSNR em dB (avg_osnr_margin_db_mean)",
        "Média da margem excedente de OSNR (OSNR - OSNR_req) das conexões aceitas.",
    ),
    "avg_fragmentation_shannon_entropy_mean": (
        "Entropia de Fragmentação de Shannon (avg_fragmentation_shannon_entropy_mean)",
        "Média da entropia de Shannon da fragmentação espectral nas rotas alocadas.",
    ),
    "avg_slots_per_service_mean": (
        "Média de Slots por Conexão (avg_slots_per_service_mean)",
        "Número médio de Frequency Slot Units (FSUs) alocados por conexão aceita.",
    ),
}


def _format_cell_value(key: str, val: object) -> str:
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if key in ("load", "margin"):
            return f"{val:.1f}"
        if key in ("elapsed_s", "elapsed_s_mean", "elapsed_s_total"):
            return f"{val:.4f}"
        return f"{val:.6f}"
    return str(val)


class ResultsPanel(QWidget):
    """Painel unificado de resultados (episodes.csv e summary.csv) e histórico de simulações."""

    state_changed = Signal()
    load_record_to_results = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.results_manager: ResultsManager | None = None
        self.history_manager: HistoryManager | None = None
        self._current_record: SimulationRecord | None = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.header_banner = create_academic_header(
            title="6. Resultados e Histórico de Simulações",
            subtitle=(
                "Inspecione as planilhas padronizadas de resultados (episodes.csv com 28 colunas e "
                "summary.csv com 45 colunas), consulte o histórico e exporte os arquivos CSV."
            ),
            badge_text="EPISODES.CSV • SUMMARY.CSV • HISTÓRICO",
            parent=self,
        )
        main_layout.addWidget(self.header_banner)

        # Barra superior de Exportação CSV Padrão (episodes.csv e summary.csv)
        self.export_group = QGroupBox("Geração Exclusiva de Resultados Padronizados (episodes.csv e summary.csv)")
        export_outer = QVBoxLayout(self.export_group)
        export_outer.setContentsMargins(14, 20, 14, 12)
        export_outer.setSpacing(8)

        self.csv_status_label = QLabel(
            "Ao concluir uma simulação, os arquivos padrão episodes.csv (28 colunas) e summary.csv (45 colunas) "
            f"são salvos automaticamente em '{default_results_dir()}' e também podem ser exportados abaixo."
        )
        self.csv_status_label.setWordWrap(True)
        self.csv_status_label.setStyleSheet(f"color: {theme.COLORS.text_secondary}; font-size: 11px;")
        export_outer.addWidget(self.csv_status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.export_bundle_btn = QPushButton("Salvar Pasta Padrão (episodes.csv + summary.csv)")
        self.export_bundle_btn.setProperty("class", "success")
        self.export_bundle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_bundle_btn.clicked.connect(self._export_legacy_folder)
        btn_row.addWidget(self.export_bundle_btn)

        self.export_episodes_btn = QPushButton("Exportar episodes.csv")
        self.export_episodes_btn.setProperty("class", "primary")
        self.export_episodes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_episodes_btn.clicked.connect(self._export_episodes_csv)
        btn_row.addWidget(self.export_episodes_btn)

        self.export_summary_btn = QPushButton("Exportar summary.csv")
        self.export_summary_btn.setProperty("class", "primary")
        self.export_summary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_summary_btn.clicked.connect(self._export_summary_csv)
        btn_row.addWidget(self.export_summary_btn)

        btn_row.addStretch(1)
        export_outer.addLayout(btn_row)
        main_layout.addWidget(self.export_group)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget, 1)

        self._build_summary_table_tab()
        self._build_episodes_table_tab()
        self._build_history_tab()

    def _build_summary_table_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        header = QLabel(
            "Planilha summary.csv (45 colunas): resumo estatístico consolidado por (policy, topology_id, load, margin). "
            "Clique no cabeçalho de qualquer coluna para consultar sua definição."
        )
        header.setWordWrap(True)
        header.setStyleSheet(f"color: {theme.COLORS.text_secondary}; font-size: 11px; font-weight: 600;")
        layout.addWidget(header)

        self.summary_table = QTableWidget()
        self._summary_column_keys = list(SUMMARY_FIELDNAMES)
        self.summary_table.setColumnCount(len(self._summary_column_keys))
        self.summary_table.setHorizontalHeaderLabels(self._summary_column_keys)

        for col_idx, key in enumerate(self._summary_column_keys):
            if key in METRIC_EXPLANATIONS:
                label, explanation = METRIC_EXPLANATIONS[key]
                item = self.summary_table.horizontalHeaderItem(col_idx)
                if item:
                    item.setToolTip(f"<b>{label}</b><br/><br/>{explanation}")

        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.summary_table.horizontalHeader().setFixedHeight(36)
        self.summary_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.horizontalHeader().sectionClicked.connect(self._on_summary_column_clicked)
        layout.addWidget(self.summary_table, 1)

        self.summary_explanation = QTextBrowser()
        self.summary_explanation.setMaximumHeight(80)
        self.summary_explanation.setFrameShape(QFrame.Shape.NoFrame)
        self.summary_explanation.setHtml(
            f'<p style="color: {theme.COLORS.text_secondary}; margin: 0;">'
            'Clique no título de qualquer coluna de <b>summary.csv</b> acima para inspecionar sua definição técnica.</p>'
        )
        layout.addWidget(self.summary_explanation)

        # Mantém self.table apontando para summary_table por compatibilidade
        self.table = self.summary_table

        self.tab_widget.addTab(tab, "Resumo Consolidado (summary.csv — 45 Colunas)")

    def _build_episodes_table_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        header = QLabel(
            "Planilha episodes.csv (28 colunas): métricas de requisição, perdas e modulações por episódio individual. "
            "Clique no cabeçalho de qualquer coluna para consultar sua definição."
        )
        header.setWordWrap(True)
        header.setStyleSheet(f"color: {theme.COLORS.text_secondary}; font-size: 11px; font-weight: 600;")
        layout.addWidget(header)

        self.raw_table = QTableWidget()
        self._raw_column_keys = list(EPISODES_FIELDNAMES)
        self._raw_column_names = list(EPISODES_FIELDNAMES)

        self.raw_table.setColumnCount(len(self._raw_column_keys))
        self.raw_table.setHorizontalHeaderLabels(self._raw_column_names)

        for col_idx, key in enumerate(self._raw_column_keys):
            if key in METRIC_EXPLANATIONS:
                label, explanation = METRIC_EXPLANATIONS[key]
                item = self.raw_table.horizontalHeaderItem(col_idx)
                if item:
                    item.setToolTip(f"<b>{label}</b><br/><br/>{explanation}")

        self.raw_table.setAlternatingRowColors(True)
        self.raw_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.raw_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.raw_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.raw_table.horizontalHeader().setFixedHeight(36)
        self.raw_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.raw_table.horizontalHeader().setStretchLastSection(True)
        self.raw_table.verticalHeader().setVisible(False)
        layout.addWidget(self.raw_table, 1)

        self.metric_explanation = QTextBrowser()
        self.metric_explanation.setMaximumHeight(80)
        self.metric_explanation.setFrameShape(QFrame.Shape.NoFrame)
        self.metric_explanation.setHtml(
            f'<p style="color: {theme.COLORS.text_secondary}; margin: 0;">'
            'Clique no título de qualquer coluna de <b>episodes.csv</b> acima para inspecionar sua definição técnica.</p>'
        )
        self.raw_table.horizontalHeader().sectionClicked.connect(self._on_raw_column_clicked)
        layout.addWidget(self.metric_explanation)

        self.tab_widget.addTab(tab, "Resultados por Episódio (episodes.csv — 28 Colunas)")

    def _build_history_tab(self) -> None:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(8, 8, 8, 8)
        tab_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        tab_layout.addWidget(splitter, 1)

        # ── Coluna Esquerda: Lista de Histórico e Ações ──────────────────
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        history_group = QGroupBox("Registros de Simulações Salvas")
        history_group_layout = QVBoxLayout(history_group)
        history_group_layout.setContentsMargins(10, 20, 10, 10)

        self.records_list = QListWidget()
        self.records_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.records_list.currentRowChanged.connect(self._on_history_selection_changed)
        history_group_layout.addWidget(self.records_list)
        left_layout.addWidget(history_group, 1)

        btn_group = QGroupBox("Ações do Registro Selecionado")
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.setContentsMargins(10, 18, 10, 10)
        btn_layout.setSpacing(6)

        self.replot_btn = QPushButton("Carregar nos Resultados Atuais")
        self.replot_btn.setProperty("class", "primary")
        self.replot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.replot_btn.clicked.connect(self._send_selected_to_results)
        btn_layout.addWidget(self.replot_btn)

        btn_row1 = QHBoxLayout()
        self.rename_btn = QPushButton("Renomear")
        self.rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rename_btn.clicked.connect(self._rename_selected)
        btn_row1.addWidget(self.rename_btn)

        self.delete_btn = QPushButton("Excluir")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._delete_selected)
        btn_row1.addWidget(self.delete_btn)
        btn_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.history_export_episodes_btn = QPushButton("Exportar episodes.csv")
        self.history_export_episodes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_export_episodes_btn.clicked.connect(self._export_history_episodes_csv)
        btn_row2.addWidget(self.history_export_episodes_btn)

        self.history_export_summary_btn = QPushButton("Exportar summary.csv")
        self.history_export_summary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_export_summary_btn.clicked.connect(self._export_history_summary_csv)
        btn_row2.addWidget(self.history_export_summary_btn)
        btn_layout.addLayout(btn_row2)

        left_layout.addWidget(btn_group)

        # ── Coluna Direita: Detalhes do Registro Selecionado ─────────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.info_group = QGroupBox("Metadados e Parâmetros da Simulação")
        info_layout = QVBoxLayout(self.info_group)
        info_layout.setContentsMargins(12, 20, 12, 12)

        self.info_label = QLabel("Selecione uma simulação na lista ao lado para inspecionar seus detalhes.")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        right_layout.addWidget(self.info_group)

        table_group = QGroupBox("Prévia de Episódios (episodes.csv) da Simulação Selecionada")
        table_tab_layout = QVBoxLayout(table_group)
        table_tab_layout.setContentsMargins(10, 20, 10, 10)

        self.history_results_table = QTableWidget()
        self.history_results_table.setColumnCount(len(EPISODES_FIELDNAMES))
        self.history_results_table.setHorizontalHeaderLabels(EPISODES_FIELDNAMES)
        self.history_results_table.setAlternatingRowColors(True)
        self.history_results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.history_results_table.horizontalHeader().setStretchLastSection(True)
        self.history_results_table.verticalHeader().setVisible(False)
        table_tab_layout.addWidget(self.history_results_table)

        right_layout.addWidget(table_group, 1)

        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([360, 600])

        self.tab_widget.addTab(tab, "Histórico de Simulações Salvas")

    def setup_controllers(
        self,
        results_manager: ResultsManager,
        history_manager: HistoryManager | None = None,
    ) -> None:
        self.results_manager = results_manager
        if history_manager is not None:
            self.history_manager = history_manager
            self.refresh_history_list()

    def update_results(self) -> None:
        if not self.results_manager:
            return

        raw_results = self.results_manager.get_raw_results()
        if not raw_results:
            self.summary_table.setRowCount(0)
            self.raw_table.setRowCount(0)
            return

        if self.results_manager.last_generated_csv_paths:
            paths_txt = " | ".join(str(p) for p in self.results_manager.last_generated_csv_paths)
            self.csv_status_label.setText(f"Arquivos gerados automaticamente: {paths_txt}")
            self.csv_status_label.setStyleSheet(f"color: {theme.COLORS.success}; font-size: 11px; font-weight: 600;")

        summary_rows = self.results_manager.get_summary_rows()
        self.summary_table.setRowCount(0)
        for s_row in summary_rows:
            row_idx = self.summary_table.rowCount()
            self.summary_table.insertRow(row_idx)
            for col_idx, key in enumerate(self._summary_column_keys):
                val_str = _format_cell_value(key, s_row.get(key, ""))
                item = QTableWidgetItem(val_str)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.summary_table.setItem(row_idx, col_idx, item)

        self._populate_raw_table(self.results_manager.get_episode_rows())

    def _populate_raw_table(self, episode_rows: list[dict]) -> None:
        self.raw_table.setRowCount(0)

        for ep_row in episode_rows:
            row_idx = self.raw_table.rowCount()
            self.raw_table.insertRow(row_idx)

            for col_idx, key in enumerate(self._raw_column_keys):
                val_str = _format_cell_value(key, ep_row.get(key, ""))
                item = QTableWidgetItem(val_str)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.raw_table.setItem(row_idx, col_idx, item)

    def _on_summary_column_clicked(self, col_index: int) -> None:
        c = theme.COLORS
        if 0 <= col_index < len(self._summary_column_keys):
            key = self._summary_column_keys[col_index]
            base_key = key[:-5] if key.endswith("_mean") else (key[:-4] if key.endswith("_std") else key)
            if key in METRIC_EXPLANATIONS:
                label, explanation = METRIC_EXPLANATIONS[key]
                self.summary_explanation.setHtml(
                    f'<h4 style="color: {c.primary_light}; margin: 0 0 4px 0;">{label}</h4>'
                    f'<p style="margin: 0; color: {c.text};">{explanation}</p>'
                )
            elif base_key in METRIC_EXPLANATIONS:
                label, explanation = METRIC_EXPLANATIONS[base_key]
                stat_suffix = "Média aritmética" if key.endswith("_mean") else "Desvio padrão amostral"
                self.summary_explanation.setHtml(
                    f'<h4 style="color: {c.primary_light}; margin: 0 0 4px 0;">{stat_suffix} — {label} ({key})</h4>'
                    f'<p style="margin: 0; color: {c.text};">{explanation}</p>'
                )
            else:
                self.summary_explanation.setHtml(
                    f'<p style="color: {c.text_secondary}; margin: 0;">'
                    f'Coluna de <b>summary.csv</b>: <b>{key}</b></p>'
                )

    def _on_raw_column_clicked(self, col_index: int) -> None:
        c = theme.COLORS
        if 0 <= col_index < len(self._raw_column_keys):
            key = self._raw_column_keys[col_index]
            if key in METRIC_EXPLANATIONS:
                label, explanation = METRIC_EXPLANATIONS[key]
                self.metric_explanation.setHtml(
                    f'<h4 style="color: {c.primary_light}; margin: 0 0 4px 0;">{label}</h4>'
                    f'<p style="margin: 0; color: {c.text};">{explanation}</p>'
                )
            else:
                self.metric_explanation.setHtml(
                    f'<p style="color: {c.text_secondary}; margin: 0;">'
                    f'Coluna de <b>episodes.csv</b>: <b>{self._raw_column_names[col_index]}</b></p>'
                )

    def _export_episodes_csv(self) -> None:
        if not self.results_manager or not self.results_manager.get_raw_results():
            QMessageBox.warning(self, "Aviso", "Não há resultados disponíveis para exportar.")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar episodes.csv (28 Colunas)",
            "episodes.csv",
            "Arquivos CSV (*.csv)",
        )
        if not filepath:
            return
        try:
            self.results_manager.export_episodes_csv(Path(filepath))
            QMessageBox.information(
                self,
                "Exportação Concluída",
                f"Arquivo episodes.csv gerado com sucesso:\n{filepath}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar episodes.csv:\n{str(e)}")

    def _export_summary_csv(self) -> None:
        if not self.results_manager or not self.results_manager.get_raw_results():
            QMessageBox.warning(self, "Aviso", "Não há resultados disponíveis para exportar.")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar summary.csv (45 Colunas)",
            "summary.csv",
            "Arquivos CSV (*.csv)",
        )
        if not filepath:
            return
        try:
            self.results_manager.export_summary_csv(Path(filepath))
            QMessageBox.information(
                self,
                "Exportação Concluída",
                f"Arquivo summary.csv gerado com sucesso:\n{filepath}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar summary.csv:\n{str(e)}")

    def _export_legacy_folder(self) -> None:
        if not self.results_manager or not self.results_manager.get_raw_results():
            QMessageBox.warning(self, "Aviso", "Não há resultados disponíveis para exportar.")
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Diretório para Salvar episodes.csv e summary.csv",
        )
        if not folder:
            return
        try:
            saved_paths = self.results_manager.save_pair_in_directory(Path(folder))
            paths_str = "\n".join(str(p) for p in saved_paths)
            self.csv_status_label.setText(f"Arquivos CSV gerados: {' | '.join(str(p) for p in saved_paths)}")
            QMessageBox.information(
                self,
                "Arquivos CSV Gerados",
                f"Os arquivos padrão foram gravados em:\n\n{paths_str}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao gerar arquivos CSV:\n{str(e)}")

    # ── Métodos de Histórico Integrado ────────────────────────────────────

    def refresh_history_list(self) -> None:
        self.records_list.clear()

        if not self.history_manager:
            return

        records = self.history_manager.get_records()
        for idx, rec in enumerate(records):
            n_tasks = len(rec.results)
            topo = rec.config.get("topology_id", "nobel-eu").upper()
            item_text = f"{rec.name}\nData: {rec.timestamp}  •  {topo} ({n_tasks} ep.)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.records_list.addItem(item)

        if records:
            self.records_list.setCurrentRow(0)
        else:
            self._on_history_selection_changed(-1)

    def refresh_list(self) -> None:
        """Alias para compatibilidade com chamadas de atualização do histórico."""
        self.refresh_history_list()

    def _on_history_selection_changed(self, row: int) -> None:
        records = self.history_manager.get_records() if self.history_manager else []
        has_selection = 0 <= row < len(records)

        self.replot_btn.setEnabled(has_selection)
        self.rename_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.history_export_episodes_btn.setEnabled(has_selection)
        self.history_export_summary_btn.setEnabled(has_selection)

        if not has_selection:
            self._current_record = None
            self.info_label.setText("Nenhum registro histórico disponível ou selecionado.")
            self.history_results_table.setRowCount(0)
            return

        rec = records[row]
        self._current_record = rec

        from optical_networking_gym_v2.gui.models.run_config import HEURISTIC_CATALOG
        h_names = {h.id: h.name for h in HEURISTIC_CATALOG}
        h_str = ", ".join(h_names.get(hid, hid) for hid in rec.heuristic_ids)
        cfg = rec.config
        load_str = f"{cfg.get('load', 'N/A')} Erlangs" if "load" in cfg else "Varredura"

        mode_val = cfg.get("run_mode", "single")
        mode_str = "Simulação Simples" if mode_val in ("single", "simple", "simples") else mode_val.upper()

        self.info_label.setText(
            f"<b>Identificador da Simulação:</b> {rec.name}<br/>"
            f"<b>Data/Hora de Execução:</b> {rec.timestamp} &nbsp;|&nbsp; "
            f"<b>Modo:</b> {mode_str}<br/>"
            f"<b>Algoritmos Avaliados:</b> {h_str}<br/>"
            f"<b>Topologia:</b> {cfg.get('topology_id', 'nobel-eu').upper()} &nbsp;|&nbsp; "
            f"<b>Grade:</b> {cfg.get('num_spectrum_resources', 320)} FSUs &nbsp;|&nbsp; "
            f"<b>Requisições/Ep:</b> {cfg.get('episode_length', 1000)} &nbsp;|&nbsp; "
            f"<b>Carga Base:</b> {load_str}"
        )

        self.history_results_table.setRowCount(0)
        for res in rec.results:
            if res.get("status") == "error":
                continue
            r_idx = self.history_results_table.rowCount()
            self.history_results_table.insertRow(r_idx)
            ep_row = format_episode_csv_row(res)
            for col_i, key in enumerate(EPISODES_FIELDNAMES):
                item = QTableWidgetItem(_format_cell_value(key, ep_row.get(key, "")))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.history_results_table.setItem(r_idx, col_i, item)

    def _send_selected_to_results(self) -> None:
        if self._current_record and self._current_record.results:
            if self.results_manager:
                self.results_manager.set_results(self._current_record.results)
                self.update_results()
                self.tab_widget.setCurrentIndex(0)
            self.load_record_to_results.emit(self._current_record.results)

    def _rename_selected(self) -> None:
        row = self.records_list.currentRow()
        if not self.history_manager or row < 0 or not self._current_record:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Renomear Registro",
            "Novo nome para o registro de simulação:",
            text=self._current_record.name,
        )
        if ok and new_name.strip():
            try:
                self.history_manager.rename_record(row, new_name.strip())
                self.refresh_history_list()
                self.records_list.setCurrentRow(row)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao renomear: {e}")

    def _delete_selected(self) -> None:
        row = self.records_list.currentRow()
        if not self.history_manager or row < 0 or not self._current_record:
            return

        reply = QMessageBox.question(
            self,
            "Excluir Registro",
            f"Deseja realmente excluir '{self._current_record.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.history_manager.delete_record(row)
                self.refresh_history_list()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao excluir: {e}")

    def _export_history_episodes_csv(self) -> None:
        row = self.records_list.currentRow()
        if not self.history_manager or row < 0 or not self._current_record:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Histórico — episodes.csv (28 Colunas)",
            "episodes.csv",
            "Arquivos CSV (*.csv)",
        )
        if filepath:
            try:
                self.history_manager.export_record_episodes_csv(row, Path(filepath))
                QMessageBox.information(self, "Sucesso", f"episodes.csv exportado com sucesso:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao exportar episodes.csv: {e}")

    def _export_history_summary_csv(self) -> None:
        row = self.records_list.currentRow()
        if not self.history_manager or row < 0 or not self._current_record:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Histórico — summary.csv (45 Colunas)",
            "summary.csv",
            "Arquivos CSV (*.csv)",
        )
        if filepath:
            try:
                self.history_manager.export_record_summary_csv(row, Path(filepath))
                QMessageBox.information(self, "Sucesso", f"summary.csv exportado com sucesso:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao exportar summary.csv: {e}")

    def load_state(self, state: GUIState) -> None:
        pass

    def update_state(self, state: GUIState) -> None:
        pass
