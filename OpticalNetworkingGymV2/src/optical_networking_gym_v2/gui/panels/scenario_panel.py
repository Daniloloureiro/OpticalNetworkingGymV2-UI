"""Painel de Configuração do Cenário de Simulação e Topologia Física.

Permite configurar os parâmetros fundamentais do cenário de simulação (topologia de
transporte, rotas candidatas K-SP, grade espectral ITU-T G.694.1, tamanho amostral
do episódio e semente de reprodutibilidade), exibindo a ficha técnica completa de
teoria dos grafos e camada física da topologia selecionada.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QGroupBox, QTextBrowser, QFrame, QSplitter, QPushButton, QScrollArea, QSizePolicy
)

from optical_networking_gym_v2 import resolve_topology, TopologyModel
from optical_networking_gym_v2.gui import theme
from optical_networking_gym_v2.gui.theme import create_academic_header
from optical_networking_gym_v2.gui.models.gui_config import GUIState
from optical_networking_gym_v2.gui.widgets.parameter_widget import ParameterWidget, ParameterHelpDialog


_TOPOLOGY_CATALOG = [
    ("nobel-eu", "nobel-eu — Rede Europeia COST/Nobel (28 Nós, 41 Enlaces)"),
    ("nsfnet_chen", "nsfnet_chen — NSFNET Clássica EUA (14 Nós, 21 Enlaces)"),
    ("nobel-us", "nobel-us — Rede Norte-Americana Nobel (14 Nós, 21 Enlaces)"),
    ("janos-us", "janos-us — Rede Backbone EUA Janos (26 Nós, 42 Enlaces)"),
    ("germany50", "germany50 — Rede Nacional Alemã DFN (50 Nós, 88 Enlaces)"),
    ("ring_4", "ring_4 — Topologia Didática em Anel (4 Nós, 4 Enlaces)"),
]


class ScenarioPanel(QWidget):
    """Painel responsável pelas configurações de cenário e análise topológica."""

    state_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        # Cabeçalho Acadêmico Padronizado
        self.header_banner = create_academic_header(
            title="1. Cenário de Simulação e Topologia de Rede Óptica",
            subtitle=(
                "Configure a malha física de roteadores ópticos (ROADMs), o pré-cálculo de rotas "
                "candidatas (K-Shortest Paths), a grade espectral flexível e o tamanho amostral estatístico."
            ),
            badge_text="ITU-T G.694.1 • TEORIA DOS GRAFOS",
            parent=self,
        )
        root_layout.addWidget(self.header_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        # ── Coluna da Esquerda: Configuração (com ScrollArea para responsividade) ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.config_container = QWidget()
        config_layout = QVBoxLayout(self.config_container)
        config_layout.setContentsMargins(0, 0, 6, 0)
        config_layout.setSpacing(12)

        # Grupo 1: Identificação e Topologia
        self.params_group = QGroupBox("Parâmetros Estruturais do Cenário")
        params_layout = QVBoxLayout(self.params_group)
        params_layout.setContentsMargins(14, 22, 14, 14)
        params_layout.setSpacing(10)

        # ID do Cenário
        self.scenario_id_widget = ParameterWidget(
            label_text="Identificador",
            input_type="lineedit",
            default_value="simulacao_rmsa",
            show_help=False,
        )
        self.scenario_id_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.scenario_id_widget)

        # Topologia Física (QComboBox com descrições claras)
        self.topology_row = QWidget()
        topo_row_layout = QHBoxLayout(self.topology_row)
        topo_row_layout.setContentsMargins(0, 3, 0, 3)
        topo_row_layout.setSpacing(10)

        topo_label = QLabel("Topologia Física")
        topo_label.setWordWrap(True)
        topo_label.setMinimumWidth(145)
        topo_label.setMaximumWidth(195)
        topo_label.setStyleSheet(
            f"font-family: {theme.FONT_FAMILY}; font-size: 11px; font-weight: 600;"
        )
        topo_row_layout.addWidget(topo_label)

        self.topology_combo = QComboBox()
        self.topology_combo.setMinimumWidth(140)
        self.topology_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for topo_id, topo_desc in _TOPOLOGY_CATALOG:
            self.topology_combo.addItem(topo_desc, topo_id)
        self.topology_combo.setCurrentIndex(0)
        self.topology_combo.currentIndexChanged.connect(self._on_topology_changed)
        topo_row_layout.addWidget(self.topology_combo, 1)

        self.topo_help_btn = self._create_help_button(
            "Topologia Física da Rede — Grafo G = (V, E)",
            "A topologia física define o grafo <i>G</i> = (<i>V</i>, <i>E</i>) onde <i>V</i> representa os nós de comutação óptica "
            "(ROADMs / OXCs instalados em cidades) e <i>E</i> representa os enlaces de fibra óptica bidirecionais.<br><br>"
            "<b>Topologias de Benchmark Disponíveis na Literatura:</b>"
            "<ul>"
            "<li><b>nobel-eu</b>: Rede pan-europeia do projeto COST 266 / NOBEL (28 nós, 41 enlaces). Padrão em artigos JOCN e LAOP.</li>"
            "<li><b>nsfnet_chen</b>: Backbone clássico dos EUA (14 nós, 21 enlaces) com distâncias continentais longas.</li>"
            "<li><b>nobel-us</b>: Rede norte-americana de referência (14 nós, 21 enlaces).</li>"
            "<li><b>janos-us</b>: Malha de transporte dos EUA com 26 nós e 42 enlaces.</li>"
            "<li><b>germany50</b>: Rede nacional alemã de alta densidade (50 nós, 88 enlaces).</li>"
            "<li><b>ring_4</b>: Anel didático de 4 nós para validação rápida e ensino em laboratório.</li>"
            "</ul>"
        )
        topo_row_layout.addWidget(self.topo_help_btn)
        params_layout.addWidget(self.topology_row)

        # K-Shortest Paths
        self.k_paths_widget = ParameterWidget(
            label_text="Rotas Candidatas (K-SP)",
            input_type="spinbox",
            default_value=3,
            min_value=1,
            max_value=20,
            suffix=" rotas",
            help_title="Algoritmo de Yen — K-Caminhos Mais Curtos (K-SP)",
            help_text=(
                "<b>Definição:</b> Número <i>K</i> de caminhos físicos mais curtos (em km) pré-computados via "
                "algoritmo de Yen para cada par de nós origem-destino (<i>s</i>, <i>d</i>).<br><br>"
                "<b>Padrão na Literatura:</b> <i>K</i> = 3 ou <i>K</i> = 5 caminhos. Valores maiores ampliam a diversidade "
                "de roteamento sob congestionamento, mas utilizam enlaces mais longos (exigindo modulações "
                "de menor ordem e mais slots espectrais)."
            )
        )
        self.k_paths_widget.valueChanged.connect(self._on_topology_changed)
        params_layout.addWidget(self.k_paths_widget)

        # Recursos Espectrais
        self.spectrum_widget = ParameterWidget(
            label_text="Slots de Espectro (FSUs)",
            input_type="spinbox",
            default_value=320,
            min_value=10,
            max_value=1000,
            step=10,
            suffix=" slots",
            help_title="Unidades de Slot de Frequência (FSUs — ITU-T G.694.1)",
            help_text=(
                "<b>Definição:</b> Quantidade total <i>S</i> de slots de frequência contíguos disponíveis em cada fibra.<br><br>"
                "<b>Norma ITU-T G.694.1:</b> Na grade flexível padrão de 12,5 GHz por slot, a Banda C "
                "óptica convencional (4,0 THz, de 191,3 a 195,3 THz) comporta exatamente "
                "<b>320 slots espectrais</b>.<br><br>"
                "<b>Restrições RMLSA:</b> Toda conexão deve obedecer à <i>continuidade</i> (mesmos slots em todos "
                "os enlaces da rota) e <i>contiguidade</i> (slots adjacentes sem lacunas)."
            )
        )
        self.spectrum_widget.valueChanged.connect(self._on_topology_changed)
        params_layout.addWidget(self.spectrum_widget)

        # Tamanho do Episódio
        self.episode_length_widget = ParameterWidget(
            label_text="Requisições por Episódio",
            input_type="spinbox",
            default_value=1000,
            min_value=10,
            max_value=100000,
            step=250,
            suffix=" req.",
            help_title="Tamanho Amostral do Episódio (Monte Carlo)",
            help_text=(
                "<b>Definição:</b> Número total de requisições de conexão óptica geradas e avaliadas por episódio.<br><br>"
                "<b>Recomendações Estatísticas:</b>"
                "<ul>"
                "<li><b>Testes exploratórios rápidos:</b> 250 a 1.000 requisições.</li>"
                "<li><b>Validação intermediária:</b> 2.500 a 5.000 requisições.</li>"
                "<li><b>Publicação científica (convergência de cauda baixa):</b> &ge; 10.000 requisições.</li>"
                "</ul>"
            )
        )
        self.episode_length_widget.valueChanged.connect(self._on_topology_changed)
        params_layout.addWidget(self.episode_length_widget)

        # Episódios por Ponto (Repetições Monte Carlo)
        self.episodes_per_point_widget = ParameterWidget(
            label_text="Episódios por Ponto",
            input_type="spinbox",
            default_value=1,
            min_value=1,
            max_value=100,
            step=1,
            suffix=" ep.",
            help_title="Número de Episódios por Ponto (Média e Desvio Padrão)",
            help_text=(
                "<b>Definição:</b> Número de episódios independentes executados para cada ponto "
                "(carga, margem e heurística).<br><br>"
                "<b>Impacto nos arquivos CSV:</b>"
                "<ul>"
                "<li><b>episodes.csv:</b> Grava uma linha individual para cada episódio executado (<code>episode_index = 0..N-1</code>).</li>"
                "<li><b>summary.csv:</b> Agrega os <i>N</i> episódios calculando a média (<code>*_mean</code>) e o desvio padrão amostral (<code>*_std</code>).</li>"
                "</ul>"
            ),
        )
        self.episodes_per_point_widget.valueChanged.connect(self._on_topology_changed)
        params_layout.addWidget(self.episodes_per_point_widget)

        # Semente Aleatória e Checkbox
        self.seed_widget = ParameterWidget(
            label_text="Semente Aleatória (Seed)",
            input_type="spinbox",
            default_value=10,
            min_value=0,
            max_value=999999,
            help_title="Semente do Gerador Pseudo-Aleatório (PRNG)",
            help_text=(
                "<b>Reprodutibilidade Científica:</b> Fixar a semente garante que diferentes heurísticas "
                "(ex: <i>First-Fit</i> vs. <i>FF QoT-Aware</i>) enfrentem exatamente a mesma sequência estocástica "
                "de chegadas (<i>s</i>, <i>d</i>, <i>B</i>, <i>t</i><sub>chegada</sub>, <i>t</i><sub>retenção</sub>), "
                "permitindo comparação pareada justa."
            )
        )
        self.seed_widget.valueChanged.connect(self._on_changed)
        params_layout.addWidget(self.seed_widget)

        self.use_seed_checkbox = QCheckBox("Fixar semente aleatória (garantir reprodutibilidade exata entre algoritmos)")
        self.use_seed_checkbox.setChecked(True)
        self.use_seed_checkbox.toggled.connect(self._on_use_seed_toggled)
        params_layout.addWidget(self.use_seed_checkbox)

        config_layout.addWidget(self.params_group)

        # Grupo 2: Indicadores Derivados do Cenário
        self.summary_group = QGroupBox("Resumo Analítico da Grade e Espaço de Busca")
        summary_layout = QVBoxLayout(self.summary_group)
        summary_layout.setContentsMargins(14, 20, 14, 12)
        self.scenario_summary_label = QLabel()
        self.scenario_summary_label.setWordWrap(True)
        summary_layout.addWidget(self.scenario_summary_label)
        config_layout.addWidget(self.summary_group)

        config_layout.addStretch(1)
        left_scroll.setWidget(self.config_container)
        left_scroll.setMinimumWidth(370)

        # ── Coluna da Direita: Ficha Técnica da Topologia ──────────────────
        self.topo_group = QGroupBox("Ficha Técnica e Caracterização da Topologia")
        self.topo_group.setMinimumWidth(260)
        topo_layout = QVBoxLayout(self.topo_group)
        topo_layout.setContentsMargins(12, 22, 12, 12)
        topo_layout.setSpacing(8)

        self.topo_details_view = QTextBrowser()
        self.topo_details_view.setFrameShape(QFrame.Shape.NoFrame)
        topo_layout.addWidget(self.topo_details_view)

        splitter.addWidget(left_scroll)
        splitter.addWidget(self.topo_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([460, 500])

        self._on_topology_changed()

    def _current_topology_id(self) -> str:
        data = self.topology_combo.currentData()
        if data:
            return str(data)
        text = self.topology_combo.currentText()
        return text.split("—")[0].strip()

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

    def _on_use_seed_toggled(self, checked: bool) -> None:
        self.seed_widget.setEnabled(checked)
        self._on_changed()

    def _on_changed(self, *args) -> None:
        self.state_changed.emit()

    def _on_topology_changed(self, *args) -> None:
        """Recalcula os indicadores da grade e exibe a ficha técnica completa da topologia."""
        c = theme.COLORS
        topology_id = self._current_topology_id()
        k_paths = int(self.k_paths_widget.value())
        num_slots = int(self.spectrum_widget.value())
        ep_len = int(self.episode_length_widget.value())

        total_bw_thz = (num_slots * 12.5) / 1000.0
        candidates_per_req = k_paths * num_slots

        self.scenario_summary_label.setText(
            f"<table style='width:100%; font-size:11px;'>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Largura Espectral Total (@12.5 GHz/FSU):</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.primary_light};'>{total_bw_thz:.2f} THz ({num_slots} FSUs)</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Opções de Rota × Slot por Modulação:</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.text};'>{candidates_per_req:,} posições</td></tr>"
            f"<tr><td style='color:{c.text_secondary}; padding:2px 0;'>Amostragem de Monte Carlo:</td>"
            f"<td style='text-align:right; font-weight:700; color:{c.success};'>{ep_len:,} requisições/episódio</td></tr>"
            f"</table>"
        )

        try:
            topo_path = resolve_topology(topology_id)
            topo = TopologyModel.from_file(topo_path, k_paths=k_paths)

            lengths = [link.length_km for link in topo.links]
            avg_len = sum(lengths) / len(lengths) if lengths else 0.0
            max_len = max(lengths) if lengths else 0.0
            min_len = min(lengths) if lengths else 0.0
            total_fiber_km = sum(lengths)
            total_spans = sum(len(link.spans) for link in topo.links)
            avg_degree = (2.0 * topo.link_count / topo.node_count) if topo.node_count > 0 else 0.0

            # Construir grade de nós em 2 colunas
            nodes_items = list(topo.node_index_by_name.items())
            node_rows_html = ""
            for i in range(0, len(nodes_items), 2):
                n1_name, n1_idx = nodes_items[i]
                if i + 1 < len(nodes_items):
                    n2_name, n2_idx = nodes_items[i + 1]
                    col2_html = (
                        f"<td style='padding:3px 6px; font-family:monospace; color:{c.primary_light}; font-weight:bold;'>#{n2_idx:02d}</td>"
                        f"<td style='padding:3px 6px;'>{n2_name}</td>"
                    )
                else:
                    col2_html = "<td></td><td></td>"
                node_rows_html += (
                    f"<tr style='border-bottom: 1px solid {c.border_light};'>"
                    f"<td style='padding:3px 6px; font-family:monospace; color:{c.primary_light}; font-weight:bold;'>#{n1_idx:02d}</td>"
                    f"<td style='padding:3px 6px;'>{n1_name}</td>"
                    f"{col2_html}</tr>"
                )

            # Construir tabela de enlaces
            link_rows_html = ""
            for link in topo.links[:30]:
                link_rows_html += (
                    f"<tr style='border-bottom: 1px solid {c.border_light};'>"
                    f"<td style='padding:3px 6px; font-family:monospace;'>e{link.id:02d}</td>"
                    f"<td style='padding:3px 6px;'><b>{link.source_name}</b> &rarr; <b>{link.target_name}</b></td>"
                    f"<td style='text-align:right; padding:3px 6px;'>{link.length_km:.1f} km</td>"
                    f"<td style='text-align:right; padding:3px 6px; color:{c.primary_light}; font-weight:bold;'>{len(link.spans)}</td>"
                    f"</tr>"
                )
            if len(topo.links) > 30:
                link_rows_html += (
                    f"<tr><td colspan='4' style='text-align:center; padding:6px; color:{c.text_secondary}; font-style:italic;'>"
                    f"+ {len(topo.links) - 30} enlaces adicionais omitidos para compacidade.</td></tr>"
                )

            html = f"""
            <div style="font-family: {theme.FONT_FAMILY}; color: {c.text};">
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 14px; font-weight: 700; color: {c.primary_light};">
                        Topologia: {topology_id.upper()}
                    </span>
                </div>

                <h4 style="color: {c.accent}; margin: 8px 0 4px 0; font-size: 11px; text-transform: uppercase;">
                    1. Invariantes de Grafo &amp; Roteamento
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 10px;">
                    <tr style="border-bottom: 1px solid {c.border_light};">
                        <td style="color:{c.text_secondary}; padding: 4px 0;">Nós de Comutação ROADM (|V|):</td>
                        <td style="text-align: right; font-weight: 700; color:{c.success};">{topo.node_count} nós</td>
                    </tr>
                    <tr style="border-bottom: 1px solid {c.border_light};">
                        <td style="color:{c.text_secondary}; padding: 4px 0;">Enlaces de Fibra Óptica (|E|):</td>
                        <td style="text-align: right; font-weight: 700; color:{c.success};">{topo.link_count} enlaces</td>
                    </tr>
                    <tr style="border-bottom: 1px solid {c.border_light};">
                        <td style="color:{c.text_secondary}; padding: 4px 0;">Grau Nodal Médio (&lt;d&gt; = 2|E|/|V|):</td>
                        <td style="text-align: right; font-weight: 700;">{avg_degree:.2f} enlaces/nó</td>
                    </tr>
                    <tr style="border-bottom: 1px solid {c.border_light};">
                        <td style="color:{c.text_secondary}; padding: 4px 0;">Caminhos Pré-Computados ({k_paths}-SP Total):</td>
                        <td style="text-align: right; font-weight: 700; color:{c.primary_light};">{topo.path_count} rotas</td>
                    </tr>
                </table>

                <h4 style="color: {c.accent}; margin: 10px 0 4px 0; font-size: 11px; text-transform: uppercase;">
                    2. Estatísticas Físicas dos Enlaces
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 10px;">
                    <tr style="border-bottom: 1px solid {c.border_light};">
                        <td style="color:{c.text_secondary}; padding: 4px 0;">Extensão Total de Fibra na Malha:</td>
                        <td style="text-align: right; font-weight: 700;">{total_fiber_km:,.1f} km</td>
                    </tr>
                    <tr style="border-bottom: 1px solid {c.border_light};">
                        <td style="color:{c.text_secondary}; padding: 4px 0;">Comprimento Médio / Mín / Máx:</td>
                        <td style="text-align: right; font-weight: 700;">{avg_len:.1f} / {min_len:.1f} / {max_len:.1f} km</td>
                    </tr>
                    <tr style="border-bottom: 1px solid {c.border_light};">
                        <td style="color:{c.text_secondary}; padding: 4px 0;">Total de Estágios de Amplificação (Spans EDFA):</td>
                        <td style="text-align: right; font-weight: 700;">{total_spans} spans</td>
                    </tr>
                </table>

                <h4 style="color: {c.accent}; margin: 10px 0 4px 0; font-size: 11px; text-transform: uppercase;">
                    3. Mapeamento de Nós da Rede (ID &rarr; Cidade)
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 10.5px; margin-bottom: 10px;">
                    <thead>
                        <tr style="background-color: {c.surface_light}; border-bottom: 1px solid {c.border};">
                            <th style="text-align:left; padding:4px 6px;">ID</th>
                            <th style="text-align:left; padding:4px 6px;">Nó (ROADM)</th>
                            <th style="text-align:left; padding:4px 6px;">ID</th>
                            <th style="text-align:left; padding:4px 6px;">Nó (ROADM)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {node_rows_html}
                    </tbody>
                </table>

                <h4 style="color: {c.accent}; margin: 10px 0 4px 0; font-size: 11px; text-transform: uppercase;">
                    4. Catálogo de Enlaces Físicos (Fibras)
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 10.5px;">
                    <thead>
                        <tr style="background-color: {c.surface_light}; border-bottom: 1px solid {c.border};">
                            <th style="text-align:left; padding:4px 6px;">ID</th>
                            <th style="text-align:left; padding:4px 6px;">Par de Nós (Origem &rarr; Destino)</th>
                            <th style="text-align:right; padding:4px 6px;">Distância</th>
                            <th style="text-align:right; padding:4px 6px;">Spans</th>
                        </tr>
                    </thead>
                    <tbody>
                        {link_rows_html}
                    </tbody>
                </table>
            </div>
            """
            self.topo_details_view.setHtml(html)
        except Exception as e:
            self.topo_details_view.setHtml(
                f"<div style='color: {c.error}; font-weight: bold;'>"
                f"Erro ao carregar dados da topologia '{topology_id}':<br>{str(e)}</div>"
            )

        self._on_changed()

    def load_state(self, state: GUIState) -> None:
        """Preenche os componentes do painel com os dados obtidos do estado."""
        self.scenario_id_widget.setValue(state.scenario_id)

        idx = self.topology_combo.findData(state.topology_id)
        if idx < 0:
            idx = self.topology_combo.findText(state.topology_id, Qt.MatchFlag.MatchContains)
        if idx >= 0:
            self.topology_combo.setCurrentIndex(idx)

        self.k_paths_widget.setValue(state.k_paths)
        self.spectrum_widget.setValue(state.num_spectrum_resources)
        self.episode_length_widget.setValue(state.episode_length)
        self.episodes_per_point_widget.setValue(getattr(state, "episodes_per_point", 1))

        self.use_seed_checkbox.setChecked(state.use_seed)
        self.seed_widget.setEnabled(state.use_seed)
        if state.seed is not None:
            self.seed_widget.setValue(state.seed)

        self._on_topology_changed()

    def update_state(self, state: GUIState) -> None:
        """Atualiza o estado global com os dados inseridos nos inputs deste painel."""
        state.scenario_id = str(self.scenario_id_widget.value())
        state.topology_id = self._current_topology_id()
        state.k_paths = int(self.k_paths_widget.value())
        state.num_spectrum_resources = int(self.spectrum_widget.value())
        state.episode_length = int(self.episode_length_widget.value())
        state.episodes_per_point = int(self.episodes_per_point_widget.value())

        state.use_seed = self.use_seed_checkbox.isChecked()
        if state.use_seed:
            state.seed = int(self.seed_widget.value())
        else:
            state.seed = None
