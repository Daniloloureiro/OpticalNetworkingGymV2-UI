"""Painel de Qualidade de Transmissão (QoT) e Formatos de Modulação Óptica.

Permite configurar o modelo físico de validação de QoT (ASE+NLI vs. Distância),
a margem de segurança de sistema (dB), o monitoramento e descarte por disrupção
não-linear intercanal e o conjunto de modulações adaptativas (BPSK a 64QAM),
atualizando em tempo real a tabela de limiares de OSNR efetiva e ocupação de slots.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QGroupBox, QTextBrowser, QFrame, QSplitter, QPushButton, QSpinBox,
    QScrollArea, QGridLayout, QSizePolicy
)

from optical_networking_gym_v2.gui import theme
from optical_networking_gym_v2.gui.theme import create_academic_header
from optical_networking_gym_v2.gui.models.gui_config import GUIState
from optical_networking_gym_v2.gui.widgets.parameter_widget import ParameterWidget, ParameterHelpDialog


_MODULATION_SPECS = [
    ("BPSK", 1, 5.0, 4000, 8, 32),
    ("QPSK", 2, 8.5, 2000, 4, 16),
    ("8QAM", 3, 12.6, 1000, 3, 11),
    ("16QAM", 4, 15.0, 500, 2, 8),
    ("32QAM", 5, 18.6, 250, 2, 7),
    ("64QAM", 6, 21.0, 125, 2, 6),
]


class QoTPanel(QWidget):
    """Painel responsável pelas configurações de QoT, disrupção e modulações."""

    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.header_banner = create_academic_header(
            title="Modulação e QoT",
            subtitle=(
                "Configure os formatos de modulação óptica adaptativa, o critério físico de admissão "
                "de canais (GSNR / Alcance), a margem de projeto e o monitoramento de disrupções."
            ),
            badge_text="",
            parent=self,
        )
        root_layout.addWidget(self.header_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        # ── Coluna da Esquerda: Configurações de Modulação e QoT ─────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.config_container = QWidget()
        config_layout = QVBoxLayout(self.config_container)
        config_layout.setContentsMargins(0, 0, 6, 0)
        config_layout.setSpacing(12)

        # Grupo 1: Configurações de Modulação (Primeiro)
        self.mods_catalog_group = QGroupBox("Configurações de Modulação (Constelações Habilitadas)")
        mods_layout = QVBoxLayout(self.mods_catalog_group)
        mods_layout.setContentsMargins(14, 22, 14, 14)
        mods_layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(8)
        self.mod_checkboxes: dict[str, QCheckBox] = {}
        for idx, (mod_name, eff, osnr_th, reach_km, _, _) in enumerate(_MODULATION_SPECS):
            cb = QCheckBox(f"{mod_name} ({eff} b/s/Hz • {osnr_th:.1f} dB)")
            cb.setChecked(True)
            cb.setStyleSheet("font-weight: 600; font-size: 10.5px;")
            cb.toggled.connect(self._on_changed)
            self.mod_checkboxes[mod_name] = cb
            grid.addWidget(cb, idx // 2, idx % 2)
        mods_layout.addLayout(grid)

        # Modulações a Considerar
        self.consider_container = QWidget()
        consider_layout = QHBoxLayout(self.consider_container)
        consider_layout.setContentsMargins(0, 4, 0, 0)
        consider_layout.setSpacing(10)

        self.limit_mod_checkbox = QCheckBox("Limitar Modulações Candidatas")
        self.limit_mod_checkbox.setMinimumWidth(145)
        self.limit_mod_checkbox.setStyleSheet("font-weight: 600;")
        self.limit_mod_checkbox.toggled.connect(self._on_limit_toggled)
        consider_layout.addWidget(self.limit_mod_checkbox)

        self.mod_count_spin = QSpinBox()
        self.mod_count_spin.setMinimum(1)
        self.mod_count_spin.setMaximum(6)
        self.mod_count_spin.setValue(6)
        self.mod_count_spin.setSuffix(" formatos")
        self.mod_count_spin.setEnabled(False)
        self.mod_count_spin.valueChanged.connect(self._on_changed)
        consider_layout.addWidget(self.mod_count_spin, 1)

        self.consider_help_btn = self._create_help_button(
            "Subconjunto de Modulações Candidatas",
            "Quando habilitado, restringe a busca às <i>N</i> modulações mais eficientes viáveis para o caminho, "
            "reduzindo a dimensão do espaço de ação em agentes de Aprendizado por Reforço e heurísticas."
        )
        consider_layout.addWidget(self.consider_help_btn)
        mods_layout.addWidget(self.consider_container)

        config_layout.addWidget(self.mods_catalog_group)

        # Grupo 2: Restrições de Qualidade de Transmissão (QoT)
        self.qot_group = QGroupBox("Critério de Validação de QoT e Margem de Projeto")
        qot_layout = QVBoxLayout(self.qot_group)
        qot_layout.setContentsMargins(14, 22, 14, 14)
        qot_layout.setSpacing(10)

        self.constraint_row = QWidget()
        constraint_row_layout = QHBoxLayout(self.constraint_row)
        constraint_row_layout.setContentsMargins(0, 3, 0, 3)
        constraint_row_layout.setSpacing(10)

        constraint_label = QLabel("Modelo de Restrição QoT")
        constraint_label.setWordWrap(True)
        constraint_label.setMinimumWidth(145)
        constraint_label.setMaximumWidth(195)
        constraint_label.setStyleSheet(
            f"font-family: {theme.FONT_FAMILY}; font-size: 11px; font-weight: 600;"
        )
        constraint_row_layout.addWidget(constraint_label)

        self.constraint_combo = QComboBox()
        self.constraint_combo.setMinimumWidth(130)
        self.constraint_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.constraint_combo.addItems(["ASE+NLI", "DIST"])
        self.constraint_combo.setCurrentText("ASE+NLI")
        self.constraint_combo.currentTextChanged.connect(self._on_changed)
        constraint_row_layout.addWidget(self.constraint_combo, 1)

        self.constraint_help_btn = self._create_help_button(
            "Modelo de Avaliação da Qualidade de Transmissão (QoT)",
            "Define o modelo físico adotado pelo kernel Cython para validar candidatos de alocação:<br><br>"
            "<ul>"
            "<li><b>ASE+NLI (Modelo Físico Completo — Recomendado):</b> Avalia em tempo real a GSNR combinando "
            "o ruído linear ASE dos EDFAs e a interferência não-linear (NLI por efeito Kerr, SPM + XPM) "
            "provocada pelos canais ativos na fibra.</li>"
            "<li><b>DIST (Alcance Óptico Tabelado):</b> Aproximação geométrica clássica que aprova uma modulação "
            "se o comprimento físico da rota for menor ou igual ao alcance máximo tabelado.</li>"
            "</ul>"
        )
        constraint_row_layout.addWidget(self.constraint_help_btn)
        qot_layout.addWidget(self.constraint_row)

        # Margem de Segurança (dB)
        self.margin_widget = ParameterWidget(
            label_text="Margem de Sistema (M)",
            input_type="doublespinbox",
            default_value=0.0,
            min_value=0.0,
            max_value=12.0,
            step=0.25,
            decimals=2,
            suffix=" dB",
            help_title="Margem de Segurança de Sistema (System Margin)",
            help_text=(
                "<b>Definição Física:</b> Folga adicional de OSNR (em dB) somada ao limiar mínimo de recepção "
                "(OSNR<sub>req</sub> = OSNR<sub>th</sub>(<i>m</i>) + <i>M</i>) no momento da admissão do serviço.<br><br>"
                "<b>Papel na Mitigação de Disrupções:</b>"
                "<ul>"
                "<li><b><i>M</i> = 0,0 dB (Zero-Margin):</b> Maximiza a eficiência espectral imediata, mas deixa "
                "canais recém-alocados vulneráveis à interferência NLI de futuras conexões vizinhas.</li>"
                "<li><b><i>M</i> = 1,0 a 2,0 dB:</b> Protege conexões ativas contra flutuações de carga, "
                "ao custo de exigir modulações mais robustas (menor ordem) em rotas longas.</li>"
                "</ul>"
            )
        )
        self.margin_widget.valueChanged.connect(self._on_changed)
        qot_layout.addWidget(self.margin_widget)

        config_layout.addWidget(self.qot_group)

        # Grupo 3: Monitoramento de Disrupção (QoT)
        self.disruption_group = QGroupBox("Dinâmica de Interferência Intercanal (Disrupção QoT)")
        disruption_layout = QVBoxLayout(self.disruption_group)
        disruption_layout.setContentsMargins(14, 22, 14, 14)
        disruption_layout.setSpacing(8)

        self.measure_disruptions_check = QCheckBox(
            "Monitorar Disrupções em Conexões Ativas (Reavaliação OSNR)"
        )
        self.measure_disruptions_check.setStyleSheet("font-weight: 600;")
        self.measure_disruptions_check.toggled.connect(self._on_changed)
        disruption_layout.addWidget(self.measure_disruptions_check)

        self.drop_on_disruption_check = QCheckBox(
            "Derrubar Conexões Degradadas (Drop on QoT Violation)"
        )
        self.drop_on_disruption_check.setStyleSheet("font-weight: 600;")
        self.drop_on_disruption_check.toggled.connect(self._on_changed)
        disruption_layout.addWidget(self.drop_on_disruption_check)

        disruption_note = QLabel(
            "Para avaliar disrupção física por interferência não-linear (NLI), "
            "ative as opções acima para contabilizar e derrubar conexões degradadas."
        )
        disruption_note.setWordWrap(True)
        disruption_note.setStyleSheet(f"color: {theme.COLORS.text_secondary}; font-size: 10.5px; padding-top: 4px;")
        disruption_layout.addWidget(disruption_note)

        config_layout.addWidget(self.disruption_group)
        config_layout.addStretch(1)
        left_scroll.setWidget(self.config_container)
        left_scroll.setMinimumWidth(370)

        # ── Coluna da Direita: Referência Teórica e Tabela Dinâmica ───────
        self.edu_group = QGroupBox("Especificação Técnica — Limiares OSNR Efetivos e Ocupação Espectral")
        self.edu_group.setMinimumWidth(260)
        edu_layout = QVBoxLayout(self.edu_group)
        edu_layout.setContentsMargins(12, 22, 12, 12)
        edu_layout.setSpacing(8)

        self.edu_view = QTextBrowser()
        self.edu_view.setFrameShape(QFrame.Shape.NoFrame)
        edu_layout.addWidget(self.edu_view)

        splitter.addWidget(left_scroll)
        splitter.addWidget(self.edu_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([470, 490])

        self._refresh_modulation_table()

    def _create_help_button(self, title: str, help_text: str) -> QPushButton:
        btn = QPushButton("?")
        btn.setToolTip(f"Clique para ver a fundamentação teórica de '{title}'")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(24, 24)
        btn.setStyleSheet(f"""
            QPushButton {{
                min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
                border-radius: 12px; padding: 0px;
                background-color: {theme.COLORS.surface_light};
                color: {theme.COLORS.primary_light};
                border: 1px solid {theme.COLORS.border};
                font-weight: 700; font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {theme.COLORS.primary};
                color: #ffffff;
                border-color: {theme.COLORS.primary};
            }}
        """)
        btn.clicked.connect(lambda: ParameterHelpDialog(title, help_text, self).exec())
        return btn

    def _on_limit_toggled(self, checked: bool) -> None:
        self.mod_count_spin.setEnabled(checked)
        self._on_changed()

    def _on_changed(self, *args) -> None:
        self._refresh_modulation_table()
        self.state_changed.emit()

    def _refresh_modulation_table(self) -> None:
        """Renderiza a tabela técnica com os limiares OSNR ajustados pela margem atual."""
        c = theme.COLORS
        margin_db = float(self.margin_widget.value())
        qot_mode = self.constraint_combo.currentText()

        rows_html = ""
        for mod_name, eff, base_osnr, reach_km, slots_100g, slots_400g in _MODULATION_SPECS:
            is_active = self.mod_checkboxes[mod_name].isChecked()
            eff_osnr = base_osnr + margin_db
            status_color = c.success if is_active else c.text_disabled
            row_opacity = "1.0" if is_active else "0.45"
            status_txt = "ATIVO" if is_active else "OFF"

            rows_html += (
                f"<tr style='border-bottom: 1px solid {c.border_light}; opacity: {row_opacity};'>"
                f"<td style='padding: 5px 6px; font-weight: 700; color: {c.primary_light};'>{mod_name}</td>"
                f"<td style='text-align: center; padding: 5px 4px; font-weight: 700; color: {status_color};'>{status_txt}</td>"
                f"<td style='text-align: center; padding: 5px 4px;'>{eff} b/s/Hz</td>"
                f"<td style='text-align: right; padding: 5px 6px;'>{base_osnr:.1f} dB</td>"
                f"<td style='text-align: right; padding: 5px 6px; font-weight: 700; color: {c.accent};'>{eff_osnr:.2f} dB</td>"
                f"<td style='text-align: right; padding: 5px 6px;'>{reach_km:,} km</td>"
                f"<td style='text-align: center; padding: 5px 4px; font-family: monospace;'>{slots_100g} / {slots_400g}</td>"
                f"</tr>"
            )

        self.edu_view.setHtml(f"""
        <div style="font-family: {theme.FONT_FAMILY}; color: {c.text}; line-height: 1.45;">
            <div style="margin-bottom: 6px;">
                <span style="font-size: 13.5px; font-weight: 700; color: {c.primary_light};">
                    Parâmetros de Modulação Óptica Adaptativa (Margem Atual: +{margin_db:.2f} dB | Modelo: {qot_mode})
                </span>
            </div>
            <p style="margin-top: 0; font-size: 11px; color: {c.text_secondary};">
                Abaixo estão os limiares de OSNR requeridos antes da correção de erro (<i>Pre-FEC BER</i>) e a
                quantidade de Unidades de Slot de Frequência (FSUs de 12.5 GHz) consumidas para demandas de 100G e 400G:
            </p>

            <table style="width: 100%; border-collapse: collapse; font-size: 10.5px; margin: 10px 0;">
                <thead>
                    <tr style="background-color: {c.surface_light}; border-bottom: 2px solid {c.border}; color: {c.text};">
                        <th style="text-align: left; padding: 6px;">Formato</th>
                        <th style="text-align: center; padding: 6px;">Estado</th>
                        <th style="text-align: center; padding: 6px;">Eficiência (&eta;)</th>
                        <th style="text-align: right; padding: 6px;">OSNR<sub>th</sub> Base</th>
                        <th style="text-align: right; padding: 6px;">OSNR<sub>req</sub> (+M)</th>
                        <th style="text-align: right; padding: 6px;">Alcance Máx.</th>
                        <th style="text-align: center; padding: 6px;">FSUs (100G/400G)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <h4 style="color: {c.accent}; margin-bottom: 4px; margin-top: 12px;">
                Fórmula de Dimensionamento de Slots Espectrais (FSUs):
            </h4>
            <div style="background-color: {c.surface_light}; border: 1px solid {c.border};
                        padding: 8px; border-radius: 5px; font-family: {theme.FONT_MONO};
                        font-size: 10.5px; text-align: center; margin-bottom: 10px;">
                N<sub>slots</sub>(B, m) = &lceil; B (Gbps) / ( &eta;<sub>m</sub> &times; &Delta;f<sub>slot</sub> (GHz) ) &rceil; + N<sub>guard</sub>
            </div>

            <h4 style="color: {c.accent}; margin-bottom: 4px; margin-top: 10px;">
                Bloqueio na Admissão vs. Disrupção em Operação:
            </h4>
            <ul style="margin-top: 2px; padding-left: 18px; font-size: 11px;">
                <li><b>Bloqueio por QoT (Admissão):</b> A requisição entrante não encontra nenhum par (rota, modulação, slot) cuja GSNR supere OSNR<sub>req</sub> = OSNR<sub>th</sub> + <i>M</i>.</li>
                <li><b>Disrupção de QoT (Pós-Alocação):</b> Um novo canal alocado injeta ruído não-linear (XPM) sobre canais vizinhos já ativos, reduzindo a GSNR destes abaixo de OSNR<sub>th</sub>. Quando habilitado, o simulador contabiliza e opcionalmente derruba as conexões afetadas.</li>
            </ul>
        </div>
        """)

    def load_state(self, state: GUIState) -> None:
        index = self.constraint_combo.findText(state.qot_constraint)
        if index >= 0:
            self.constraint_combo.setCurrentIndex(index)

        self.margin_widget.setValue(state.margin)

        if state.modulations_to_consider is not None:
            self.limit_mod_checkbox.setChecked(True)
            self.mod_count_spin.setEnabled(True)
            self.mod_count_spin.setValue(state.modulations_to_consider)
        else:
            self.limit_mod_checkbox.setChecked(False)
            self.mod_count_spin.setEnabled(False)
            self.mod_count_spin.setValue(6)

        self.measure_disruptions_check.setChecked(state.measure_disruptions)
        self.drop_on_disruption_check.setChecked(state.drop_on_disruption)

        for mod_name, cb in self.mod_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(mod_name in state.modulations)
            cb.blockSignals(False)

        self._refresh_modulation_table()

    def update_state(self, state: GUIState) -> None:
        state.qot_constraint = self.constraint_combo.currentText()
        state.margin = float(self.margin_widget.value())

        if self.limit_mod_checkbox.isChecked():
            state.modulations_to_consider = int(self.mod_count_spin.value())
        else:
            state.modulations_to_consider = None

        state.measure_disruptions = self.measure_disruptions_check.isChecked()
        state.drop_on_disruption = self.drop_on_disruption_check.isChecked()

        active_mods = [mod_name for mod_name, cb in self.mod_checkboxes.items() if cb.isChecked()]
        if not active_mods:
            active_mods = ["BPSK", "QPSK", "8QAM", "16QAM", "32QAM", "64QAM"]
            for cb in self.mod_checkboxes.values():
                cb.setChecked(True)
        state.modulations = active_mods
