"""Widget de barra de progresso com cálculo de ETA para simulações demoradas."""

from __future__ import annotations
import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from optical_networking_gym_v2.gui.theme import COLORS, FONT_FAMILY


class ProgressWidget(QWidget):
    """Widget de progresso com indicador visual e estimativa de tempo restante (ETA).
    
    Exibe a porcentagem concluída, quantidade de passos executados/totais,
    tempo decorrido e o tempo restante estimado para a conclusão da simulação.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Inicializa o widget de progresso."""
        super().__init__(parent)
        self.start_time: float | None = None
        self.last_current: int = 0

        # Layout principal vertical
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.main_layout.setSpacing(8)

        # 1. Layout de rótulos superiores (Status e Progresso textual)
        self.top_layout = QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("Aguardando simulação...")
        self.status_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            color: {COLORS.text_secondary};
        """)
        self.top_layout.addWidget(self.status_label)
        
        self.progress_text_label = QLabel("0 / 0 (0.0%)")
        self.progress_text_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.progress_text_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 11px;
            font-weight: bold;
            color: {COLORS.text};
        """)
        self.top_layout.addWidget(self.progress_text_label)
        
        self.main_layout.addLayout(self.top_layout)

        # 2. Barra de progresso (QProgressBar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)  # Usamos o label de cima para a porcentagem
        self.main_layout.addWidget(self.progress_bar)

        # 3. Layout de rótulos inferiores (Tempo Decorrido e ETA)
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.elapsed_label = QLabel("Tempo decorrido: --:--")
        self.elapsed_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 10px;
            color: {COLORS.text_disabled};
        """)
        self.bottom_layout.addWidget(self.elapsed_label)

        self.eta_label = QLabel("Tempo restante (ETA): --:--")
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.eta_label.setStyleSheet(f"""
            font-family: {FONT_FAMILY};
            font-size: 10px;
            font-weight: 600;
            color: {COLORS.warning};
        """)
        self.bottom_layout.addWidget(self.eta_label)

        self.main_layout.addLayout(self.bottom_layout)

    def _format_time(self, seconds: float) -> str:
        """Formata uma quantidade de segundos em uma string hh:mm:ss ou mm:ss."""
        if seconds < 0:
            return "--:--"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def reset(self) -> None:
        """Reseta o estado do progresso e cronômetros."""
        self.start_time = None
        self.last_current = 0
        self.progress_bar.setValue(0)
        self.progress_text_label.setText("0 / 0 (0.0%)")
        self.status_label.setText("Aguardando simulação...")
        self.elapsed_label.setText("Tempo decorrido: --:--")
        self.eta_label.setText("Tempo restante (ETA): --:--")
        self.eta_label.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 10px; font-weight: 600; color: {COLORS.warning};")

    def update_progress(self, current: int, total: int, status_text: str | None = None) -> None:
        """Atualiza a barra de progresso e recalcula o tempo restante estimado (ETA).

        Parameters
        ----------
        current : int
            O número de passos concluídos até o momento.
        total : int
            O total de passos da simulação.
        status_text : str, optional
            Um texto descritivo do status atual (ex: 'Executando...', 'Finalizando...').
        """
        # Tratar divisões por zero ou limites inválidos
        if total <= 0:
            self.reset()
            return

        # Prevenir valores de progresso fora dos limites
        current = max(0, min(current, total))

        # Detectar se a tarefa reiniciou ou voltou passos atrás
        if self.start_time is None or current < self.last_current:
            self.start_time = time.time()
        
        self.last_current = current
        now = time.time()
        elapsed = now - self.start_time

        # Calcular porcentagem
        percentage = (current / total) * 100.0
        self.progress_bar.setValue(int(percentage))

        # Atualizar textos
        self.progress_text_label.setText(f"{current} / {total} ({percentage:.1f}%)")
        if status_text:
            self.status_label.setText(status_text)
        elif current == total:
            self.status_label.setText("Simulação concluída!")
        else:
            self.status_label.setText("Executando simulação...")

        # Atualizar tempo decorrido
        self.elapsed_label.setText(f"Tempo decorrido: {self._format_time(elapsed)}")

        # Calcular ETA (Tempo Restante Estimado)
        if current == total:
            self.eta_label.setText("Tempo restante: Finalizado")
            self.eta_label.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 10px; font-weight: 600; color: {COLORS.success};")
        elif current > 0:
            # Velocidade média de processamento por passo
            seconds_per_step = elapsed / current
            steps_remaining = total - current
            eta_seconds = seconds_per_step * steps_remaining
            self.eta_label.setText(f"Tempo restante (ETA): {self._format_time(eta_seconds)}")
            self.eta_label.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 10px; font-weight: 600; color: {COLORS.warning};")
        else:
            self.eta_label.setText("Tempo restante (ETA): Calculando...")
            self.eta_label.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 10px; font-weight: 600; color: {COLORS.warning};")
