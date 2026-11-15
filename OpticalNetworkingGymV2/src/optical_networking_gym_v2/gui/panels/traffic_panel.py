"""Painel de Configuração de Tráfego e Teoria de Teletráfego.

Permite configurar o perfil de tráfego da rede óptica (Dinâmico Poisson vs. Estático),
a carga oferecida (Erlang), o tempo médio de retenção exponencial (Holding Time) e
a distribuição de probabilidades das taxas de linha (10G, 40G, 100G, 400G), com
cálculo analítico em tempo real da taxa de chegada (λ) e tabela de distribuição PMF.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QCheckBox, QSpinBox, QDoubleSpinBox, QFrame, QSplitter,
    QLabel, QPushButton, QScrollArea, QTextBrowser
)

from optical_networking_gym_v2.gui import theme
from optical_networking_gym_v2.gui.theme import create_academic_header
from optical_networking_gym_v2.gui.models.gui_config import GUIState
from optical_networking_gym_v2.gui.widgets.parameter_widget import ParameterWidget, ParameterHelpDialog


class TrafficPanel(QWidget):
    """Painel responsável pelas configurações estocásticas de tráfego e demandas."""

    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.header_banner = create_academic_header(
            title="3. Modelagem Estocástica de Tráfego & Demandas de Banda",
            subtitle=(
                "Configure o processo estocástico de geração de requisições (Poisson/Exponencial), "
                "a intensidade de tráfego em Erlangs e a distribuição de taxas de transmissão (Gbps)."
            ),
            badge_text="TEORIA DE TELETRÁFEGO • PROCESSO DE POISSON",
            parent=self,
        )
        root_layout.addWidget(self.header_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        # ── Coluna da Esquerda: Configurações de Tráfego ──────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.config_container = QWidget()
        config_layout = QVBoxLayout(self.config_container)
        config_layout.setContentsMargins(0, 0, 6, 0)
        config_layout.setSpacing(12)

        # Grupo 1: Regime de Tráfego e Dinâmica
        self.mode_group = QGroupBox("Regime Estocástico e Intensidade de Tráfego")
        mode_layout = QVBoxLayout(self.mode_group)
        mode_layout.setContentsMargins(14, 22, 14, 14)
        mode_layout.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)

        mode_label = QLabel("Regime de Tráfego:")
        mode_label.setMinimumWidth(135)
        mode_label.setStyleSheet(f"font-family: {theme.FONT_FAMILY}; font-size: 11px; font-weight: 600;")
        mode_row.addWidget(mode_label)

        self.radio_dynamic = QRadioButton("Dinâmico (Poisson)")
        self.radio_static = QRadioButton("Estático (Incremental)")
        self.radio_dynamic.setChecked(True)

        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.addButton(self.radio_dynamic)
        self.mode_button_group.addButton(self.radio_static)

        mode_row.addWidget(self.radio_dynamic)
        mode_row.addWidget(self.radio_static)
        mode_row.addStretch()

        self.mode_help_btn = QPushButton("?")
        self.mode_help_btn.setToolTip("Fundamentação teórica sobre regimes de tráfego óptico")
        self.mode_help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_help_btn.setFixedSize(24, 24)
        self.mode_help_btn.setStyleSheet(f"""
            QPushButton {{
                min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
                border-radius: 12px; padding: 0px;
                background-color: {theme.COLORS.surface_light}; color: {theme.COLORS.primary_light};
                border: 1px solid {theme.COLORS.border}; font-weight: 700; font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {theme.COLORS.primary}; color: #ffffff; border-color: {theme.COLORS.primary};
            }}
        """)
        self.mode_help_btn.clicked.connect(self._show_mode_help)
        mode_row.addWidget(self.mode_help_btn)
        mode_layout.addLayout(mode_row)

        sep = QFrame()
        sep.setProperty("class", "separator")
        mode_layout.addWidget(sep)

        self.dynamic_params_widget = QWidget()
        dynamic_form = QVBoxLayout(self.dynamic_params_widget)
        dynamic_form.setContentsMargins(0, 0, 0, 0)
        dynamic_form.setSpacing(10)

        self.load_widget = ParameterWidget(
            label_text="Carga Oferecida (A)",
            input_type="doublespinbox",
            default_value=300.0,
            min_value=1.0,
            max_value=5000.0,
            step=25.0,
            decimals=1,
            suffix=" Erlang",
            help_title="Intensidade de Tráfego Oferecido (Erlang)",
            help_text=(
                "<b>Definição (Teoria de Teletráfego de A. K. Erlang):</b> Medida adimensional da intensidade "
                "de carga oferecida à malha óptica, definida pelo produto entre a taxa média de chegada de "
                "requisições (&lambda;, em chegadas/s) e o tempo médio de retenção (<i>h̄</i> = 1/&mu;, em s):<br><br>"
                "<code>A (Erlangs) = λ × h̄ = λ / μ</code><br><br>"
                "<b>Interpretação Física:</b> Corresponde ao número médio esperado de conexões simultaneamente "
                "ativas na rede caso não houvesse bloqueio."
            )
        )
        self.load_widget.valueChanged.connect(self._on_changed)
        dynamic_form.addWidget(self.load_widget)

        self.holding_time_widget = ParameterWidget(
            label_text="Tempo de Retenção (h̄)",
            input_type="doublespinbox",
            default_value=10800.0,
            min_value=1.0,
            max_value=100000.0,
            step=100.0,
            decimals=1,
            suffix=" s",
            help_title="Tempo Médio de Retenção / Duração da Conexão (Holding Time)",
            help_text=(
                "<b>Definição:</b> Valor esperado <i>h̄</i> = 1/&mu; da variável aleatória exponencial que "
                "modela a duração de cada serviço ativo antes de sua desmontagem (<i>teardown</i>).<br><br>"
                "<b>Nota Técnica:</b> Como o simulador ajusta automaticamente &lambda; = <i>A</i> / <i>h̄</i> "
                "para manter a carga em Erlangs constante, <i>h̄</i> define a escala temporal absoluta do relógio "
                "de eventos discretos (ex: 10.800 s = 3 horas ou 100 s normalizado)."
            )
        )
        self.holding_time_widget.valueChanged.connect(self._on_changed)
        dynamic_form.addWidget(self.holding_time_widget)

        mode_layout.addWidget(self.dynamic_params_widget)

        self.radio_dynamic.toggled.connect(self._toggle_mode_visibility)
        self.radio_static.toggled.connect(self._toggle_mode_visibility)

        config_layout.addWidget(self.mode_group)

        # Grupo 2: Bit Rates e Pesos
        self.rates_group = QGroupBox("Perfil de Demandas de Taxa de Linha (Bit Rates)")
        rates_layout = QVBoxLayout(self.rates_group)
        rates_layout.setContentsMargins(14, 22, 14, 14)
        rates_layout.setSpacing(8)

        header_row = QHBoxLayout()
        lbl_col1 = QLabel("Taxa de Linha")
        lbl_col1.setMinimumWidth(110)
        lbl_col1.setStyleSheet("font-weight: 700; font-size: 10.5px;")
        lbl_col2 = QLabel("Peso Relativo")
        lbl_col2.setMinimumWidth(115)
        lbl_col2.setStyleSheet("font-weight: 700; font-size: 10.5px;")
        lbl_col3 = QLabel("Prob. Efetiva")
        lbl_col3.setStyleSheet("font-weight: 700; font-size: 10.5px;")
        header_row.addWidget(lbl_col1)
        header_row.addWidget(lbl_col2)
        header_row.addWidget(lbl_col3)
        header_row.addStretch()

        self.uniform_btn = QPushButton("Uniformizar Pesos")
        self.uniform_btn.setProperty("class", "flat")
        self.uniform_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uniform_btn.setToolTip("Define peso igual (1.0) para todas as taxas ativas (25% cada)")
        self.uniform_btn.clicked.connect(self._set_uniform_weights)
        header_row.addWidget(self.uniform_btn)
        rates_layout.addLayout(header_row)

        self.rate_config_rows: list[tuple[QCheckBox, QSpinBox, QDoubleSpinBox, QLabel]] = []
        standard_rates = [48, 120, 240, 480]
        default_weights = [1.0, 1.0, 1.0, 1.0]

        for rate, weight in zip(standard_rates, default_weights):
            row_widget = QWidget()
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(0, 2, 0, 2)
            row_lay.setSpacing(12)

            chk = QCheckBox()
            chk.setChecked(True)
            chk.toggled.connect(self._on_rate_toggled)

            rate_spin = QSpinBox()
            rate_spin.setRange(1, 10000)
            rate_spin.setSingleStep(10)
            rate_spin.setSuffix(" Gbps")
            rate_spin.setValue(rate)
            rate_spin.setMinimumWidth(95)
            rate_spin.setStyleSheet("font-weight: 600;")
            rate_spin.valueChanged.connect(self._on_weight_changed)

            spin = QDoubleSpinBox()
            spin.setRange(0.01, 100.0)
            spin.setSingleStep(0.25)
            spin.setDecimals(2)
            spin.setValue(weight)
            spin.setMinimumWidth(115)
            spin.valueChanged.connect(self._on_weight_changed)

            prob_lbl = QLabel("25.0%")
            prob_lbl.setMinimumWidth(65)
            prob_lbl.setStyleSheet(f"font-family: {theme.FONT_MONO}; font-weight: 700;")

            row_lay.addWidget(chk)
            row_lay.addWidget(rate_spin)
            row_lay.addWidget(spin)
            row_lay.addWidget(prob_lbl)
            row_lay.addStretch()

            rates_layout.addWidget(row_widget)
            self.rate_config_rows.append((chk, rate_spin, spin, prob_lbl))

        config_layout.addWidget(self.rates_group)

        # Grupo 3: Indicadores Analíticos de Teletráfego
        self.teletraffic_group = QGroupBox("Parâmetros Derivados de Teletráfego (Tempo Real)")
        tt_layout = QVBoxLayout(self.teletraffic_group)
        tt_layout.setContentsMargins(14, 20, 14, 12)
        self.teletraffic_summary_label = QLabel()
        self.teletraffic_summary_label.setWordWrap(True)
        tt_layout.addWidget(self.teletraffic_summary_label)
        config_layout.addWidget(self.teletraffic_group)

        config_layout.addStretch(1)
        left_scroll.setWidget(self.config_container)
        left_scroll.setMinimumWidth(370)

        # ── Coluna da Direita: Especificação Técnica da Distribuição ──────
        self.plot_group = QGroupBox("Especificação da Função Massa de Probabilidade (PMF) e Teletráfego")
        self.plot_group.setMinimumWidth(260)
        plot_layout = QVBoxLayout(self.plot_group)
        plot_layout.setContentsMargins(12, 22, 12, 12)

        self.pmf_view = QTextBrowser()
        self.pmf_view.setFrameShape(QFrame.Shape.NoFrame)
        plot_layout.addWidget(self.pmf_view)

        splitter.addWidget(left_scroll)
        splitter.addWidget(self.plot_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([470, 490])

        self._update_probability_chart()

    def _set_uniform_weights(self) -> None:
        for chk, _rate_spin, spin, _lbl in self.rate_config_rows:
            if chk.isChecked():
                spin.blockSignals(True)
                spin.setValue(1.0)
                spin.blockSignals(False)
        self._update_probability_chart()
        self._on_changed()

    def _show_mode_help(self) -> None:
        help_text = (
            "<b>1. Tráfego Dinâmico (Processo de Poisson / Erlang-B Generalizado):</b><br>"
            "As requisições chegam segundo um processo de Poisson com taxa &lambda; = <i>A</i> / <i>h̄</i> "
            "(intervalos entre chegadas exponencialmente distribuídos) e permanecem ativas por um tempo "
            "exponencial com média <i>h̄</i>. Avalia a probabilidade de bloqueio em regime estacionário "
            "e o fenômeno de fragmentação espectral.<br><br>"
            "<b>2. Tráfego Estático (Planejamento de Capacidade Incremental):</b><br>"
            "As conexões estabelecidas permanecem ativas indefinidamente (<i>h̄</i> &rarr; &infin;), permitindo "
            "estudar o ponto de saturação espectral da malha óptica."
        )
        ParameterHelpDialog("Regimes de Tráfego em Redes Ópticas", help_text, self).exec()

    def _toggle_mode_visibility(self) -> None:
        is_dynamic = self.radio_dynamic.isChecked()
        self.dynamic_params_widget.setVisible(is_dynamic)
        self._update_probability_chart()
        self._on_changed()

    def _on_rate_toggled(self, checked: bool) -> None:
        sender = self.sender()
        for chk, rate_spin, spin, _lbl in self.rate_config_rows:
            if chk == sender:
                rate_spin.setEnabled(checked)
                spin.setEnabled(checked)
                break
        self._update_probability_chart()
        self._on_changed()

    def _on_weight_changed(self, val: float) -> None:
        self._update_probability_chart()
        self._on_changed()

    def _on_changed(self, *args) -> None:
        self._update_teletraffic_summary()
        self.state_changed.emit()

    def _get_active_rates_and_probabilities(self) -> tuple[list[int], list[float]]:
        active_rates = []
        weights = []

        for chk, rate_spin, spin, _lbl in self.rate_config_rows:
            if chk.isChecked():
                active_rates.append(int(rate_spin.value()))
                weights.append(spin.value())

        if not weights:
            return [], []

        total_weight = sum(weights)
        probabilities = [w / total_weight for w in weights]
        return active_rates, probabilities

    def _update_teletraffic_summary(self) -> None:
        c = theme.COLORS
        active_rates, probs = self._get_active_rates_and_probabilities()
        load = float(self.load_widget.value())
        ht = float(self.holding_time_widget.value())
        lam = load / ht if ht > 0 else 0.0
        inter_arrival = 1.0 / lam if lam > 0 else 0.0
        mean_br = sum(r * p for r, p in zip(active_rates, probs)) if active_rates else 0.0
        offered_tbps = (load * mean_br) / 1000.0

        # Atualizar labels de probabilidade ao lado de cada spinbox
        prob_map = dict(zip(active_rates, probs))
        for chk, rate_spin, _spin, lbl in self.rate_config_rows:
            rate = int(rate_spin.value())
            if chk.isChecked() and rate in prob_map:
                lbl.setText(f"{prob_map[rate] * 100:.1f}%")
                lbl.setStyleSheet(f"font-family: {theme.FONT_MONO}; font-weight: 700; color: {c.primary_light};")
            else:
                lbl.setText("0.0% (Inativo)")
                lbl.setStyleSheet(f"font-family: {theme.FONT_MONO}; color: {c.text_disabled};")

        self.teletraffic_summary_label.setText(
            f"<table style='width:100%; font-size:11px;'>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Taxa de Chegada de Poisson (λ = A / h̄):</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.primary_light};'>{lam:.4f} req/s (Δt̄ = {inter_arrival:.2f} s)</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Taxa de Linha Média por Demanda (E[B]):</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.success};'>{mean_br:.1f} Gbps</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Tráfego Agregado Médio Oferecido (A × E[B]):</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.accent};'>{offered_tbps:.2f} Tbps</td></tr>"
            f"</table>"
        )

    def _update_probability_chart(self) -> None:
        """Atualiza a tabela analítica de distribuição PMF e o resumo de teletráfego."""
        self._update_teletraffic_summary()
        c = theme.COLORS
        active_rates, probabilities = self._get_active_rates_and_probabilities()
        load = float(self.load_widget.value())
        ht = float(self.holding_time_widget.value())
        lam = load / ht if ht > 0 else 0.0
        mean_br = sum(r * p for r, p in zip(active_rates, probabilities)) if active_rates else 0.0

        prob_map = dict(zip(active_rates, probabilities))
        rows_html = ""
        for chk, rate_spin, spin, _lbl in self.rate_config_rows:
            rate = int(rate_spin.value())
            is_on = chk.isChecked()
            w_val = float(spin.value()) if is_on else 0.0
            p_val = prob_map.get(rate, 0.0) if is_on else 0.0
            contrib_gbps = rate * p_val
            state_txt = "ATIVO" if is_on else "INATIVO"
            state_col = c.success if is_on else c.text_disabled
            row_col = c.text if is_on else c.text_disabled

            rows_html += (
                f"<tr style='color:{row_col}; border-bottom:1px solid {c.border_light};'>"
                f"<td style='padding:5px 4px; font-weight:700; color:{c.primary_light if is_on else c.text_disabled};'>{rate} Gbps</td>"
                f"<td style='padding:5px 4px; text-align:center; font-weight:700; color:{state_col};'>{state_txt}</td>"
                f"<td style='padding:5px 4px; text-align:right; font-family:{theme.FONT_MONO};'>{w_val:.2f}</td>"
                f"<td style='padding:5px 4px; text-align:right; font-weight:700; font-family:{theme.FONT_MONO};'>{p_val * 100:.2f}%</td>"
                f"<td style='padding:5px 4px; text-align:right; font-family:{theme.FONT_MONO};'>{contrib_gbps:.2f} Gbps</td>"
                f"</tr>"
            )

        self.pmf_view.setHtml(
            f"<div style='font-family:{theme.FONT_FAMILY}; color:{c.text}; line-height:1.5;'>"
            f"<h3 style='color:{c.primary_light}; margin-top:0px; margin-bottom:6px;'>"
            f"Tabela da Função Massa de Probabilidade P(B = b<sub>k</sub>)</h3>"
            f"<p style='font-size:11px; color:{c.text_secondary}; margin-top:0px;'>"
            f"A cada chegada de conexão no simulador de eventos discretos, a taxa de linha <i>B</i> é sorteada "
            f"segundo a distribuição discreta normalizada abaixo:</p>"
            f"<table width='100%' cellspacing='0' cellpadding='3' style='font-size:11px; border-collapse:collapse;'>"
            f"<tr style='background-color:{c.surface_light}; color:{c.text_secondary}; font-weight:700;'>"
            f"<td style='padding:6px 4px;'>Taxa (b<sub>k</sub>)</td>"
            f"<td style='padding:6px 4px; text-align:center;'>Estado</td>"
            f"<td style='padding:6px 4px; text-align:right;'>Peso (w<sub>k</sub>)</td>"
            f"<td style='padding:6px 4px; text-align:right;'>Probabilidade P(b<sub>k</sub>)</td>"
            f"<td style='padding:6px 4px; text-align:right;'>b<sub>k</sub> &times; P(b<sub>k</sub>)</td>"
            f"</tr>"
            f"{rows_html}"
            f"<tr style='background-color:{c.surface_light}; font-weight:700;'>"
            f"<td colspan='3' style='padding:6px 4px;'>Esperança Matemática E[B] = &Sigma; b<sub>k</sub> P(b<sub>k</sub>)</td>"
            f"<td style='padding:6px 4px; text-align:right; font-family:{theme.FONT_MONO};'>100.00%</td>"
            f"<td style='padding:6px 4px; text-align:right; color:{c.success}; font-family:{theme.FONT_MONO};'>{mean_br:.2f} Gbps</td>"
            f"</tr>"
            f"</table>"
            f"<h4 style='color:{c.accent}; margin-top:14px; margin-bottom:4px;'>"
            f"Modelagem Estocástica de Chegadas e Retenção (M/M/C/C Generalizado)</h4>"
            f"<ul style='margin-top:2px; padding-left:18px; font-size:11px;'>"
            f"<li><b>Processo de Chegada (Poisson Homogêneo):</b> Os intervalos entre chegadas consecutivas "
            f"&Delta;<i>t</i> seguem distribuição exponencial com taxa &lambda; = <i>A</i> / <i>h̄</i> = "
            f"<b>{lam:.4f} requisições/s</b>.</li>"
            f"<li><b>Tempo de Serviço (Exponencial):</b> Cada conexão admitida permanece ativa por um tempo "
            f"exponencialmente distribuído com média <i>h̄</i> = 1/&mu; = <b>{ht:.1f} s</b>.</li>"
            f"<li><b>Seleção Uniforme de Par Origem-Destino:</b> Os nós de origem <i>s</i> e destino <i>d</i> "
            f"(<i>s</i> &ne; <i>d</i>) são amostrados uniformemente dentre os |<i>V</i>|(|<i>V</i>| &minus; 1) pares direcionados da topologia.</li>"
            f"</ul>"
            f"</div>"
        )

    def load_state(self, state: GUIState) -> None:
        if state.traffic_mode == "static":
            self.radio_static.setChecked(True)
        else:
            self.radio_dynamic.setChecked(True)

        self.load_widget.setValue(state.load)
        self.holding_time_widget.setValue(state.mean_holding_time)
        self._toggle_mode_visibility()

        state_rates = list(state.bit_rates) if state.bit_rates else [48, 120, 240, 480]
        state_probs = state.bit_rate_probabilities
        if state_probs is None and state_rates:
            state_probs = [1.0 / len(state_rates)] * len(state_rates)

        for idx, (chk, rate_spin, spin, _lbl) in enumerate(self.rate_config_rows):
            chk.blockSignals(True)
            rate_spin.blockSignals(True)
            spin.blockSignals(True)
            if idx < len(state_rates):
                chk.setChecked(True)
                rate_spin.setEnabled(True)
                rate_spin.setValue(int(state_rates[idx]))
                spin.setEnabled(True)
                prob_val = state_probs[idx] if state_probs and idx < len(state_probs) else (1.0 / len(state_rates))
                spin.setValue(max(0.01, prob_val * len(state_rates)))
            else:
                chk.setChecked(False)
                rate_spin.setEnabled(False)
                spin.setEnabled(False)
                spin.setValue(1.0)
            chk.blockSignals(False)
            rate_spin.blockSignals(False)
            spin.blockSignals(False)

        self._update_probability_chart()

    def update_state(self, state: GUIState) -> None:
        state.traffic_mode = "static" if self.radio_static.isChecked() else "dynamic"
        state.load = float(self.load_widget.value())
        state.mean_holding_time = float(self.holding_time_widget.value())

        active_rates, probabilities = self._get_active_rates_and_probabilities()
        if not active_rates:
            active_rates = [100]
            probabilities = [1.0]

        state.bit_rates = active_rates
        state.bit_rate_probabilities = probabilities
