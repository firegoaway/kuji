"""Дизайн-система (Swiss Utilitarian) и форматирование чисел.

Палитра строго по ТЗ: плоские поверхности, 1px структурные границы,
без градиентов/теней/декоративных иконок; 8px пространственная сетка.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QFont, QFontMetricsF

# математическая типографика формул (сессия 8, Задача 2): единая точка
# входа для ядра (layout) и UI (render/формы/PDF)
from .math_text import (math, math_height, math_html_lines, math_plain,
                        math_size, math_wrap, paint_math)

# ---------- палитра ----------
APP_BG = "#F8FAFC"
PANEL_BG = "#FFFFFF"
BORDER = "#CBD5E1"
GRID_LINE = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#475569"
ACCENT = "#2563EB"
SAFE = "#16A34A"
HAZARD = "#DC2626"
CUTOFF = "#94A3B8"
NODE_FILL = "#FFFFFF"
EDGE = "#475569"

QCOLOR = {k: QColor(v) for k, v in dict(
    app_bg=APP_BG, panel=PANEL_BG, border=BORDER, grid=GRID_LINE,
    text=TEXT_PRIMARY, text2=TEXT_SECONDARY, accent=ACCENT,
    safe=SAFE, hazard=HAZARD, cutoff=CUTOFF,
    node_fill=NODE_FILL, edge=EDGE,
).items()}

FONT_STACK_UI = ["Inter", "Segoe UI", "Roboto", "Arial"]
FONT_STACK_MONO = ["JetBrains Mono", "Consolas", "Courier New"]

# кегли (px @96 dpi). Задача 5 (сессия 17, LOCKED «и то и другое»):
# базовая геометрия дерева КРУПНЕЕ – дерево событий не «островок» рядом
# с матрицей; выросшие кегли заголовка/меты/ΣQ (canvas и PDF растут
# вместе – константы одни на обоих потребителей, WYSIWYG)
F_TITLE = 14       # заголовок узла (полужирный)
F_META = 11        # подписи, метки ветвей
F_MONO = 12        # P и Q – моноширинные
F_HEADER = 12      # шапка эшелонов (полужирный)
F_SMALL = 9        # бейдж статуса
F_FORMULA = 14     # формула ΣQ в теле ноды (моно-болд; строка ΣQ есть
                   # только у ноды «Возникновение» – акцент «стока» дерева)

# пространственная сетка 8px. Задача 5 (сессия 17): вертикальные поля
# узла и внутренний отступ текста увеличены – ноды заметно выше и
# свободнее (метрики по-прежнему решают геометрию, потолка ширины нет)
PAD_H = 16         # горизонтальный паддинг узла
PAD_V = 16         # вертикальный паддинг узла
NODE_INSET = 13    # горизонтальный отступ текста в узле (слева/справа) –
                   # ширины в layout.py считаются как advance + 2×NODE_INSET
LABEL_INSET = 6    # отступ текста в плашке ветви – ширина = advance + 2×LABEL_INSET
MARGIN = 32        # поле сцены
HEADER_H = 48      # высота шапки эшелонов
HGAP = 176         # горизонтальный зазор между колонками FTA (вмещает плашку P целиком)
VGAP_ROW = 44      # шаг между строками листьев (мин.)
MIN_NODE_W = 130
MAX_NODE_W = 208
MIN_COL_W = 170

# Заголовок секции противоаварийных мер в формах оборудования (сессия 8,
# Задача 6): единая строка для окна «База данных» и инспектора. Внутренний
# ключ секции по-прежнему pedals – переименование только отображаемое.
PEDALS_CAPTION = "ЗАЩИТНЫЕ СРЕДСТВА И ПОПРАВОЧНЫЕ КОЭФФИЦИЕНТЫ"

# ---------- палитра глифов (сессия 9, Задача 1) ----------
# ЕДИНЫЙ источник цветов иконок: контрастные, но гармонированные с базовой
# палитрой (уровни насыщенности ~Tailwind-600/700). Имена – константы
# eta.ui.icons. Глифы вне ICON_PALETTE и не входящие в ICON_NEUTRAL_GLYPHS
# считаются ошибкой покрытия (тест smoke «палитра иконок»).
ICON_BASE = "#475569"            # нейтральный slate для служебных глифов
ICON_PALETTE: dict[str, str] = {
    # иерархия объектов: земля / сталь / бетон / бирюза / янтарь / зелёный
    "territory": "#B45309",      # территория – земля (amber-700)
    "building": "#475569",       # здание – сталь (slate-600)
    "compartment": "#0E7490",    # отсек – cyan-700
    "room": "#0F766E",           # помещение – teal-700
    "area": "#D97706",           # участок – янтарь (amber-600)
    "equipment": "#059669",      # оборудование – emerald-600
    "outdoor": "#059669",        # наружная установка – аппарат (emerald-600)
    # события и логика
    "event-add": "#EA580C",      # событие/молния – тёплый акцент (orange-600)
    # сессия 16, Задача 4 (LOCKED): списки причин различимы с первого
    # взгляда – ГС = облако в янтаре, ИЗ = пламя в красном; ЦВЕТА =
    # классы нод холста (render.py), одна семантика – один цвет
    "gs-cause": "#B45309",       # причины ГС – облако (amber-700, как ноды ГС)
    "iz-cause": "#B91C1C",       # причины ИЗ – пламя (red-700, как ноды ИЗ)
    "shield": "#16A34A",         # защиты/ПАЗ – зелёное семейство (green-600)
    "domino-link": "#2563EB",    # связь домино – пунктир ACCENT
    # виды документа – синее семейство
    "matrix": "#2563EB",
    "schema": "#1D4ED8",
    "table-pop": "#0369A1",
    # сессия 13: добавление дерева сценариев – фиолетовый акцент
    "tree-add": "#7C3AED",
    # сессия 18, Задача 13: справка «Базы данных» – акцентный синий
    "help": "#2563EB",
    # опасные действия – красное семейство
    "trash": "#DC2626",
}
# служебные глифы, ОСОЗНАННО нейтральные (opt-out из цветной палитры)
ICON_NEUTRAL_GLYPHS = {
    "zoom-in", "zoom-out", "fit", "sticky", "free",
    "pencil", "props", "crosshair", "funnel", "auto-layout",
}
# толщина штриха глифов (было 1.6 – сессия 9: крупнее и жирнее)
ICON_STROKE = 2.2
ICON_STROKE_THIN = 1.7          # штрих пунктирных подэлементов глифа
# кегли глифов по местам применения (сессия 9, Задача 1): крупные цветные
# глифы в кнопках панелей; меню – по умолчанию QStyle (вопрос Q19)
ICON_PX_PANEL = 22              # горизонтальные тулбары (кроме панели иерархии)
ICON_PX_HIER = 32               # панель иерархии: крупные кнопки (сессия 12, Задача 1)
ICON_PX_LEFTBAR = 24            # левая вертикальная панель вьюпорта

# ---------- пины «ДА/НЕТ» (единственный источник геометрии) ----------
# Сессия 8, Задача 5: и холст (canvas), и раскладка (layout) берут
# положение пинов отсюда – ребра кончаются точно на кружках.
PIN_Y_TOP = 0.32        # доля высоты узла: верхний пин («ДА», зелёный)
PIN_Y_BOT = 0.68        # нижний пин («НЕТ», красный)
PIN_R = 5.5             # радиус пина (px, 11 px в диаметре)
PIN_HIT_R = 7.5         # радиус hit-теста пина


def pin_centers(rect) -> dict[str, QPointF]:
    """Центры пинов узла в координатах сцены: слева/справа зелёный
    («ДА», верх) и красный («НЕТ», низ)."""
    y1 = rect.top() + rect.height() * PIN_Y_TOP
    y2 = rect.top() + rect.height() * PIN_Y_BOT
    return {
        "left-yes": QPointF(rect.left(), y1),
        "left-no": QPointF(rect.left(), y2),
        "right-yes": QPointF(rect.right(), y1),
        "right-no": QPointF(rect.right(), y2),
    }


def ui_font(point_px: int = F_TITLE, bold: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(FONT_STACK_UI)
    f.setPixelSize(point_px)
    f.setBold(bold)
    return f


def mono_font(point_px: int = F_MONO, bold: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(FONT_STACK_MONO)
    f.setPixelSize(point_px)
    f.setBold(bold)
    return f


# ---------- форматирование чисел ----------
_SUP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "-": "⁻"}


def _sup(exp: int) -> str:
    return "".join(_SUP.get(ch, ch) for ch in str(exp))


def sil_combo_item(lvl: int, lo: float, hi: float) -> str:
    """Пункт списка уровней полноты безопасности: «SIL 2: PFD 10⁻³…10⁻²» –
    настоящие Unicode-надстрочники, без каретки «10^» (Задача 1; диапазоны
    по табл. 2 ГОСТ Р МЭК 61508-1-2012)."""
    import math as _mathmod

    def _exp10(v: float) -> int:
        return int(round(_mathmod.log10(v))) if v > 0 else 0

    return f"SIL {lvl}: PFD 10{_sup(_exp10(lo))}…10{_sup(_exp10(hi))}"


def fmt_prob(p: float) -> str:
    """0.965 -> «0,965»; 1.0 -> «1,000»."""
    return f"{p:.3f}".replace(".", ",")


def fmt_q(q: float) -> str:
    """Экспоненциальный формат: 6.2e-4 -> «6,20 × 10⁻⁴»."""
    if q == 0:
        return "0"
    if q >= 1:
        return f"{q:.2f}".replace(".", ",")
    exp = 0
    m = q
    while m < 1:
        m *= 10
        exp += 1
    while m >= 10:
        m /= 10
        exp -= 1
    return f"{m:.2f}".replace(".", ",") + " × 10" + _sup(-exp)


def fmt_q_full(q: float) -> str:
    return fmt_q(q) + " год⁻¹"


def parse_prob(text: str) -> float | None:
    """«0,965» / «0.965» / «9,65e-1» -> float."""
    t = text.strip().replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    if 0.0 <= v <= 1.0:
        return v
    return None


def parse_sci(text: str) -> float | None:
    """«6,2e-4» / «3,2^-5» / «6.2·10^-4» -> float. Задача 7 (сессия 14):
    реализация – общая core.numfmt.parse_eng (экспоненциальная запись И
    каретка m^e = m×10^e); здесь остается только имя для потребителей
    темы (редактор чисел БД и др.)."""
    from ..core.numfmt import parse_eng
    return parse_eng(text)


QSS = f"""
* {{
    font-family: "Inter", "Segoe UI", "Roboto", "Arial";
    font-size: 12px;
    color: {TEXT_PRIMARY};
}}
QMainWindow, QWidget#central {{ background: {APP_BG}; }}
QToolBar {{
    background: {PANEL_BG}; border: none;
    border-bottom: 1px solid {BORDER};
    padding: 4px 8px; spacing: 8px;
}}
QToolButton {{
    background: transparent; border: 1px solid transparent;
    border-radius: 0px; padding: 6px 10px;
}}
QToolButton:hover {{ border: 1px solid {BORDER}; background: {APP_BG}; }}
QToolButton:pressed {{ background: {GRID_LINE}; }}
QSplitter::handle {{ background: #94A3B8; }}
QSplitter::handle:horizontal {{ width: 7px; margin: 0 1px 0 1px; }}
QSplitter::handle:vertical {{ height: 7px; margin: 1px 0 1px 0; }}
QSplitter::handle:hover {{ background: {ACCENT}; }}
QSplitter::handle:pressed {{ background: #1D4ED8; }}
#panel {{ background: {PANEL_BG}; border: 1px solid {BORDER}; }}
#inspectorForm {{ background: {PANEL_BG}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
    background: {PANEL_BG}; border: 1px solid {BORDER};
    padding: 4px 8px; selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton {{
    background: {PANEL_BG}; border: 1px solid {BORDER};
    padding: 6px 16px;
}}
QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton:pressed {{ background: {GRID_LINE}; }}
QPushButton#primary {{ background: #3B82F6; color: #FFFFFF;
    border: 1px solid #3B82F6; }}
QPushButton#primary:hover {{ background: #2563EB; }}
QPushButton#primary:pressed {{ background: #1D4ED8; }}
QPushButton#primaryOutline {{ background: #FFFFFF; color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT}; }}
QPushButton#primaryOutline:hover {{ background: #EFF6FF;
    border: 1px solid #1D4ED8; color: {TEXT_PRIMARY}; }}
QPushButton#primaryOutline:pressed {{ background: #DBEAFE;
    color: {TEXT_PRIMARY}; }}
QTableWidget {{
    background: {PANEL_BG}; border: 1px solid {BORDER};
    gridline-color: {GRID_LINE};
}}
QHeaderView::section {{
    background: {APP_BG}; border: none;
    border-bottom: 1px solid {BORDER}; border-right: 1px solid {GRID_LINE};
    padding: 6px 8px; font-weight: 600;
}}
QTableWidget::item {{ padding: 4px 8px; border: none; }}
QListWidget {{ background: {PANEL_BG}; border: 1px solid {BORDER}; }}
QListWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {GRID_LINE}; }}
/* Сессия 15/1: мягкий синий выделения – как в дереве иерархии */
QListWidget::item:selected {{ background: #93C5FD; color: {TEXT_PRIMARY}; }}
/* сессия 12, Задача 1: дерево иерархии – крупные строки (гриф ~32 px),
   заметный отступ уровней, наведение и выделение в плоском стиле */
QTreeWidget#hierTree {{ background: {PANEL_BG}; border: 1px solid {BORDER}; }}
QTreeWidget#hierTree::item {{ min-height: 30px; padding: 3px 4px; border-radius: 4px; }}
QTreeWidget#hierTree::item:hover {{ background: {GRID_LINE}; }}
/* Сессия 15/1 (просьба заказчика): выделение строк – МЯГКИЙ синий
   (было ярко-синее #2563EB с белым текстом – «ядовито»); темный текст
   сохраняет контраст на светлом фоне */
QTreeWidget#hierTree::item:selected {{ background: #93C5FD; color: {TEXT_PRIMARY}; }}
QLabel#caption {{
    color: {TEXT_SECONDARY}; font-size: 10px;
    font-weight: 600; letter-spacing: 0.5px;
}}
QLabel#h1 {{ font-size: 13px; font-weight: 600; }}
QScrollArea {{ border: none; background: transparent; }}
QTabWidget::pane {{ border: none; border-top: 1px solid {BORDER}; }}
QTabBar {{ outline: none; }}
QTabBar::tab {{
    background: {PANEL_BG}; padding: 8px 16px;
    border: 1px solid {BORDER}; margin-right: -1px; outline: none;
}}
QTabBar::tab:selected {{ border-bottom: 2px solid {ACCENT}; font-weight: 600; }}
QStatusBar {{ background: {PANEL_BG}; border-top: 1px solid {BORDER}; }}
QToolTip {{
    background: {TEXT_PRIMARY}; color: #FFFFFF; border: 1px solid {TEXT_PRIMARY};
    padding: 6px 8px; font-size: 11px;
}}
QComboBox QAbstractItemView {{ background: {PANEL_BG}; border: 1px solid {BORDER}; }}
/* сессия 12, Задача 5: вертикальный паддинг пунктов – кликабельна почти
   вся высота разворота (интервал между пунктами – 2 px, controls.py) */
QComboBox QAbstractItemView::item {{ padding: 7px 8px; }}
QComboBox {{ min-width: 110px; }}
/* Задача 4 (сессия 14): компактный список единиц (км²|м²) – шириной
   по содержимому, НЕ наследует общий min-width кнопок-списков */
QComboBox#compactCombo {{ min-width: 0px; padding: 4px 6px; }}
QComboBox[inactive="true"] {{ color: {CUTOFF}; }}
/* Задача 5 (сессия 14): наследуемое значение площади показывается
   приглушенным цветом (своё значение – обычным) */
QDoubleSpinBox[inactive="true"] {{ color: {CUTOFF}; }}
QLabel#thresholdCaption[inactive="true"] {{ color: {CUTOFF}; }}
QPushButton[compact="true"] {{ padding: 3px 8px; font-size: 11px; }}
#leftToolbar {{
    background: {PANEL_BG}; border: none;
    border-right: 1px solid {BORDER};
}}
#leftToolbar QToolButton {{
    background: transparent; border: 1px solid transparent;
    border-radius: 0px; padding: 2px; margin: 0;
}}
#leftToolbar QToolButton:hover {{ border: 1px solid {BORDER}; background: {APP_BG}; }}
#leftToolbar QToolButton:pressed {{ background: {GRID_LINE}; }}
#leftToolbar QToolButton:checked {{ border: 1px solid {ACCENT}; background: {GRID_LINE}; }}
#leftToolbar QToolButton:disabled {{ color: {CUTOFF}; border-color: transparent; }}
#leftToolbarSeparator {{ color: {BORDER}; max-height: 1px; }}
QFrame#paletteGroupHeader {{
    background: {APP_BG}; border: 1px solid {BORDER};
}}
EventCard[selected="true"] {{
    background: {APP_BG}; border: 1px solid {ACCENT};
    border-left: 3px solid {ACCENT};
}}
QFrame#paletteGroupHeader:hover {{ background: {GRID_LINE}; }}
QLabel#paletteGroupTitle {{ color: {TEXT_PRIMARY}; }}
QLabel#paletteGroupCount {{ color: {TEXT_SECONDARY}; }}
QLabel#paletteGroupChevron {{ color: {TEXT_SECONDARY}; }}
QCheckBox {{ spacing: 8px; }}
QScrollBar:vertical {{ background: {APP_BG}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar:horizontal {{ background: {APP_BG}; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
/* сессия 10.1: пунктирных фокус-рамок нигде не должно быть */
QListWidget, QTreeWidget, QTableView, QTreeView, QListView {{
    outline: none;
}}
/* сессия 11, Задача 4: карточки шаблонов оборудования (окно БД) –
   базовое состояние, наведение и выбранная карточка */
QFrame#kbCard {{
    background: {PANEL_BG}; border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#kbCard:hover {{
    border-color: #94A3B8; background: {APP_BG};
}}
QFrame#kbCard[selected="true"] {{
    border: 1px solid {ACCENT}; border-left: 3px solid {ACCENT};
    background: #EFF6FF;
}}
/* сессия 11, Задача 3: компактная полоса под-вкладок таблиц типовых
   частот (П1.3/П1.4/П2.1) – тот же плоский стиль, меньше поля */
QTabWidget#kbSubTabs > QTabBar::tab {{
    padding: 5px 12px; font-size: 11px;
}}
/* плашка «Цель: …» на вкладке шаблонов (окно БД) */
QLabel#targetBadge {{
    background: {APP_BG}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER}; border-radius: 10px;
    padding: 3px 12px; font-size: 11px;
}}
"""
