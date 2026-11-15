"""Painel de Configurações Físicas da Rede Óptica (Camada Física).

Permite configurar os parâmetros da camada física de transmissão (comprimento
máximo de span, coeficiente de atenuação da fibra SSMF, figura de ruído dos EDFAs,
largura nominal de canal, granularidade do slot ITU-T G.694.1 e potência de
lançamento), exibindo cálculos analíticos em tempo real e a fundamentação
matemática do Modelo de Ruído Gaussiano (GN Model).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTextBrowser, QFrame, QSplitter, QScrollArea, QLabel
)

from optical_networking_gym_v2.gui import theme
from optical_networking_gym_v2.gui.theme import create_academic_header
from optical_networking_gym_v2.gui.models.gui_config import GUIState
from optical_networking_gym_v2.gui.widgets.parameter_widget import ParameterWidget


class PhysicsPanel(QWidget):
    """Painel responsável pelos parâmetros e modelagem teórica da camada física."""

    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.header_banner = create_academic_header(
            title="2. Modelagem Física da Fibra Óptica & Amplificação EDFA",
            subtitle=(
                "Defina os parâmetros de propagação óptica na fibra monomodo padrão (SSMF), amplificação "
                "a fibra dopada com Érbio (EDFA) e densidade espectral para avaliação da OSNR (ASE + NLI)."
            ),
            badge_text="ITU-T G.652 • MODELO GN (BANDA C)",
            parent=self,
        )
        root_layout.addWidget(self.header_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        # ── Coluna da Esquerda: Configuração Física ────────────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.config_container = QWidget()
        config_layout = QVBoxLayout(self.config_container)
        config_layout.setContentsMargins(0, 0, 6, 0)
        config_layout.setSpacing(12)

        self.physics_group = QGroupBox("Parâmetros de Transmissão e Amplificação")
        params_layout = QVBoxLayout(self.physics_group)
        params_layout.setContentsMargins(14, 22, 14, 14)
        params_layout.setSpacing(10)

        # Comprimento Máximo de Span
        self.max_span_widget = ParameterWidget(
            label_text="Comp. Máx. de Span (L_span)",
            input_type="doublespinbox",
            default_value=80.0,
            min_value=10.0,
            max_value=200.0,
            step=5.0,
            decimals=1,
            suffix=" km",
            help_title="Comprimento Máximo de Span entre Amplificadores (L_span)",
            help_text=(
                "<b>Definição Física:</b> Distância máxima permitida (em km) entre amplificadores ópticos "
                "EDFA consecutivos em um enlace de fibra.<br><br>"
                "<b>Particionamento Homogêneo:</b> Um enlace de comprimento <i>L</i> é subdividido em "
                "<i>N</i><sub>s</sub> = &lceil;<i>L</i> / <i>L</i><sub>span</sub>&rceil; spans iguais. Em cada span, o amplificador EDFA "
                "restaura integralmente a potência perdida por atenuação (<i>G</i><sub>dB</sub> = &alpha; &middot; <i>L</i><sub>s</sub>)."
            )
        )
        self.max_span_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.max_span_widget)

        # Atenuação Linear (dB/km)
        self.attenuation_widget = ParameterWidget(
            label_text="Atenuação da Fibra (α)",
            input_type="doublespinbox",
            default_value=0.20,
            min_value=0.01,
            max_value=1.0,
            step=0.01,
            decimals=3,
            suffix=" dB/km",
            help_title="Coeficiente de Atenuação Linear da Fibra (α)",
            help_text=(
                "<b>Definição Física:</b> Taxa de perda de potência óptica por quilômetro na janela de "
                "comprimento de onda de 1550 nm (Banda C), causada por espalhamento Rayleigh e absorção.<br><br>"
                "<b>Valor de Referência (ITU-T G.652 SSMF):</b> &alpha; = 0,20 dB/km "
                "(correspondendo a 4,61 &times; 10<sup>&minus;5</sup> m<sup>&minus;1</sup> em escala neperiana)."
            )
        )
        self.attenuation_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.attenuation_widget)

        # Figura de Ruído do Amplificador (dB)
        self.noise_figure_widget = ParameterWidget(
            label_text="Figura de Ruído EDFA (NF)",
            input_type="doublespinbox",
            default_value=4.5,
            min_value=0.0,
            max_value=15.0,
            step=0.1,
            decimals=2,
            suffix=" dB",
            help_title="Figura de Ruído do Amplificador EDFA (Noise Figure)",
            help_text=(
                "<b>Definição Física:</b> Degradação na relação sinal-ruído introduzida pelo processo quântico "
                "de Emissão Espontânea Amplificada (ASE) nos amplificadores a fibra dopada com Érbio.<br><br>"
                "<b>Equação da Potência ASE por Span:</b><br>"
                "<code>P_ASE = h · f · B_ref · (G - 1) · NF_linear</code><br><br>"
                "<b>Valor Padrão Acadêmico:</b> 4,5 dB a 5,5 dB."
            )
        )
        self.noise_figure_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.noise_figure_widget)

        # Largura de Canal (GHz)
        self.channel_width_widget = ParameterWidget(
            label_text="Largura Nominal de Canal",
            input_type="doublespinbox",
            default_value=12.5,
            min_value=1.0,
            max_value=200.0,
            step=0.5,
            decimals=2,
            suffix=" GHz",
            help_title="Largura Espectral de Referência do Canal",
            help_text=(
                "<b>Definição:</b> Largura espectral base usada no cálculo de densidade espectral de potência "
                "(PSD) e avaliação de ruído de canal.<br><br>"
                "Em redes EON baseadas na recomendação ITU-T G.694.1, coincide tipicamente com a largura "
                "do slot elementar de 12,5 GHz."
            )
        )
        self.channel_width_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.channel_width_widget)

        # Largura do Slot de Frequência (GHz)
        self.slot_bandwidth_widget = ParameterWidget(
            label_text="Largura do Slot (Δf_slot)",
            input_type="doublespinbox",
            default_value=12.5,
            min_value=1.0,
            max_value=100.0,
            step=0.5,
            decimals=2,
            suffix=" GHz",
            help_title="Granularidade do Slot Espectral (ITU-T G.694.1)",
            help_text=(
                "<b>Norma ITU-T G.694.1:</b> Define a largura de banda &Delta;<i>f</i><sub>slot</sub> de uma "
                "Unidade de Slot de Frequência (FSU). O valor padronizado mundialmente para redes ópticas "
                "elásticas (EONs) é <b>12,5 GHz</b> (ou 6,25 GHz em grades ultra-finas)."
            )
        )
        self.slot_bandwidth_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.slot_bandwidth_widget)

        # Potência de Lançamento (dBm)
        self.launch_power_widget = ParameterWidget(
            label_text="Potência de Lançamento (P_tx)",
            input_type="doublespinbox",
            default_value=0.0,
            min_value=-15.0,
            max_value=15.0,
            step=0.2,
            decimals=2,
            suffix=" dBm",
            help_title="Potência Óptica de Lançamento por Canal (P_tx)",
            help_text=(
                "<b>Definição Física:</b> Potência óptica injetada na entrada de cada span de fibra "
                "(em dBm, onde 0 dBm = 1 mW).<br><br>"
                "<b>Compromisso Não-Linear (Kerr Effect):</b>"
                "<ul>"
                "<li><b>Regime Linear (<i>P</i><sub>tx</sub> baixa):</b> Dominado pelo ruído ASE dos EDFAs (OSNR &prop; <i>P</i><sub>tx</sub>).</li>"
                "<li><b>Regime Não-Linear (<i>P</i><sub>tx</sub> alta):</b> Dominado pela interferência não-linear NLI (<i>P</i><sub>NLI</sub> &prop; <i>P</i><sub>tx</sub><sup>3</sup>, fazendo a OSNR cair com <i>P</i><sub>tx</sub><sup>&minus;2</sup>).</li>"
                "</ul>"
            )
        )
        self.launch_power_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.launch_power_widget)

        config_layout.addWidget(self.physics_group)

        # Calculadora de Orçamento Óptico em Tempo Real
        self.budget_group = QGroupBox("Orçamento Óptico por Span (Calculado em Tempo Real)")
        budget_layout = QVBoxLayout(self.budget_group)
        budget_layout.setContentsMargins(14, 20, 14, 12)
        self.budget_summary_label = QLabel()
        self.budget_summary_label.setWordWrap(True)
        budget_layout.addWidget(self.budget_summary_label)
        config_layout.addWidget(self.budget_group)

        config_layout.addStretch(1)
        left_scroll.setWidget(self.config_container)
        left_scroll.setMinimumWidth(370)

        # ── Coluna da Direita: Referência de Efeitos Físicos ──────────────
        self.edu_group = QGroupBox("Fundamentação Teórica — Modelo GN e Degradações Físicas")
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
        splitter.setSizes([460, 500])

        self._refresh_theoretical_view()
        self._update_budget_summary()

    def _update_budget_summary(self) -> None:
        c = theme.COLORS
        span_km = float(self.max_span_widget.value())
        att_db = float(self.attenuation_widget.value())
        nf_db = float(self.noise_figure_widget.value())
        p_dbm = float(self.launch_power_widget.value())
        slot_ghz = float(self.slot_bandwidth_widget.value())

        span_loss_db = span_km * att_db
        p_mw = 10.0 ** (p_dbm / 10.0)
        psd_mw_per_ghz = p_mw / slot_ghz if slot_ghz > 0 else 0.0

        self.budget_summary_label.setText(
            f"<table style='width:100%; font-size:11px;'>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Perda Máxima por Span (α × L_span):</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.accent};'>{span_loss_db:.2f} dB (Ganho EDFA = +{span_loss_db:.2f} dB)</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Potência Linear de Lançamento (P_tx):</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.primary_light};'>{p_mw:.3f} mW ({p_dbm:+.2f} dBm)</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Densidade Espectral de Potência (PSD):</td>"
            f"<td style='text-align:right; font-weight:700;'>{psd_mw_per_ghz*1000:.2f} μW/GHz (NF = {nf_db:.1f} dB)</td></tr>"
            f"</table>"
        )

    def _refresh_theoretical_view(self) -> None:
        c = theme.COLORS
        self.edu_view.setHtml(f"""
        <div style="font-family: {theme.FONT_FAMILY}; color: {c.text}; line-height: 1.5;">
            <h3 style="color: {c.primary_light}; margin-top: 0px; margin-bottom: 6px;">
                Modelagem de Qualidade de Transmissão (QoT) em Banda C
            </h3>
            <p style="margin-top: 0;">
                Em Redes Ópticas Elásticas (EONs) com detecção coerente, a viabilidade física de um
                caminho óptico (<i>lightpath</i>) depende da <b>Relação Sinal-Ruído Óptica Generalizada (GSNR / OSNR)</b>
                no receptor, que combina degradações lineares e não-lineares acumuladas ao longo dos múltiplos
                spans da rota:
            </p>

            <div style="background-color: {c.surface_light}; border: 1px solid {c.border};
                        border-left: 4px solid {c.primary}; padding: 10px; border-radius: 6px;
                        text-align: center; font-family: {theme.FONT_MONO}; font-weight: 700; margin: 10px 0;">
                GSNR = P<sub>tx</sub> / ( P<sub>ASE</sub> + P<sub>NLI</sub> ) &ge; OSNR<sub>th</sub>(m) + M<sub>sistema</sub>
            </div>

            <h4 style="color: {c.accent}; margin-bottom: 4px; margin-top: 12px;">
                1. Ruído de Emissão Espontânea Amplificada (P<sub>ASE</sub> — Linear)
            </h4>
            <p style="margin-top: 0;">
                Gerado nos amplificadores EDFA instalados a cada span para compensar a atenuação da fibra
                (&alpha; em dB/km). Independe da potência dos demais canais ativos na fibra e cresce
                linearmente com o número de spans atravessados:
            </p>
            <div style="background-color: {c.surface_light}; padding: 6px 10px; border-radius: 4px;
                        font-family: {theme.FONT_MONO}; font-size: 10.5px;">
                P<sub>ASE,span</sub> = h &middot; &nu; &middot; B<sub>ref</sub> &middot; (10<sup>(&alpha;&middot;L/10)</sup> &minus; 1) &middot; 10<sup>(NF/10)</sup>
            </div>

            <h4 style="color: {c.accent}; margin-bottom: 4px; margin-top: 12px;">
                2. Interferência Não-Linear por Efeito Kerr (P<sub>NLI</sub> — Modelo GN)
            </h4>
            <p style="margin-top: 0;">
                O índice de refração da sílica depende da intensidade óptica instantânea. Pelo
                <b>Modelo de Ruído Gaussiano (GN Model — Poggiolini et al., JLT)</b>, a interação entre
                o próprio canal (<b>SPM</b> — <i>Self-Phase Modulation</i>) e os canais adjacentes ativos
                no mesmo enlace (<b>XPM</b> — <i>Cross-Phase Modulation</i>) atua como ruído gaussiano aditivo
                proporcional ao cubo da potência:
            </p>
            <div style="background-color: {c.surface_light}; padding: 6px 10px; border-radius: 4px;
                        font-family: {theme.FONT_MONO}; font-size: 10.5px;">
                P<sub>NLI</sub> = &eta;<sub>NLI</sub>(f<sub>i</sub>, Espectro Ativo) &middot; P<sub>tx</sub><sup>3</sup>
            </div>

            <h4 style="color: {c.accent}; margin-bottom: 4px; margin-top: 12px;">
                3. Impacto Dinâmico nas Conexões Vizinhas (Disrupção de QoT)
            </h4>
            <p style="margin-top: 0;">
                Quando uma nova requisição é alocada em slots espectrais próximos a conexões já ativas,
                o termo de modulação cruzada (XPM) aumenta o <i>P</i><sub>NLI</sub> dos canais vizinhos. Se a
                GSNR de uma conexão existente cair abaixo do seu limiar OSNR<sub>th</sub>, ocorre uma
                <b>disrupção de serviço em operação</b>.
            </p>
        </div>
        """)

    def _on_changed(self, *args) -> None:
        self._update_budget_summary()
        self.state_changed.emit()

    def load_state(self, state: GUIState) -> None:
        """Preenche o painel com as configurações físicas obtidas do estado global."""
        self.max_span_widget.setValue(state.max_span_length_km)
        self.attenuation_widget.setValue(state.default_attenuation_db_per_km)
        self.noise_figure_widget.setValue(state.default_noise_figure_db)
        self.channel_width_widget.setValue(state.channel_width)
        self.slot_bandwidth_widget.setValue(state.frequency_slot_bandwidth / 1e9)
        self.launch_power_widget.setValue(state.launch_power_dbm)
        self._refresh_theoretical_view()
        self._update_budget_summary()

    def update_state(self, state: GUIState) -> None:
        """Exporta os valores do painel de volta para a estrutura de estado global."""
        state.max_span_length_km = float(self.max_span_widget.value())
        state.default_attenuation_db_per_km = float(self.attenuation_widget.value())
        state.default_noise_figure_db = float(self.noise_figure_widget.value())
        state.channel_width = float(self.channel_width_widget.value())
        state.frequency_slot_bandwidth = float(self.slot_bandwidth_widget.value()) * 1e9
        state.launch_power_dbm = float(self.launch_power_widget.value())
