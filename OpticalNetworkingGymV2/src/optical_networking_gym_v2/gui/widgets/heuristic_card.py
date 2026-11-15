"""Widget de cartão acadêmico para representação de heurísticas RMLSA/RMSA."""

from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QWidget
)
from optical_networking_gym_v2.gui import theme


_COMPLEXITY_PT = {
    "LOW": "BAIXA • O(K·M)",
    "MEDIUM": "MÉDIA • O(K·M·S)",
    "HIGH": "ALTA • 2-Estágios",
}


class HeuristicCard(QFrame):
    """Cartão visual para exibir e selecionar heurísticas de roteamento e alocação de espectro."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        category: str,
        description: str,
        complexity: str,
        accent: str = "primary",
        checked: bool = False,
        heuristic_id: str = "",
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.title_text = title
        self.category_text = category
        self.description_text = description
        self.complexity_text = complexity.upper()
        self.accent = accent.lower()
        self.heuristic_id = heuristic_id

        self.setObjectName("HeuristicCardFrame")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(12, 10, 12, 10)
        self.main_layout.setSpacing(12)

        # 1. Barra de destaque vertical (Accent Bar)
        self.accent_bar = QFrame()
        self.accent_bar.setFixedWidth(4)
        self.main_layout.addWidget(self.accent_bar)

        # 2. Painel central com as informações de texto
        self.text_container = QWidget()
        self.text_container.setStyleSheet("background: transparent;")
        self.text_layout = QVBoxLayout(self.text_container)
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(4)

        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.header_layout.addWidget(self.title_label)

        self.category_badge = QLabel(category.upper())
        self.header_layout.addWidget(self.category_badge)

        comp_display = _COMPLEXITY_PT.get(self.complexity_text, self.complexity_text)
        self.complexity_badge = QLabel(comp_display)
        self.header_layout.addWidget(self.complexity_badge)

        self.header_layout.addStretch()
        self.text_layout.addLayout(self.header_layout)

        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.text_layout.addWidget(self.desc_label)

        if self.heuristic_id:
            self.id_label = QLabel(f"Kernel: {self.heuristic_id}()")
            self.text_layout.addWidget(self.id_label)
        else:
            self.id_label = None

        self.main_layout.addWidget(self.text_container, 1)

        # 3. Checkbox na lateral direita
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkbox.toggled.connect(self._on_checkbox_toggled)
        self.main_layout.addWidget(self.checkbox)

        self.update_card_style()

    def _get_accent_hex(self) -> str:
        colors = theme.COLORS
        if self.accent == "success":
            return colors.success
        elif self.accent == "warning":
            return colors.warning
        elif self.accent == "accent":
            return colors.accent
        elif self.accent == "info":
            return colors.info
        elif self.accent == "primary":
            return colors.primary_light
        return self.accent

    def update_card_style(self) -> None:
        """Atualiza o estilo dinamicamente com base no tema atual e seleção."""
        colors = theme.COLORS
        accent_color = self._get_accent_hex()
        is_checked = self.checkbox.isChecked()

        self.accent_bar.setStyleSheet(
            f"background-color: {accent_color}; border-radius: 2px;"
        )
        self.title_label.setStyleSheet(
            f"font-family: {theme.FONT_FAMILY}; font-size: 13px; font-weight: 700; color: {colors.text};"
        )
        self.category_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {colors.surface_light};
                color: {accent_color};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 700;
            }}
        """)
        self.complexity_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {colors.surface_light};
                color: {colors.text_secondary};
                border: 1px solid {colors.border_light};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 600;
            }}
        """)
        self.desc_label.setStyleSheet(
            f"font-size: 11px; color: {colors.text_secondary};"
        )
        if self.id_label is not None:
            self.id_label.setStyleSheet(
                f"font-family: {theme.FONT_MONO}; font-size: 10px; color: {colors.text_disabled};"
            )

        if is_checked:
            self.setStyleSheet(f"""
                QFrame#HeuristicCardFrame {{
                    background-color: {colors.surface};
                    border: 2px solid {colors.primary};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#HeuristicCardFrame {{
                    background-color: {colors.surface};
                    border: 1px solid {colors.border};
                    border-radius: 8px;
                }}
                QFrame#HeuristicCardFrame:hover {{
                    background-color: {colors.surface_hover};
                    border-color: {accent_color};
                }}
            """)

    def _on_checkbox_toggled(self, checked: bool) -> None:
        self.update_card_style()
        self.toggled.emit(checked)

    def mousePressEvent(self, event) -> None:
        self.checkbox.setChecked(not self.checkbox.isChecked())
        super().mousePressEvent(event)

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.checkbox.setChecked(checked)
        self.update_card_style()
