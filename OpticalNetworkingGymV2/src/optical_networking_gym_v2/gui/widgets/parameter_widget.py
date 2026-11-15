"""Widget de parâmetro padronizado com unidade física e ajuda teórica integrada."""

from __future__ import annotations
from typing import Union, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QSlider, QPushButton, QDialog, QVBoxLayout, QTextBrowser, QSizePolicy
)
from optical_networking_gym_v2.gui import theme


class ParameterHelpDialog(QDialog):
    """Diálogo de ajuda acadêmica e teórica para os parâmetros da simulação.

    Exibe explicações detalhadas sobre o parâmetro, seu papel matemático/físico,
    valores típicos de literatura (IEEE/JOCN/ITU-T) e impacto no desempenho.
    """

    def __init__(self, title: str, help_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Referência Acadêmica — {title}")
        self.setMinimumSize(500, 360)
        self.resize(540, 420)

        colors = theme.COLORS
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors.surface};
                border: 1px solid {colors.border};
                border-radius: 8px;
            }}
            QLabel {{
                color: {colors.text};
                font-family: {theme.FONT_FAMILY};
            }}
            QTextBrowser {{
                background-color: {colors.input_bg};
                color: {colors.text};
                border: 1px solid {colors.border};
                border-radius: 6px;
                padding: 12px;
                font-family: {theme.FONT_FAMILY};
                font-size: 12px;
                line-height: 1.5;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {colors.primary_light};"
        )
        header_row.addWidget(self.title_label)
        header_row.addStretch()
        layout.addLayout(header_row)

        self.text_browser = QTextBrowser()
        self.text_browser.setHtml(
            f"<div style='line-height: 1.55; color: {colors.text};'>{help_text}</div>"
        )
        self.text_browser.setOpenExternalLinks(True)
        layout.addWidget(self.text_browser, 1)

        self.close_button = QPushButton("Fechar")
        self.close_button.setProperty("class", "primary")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)


class ParameterWidget(QWidget):
    """Widget reutilizável contendo rótulo padronizado, campo de entrada com unidade e botão [?]."""

    valueChanged = Signal(object)

    def __init__(
        self,
        label_text: str,
        input_type: str = "spinbox",
        default_value: Union[int, float, str] = 0,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        step: Optional[Union[int, float]] = None,
        suffix: str = "",
        decimals: int = 2,
        help_title: str = "",
        help_text: str = "",
        show_help: bool = True,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.help_title = help_title or label_text
        self.help_text = help_text or "Nenhuma explicação acadêmica disponível para este parâmetro."
        self.input_type = input_type.lower()

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 3, 0, 3)
        self.main_layout.setSpacing(10)

        # Rótulo (Label) com largura protegida e quebra de linha suave
        self.label = QLabel(label_text)
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(145)
        self.label.setMaximumWidth(195)
        self.label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.label.setStyleSheet(
            f"font-family: {theme.FONT_FAMILY}; font-size: 11px; font-weight: 600;"
        )
        self.main_layout.addWidget(self.label)

        self.input_widget: QWidget

        if self.input_type == "lineedit":
            line = QLineEdit()
            line.setText(str(default_value))
            line.setMinimumWidth(120)
            line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            line.textChanged.connect(self.valueChanged.emit)
            self.input_widget = line
            self.main_layout.addWidget(self.input_widget, 1)

        elif self.input_type == "spinbox":
            spin = QSpinBox()
            spin.setMinimum(int(min_value) if min_value is not None else -999999)
            spin.setMaximum(int(max_value) if max_value is not None else 999999)
            if step is not None:
                spin.setSingleStep(int(step))
            if suffix:
                spin.setSuffix(suffix)
            spin.setValue(int(default_value))
            spin.setMinimumWidth(120)
            spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            spin.valueChanged.connect(self.valueChanged.emit)
            self.input_widget = spin
            self.main_layout.addWidget(self.input_widget, 1)

        elif self.input_type == "doublespinbox":
            dspin = QDoubleSpinBox()
            dspin.setDecimals(decimals)
            dspin.setMinimum(float(min_value) if min_value is not None else -999999.0)
            dspin.setMaximum(float(max_value) if max_value is not None else 999999.0)
            if step is not None:
                dspin.setSingleStep(float(step))
            if suffix:
                dspin.setSuffix(suffix)
            dspin.setValue(float(default_value))
            dspin.setMinimumWidth(120)
            dspin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            dspin.valueChanged.connect(self.valueChanged.emit)
            self.input_widget = dspin
            self.main_layout.addWidget(self.input_widget, 1)

        elif self.input_type == "slider":
            slider_container = QWidget()
            slider_layout = QHBoxLayout(slider_container)
            slider_layout.setContentsMargins(0, 0, 0, 0)
            slider_layout.setSpacing(8)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(int(min_value) if min_value is not None else 0)
            slider.setMaximum(int(max_value) if max_value is not None else 100)
            if step is not None:
                slider.setSingleStep(int(step))
            slider.setValue(int(default_value))

            self.value_label = QLabel(f"{default_value}{suffix}")
            self.value_label.setMinimumWidth(46)
            self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.value_label.setStyleSheet("font-weight: 700;")

            def on_slider_changed(val: int) -> None:
                self.value_label.setText(f"{val}{suffix}")
                self.valueChanged.emit(val)

            slider.valueChanged.connect(on_slider_changed)

            slider_layout.addWidget(slider, 1)
            slider_layout.addWidget(self.value_label)

            self.input_widget = slider
            self._slider_container = slider_container
            self.main_layout.addWidget(slider_container, 1)

        else:
            raise ValueError(f"Tipo de entrada inválido: {self.input_type}")

        # Botão de ajuda contextual [?]
        self.help_button = QPushButton("?")
        self.help_button.setToolTip(f"Clique para ver a fundamentação teórica de '{self.help_title}'")
        self.help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_button.setFixedSize(24, 24)
        self.help_button.setStyleSheet(f"""
            QPushButton {{
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                border-radius: 12px;
                padding: 0px;
                background-color: {theme.COLORS.surface_light};
                color: {theme.COLORS.primary_light};
                border: 1px solid {theme.COLORS.border};
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {theme.COLORS.primary};
                color: #ffffff;
                border-color: {theme.COLORS.primary};
            }}
        """)
        self.help_button.clicked.connect(self.show_help)
        self.help_button.setVisible(show_help)
        self.main_layout.addWidget(self.help_button)

    def show_help(self) -> None:
        """Abre o diálogo explicativo sobre o parâmetro."""
        dialog = ParameterHelpDialog(self.help_title, self.help_text, self)
        dialog.exec()

    def value(self) -> Union[int, float, str]:
        """Retorna o valor atual do parâmetro."""
        if self.input_type == "lineedit":
            return self.input_widget.text()
        elif self.input_type in ["spinbox", "doublespinbox", "slider"]:
            return self.input_widget.value()
        return ""

    def setValue(self, val: Union[int, float, str]) -> None:
        """Define o valor da entrada de dados."""
        if self.input_type == "lineedit":
            self.input_widget.setText(str(val))
        elif self.input_type == "spinbox":
            self.input_widget.setValue(int(val))
        elif self.input_type == "doublespinbox":
            self.input_widget.setValue(float(val))
        elif self.input_type == "slider":
            self.input_widget.setValue(int(val))
