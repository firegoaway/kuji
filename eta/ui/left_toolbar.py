"""Левая вертикальная панель инструментов вьюпорта (Задача 3 + 4).

Узкая колонка (~44 px) слева от рабочего вьюпорта: триггер pop-out окна
«Документ – таблица / лист для PDF» (сессия 8, верхняя кнопка), зум±,
«Показать всё» (Alt+A), переключатель режима обзора «липкий/свободный»
и кнопка-мусорка (удаление выделенных поддеревьев). Сенсорный запас:
кнопки ≥32×32 px, межкнопочный отступ ≥8 px (Задача 5).

Иконки – плоская векторная графика, нарисованная кодом (eta/ui/icons.py):
монохром, 1px-штрихи, ACCENT для активных состояний, без внешних icon-паков.
Tooltip'ы – rich text: название + краткое описание + горячая клавиша.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (QFrame, QSizePolicy, QToolButton, QVBoxLayout,
                               QWidget)

from .canvas import FREE, STICKY
from .icons import (GLYPH_AUTOLAYOUT, GLYPH_FIT, GLYPH_FREE, GLYPH_IN,
                    GLYPH_OUT, GLYPH_STICKY, GLYPH_TABLE_POP, GLYPH_TRASH,
                    glyph_icon)
from .theme import ICON_PX_LEFTBAR

PANEL_W = 44          # ширина колонки
BTN = 36              # кнопка ≥32px с запасом под палец


def _tool_button(tooltip_rich: str, plain_tip: str) -> QToolButton:
    b = QToolButton()
    b.setFixedSize(BTN, BTN)
    # крупный цветной глиф (сессия 9, Задача 1): ~24px в кнопке 36px
    b.setIconSize(QSize(ICON_PX_LEFTBAR, ICON_PX_LEFTBAR))
    b.setToolTip(tooltip_rich)
    b.setStatusTip(plain_tip)
    b.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # клики не крадут Delete-фокус
    b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return b


class ViewportToolbar(QWidget):
    """Вертикальная линия кнопок управления вьюпортом."""

    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    fit_requested = Signal()
    autolayout_requested = Signal()     # «Авторазметка» (сессия 12, Задача 11)
    mode_requested = Signal(str)       # "sticky" | "free"
    delete_requested = Signal()
    doc_window_requested = Signal()    # pop-out окно «Документ» (сессия 8)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("leftToolbar")
        self.setFixedWidth(PANEL_W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(8)

        # верхняя кнопка колонки: панель «Документ – таблица / лист для
        # PDF» в отдельном нативном окне (можно увести на второй монитор);
        # checked = окно открыто (синяя рамка, как у активного режима)
        self.btn_doc_window = _tool_button(
            "<b>Открыть таблицу сценариев в отдельном окне</b> – панель"
            " «Документ – таблица / лист для PDF» в нативном окне ОС<br>"
            "(перетаскивайте на второй монитор; масштаб – колесо,"
            " «+»/«–», Ctrl+0 – вписать по ширине)",
            "Открыть таблицу сценариев в отдельном окне")
        self.btn_doc_window.setCheckable(True)
        self.btn_doc_window.setIcon(glyph_icon(GLYPH_TABLE_POP))
        self.btn_doc_window.clicked.connect(
            lambda _checked=False: self.doc_window_requested.emit())
        lay.addWidget(self.btn_doc_window)

        sep_doc = QFrame()
        sep_doc.setFrameShape(QFrame.Shape.HLine)
        sep_doc.setObjectName("leftToolbarSeparator")
        lay.addWidget(sep_doc)

        self.btn_zoom_in = _tool_button(
            "<b>Приблизить</b> – увеличить масштаб вьюпорта<br>"
            "(колесо мыши – плавный зум к курсору)",
            "Приблизить")
        self.btn_zoom_in.setIcon(glyph_icon(GLYPH_IN))
        self.btn_zoom_in.clicked.connect(self.zoom_in_requested.emit)
        lay.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = _tool_button(
            "<b>Отдалить</b> – уменьшить масштаб вьюпорта",
            "Отдалить")
        self.btn_zoom_out.setIcon(glyph_icon(GLYPH_OUT))
        self.btn_zoom_out.clicked.connect(self.zoom_out_requested.emit)
        lay.addWidget(self.btn_zoom_out)

        self.btn_fit = _tool_button(
            "<b>Показать всё</b> – вписать дерево в окно<br><b>Alt+A</b>",
            "Показать всё (Alt+A)")
        self.btn_fit.setIcon(glyph_icon(GLYPH_FIT))
        self.btn_fit.clicked.connect(self.fit_requested.emit)
        lay.addWidget(self.btn_fit)

        # Задача 11 (сессия 12): сброс ручного перетаскивания нод –
        # показанные деревья возвращаются к автоматической раскладке
        self.btn_autolayout = _tool_button(
            "<b>Авторазметка</b> – вернуть ноды показанных деревьев"
            " на автоматические места<br>(смещения ручного"
            " перетаскивания сбрасываются)",
            "Авторазметка (сбросить перетаскивание)")
        self.btn_autolayout.setIcon(glyph_icon(GLYPH_AUTOLAYOUT))
        self.btn_autolayout.clicked.connect(self.autolayout_requested.emit)
        lay.addWidget(self.btn_autolayout)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("leftToolbarSeparator")
        lay.addWidget(sep)

        self.btn_sticky = _tool_button(
            "<b>Липкий обзор</b> – камера не уходит за границы дерева "
            "(ползунки только у большого дерева)",
            "Липкий обзор")
        self.btn_sticky.setCheckable(True)
        self.btn_sticky.setIcon(glyph_icon(GLYPH_STICKY))
        self.btn_sticky.clicked.connect(lambda: self.mode_requested.emit(STICKY))
        lay.addWidget(self.btn_sticky)

        self.btn_free = _tool_button(
            "<b>Свободный обзор</b> – камеру можно увести за пределы дерева; "
            "панорама и зум работают всегда",
            "Свободный обзор")
        self.btn_free.setCheckable(True)
        self.btn_free.setIcon(glyph_icon(GLYPH_FREE))
        self.btn_free.clicked.connect(lambda: self.mode_requested.emit(FREE))
        lay.addWidget(self.btn_free)

        lay.addStretch(1)

        self.btn_trash = _tool_button(
            "<b>Удалить выделенное</b> – удалить узлы и их поддеревья<br>"
            "(клавиша Delete)",
            "Удалить выделенное (Delete)")
        self.btn_trash.setIcon(glyph_icon(GLYPH_TRASH))
        self.btn_trash.setEnabled(False)          # без выделения приглушена
        self.btn_trash.clicked.connect(self.delete_requested.emit)
        lay.addWidget(self.btn_trash)

        self.set_mode(STICKY)

    # ---------- состояние ----------
    def set_mode(self, mode: str) -> None:
        """Синхронизация checked-состояний переключателя обзора."""
        self.btn_sticky.setChecked(mode == STICKY)
        self.btn_free.setChecked(mode == FREE)

    def set_doc_window_open(self, is_open: bool) -> None:
        """Активное состояние триггера pop-out окна (синяя рамка)."""
        self.btn_doc_window.setChecked(is_open)

    def set_trash_enabled(self, enabled: bool) -> None:
        self.btn_trash.setEnabled(enabled)
