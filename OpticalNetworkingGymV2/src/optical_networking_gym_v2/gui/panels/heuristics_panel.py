"""Painel de Seleção de Heurísticas de Roteamento, Modulação e Espectro (RMLSA/RMSA).

Permite pesquisar, filtrar e selecionar uma ou mais heurísticas para avaliação
comparativa sob as mesmas sementes de simulação.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QGroupBox, QTextBrowser, QFrame, QSplitter, QScrollArea, QPushButton
)

from optical_networking_gym_v2.gui import theme
from optical_networking_gym_v2.gui.theme import create_academic_header
from optical_networking_gym_v2.gui.models.gui_config import GUIState
from optical_networking_gym_v2.gui.models.run_config import HEURISTIC_CATALOG
from optical_networking_gym_v2.gui.widgets.heuristic_card import HeuristicCard


class HeuristicsPanel(QWidget):
    """Painel responsável por gerenciar a seleção e estudo de heurísticas."""

    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.header_banner = create_academic_header(
            title="Heurísticas",
            subtitle=(
                "Selecione um ou mais algoritmos de decisão para comparação sob as mesmas sementes "
                "estatísticas de simulação."
            ),
            badge_text="",
            parent=self,
        )
        root_layout.addWidget(self.header_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        # ── Coluna da Esquerda: Filtro e Lista de Heurísticas ────
        self.list_container = QWidget()
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)

        self.filter_group = QGroupBox("Filtros de Busca e Seleção")
        filter_outer = QVBoxLayout(self.filter_group)
        filter_outer.setContentsMargins(12, 20, 12, 10)
        filter_outer.setSpacing(8)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar algoritmo por nome ou critério...")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_input, 2)

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Todas as Complexidades",
            "Complexidade Baixa (Baselines)",
            "Complexidade Média",
            "Complexidade Alta",
        ])
        self.category_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.category_combo, 1)
        filter_outer.addLayout(filter_layout)

        # Linha de Seleção Rápida
        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)

        self.selected_count_label = QLabel("Selecionadas: 1")
        self.selected_count_label.setStyleSheet(
            f"font-weight: 700; font-size: 11px; color: {theme.COLORS.primary_light};"
        )
        presets_row.addWidget(self.selected_count_label)
        presets_row.addStretch()

        btn_all = QPushButton("Selecionar Todas")
        btn_all.setProperty("class", "flat")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.clicked.connect(lambda: self._apply_preset([h.id for h in HEURISTIC_CATALOG]))
        presets_row.addWidget(btn_all)

        btn_ff = QPushButton("Apenas First-Fit")
        btn_ff.setProperty("class", "flat")
        btn_ff.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ff.clicked.connect(lambda: self._apply_preset(["select_first_fit_action"]))
        presets_row.addWidget(btn_ff)

        filter_outer.addLayout(presets_row)
        list_layout.addWidget(self.filter_group)

        # Área de Rolagem para os Cartões de Heurísticas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("background-color: transparent;")
        self.cards_layout = QVBoxLayout(self.scroll_widget)
        self.cards_layout.setContentsMargins(0, 0, 6, 0)
        self.cards_layout.setSpacing(8)

        self.cards: dict[str, HeuristicCard] = {}
        for entry in HEURISTIC_CATALOG:
            accent_color = "primary"
            if entry.complexity == "low":
                accent_color = "success"
            elif entry.complexity == "medium":
                accent_color = "warning"
            elif entry.complexity == "high":
                accent_color = "accent"

            card = HeuristicCard(
                title=entry.name,
                category=entry.category,
                description=entry.description,
                complexity=entry.complexity.upper(),
                accent=accent_color,
                checked=False,
                heuristic_id=entry.id,
            )
            card.setProperty("heuristic_id", entry.id)
            card.toggled.connect(self._on_card_toggled)

            self.cards_layout.addWidget(card)
            self.cards[entry.id] = card

        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        list_layout.addWidget(self.scroll_area, 1)

        # ── Coluna da Direita: Referência Teórica/Educacional ────────────
        self.edu_group = QGroupBox("Taxonomia Científica de Algoritmos RMLSA")
        edu_layout = QVBoxLayout(self.edu_group)
        edu_layout.setContentsMargins(12, 22, 12, 12)
        edu_layout.setSpacing(8)

        self.edu_view = QTextBrowser()
        self.edu_view.setFrameShape(QFrame.Shape.NoFrame)
        edu_layout.addWidget(self.edu_view)

        self.list_container.setMinimumWidth(400)
        self.edu_group.setMinimumWidth(250)
        splitter.addWidget(self.list_container)
        splitter.addWidget(self.edu_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([560, 380])

        self._refresh_educational_guide()
        self._update_selected_counter()

    def _apply_preset(self, target_ids: list[str]) -> None:
        target_set = set(target_ids)
        for hid, card in self.cards.items():
            card.toggled.disconnect(self._on_card_toggled)
            card.setChecked(hid in target_set)
            card.toggled.connect(self._on_card_toggled)
        self._update_selected_counter()
        self.state_changed.emit()

    def _update_selected_counter(self) -> None:
        c = theme.COLORS
        count = sum(1 for card in self.cards.values() if card.isChecked())
        total = len(self.cards)
        self.selected_count_label.setText(f"Selecionadas: {count}/{total}")
        self.selected_count_label.setStyleSheet(
            f"font-weight: 700; font-size: 11px; color: {c.primary_light if count > 0 else c.error};"
        )
        for card in self.cards.values():
            card.update_card_style()

    def _refresh_educational_guide(self) -> None:
        c = theme.COLORS
        self.edu_view.setHtml(f"""
        <div style="font-family: {theme.FONT_FAMILY}; color: {c.text}; line-height: 1.5;">
            <h3 style="color: {c.primary_light}; margin-top: 0px; margin-bottom: 6px;">
                Formulação do Problema RMLSA
            </h3>
            <p style="margin-top: 0;">
                O problema de <b>Roteamento, Modulação e Alocação de Espectro (RMLSA)</b> em Redes Ópticas
                Elásticas é NP-Difícil. A cada chegada de requisição (<i>s</i>, <i>d</i>, <i>B</i>), o controlador deve selecionar
                uma tupla (<i>k</i>, <i>m</i>, <i>f</i>) dentre os <i>K</i> caminhos, <i>M</i> modulações e <i>S</i> slots iniciais que satisfaça:
            </p>
            <ol style="margin-top: 4px; padding-left: 18px;">
                <li><b>Continuidade Espectral:</b> O mesmo bloco de slots deve estar livre em todos os enlaces da rota <i>k</i>.</li>
                <li><b>Contiguidade Espectral:</b> Os <i>N</i><sub>slots</sub>(<i>B</i>, <i>m</i>) devem ser estritamente adjacentes na grade ITU-T G.694.1.</li>
                <li><b>Viabilidade de QoT:</b> GSNR(<i>k</i>, <i>m</i>, <i>f</i>) &ge; OSNR<sub>th</sub>(<i>m</i>) + <i>M</i><sub>sistema</sub>.</li>
            </ol>

            <h4 style="color: {c.accent}; margin-bottom: 4px; margin-top: 12px;">
                Famílias de Algoritmos no Catálogo:
            </h4>
            <ul style="margin-top: 2px; padding-left: 18px;">
                <li><b>Baselines Clássicos (First-Fit / Random):</b> Avaliam a tupla na ordem canônica
                <code>Rota k &rarr; Modulação m &rarr; Slot f</code> ou por amostragem uniforme entre candidatos válidos.</li>
                <li><b>Maximização de Relação Sinal-Ruído (Highest SNR):</b> Seleciona o candidato com a maior folga de OSNR,
                priorizando robustez física do enlace óptico.</li>
                <li><b>Balanceamento de Carga (Load Balancing):</b> Minimiza a ocupação máxima entre os enlaces da rota para
                distribuir o tráfego uniformemente na malha.</li>
                <li><b>Mitigação de Fragmentação (Lowest Fragmentation / KSP + Best Mod + Last Fit):</b> Preserva blocos
                contíguos livres no espectro para proteger demandas futuras de alta capacidade (100G e 400G).</li>
            </ul>
        </div>
        """)

    def _on_card_toggled(self, checked: bool) -> None:
        self._update_selected_counter()
        self.state_changed.emit()

    def _apply_filters(self, *args) -> None:
        search_text = self.search_input.text().strip().lower()
        category_filter = self.category_combo.currentText()

        for entry in HEURISTIC_CATALOG:
            card = self.cards.get(entry.id)
            if not card:
                continue

            matches_category = True
            if "Baixa" in category_filter:
                matches_category = (entry.complexity.lower() == "low")
            elif "Média" in category_filter:
                matches_category = (entry.complexity.lower() == "medium")
            elif "Alta" in category_filter:
                matches_category = (entry.complexity.lower() == "high")

            matches_text = True
            if search_text:
                matches_text = (
                    search_text in entry.name.lower()
                    or search_text in entry.description.lower()
                    or search_text in entry.id.lower()
                )

            card.setVisible(matches_category and matches_text)

    def load_state(self, state: GUIState) -> None:
        for card in self.cards.values():
            card.toggled.disconnect(self._on_card_toggled)

        valid_selected = [hid for hid in state.selected_heuristics if hid in self.cards]
        if not valid_selected and HEURISTIC_CATALOG:
            valid_selected = [HEURISTIC_CATALOG[0].id]

        for heuristic_id, card in self.cards.items():
            card.setChecked(heuristic_id in valid_selected)

        for card in self.cards.values():
            card.toggled.connect(self._on_card_toggled)

        self._refresh_educational_guide()
        self._update_selected_counter()

    def update_state(self, state: GUIState) -> None:
        selected_ids = [hid for hid, card in self.cards.items() if card.isChecked()]
        if not selected_ids and HEURISTIC_CATALOG:
            selected_ids = [HEURISTIC_CATALOG[0].id]
            self.cards[selected_ids[0]].setChecked(True)
        self._update_selected_counter()
        state.selected_heuristics = selected_ids
