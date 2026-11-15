"""
Tema profissional e acadêmico para a GUI do Optical Networking Gym v2.

Paleta de cores de alto contraste (claro e escuro), ícones vetoriais SVG nativos
para listas/seletores/spinboxes (eliminando artefatos de seta do Qt QSS), e
componentes padronizados de cabeçalho acadêmico/pedagógico.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtGui import QPalette, QColor


# ── Paleta de cores ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class DarkColors:
    """Cores do tema escuro profissional."""

    background: str = "#0f172a"
    surface: str = "#1e293b"
    surface_light: str = "#334155"
    surface_hover: str = "#3b4c66"
    primary: str = "#2563eb"
    primary_light: str = "#3b82f6"
    primary_dark: str = "#1d4ed8"
    accent: str = "#e11d48"
    accent_light: str = "#f43f5e"
    accent_dark: str = "#be123c"
    success: str = "#10b981"
    success_light: str = "#34d399"
    warning: str = "#f59e0b"
    warning_dark: str = "#d97706"
    error: str = "#ef4444"
    info: str = "#38bdf8"
    text: str = "#f8fafc"
    text_secondary: str = "#cbd5e1"
    text_disabled: str = "#64748b"
    border: str = "#334155"
    border_light: str = "#475569"
    input_bg: str = "#090f1d"
    scrollbar: str = "#475569"
    scrollbar_hover: str = "#64748b"
    shadow: str = "rgba(0, 0, 0, 0.35)"
    overlay: str = "rgba(15, 23, 42, 0.92)"


@dataclass(frozen=True, slots=True)
class LightColors:
    """Cores do tema claro acadêmico de alto contraste."""

    background: str = "#f1f5f9"
    surface: str = "#ffffff"
    surface_light: str = "#f8fafc"
    surface_hover: str = "#e2e8f0"
    primary: str = "#1e40af"
    primary_light: str = "#2563eb"
    primary_dark: str = "#1e3a8a"
    accent: str = "#be123c"
    accent_light: str = "#e11d48"
    accent_dark: str = "#9f1239"
    success: str = "#15803d"
    success_light: str = "#16a34a"
    warning: str = "#b45309"
    warning_dark: str = "#92400e"
    error: str = "#dc2626"
    info: str = "#0369a1"
    text: str = "#0f172a"
    text_secondary: str = "#475569"
    text_disabled: str = "#94a3b8"
    border: str = "#cbd5e1"
    border_light: str = "#e2e8f0"
    input_bg: str = "#ffffff"
    scrollbar: str = "#cbd5e1"
    scrollbar_hover: str = "#94a3b8"
    shadow: str = "rgba(15, 23, 42, 0.08)"
    overlay: str = "rgba(255, 255, 255, 0.95)"


# ── Estado global do tema ────────────────────────────────────────

CURRENT_THEME: str = "light"
COLORS: DarkColors | LightColors = LightColors()

# ── Fontes ───────────────────────────────────────────────────────

FONT_FAMILY = "'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace"
FONT_SIZE_XS = 10
FONT_SIZE_SM = 11
FONT_SIZE_MD = 12
FONT_SIZE_LG = 13
FONT_SIZE_XL = 16
FONT_SIZE_XXL = 20
FONT_SIZE_TITLE = 24

# ── Dimensões ────────────────────────────────────────────────────

BORDER_RADIUS = 8
BORDER_RADIUS_SM = 5
BORDER_RADIUS_LG = 12
PADDING_XS = 4
PADDING_SM = 6
PADDING_MD = 10
PADDING_LG = 14
PADDING_XL = 20
SIDEBAR_WIDTH = 215
ICON_SIZE = 20


def _ensure_theme_icons(theme_name: str, colors: DarkColors | LightColors) -> dict[str, str]:
    """Gera ícones SVG vetoriais para setas de listas (ComboBox), SpinBoxes e seletores.

    Isso substitui o truque de bordas CSS transparentes que o motor QSS do Qt
    renderizava incorretamente como blocos retangulares sólidos.
    """
    icon_dir = Path.home() / ".optical_networking_gym" / "ui_icons" / theme_name
    icon_dir.mkdir(parents=True, exist_ok=True)

    svgs = {
        "chevron_down": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
            f'fill="none" stroke="{colors.text}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
            f'<polyline points="6 9 12 15 18 9"/></svg>'
        ),
        "chevron_down_disabled": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
            f'fill="none" stroke="{colors.text_disabled}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
            f'<polyline points="6 9 12 15 18 9"/></svg>'
        ),
        "chevron_up": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
            f'fill="none" stroke="{colors.text}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
            f'<polyline points="18 15 12 9 6 15"/></svg>'
        ),
        "chevron_up_disabled": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
            f'fill="none" stroke="{colors.text_disabled}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
            f'<polyline points="18 15 12 9 6 15"/></svg>'
        ),
        "chevron_down_white": (
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" '
            'fill="none" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="6 9 12 15 18 9"/></svg>'
        ),
        "chevron_up_white": (
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" '
            'fill="none" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="18 15 12 9 6 15"/></svg>'
        ),
        "check": (
            '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
            'fill="none" stroke="#ffffff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="20 6 9 17 4 12"/></svg>'
        ),
        "radio_dot": (
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 20 20">'
            '<circle cx="10" cy="10" r="4.5" fill="#ffffff"/></svg>'
        ),
    }

    paths: dict[str, str] = {}
    for name, content in svgs.items():
        file_path = icon_dir / f"{name}.svg"
        file_path.write_text(content, encoding="utf-8")
        paths[name] = file_path.as_posix()

    return paths


def create_academic_header(
    title: str,
    subtitle: str,
    badge_text: str = "",
    parent: QWidget | None = None,
) -> QFrame:
    """Cria um cabeçalho padronizado e autoexplicativo para os painéis acadêmicos.

    Exibe o título da etapa, um selo de norma/padrão técnico (ex: ITU-T G.694.1, Modelo GN)
    e uma explicação concisa do propósito científico daquela aba.
    """
    banner = QFrame(parent)
    banner.setObjectName("AcademicBanner")
    layout = QVBoxLayout(banner)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(4)

    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    top_row.setSpacing(10)

    title_lbl = QLabel(title, banner)
    title_lbl.setObjectName("BannerTitle")
    top_row.addWidget(title_lbl)

    if badge_text:
        badge_lbl = QLabel(badge_text, banner)
        badge_lbl.setObjectName("BannerBadge")
        top_row.addWidget(badge_lbl)

    top_row.addStretch(1)
    layout.addLayout(top_row)

    sub_lbl = QLabel(subtitle, banner)
    sub_lbl.setObjectName("BannerSubtitle")
    sub_lbl.setWordWrap(True)
    layout.addWidget(sub_lbl)

    return banner


def _build_stylesheet(colors: DarkColors | LightColors, theme_name: str = "light") -> str:
    """Gera o QSS (Qt Style Sheet) completo para o tema selecionado."""
    icons = _ensure_theme_icons(theme_name, colors)

    return f"""
    /* ── Base ──────────────────────────────────────────── */

    QMainWindow, QWidget {{
        background-color: {colors.background};
        color: {colors.text};
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_MD}px;
    }}

    /* ── Academic Banner ───────────────────────────────── */

    QFrame#AcademicBanner {{
        background-color: {colors.surface};
        border: 1px solid {colors.border};
        border-left: 4px solid {colors.primary};
        border-radius: {BORDER_RADIUS}px;
    }}

    QLabel#BannerTitle {{
        font-size: {FONT_SIZE_LG}px;
        font-weight: 700;
        color: {colors.text};
        background: transparent;
    }}

    QLabel#BannerBadge {{
        background-color: {colors.surface_light};
        color: {colors.primary_light};
        border: 1px solid {colors.border};
        border-radius: 4px;
        padding: 2px 8px;
        font-size: {FONT_SIZE_XS}px;
        font-weight: 700;
    }}

    QLabel#BannerSubtitle {{
        font-size: {FONT_SIZE_SM}px;
        color: {colors.text_secondary};
        background: transparent;
    }}

    /* ── QLabel ────────────────────────────────────────── */

    QLabel {{
        color: {colors.text};
        background: transparent;
        padding: 0px;
    }}

    QLabel[class="heading"] {{
        font-size: {FONT_SIZE_XL}px;
        font-weight: 700;
        color: {colors.text};
    }}

    QLabel[class="subheading"] {{
        font-size: {FONT_SIZE_LG}px;
        font-weight: 600;
        color: {colors.text_secondary};
    }}

    QLabel[class="caption"] {{
        font-size: {FONT_SIZE_XS}px;
        color: {colors.text_secondary};
    }}

    QLabel[class="accent"] {{
        color: {colors.accent};
        font-weight: 600;
    }}

    /* ── QPushButton ───────────────────────────────────── */

    QPushButton {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 6px 12px;
        font-size: {FONT_SIZE_SM}px;
        font-weight: 600;
        min-height: 26px;
    }}

    QPushButton:hover {{
        background-color: {colors.surface_hover};
        border-color: {colors.primary_light};
        color: {colors.primary_light};
    }}

    QPushButton:pressed {{
        background-color: {colors.border};
    }}

    QPushButton:disabled {{
        background-color: {colors.surface_light};
        color: {colors.text_disabled};
        border: 1px solid {colors.border_light};
    }}

    QPushButton[class="primary"], QPushButton[class="dark"] {{
        background-color: {colors.primary};
        border: 1px solid {colors.primary_dark};
        color: #ffffff;
        font-weight: 700;
    }}

    QPushButton[class="primary"]:hover, QPushButton[class="dark"]:hover {{
        background-color: {colors.primary_light};
        border-color: {colors.primary};
        color: #ffffff;
    }}

    QPushButton[class="primary"]:pressed, QPushButton[class="dark"]:pressed {{
        background-color: {colors.primary_dark};
    }}

    QPushButton[class="primary"]:disabled, QPushButton[class="dark"]:disabled {{
        background-color: {colors.surface_light};
        color: {colors.text_disabled};
        border: 1px solid {colors.border_light};
    }}

    QPushButton[class="accent"] {{
        background-color: {colors.accent};
        border: 1px solid {colors.accent_dark};
        color: #ffffff;
    }}

    QPushButton[class="accent"]:hover {{
        background-color: {colors.accent_light};
        color: #ffffff;
    }}

    QPushButton[class="accent"]:pressed {{
        background-color: {colors.accent_dark};
    }}

    QPushButton[class="accent"]:disabled {{
        background-color: {colors.surface_light};
        color: {colors.text_disabled};
        border: 1px solid {colors.border_light};
    }}

    QPushButton[class="success"] {{
        background-color: {colors.success};
        border: 1px solid {colors.success};
        color: #ffffff;
        font-weight: 700;
    }}

    QPushButton[class="success"]:hover {{
        background-color: {colors.success_light};
        color: #ffffff;
    }}

    QPushButton[class="success"]:disabled {{
        background-color: {colors.surface_light};
        color: {colors.text_disabled};
        border: 1px solid {colors.border_light};
    }}

    QPushButton[class="danger"] {{
        background-color: {colors.surface};
        border: 1px solid {colors.error};
        color: {colors.error};
    }}

    QPushButton[class="danger"]:hover {{
        background-color: {colors.error};
        color: #ffffff;
    }}

    QPushButton[class="danger"]:disabled {{
        background-color: {colors.surface_light};
        color: {colors.text_disabled};
        border: 1px solid {colors.border_light};
    }}

    QPushButton[class="flat"] {{
        background: transparent;
        border: 1px solid transparent;
        color: {colors.text_secondary};
        padding: 4px 8px;
        min-height: 22px;
    }}

    QPushButton[class="flat"]:hover {{
        background-color: {colors.surface_hover};
        color: {colors.text};
        border-color: {colors.border};
    }}

    /* ── QLineEdit / QSpinBox / QDoubleSpinBox ─────────── */

    QLineEdit {{
        background-color: {colors.input_bg};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 5px 10px;
        font-size: {FONT_SIZE_MD}px;
        min-height: 24px;
        selection-background-color: {colors.primary};
        selection-color: #ffffff;
    }}

    QSpinBox, QDoubleSpinBox {{
        background-color: {colors.input_bg};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 5px 26px 5px 10px;
        font-size: {FONT_SIZE_MD}px;
        min-height: 24px;
        selection-background-color: {colors.primary};
        selection-color: #ffffff;
    }}

    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {colors.primary_light};
    }}

    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: {colors.surface_light};
        color: {colors.text_disabled};
        border-color: {colors.border_light};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 22px;
        border-left: 1px solid {colors.border};
        border-bottom: 1px solid {colors.border};
        border-top-right-radius: {BORDER_RADIUS_SM}px;
        background-color: {colors.surface_light};
    }}

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
        background-color: {colors.surface_hover};
    }}

    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 22px;
        border-left: 1px solid {colors.border};
        border-bottom-right-radius: {BORDER_RADIUS_SM}px;
        background-color: {colors.surface_light};
    }}

    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {colors.surface_hover};
    }}

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: url({icons['chevron_up']});
        width: 11px;
        height: 11px;
    }}

    QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off,
    QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:off {{
        image: url({icons['chevron_up_disabled']});
    }}

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: url({icons['chevron_down']});
        width: 11px;
        height: 11px;
    }}

    QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off,
    QDoubleSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:off {{
        image: url({icons['chevron_down_disabled']});
    }}

    /* ── QComboBox (Listas Suspensas) ──────────────────── */

    QComboBox {{
        background-color: {colors.input_bg};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 5px 30px 5px 10px;
        font-size: {FONT_SIZE_MD}px;
        min-height: 24px;
    }}

    QComboBox:hover {{
        border-color: {colors.primary_light};
    }}

    QComboBox:focus {{
        border-color: {colors.primary};
    }}

    QComboBox:disabled {{
        background-color: {colors.surface_light};
        color: {colors.text_disabled};
        border-color: {colors.border_light};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 26px;
        border-left: 1px solid {colors.border};
        border-top-right-radius: {BORDER_RADIUS_SM}px;
        border-bottom-right-radius: {BORDER_RADIUS_SM}px;
        background-color: {colors.surface_light};
    }}

    QComboBox::drop-down:hover {{
        background-color: {colors.surface_hover};
    }}

    QComboBox::down-arrow {{
        image: url({icons['chevron_down']});
        width: 13px;
        height: 13px;
    }}

    QComboBox::down-arrow:disabled {{
        image: url({icons['chevron_down_disabled']});
    }}

    QComboBox QAbstractItemView {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        selection-background-color: {colors.primary};
        selection-color: #ffffff;
        padding: 4px;
        outline: none;
    }}

    QComboBox QAbstractItemView::item {{
        min-height: 26px;
        padding: 4px 10px;
        border-radius: 3px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: {colors.surface_hover};
        color: {colors.text};
    }}

    QComboBox QAbstractItemView::item:selected {{
        background-color: {colors.primary};
        color: #ffffff;
    }}

    /* ── QCheckBox / QRadioButton ──────────────────────── */

    QCheckBox, QRadioButton {{
        color: {colors.text};
        spacing: 8px;
        font-size: {FONT_SIZE_SM}px;
        background: transparent;
    }}

    QCheckBox:disabled, QRadioButton:disabled {{
        color: {colors.text_disabled};
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1.5px solid {colors.border};
        border-radius: 4px;
        background-color: {colors.input_bg};
    }}

    QCheckBox::indicator:hover {{
        border-color: {colors.primary_light};
    }}

    QCheckBox::indicator:checked {{
        background-color: {colors.primary};
        border-color: {colors.primary};
        image: url({icons['check']});
    }}

    QCheckBox::indicator:disabled {{
        background-color: {colors.surface_light};
        border-color: {colors.border_light};
    }}

    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1.5px solid {colors.border};
        border-radius: 9px;
        background-color: {colors.input_bg};
    }}

    QRadioButton::indicator:hover {{
        border-color: {colors.primary_light};
    }}

    QRadioButton::indicator:checked {{
        background-color: {colors.primary};
        border-color: {colors.primary};
        image: url({icons['radio_dot']});
    }}

    /* ── QSlider ───────────────────────────────────────── */

    QSlider::groove:horizontal {{
        border: 1px solid {colors.border};
        height: 6px;
        background-color: {colors.surface_light};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background-color: {colors.primary};
        border: 2px solid #ffffff;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 8px;
    }}

    QSlider::handle:horizontal:hover {{
        background-color: {colors.primary_light};
    }}

    QSlider::sub-page:horizontal {{
        background-color: {colors.primary};
        border-radius: 3px;
    }}

    /* ── QProgressBar ──────────────────────────────────── */

    QProgressBar {{
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        background-color: {colors.surface_light};
        text-align: center;
        color: {colors.text};
        font-size: {FONT_SIZE_SM}px;
        font-weight: 600;
        min-height: 18px;
        max-height: 18px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {colors.primary},
            stop:1 {colors.primary_light}
        );
        border-radius: 4px;
    }}

    /* ── QTabWidget / QTabBar ──────────────────────────── */

    QTabWidget::pane {{
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS}px;
        background-color: {colors.surface};
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {colors.surface_light};
        color: {colors.text_secondary};
        border: 1px solid {colors.border};
        border-bottom: none;
        padding: 7px 16px;
        margin-right: 3px;
        border-top-left-radius: {BORDER_RADIUS_SM}px;
        border-top-right-radius: {BORDER_RADIUS_SM}px;
        font-weight: 600;
        font-size: {FONT_SIZE_SM}px;
    }}

    QTabBar::tab:selected {{
        background-color: {colors.surface};
        color: {colors.primary_light};
        border-top: 2px solid {colors.primary};
        font-weight: 700;
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {colors.surface_hover};
        color: {colors.text};
    }}

    /* ── QGroupBox ─────────────────────────────────────── */

    QGroupBox {{
        font-size: {FONT_SIZE_MD}px;
        font-weight: 700;
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS}px;
        margin-top: 10px;
        padding-top: 16px;
        background-color: {colors.surface};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 3px 10px;
        background-color: {colors.primary};
        border-radius: {BORDER_RADIUS_SM}px;
        color: #ffffff;
        font-size: {FONT_SIZE_SM}px;
    }}

    /* ── QScrollArea / QScrollBar ──────────────────────── */

    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background-color: {colors.scrollbar};
        border-radius: 4px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {colors.scrollbar_hover};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: transparent;
        height: 8px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {colors.scrollbar};
        border-radius: 4px;
        min-width: 28px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {colors.scrollbar_hover};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── QTextEdit / QPlainTextEdit / QTextBrowser ─────── */

    QTextEdit, QPlainTextEdit {{
        background-color: {colors.input_bg};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 8px;
        font-family: {FONT_MONO};
        font-size: {FONT_SIZE_SM}px;
        selection-background-color: {colors.primary};
        selection-color: #ffffff;
    }}

    QTextBrowser {{
        background-color: {colors.input_bg};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 10px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_SM}px;
        selection-background-color: {colors.primary};
        selection-color: #ffffff;
    }}

    /* ── QTableView / QTableWidget / QHeaderView ───────── */

    QTableView, QTableWidget {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        gridline-color: {colors.border_light};
        selection-background-color: {colors.primary};
        selection-color: #ffffff;
        alternate-background-color: {colors.surface_light};
        font-size: {FONT_SIZE_SM}px;
    }}

    QHeaderView::section {{
        background-color: {colors.primary_dark};
        color: #ffffff;
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {colors.border};
        border-bottom: 1px solid {colors.border};
        font-weight: 700;
        font-size: {FONT_SIZE_XS}px;
    }}

    QHeaderView::down-arrow {{
        image: url({icons['chevron_down_white']});
        width: 10px;
        height: 10px;
        subcontrol-position: center right;
        right: 4px;
    }}

    QHeaderView::up-arrow {{
        image: url({icons['chevron_up_white']});
        width: 10px;
        height: 10px;
        subcontrol-position: center right;
        right: 4px;
    }}

    /* ── QToolTip ───────────────────────────────────────── */

    QToolTip {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.primary};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 6px 10px;
        font-size: {FONT_SIZE_SM}px;
    }}

    /* ── QSplitter ─────────────────────────────────────── */

    QSplitter::handle {{
        background-color: {colors.border};
        border-radius: 1px;
    }}

    QSplitter::handle:hover {{
        background-color: {colors.primary_light};
    }}

    QSplitter::handle:horizontal {{
        width: 3px;
        margin: 0 2px;
    }}

    QSplitter::handle:vertical {{
        height: 3px;
        margin: 2px 0;
    }}

    /* ── QStatusBar ────────────────────────────────────── */

    QStatusBar {{
        background-color: {colors.surface};
        color: {colors.text_secondary};
        border-top: 1px solid {colors.border};
        font-size: {FONT_SIZE_SM}px;
        padding: 2px 8px;
    }}

    QStatusBar QLabel {{
        padding: 0 6px;
    }}

    /* ── QMenuBar / QMenu ──────────────────────────────── */

    QMenuBar {{
        background-color: {colors.surface};
        color: {colors.text};
        border-bottom: 1px solid {colors.border};
        padding: 2px 4px;
        font-weight: 600;
    }}

    QMenuBar::item {{
        padding: 5px 10px;
        border-radius: {BORDER_RADIUS_SM}px;
    }}

    QMenuBar::item:selected {{
        background-color: {colors.surface_hover};
    }}

    QMenu {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {colors.primary};
        color: #ffffff;
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {colors.border};
        margin: 4px 8px;
    }}

    /* ── Sidebar Navigation & Lists ────────────────────── */

    QWidget#Sidebar {{
        background-color: {colors.surface};
        border-right: 1px solid {colors.border};
    }}

    QFrame#SidebarHeader {{
        background-color: {colors.primary_dark};
        border-bottom: 1px solid {colors.border};
    }}

    QListWidget {{
        background-color: {colors.input_bg};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS_SM}px;
        outline: none;
        font-size: {FONT_SIZE_SM}px;
    }}

    QListWidget::item {{
        color: {colors.text};
        padding: 8px 10px;
        border-bottom: 1px solid {colors.border_light};
    }}

    QListWidget::item:selected {{
        background-color: {colors.primary};
        color: #ffffff;
        font-weight: 600;
    }}

    QListWidget::item:hover:!selected {{
        background-color: {colors.surface_hover};
    }}

    QListWidget#SidebarList {{
        background-color: {colors.surface};
        border: none;
        border-right: 1px solid {colors.border};
        border-radius: 0px;
        outline: none;
        font-size: {FONT_SIZE_MD}px;
    }}

    QListWidget#SidebarList::item {{
        color: {colors.text_secondary};
        padding: 11px 14px;
        border-radius: 0px;
        border-bottom: 1px solid {colors.border_light};
        border-left: 3px solid transparent;
    }}

    QListWidget#SidebarList::item:selected {{
        background-color: {colors.primary};
        color: #ffffff;
        border-left: 4px solid {colors.accent_light};
        font-weight: 700;
    }}

    QListWidget#SidebarList::item:hover:!selected {{
        background-color: {colors.surface_hover};
        color: {colors.text};
    }}

    /* ── Card Frame ────────────────────────────────────── */

    QFrame[class="card"] {{
        background-color: {colors.surface};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS}px;
        padding: {PADDING_MD}px;
    }}

    QFrame[class="card"]:hover {{
        border-color: {colors.primary_light};
    }}

    QFrame[class="card-selected"] {{
        background-color: {colors.surface};
        border: 2px solid {colors.primary};
        border-radius: {BORDER_RADIUS}px;
        padding: {PADDING_MD}px;
    }}

    QFrame[class="surface"] {{
        background-color: {colors.surface};
        border: 1px solid {colors.border};
        border-radius: {BORDER_RADIUS}px;
    }}

    /* ── Separator ─────────────────────────────────────── */

    QFrame[class="separator"] {{
        background-color: {colors.border};
        max-height: 1px;
        min-height: 1px;
    }}
    """


_STYLESHEET_CACHE: dict[str, str] = {}


def apply_theme(app: QApplication, theme: str = "light") -> None:
    """Aplica o tema claro padrão à aplicação."""
    global COLORS, CURRENT_THEME

    COLORS = LightColors()
    theme = "light"
    CURRENT_THEME = "light"

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS.background))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS.input_bg))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS.surface))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS.surface))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS.text))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(COLORS.accent))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS.primary))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLORS.surface))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(COLORS.text))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLORS.text_disabled))

    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,
        QColor(COLORS.text_disabled),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,
        QColor(COLORS.text_disabled),
    )

    app.setPalette(palette)

    _STYLESHEET_CACHE[theme] = _build_stylesheet(COLORS, theme_name=theme)
    app.setStyleSheet(_STYLESHEET_CACHE[theme])


def clear_theme_cache() -> None:
    """Limpa o cache de stylesheets para forçar reconstrução."""
    _STYLESHEET_CACHE.clear()
