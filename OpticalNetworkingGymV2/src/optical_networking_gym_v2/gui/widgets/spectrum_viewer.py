"""
Widget de visualização de slots espectrais.

Renderiza uma grade de quadrados coloridos representando a alocação de slots
frequência-espectral em cada enlace da rede óptica. Permite selecionar o enlace
a visualizar e mostra tooltips informativos para cada slot.
"""

from __future__ import annotations

import numpy as np

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSizePolicy, QToolTip,
)


class SpectrumGrid(QWidget):
    """Widget que desenha a grade de slots espectrais usando QPainter.

    Cada slot é um pequeno quadrado colorido:
    - Slots livres (-1): cor neutra clara (adapta ao tema)
    - Slots ocupados: coloridos por service_id usando um colormap distinto

    A grade quebra em linhas (ex.: 32 slots por linha para 320 slots = 10 linhas).
    """

    SLOT_SIZE = 14  # px por quadrado de slot
    SLOT_GAP = 1    # px de espaço entre quadrados
    SLOTS_PER_ROW = 32  # quebra de linha após essa quantidade de slots

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_data = None  # np.ndarray shape (num_slots,) com valores int32
        self._num_slots = 320
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Cores distintas para slots ocupados (por hash de service_id)
        self._service_colors = {}  # cache: service_id -> QColor

        # Paleta de cores para serviços (20 cores distintas)
        self._palette = [
            '#e94560', '#0f3460', '#00b894', '#fdcb6e', '#74b9ff',
            '#a29bfe', '#fd79a8', '#55efc4', '#fab1a0', '#81ecec',
            '#dfe6e9', '#636e72', '#ff7675', '#6c5ce7', '#00cec9',
            '#e17055', '#d63031', '#2d3436', '#b2bec3', '#ffeaa7',
        ]

    def set_slot_data(self, data: np.ndarray | None, num_slots: int = 320):
        """Define os dados de alocação de slots para um link.

        Parameters
        ----------
        data : np.ndarray | None
            Array 1D com shape (num_slots,). Valor -1 = livre, >= 0 = service_id.
        num_slots : int
            Número total de slots espectrais.
        """
        self._slot_data = data
        self._num_slots = num_slots
        self._service_colors.clear()
        self.update()  # dispara repintura

    def _get_service_color(self, service_id: int) -> QColor:
        """Retorna a cor associada a um service_id, usando cache."""
        if service_id not in self._service_colors:
            color_hex = self._palette[service_id % len(self._palette)]
            self._service_colors[service_id] = QColor(color_hex)
        return self._service_colors[service_id]

    def sizeHint(self) -> QSize:
        """Retorna o tamanho ideal baseado no número de slots."""
        rows = (self._num_slots + self.SLOTS_PER_ROW - 1) // self.SLOTS_PER_ROW
        w = self.SLOTS_PER_ROW * (self.SLOT_SIZE + self.SLOT_GAP) + self.SLOT_GAP
        h = rows * (self.SLOT_SIZE + self.SLOT_GAP) + self.SLOT_GAP + 30  # 30px para cabeçalho
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        """Retorna o tamanho mínimo do widget."""
        return QSize(200, 100)

    def paintEvent(self, event):
        """Desenha a grade de slots espectrais."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Importa cores do tema dinamicamente para suportar troca de tema
        from optical_networking_gym_v2.gui.theme import COLORS

        # Fundo
        painter.fillRect(self.rect(), QColor(COLORS.surface))

        if self._slot_data is None:
            # Desenha texto placeholder
            painter.setPen(QColor(COLORS.text_secondary))
            painter.setFont(QFont('Inter', 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           'Nenhum dado de espectro disponível.\nExecute uma simulação primeiro.')
            painter.end()
            return

        # Cor de slot livre
        free_color = QColor(COLORS.border_light)
        border_color = QColor(COLORS.border)

        # Estatísticas
        total = len(self._slot_data)
        free_count = int(np.sum(self._slot_data == -1))
        used_count = total - free_count
        occupancy = used_count / total * 100 if total > 0 else 0

        # Desenha cabeçalho com estatísticas
        painter.setPen(QColor(COLORS.text))
        painter.setFont(QFont('Inter', 9, QFont.Weight.Bold))
        header_text = f'Slots: {total} | Livres: {free_count} | Ocupados: {used_count} ({occupancy:.1f}%)'
        painter.drawText(5, 15, header_text)

        y_offset = 25
        pen = QPen(border_color, 1)
        painter.setPen(pen)

        for i in range(total):
            row = i // self.SLOTS_PER_ROW
            col = i % self.SLOTS_PER_ROW
            x = self.SLOT_GAP + col * (self.SLOT_SIZE + self.SLOT_GAP)
            y = y_offset + self.SLOT_GAP + row * (self.SLOT_SIZE + self.SLOT_GAP)

            val = int(self._slot_data[i])
            if val == -1:
                color = free_color
            else:
                color = self._get_service_color(val)

            painter.setBrush(QBrush(color))
            painter.drawRect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

        painter.end()

    def mouseMoveEvent(self, event):
        """Mostra tooltip com informações do slot ao passar o mouse."""
        if self._slot_data is None:
            return

        pos = event.position() if hasattr(event, 'position') else event.pos()
        x, y = pos.x(), pos.y()
        y_offset = 25

        col = int((x - self.SLOT_GAP) / (self.SLOT_SIZE + self.SLOT_GAP))
        row = int((y - y_offset - self.SLOT_GAP) / (self.SLOT_SIZE + self.SLOT_GAP))

        slot_idx = row * self.SLOTS_PER_ROW + col

        if 0 <= slot_idx < len(self._slot_data) and 0 <= col < self.SLOTS_PER_ROW:
            val = int(self._slot_data[slot_idx])
            if val == -1:
                tip = f'Slot {slot_idx}: Livre'
            else:
                tip = f'Slot {slot_idx}: Ocupado (Serviço #{val})'
            QToolTip.showText(
                event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos(),
                tip, self,
            )


class SpectrumViewer(QWidget):
    """Widget completo de visualização de espectro com seleção de enlace.

    Contém:
    - Um QComboBox para selecionar qual link visualizar
    - O widget SpectrumGrid mostrando a alocação de slots
    - Uma legenda mostrando o significado das cores
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_data = None  # np.ndarray shape (num_links, num_slots)
        self._link_names = []  # lista de nomes dos links
        self._num_slots = 320

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Barra de controle
        control_bar = QHBoxLayout()

        link_label = QLabel('Enlace:')
        link_label.setStyleSheet('font-weight: bold; font-size: 11px;')
        control_bar.addWidget(link_label)

        self.link_combo = QComboBox()
        self.link_combo.currentIndexChanged.connect(self._on_link_changed)
        control_bar.addWidget(self.link_combo, 1)

        # Legenda
        self._legend_free = QLabel('Livre')
        self._legend_free.setStyleSheet('font-size: 10px; margin-left: 16px;')
        control_bar.addWidget(self._legend_free)

        self._legend_used = QLabel('Ocupado')
        self._legend_used.setStyleSheet('font-size: 10px;')
        control_bar.addWidget(self._legend_used)

        layout.addLayout(control_bar)

        # Grade de espectro
        self.grid = SpectrumGrid(self)
        layout.addWidget(self.grid, 1)

    def set_data(self, slot_allocation: np.ndarray | list | None, link_names: list[str] | None = None):
        """Define os dados completos de alocação de slots.

        Parameters
        ----------
        slot_allocation : np.ndarray | list | None
            Matriz 2D (num_links, num_slots) ou None.
            Valor -1 = livre, >= 0 = service_id.
        link_names : list[str] | None
            Nomes dos links. Se None, usa 'Enlace 0', 'Enlace 1', etc.
        """
        if slot_allocation is None:
            self._full_data = None
            self.link_combo.clear()
            self.grid.set_slot_data(None)
            return

        data = np.asarray(slot_allocation, dtype=np.int32)
        if data.ndim == 1:
            data = data.reshape(1, -1)

        self._full_data = data
        self._num_slots = data.shape[1]

        num_links = data.shape[0]
        if link_names:
            self._link_names = link_names
        else:
            self._link_names = [f'Enlace {i}' for i in range(num_links)]

        self.link_combo.blockSignals(True)
        self.link_combo.clear()
        self.link_combo.addItems(self._link_names)
        self.link_combo.blockSignals(False)

        if num_links > 0:
            self.link_combo.setCurrentIndex(0)
            self.grid.set_slot_data(data[0], self._num_slots)

    def _on_link_changed(self, index: int):
        """Callback para troca de enlace selecionado no combo."""
        if self._full_data is not None and 0 <= index < self._full_data.shape[0]:
            self.grid.set_slot_data(self._full_data[index], self._num_slots)
