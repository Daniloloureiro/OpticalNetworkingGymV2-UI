"""Widget de grupo colapsável com animação para a interface gráfica."""

from __future__ import annotations
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLayout
)
from optical_networking_gym_v2.gui.theme import COLORS, FONT_FAMILY


class CollapsibleGroup(QWidget):
    """Widget de contêiner colapsável com animações de transição suaves.
    
    Permite agrupar outros widgets e ocultá-los/exibi-los dinamicamente,
    economizando espaço na tela e organizando a interface de simulação.
    """

    def __init__(
        self,
        title: str,
        expanded: bool = True,
        animation_duration: int = 300,
        parent: QWidget | None = None
    ) -> None:
        """Inicializa o grupo colapsável.

        Parameters
        ----------
        title : str
            Título exibido na barra superior (header).
        expanded : bool, optional
            Se True, o widget inicia expandido; caso contrário, colapsado.
        animation_duration : int, optional
            Duração da animação de colapso/expansão em milissegundos.
        parent : QWidget, optional
            Widget pai.
        """
        super().__init__(parent)
        self.title_text = title
        self.expanded = expanded
        self.animation_duration = animation_duration

        # Layout principal vertical
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.main_layout.setSpacing(0)

        # Botão de Toggle (Header)
        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("CollapsibleHeader")
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.setStyleSheet(f"""
            QPushButton#CollapsibleHeader {{
                background-color: {COLORS.surface_light};
                color: {COLORS.text};
                border: 1px solid {COLORS.border};
                border-radius: 6px;
                padding: 10px 14px;
                font-family: {FONT_FAMILY};
                font-weight: bold;
                font-size: 12px;
                text-align: left;
            }}
            QPushButton#CollapsibleHeader:hover {{
                background-color: {COLORS.surface_hover};
                border-color: {COLORS.accent};
            }}
        """)
        self.toggle_button.clicked.connect(self.toggle_collapse)
        self.main_layout.addWidget(self.toggle_button)

        # Área de conteúdo (onde os widgets filhos residem)
        self.content_area = QWidget()
        self.content_area.setObjectName("CollapsibleContent")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(8)
        
        # Estilo exclusivo da área de conteúdo (evitando aplicar aos filhos via ID)
        self.content_area.setStyleSheet(f"""
            QWidget#CollapsibleContent {{
                background-color: {COLORS.surface};
                border-left: 1px solid {COLORS.border};
                border-right: 1px solid {COLORS.border};
                border-bottom: 1px solid {COLORS.border};
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
        """)
        self.main_layout.addWidget(self.content_area)

        # Animação da altura máxima (maximumHeight) para o efeito de recolhimento
        self.toggle_animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.toggle_animation.setDuration(self.animation_duration)
        self.toggle_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.update_arrow()

        # Configurar estado inicial
        if not self.expanded:
            self.content_area.setMaximumHeight(0)
            self.content_area.hide()
        else:
            self.content_area.show()

    def update_arrow(self) -> None:
        """Atualiza o ícone de seta do cabeçalho de acordo com o estado do colapso."""
        arrow = "▼" if self.expanded else "▶"
        self.toggle_button.setText(f"{arrow}   {self.title_text}")

    def toggle_collapse(self) -> None:
        """Alterna entre expandido e colapsado usando animações suaves."""
        self.expanded = not self.expanded
        self.update_arrow()

        # Obter a altura atual do widget de conteúdo
        current_height = self.content_area.height()

        if self.expanded:
            # Mostrar a área antes de animar
            self.content_area.show()
            # Forçar recálculo de layout para obter o tamanho correto do container
            self.content_area.layout().activate()
            target_height = self.content_area.layout().sizeHint().height()

            # Configurar animação
            self.toggle_animation.setStartValue(current_height)
            self.toggle_animation.setEndValue(target_height)

            def on_expand_finished() -> None:
                if self.expanded:
                    # Permite que o container mude de tamanho livremente após a expansão
                    self.content_area.setMaximumHeight(16777215)

            try:
                self.toggle_animation.finished.disconnect()
            except RuntimeError:
                pass
            self.toggle_animation.finished.connect(on_expand_finished)
            self.toggle_animation.start()
        else:
            # Configurar animação para reduzir a altura a zero
            self.toggle_animation.setStartValue(current_height)
            self.toggle_animation.setEndValue(0)

            def on_collapse_finished() -> None:
                if not self.expanded:
                    self.content_area.hide()

            try:
                self.toggle_animation.finished.disconnect()
            except RuntimeError:
                pass
            self.toggle_animation.finished.connect(on_collapse_finished)
            self.toggle_animation.start()

    def addWidget(self, widget: QWidget) -> None:
        """Adiciona um widget à área de conteúdo colapsável.

        Parameters
        ----------
        widget : QWidget
            O widget filho a ser adicionado.
        """
        self.content_layout.addWidget(widget)
        if self.expanded:
            self.content_area.setMaximumHeight(16777215)

    def addLayout(self, layout: QLayout) -> None:
        """Adiciona um layout filho à área de conteúdo colapsável.

        Parameters
        ----------
        layout : QLayout
            O layout a ser adicionado.
        """
        self.content_layout.addLayout(layout)
        if self.expanded:
            self.content_area.setMaximumHeight(16777215)
