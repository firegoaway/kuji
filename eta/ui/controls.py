# -*- coding: utf-8 -*-
"""Общие элементы управления (сессия 10.1, полировка UX):

* `wide_combo` – выпадающий список: ширина разворота вдвое больше кнопки,
  перенос текста пунктов по словам (без «…»), межстрочный интервал;
* `HLine`/`section_header` – тонкая разделительная линия и заголовок
  блока с нормативными отступами (UI/UX-блоки свойств);
* `html_delegate` – делегат таблиц с поддержкой формул (math_html:
  индексы/степени) и переносом по словам;
* `wrap85` – перенос длинных текстов по словам не шире 85 символов.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (QAbstractItemDelegate, QComboBox, QFrame,
                               QLabel, QListView, QSizePolicy,
                               QStyle, QStyleOptionViewItem,
                               QStyledItemDelegate)

from .theme import BORDER, TEXT_SECONDARY, math

WRAP_CHARS = 85            # лимет символов в ячейках таблиц (перенос по словам)
COMBO_POPUP_CHARS = 85     # Задача 11.3: строка пункта разворота ≤85 символов
_POPUP_PAD_PX = 34         # паддинги пунктов + рамка + запас под ползунок

# ---------------- Задача 7 (сессия 13): общий перенос ≤85 символов ----------
# Алгоритм перенесен из modern_tooltip (wrap_tip_line/_split_long_word):
# ЕДИНАЯ реализация для подсказок и таблиц БД – по ЦЕЛЫМ словам, слово
# длиннее строки разбивается по слогам с коротким тире «–».
_VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯaeiouyAEIOUY")


def split_long_word(word: str, limit: int) -> list[str]:
    """Разбить слово по слогам на куски ≤ limit символов ВМЕСТЕ с
    коротким тире «–» на разрыве. Простой русский алгоритм: граница
    слога – сразу после гласной (мо-ло-ко, ре-зер-ву-ар)."""
    parts: list[str] = []
    rest = word
    while len(rest) > limit:
        cut = 0
        # тире занимает последний символ куска – под буквы остаётся
        # limit-1, иначе строка получается длиной limit+1
        for i in range(2, min(limit - 1, len(rest) - 1) + 1):
            if rest[i - 1] in _VOWELS:
                cut = i
        if cut == 0:
            cut = max(2, limit - 1)   # слоговой границы нет – жёсткий разрыв
        parts.append(rest[:cut] + "–")
        rest = rest[cut:]
    parts.append(rest)
    return parts


def wrap_words85(line: str, width: int = WRAP_CHARS) -> list[str]:
    """Перенос строки по ЦЕЛЫМ словам не длиннее width символов; слово
    длиннее строки разбивается по слогам с «–» (Задача 3 сессии 12 /
    Задача 7 сессии 13 – общая реализация для подсказок и таблиц)."""
    out: list[str] = []
    cur = ""
    for word in line.split(" "):
        pieces = (split_long_word(word, width)
                  if len(word) > width else [word])
        for piece in pieces:
            cand = (cur + " " + piece).strip() if cur else piece
            if cur and len(cand) > width:
                out.append(cur)
                cur = piece
            else:
                cur = cand
    if cur:
        out.append(cur)
    return out or [""]


def wrap_text85(text: str, width: int = WRAP_CHARS) -> str:
    """Многострочный вариант wrap_words85: каждая логическая строка
    переносится по словам ≤ width символов, результат склеен «\\n»."""
    out: list[str] = []
    for ln in text.split("\n"):
        out.extend(wrap_words85(ln, width))
    return "\n".join(out)


def wrap85(text: str, width: int = WRAP_CHARS) -> str:
    """Устаревший textwrap-вариант (совместимость); новые места
    используют wrap_text85 – со слоговым разбиением длинных слов."""
    import textwrap
    return "\n".join(textwrap.wrap(text, width=width,
                                   break_long_words=False,
                                   break_on_hyphens=True)) or text


def wide_combo() -> QComboBox:
    """QComboBox с «дышащим» списком: пункты без усечений, перенос по
    словам, почти вся высота списка кликабельна (сессия 12, Задачи 5/6).

    Задача 11.3 (сессия 15): ширина разворота динамическая – по самому
    длинному пункту, но строка не длиннее 85 символов (шире – перенос
    по словам/слогам, делегат PopupWrapDelegate); нижняя граница –
    ширина кнопки. Кнопка закрытого списка свою ширину не меняет."""
    cb = QComboBox()
    lv = QListView()
    cb.setView(lv)
    lv.setWordWrap(True)
    lv.setUniformItemSizes(False)
    # Задача 5: вертикальный «хит» почти по всей высоте списка –
    # минимальный интервал между пунктами + вертикальный паддинг самих
    # пунктов (QSS в theme.py, селектор QComboBox QAbstractItemView::item)
    lv.setSpacing(2)
    lv.setTextElideMode(Qt.TextElideMode.ElideNone)
    lv.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    # Задача 2 (сессии 11): попиксельный скролл длинных списков
    lv.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
    lv.setHorizontalScrollMode(QListView.ScrollMode.ScrollPerPixel)
    lv.verticalScrollBar().setSingleStep(20)
    delegate = PopupWrapDelegate(lv)
    lv.setItemDelegate(delegate)
    cb.showPopup = _patched_show_popup(cb, lv, delegate)
    return cb


def compact_combo() -> QComboBox:
    """Задача 4 (сессия 14): КОМПАКТНЫЙ выпадающий список – ширина по
    содержимому (текст + стрелка, ~60–80 px), никогда не тянется с
    формой. Отдельный objectName «compactCombo» выводит список из-под
    общего QSS-правила QComboBox { min-width: 110px } (тема), поэтому
    остальные списки (БД/формы) остаются широкими. Выбор сделан в
    пользу помощника, а не точечной подгонки одного списка: единицы
    (км²|м²) могут появиться и в других местах. Разворот – обычный
    адаптивный (для коротких пунктов «км²»/«м²» этого достаточно)."""
    cb = QComboBox()
    cb.setObjectName("compactCombo")
    cb.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToContents)
    cb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return cb


class PopupWrapDelegate(QStyledItemDelegate):
    """Задача 11.3 (сессия 15): пункты разворота переносятся по ЦЕЛЫМ
    словам, слово длиннее строки – по слогам с «–» (та же машинерия
    wrap_words85, что в таблицах БД); строка не длиннее 85 символов и
    не шире ширины разворота (_width_px задается showPopup до открытия).
    Закрытая кнопка списка показывает исходный однострочный текст –
    перенос живет только в развороте."""

    TEXT_PAD_PX = 20        # горизонтальные поля пункта (8 слева + 8 справа + рамка)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._width_px: int = 0      # 0 – ширина еще не известна

    def _lines(self, text: str, fm, width_px: int) -> list[str]:
        text = str(text)
        limit = COMBO_POPUP_CHARS
        if width_px <= 0:
            # ширина неизвестна (подсчет для showPopup) – только лимит
            # символов
            return [text] if len(text) <= limit \
                else wrap_words85(text, limit)
        if fm.horizontalAdvance(text) <= width_px \
                and len(text) <= limit:
            return [text]
        # подбираем символьный лимит, пока все строки не влезут в пиксели
        while limit >= 8:
            lines = wrap_words85(text, limit)
            if all(fm.horizontalAdvance(l) <= width_px for l in lines):
                return lines
            limit = int(limit * 0.8)
        return wrap_words85(text, 10)

    def paint(self, p, option, index) -> None:
        from PySide6.QtWidgets import QApplication
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""      # фон/выделение рисует стиль, текст – сами
        widget = opt.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, p,
                          widget)
        fm = opt.fontMetrics
        width = (self._width_px - self.TEXT_PAD_PX) or \
            (opt.rect.width() - self.TEXT_PAD_PX)
        lines = self._lines(text, fm, max(40, width))
        p.save()
        if opt.state & QStyle.StateFlag.State_Selected:
            p.setPen(opt.palette.highlightedText().color())
        else:
            p.setPen(opt.palette.text().color())
        y = opt.rect.top() + max(
            2.0, (opt.rect.height() - len(lines) * fm.height()) / 2.0)
        for ln in lines:
            p.drawText(QRect(opt.rect.left() + 8, int(y),
                             max(40, width), fm.height()),
                       int(Qt.AlignmentFlag.AlignLeft
                           | Qt.AlignmentFlag.AlignVCenter), ln)
            y += fm.height()
        p.restore()

    def sizeHint(self, option, index):
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        fm = option.fontMetrics
        lines = self._lines(text, fm, self._width_px - self.TEXT_PAD_PX)
        w = max((fm.horizontalAdvance(l) for l in lines), default=0)
        return QSize(w + self.TEXT_PAD_PX, len(lines) * fm.height() + 6)


def _popup_target_width(cb: QComboBox, lv: QListView,
                        delegate: PopupWrapDelegate) -> int:
    """Задача 11.3 (шов для тестов): целевая ширина разворота – самый
    длинный пункт (после переноса ≤85 символов), потолок – 85 символов,
    низ – ширина кнопки; закрытая кнопка свою ширину не меняет."""
    fm = lv.fontMetrics()
    widest = 0
    for i in range(cb.count()):
        for ln in delegate._lines(cb.itemText(i), fm, 0):
            widest = max(widest, fm.horizontalAdvance(ln))
    cap = fm.horizontalAdvance("А" * COMBO_POPUP_CHARS) + _POPUP_PAD_PX
    want = widest + _POPUP_PAD_PX
    return int(max(cb.width(), min(want, cap)))


def _patched_show_popup(cb: QComboBox, lv: QListView,
                        delegate: PopupWrapDelegate):
    orig = cb.showPopup

    def popup():
        width = _popup_target_width(cb, lv, delegate)
        delegate._width_px = width
        lv.setMinimumWidth(width)
        orig()
    return popup


def HLine() -> QFrame:
    """Едва уловимая горизонтальная разделительная линия между блоками."""
    line = QFrame()
    # плоская линия: заливка 1px, без рамок (QFrame.HLine стилем рисуется
    # ненадёжно – используем background-color)
    line.setStyleSheet(f"background-color: {BORDER}; border: none;")
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Policy.Expanding,
                       QSizePolicy.Policy.Fixed)
    return line


def section_header(text: str, rich: bool = False) -> QLabel:
    """Заголовок блока свойств (капс, приглушённый цвет); rich=True –
    текст уже размечен (формулы math_html)."""
    lab = QLabel(text if rich else math(text))
    lab.setObjectName("caption")
    lab.setWordWrap(True)
    return lab


class HtmlDelegate(QAbstractItemDelegate):
    """Делегат таблиц: рисует ячейку как HTML (поддержка индексов/степеней
    из math_html) с переносом по словам; редактирование не меняется."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = QTextDocument(self)

    def paint(self, p, option, index) -> None:
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QStyle
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        opt = option.widget.style().visualRect(
            option.direction, option.rect, option.rect)
        self._doc.setDefaultFont(
            index.data(Qt.ItemDataRole.FontRole) or QFont(option.font))
        self._doc.setHtml(str(text))
        self._doc.setTextWidth(max(20.0, option.rect.width() - 8))
        p.save()
        p.translate(option.rect.topLeft())
        if option.state & QStyle.StateFlag.State_Selected:
            p.fillRect(option.rect, option.palette.highlight())
            p.setPen(option.palette.highlightedText().color())
        else:
            p.setPen(option.palette.text().color())
        y = (option.rect.height()
             - self._doc.size().height()) / 2.0
        p.translate(4, max(0.0, y))
        self._doc.drawContents(p)
        p.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        self._doc.setHtml(str(text))
        self._doc.setTextWidth(max(20.0, option.rect.width() - 8))
        from PySide6.QtCore import QSize
        return QSize(int(option.rect.width()),
                     int(self._doc.size().height()) + 8)
