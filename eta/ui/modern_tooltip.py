"""Современные анимированные всплывающие подсказки (сессия 9, Задача 2).

СКЕЛЕТ ЗА ФЛАГОМ: модуль не подключается в main.py, пока не получены
ответы на вопросы сессии; установка – явным вызовом
``install_modern_tooltips(app)`` (или переменной окружения
``KUJI_MODERN_TOOLTIPS=1`` в будущем подключении).

Архитектура (один компонент на всё приложение, без аллокации на каждый
hover):
  * ``ModernTooltip`` – ЕДИНЫЙ QWidget-«окно» подсказки
    (Qt.WindowFlags.ToolTip | FramelessWindowHint, WA_TranslucentBackground,
    WA_ShowWithoutActivating, прозрачный для мыши). Рисует тёмную
    полупрозрачную панель (slate ~#0F1219, 95 %), скругление 10 px,
    1px-рамка ACCENT + мягкое свечение; контент – QTextDocument
    (перенос по словам, ограниченная ширина, рост ВНИЗ);
  * ``TooltipController`` – прикладной фильтр событий на QApplication
    (сильная ссылка – грабли GC из scroll.py): Enter/Leave, dwell-таймер
    400 мс, перенацеливание без мерцания, авто-скрытие по клику/скрытию
    виджета; читает ТОТ ЖЕ источник данных ``widget.toolTip()`` –
    содержимое вызовов setToolTip не переписывается;
  * анимации – QPropertyAnimation (opacity) + QVariantAnimation (pos):
    появление 150 мс OutCubic (fade 0→0,95 + подъём 8 px), скрытие 100 мс;
    под offscreen (QT_QPA_PLATFORM=offscreen) или флагом KUJI_NO_ANIMATION
    – мгновенное показывание в конечном состоянии (шов для тестов);
  * программный показ для холста (пины/валидатор/домино) –
    ``controller.show_tip(...)`` / модульная функция ``scene_tip(...)``:
    без dwell-задержки (это обратная связь, а не hover).

Классификация строк контента (стилизация без изменения текста БД):
первая непустая строка – заголовок (полужирный, крупнее); строки
«Источник: …» – приглушённые; «формульные» строки (содержат «=» и
математические символы λ/·/×/∏/Σ/Q/P/F) – моноширинные с левым
акцентным бордюром. Уже готовый HTML (<b>, <br>, <sub>/<sup> из math())
проходит как есть – без двойного экранирования.

Обычный QToolTip (блок QSS) остаётся резервным путём для всего, что ещё
не маршрутизировано через контроллер.
"""

from __future__ import annotations

import os
import re

from PySide6.QtCore import (QEasingCurve, QEvent, QObject, QPointF, QRectF,
                            Qt, QTimer, QPropertyAnimation)
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetricsF, QPainter,
                           QPainterPath, QPen)
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication, QWidget

from .math_text import math
from .theme import ACCENT, FONT_STACK_MONO, FONT_STACK_UI

# ---------- константы визуального языка (единый источник) ----------
TIP_BG = QColor(15, 18, 25, 242)          # тёмный slate, ~95 % непрозрачности
TIP_BORDER = QColor(ACCENT)               # 1px рамка – проектный акцент
TIP_GLOW = QColor(37, 99, 235, 60)        # мягкое свечение вокруг рамки
TIP_RADIUS = 10.0                         # скругление панели
TIP_PAD = 10.0                            # внутренние поля
TIP_MAX_W = 560.0                         # ограниченная ширина (рост вниз)
TIP_WRAP_CHARS = 85                       # максимум символов в строке (Задача 3)
TIP_MIN_CHARS = 24                        # минимальная ширина ≈ 24 символа + поля
TIP_OFFSET = QPointF(15.0, 15.0)          # сдвиг от курсора
TIP_SLIDE_PX = 8.0                        # подъём при появлении
TIP_OPACITY = 0.95                        # конечная непрозрачность
DWELL_MS = 400                            # задержка перед показом (hover)
FADE_IN_MS = 150                          # появление
FADE_OUT_MS = 100                         # скрытие

# формульные признаки: «=» И математический символ (мини-нотация/Unicode)
_RE_FORMULA = re.compile(r"[=≈]")
_RE_MATH_CHAR = re.compile(r"[λΣ∏η·×±≤≥^_]")
_RE_SOURCE = re.compile(r"^\W*Источник\b", re.IGNORECASE)


def animations_disabled() -> bool:
    """Мгновенный режим: offscreen-платформа или флаг KUJI_NO_ANIMATION
    (шов тестируемости – утверждения не зависят от таймеров)."""
    if os.environ.get("KUJI_NO_ANIMATION"):
        return True
    p = os.environ.get("QT_QPA_PLATFORM", "")
    return "offscreen" in p


def _strip_html(line: str) -> str:
    """Текст строки без тегов (для классификации)."""
    return re.sub(r"<[^>]+>", "", line)


def classify_line(line: str, is_first: bool) -> str:
    """Класс строки контента: header | source | formula | text.

    Классификация только по ВИДИМОМУ тексту – исходный HTML строки
    (в т.ч. <sub>/<sup> из math()) сохраняется как есть.
    """
    plain = _strip_html(line).strip()
    if not plain:
        return "text"
    if is_first:
        return "header"
    if _RE_SOURCE.match(plain):
        return "source"
    if _RE_FORMULA.search(plain) and _RE_MATH_CHAR.search(plain):
        return "formula"
    return "text"


def _looks_like_html(text: str) -> bool:
    """Строка уже является rich text (QToolTip-стиль вызовов setToolTip)?"""
    return bool(re.search(r"<\s*(b|br|i|sub|sup|u|span|code|em|strong)[\s>/]",
                          text, re.IGNORECASE))


# ---------------- Задача 3 (сессия 12): перенос строк подсказки ----------
# Задача 7 (сессия 13): слоговое разбиение и перенос по словам ВЫНЕСЕНЫ
# в controls.wrap_words85/split_long_word – единая реализация для
# подсказок и таблиц окна БД (здесь – тонкие обертки для совместимости)
from .controls import split_long_word as _split_long_word
from .controls import wrap_words85 as wrap_tip_line


def _wrap_rich_line(line: str, width: int = TIP_WRAP_CHARS) -> str:
    """Перенос rich-строки (HTML) по целым словам ≤ width символов
    видимого текста. Разрывы – только на пробелах; открытые inline-теги
    закрываются перед <br> и переоткрываются на следующей строке."""
    if len(_strip_html(line).strip()) <= width:
        return line
    # один проход: для каждого пробела – индекс в html и открытые теги
    spaces: list[tuple[int, list[tuple[str, str]]]] = []  # (idx, [(имя, тег)])
    open_tags: list[tuple[str, str]] = []
    word_lens: list[int] = []
    cur_word = 0
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "<":
            j = line.find(">", i)
            if j == -1:
                cur_word += 1          # одиночная «<» – считаем символом
                i += 1
                continue
            tag = line[i:j + 1]
            m = re.match(r"</?\s*([A-Za-z]+)", tag)
            nm = m.group(1).lower() if m else ""
            if tag.startswith("</"):
                for k in range(len(open_tags) - 1, -1, -1):
                    if open_tags[k][0] == nm:
                        open_tags.pop(k)
                        break
            elif not tag.endswith("/>") and nm not in ("br", "hr", "img"):
                open_tags.append((nm, tag))
            i = j + 1
            continue
        if ch == " ":
            word_lens.append(cur_word)
            spaces.append((i, list(open_tags)))
            cur_word = 0
        else:
            cur_word += 1
        i += 1
    if cur_word:
        word_lens.append(cur_word)
        spaces.append((-1, list(open_tags)))   # хвостовой маркер
    # жадный перенос по длинам слов (учёт пробела +1); разрыв – на
    # пробеле ПЕРЕ словом, которое не помещается (spaces[k-1] – пробел
    # после предыдущего слова)
    breaks: list[int] = []
    cur = -1
    for k, w in enumerate(word_lens):
        cand = w if cur < 0 else cur + 1 + w
        if cur >= 0 and cand > width and k >= 1 and spaces[k - 1][0] >= 0:
            breaks.append(spaces[k - 1][0])
            cur = w
        else:
            cur = cand
    out = line
    for idx, tags in reversed(
            [spaces[i2] for i2 in range(len(spaces)) if spaces[i2][0] in breaks]):
        close = "".join(f"</{nm}>" for nm, _ in reversed(tags))
        reopen = "".join(full for _, full in tags)
        out = out[:idx] + close + "<br>" + reopen + out[idx + 1:]
    return out


def compose_tip_html(raw: str) -> str:
    """Собрать HTML подсказки из исходной строки ``toolTip()``.

    * готовый HTML – построчный перенос по словам (Задача 3, ≤85
      символов видимого текста) без изменения разметки, затем
      классификация;
    * обычный текст (в т.ч. мини-нотация) – перенос по словам ≤85
      символов (слово длиннее строки – по слогам с «–»), затем ``math()``
      построчно и классификация.
    """
    if _looks_like_html(raw):
        lines = re.split(r"(?i)<br\s*/?>", raw)
        body = "<br>".join(
            (_wrap_rich_line(ln) if _strip_html(ln).strip() else ln)
            for ln in lines)
    else:
        wrapped: list[str] = []
        for ln in raw.split("\n"):
            wrapped.extend(wrap_tip_line(ln))
        body = "<br>".join(math(t) for t in wrapped)
    lines = re.split(r"(?i)<br\s*/?>", body)
    out: list[str] = []
    seen_content = False
    for ln in lines:
        kind = classify_line(ln, not seen_content)
        if _strip_html(ln).strip():
            seen_content = True
        if kind == "header":
            out.append(
                f'<span style="font-size:13px; font-weight:600; color:#F8FAFC">'
                f"{ln}</span>")
        elif kind == "source":
            out.append(
                f'<span style="color:#94A3B8; font-size:11px">{ln}</span>')
        elif kind == "formula":
            # формулы: моноширинно, полужирно, голубым по синему подтону;
            # border-left/padding на inline-элементах Qt rich text НЕ
            # поддерживает – «плашку формулы» даёт background-color
            mono = ", ".join(f"'{f}'" for f in FONT_STACK_MONO)
            out.append(
                f'<span style="font-family: {mono}; font-size:12.5px;'
                f' font-weight:600; color:#93C5FD;'
                f' background-color:#132140">{ln}</span>')
        else:
            out.append(f'<span style="color:#CBD5E1; font-size:12px">{ln}</span>')
    return "<br>".join(out)


class ModernTooltip(QWidget):
    """Единое окно подсказки: тёмная панель + QTextDocument-контент."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip
                            | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                          True)
        self._doc = QTextDocument(self)
        self._doc.setDefaultFont(self._base_font())
        self._html = ""
        self._content_w = TIP_MAX_W    # выбранная ширина текста (Задача 3)
        self._anim_opacity: QPropertyAnimation | None = None
        self._anim_pos: QVariantAnimation | None = None
        self._final_pos = QPointF()

    # ---------- контент ----------
    @staticmethod
    def _base_font() -> QFont:
        f = QFont()
        f.setFamilies(FONT_STACK_UI)
        f.setPixelSize(12)
        return f

    def set_content(self, raw: str) -> None:
        """Разметить контент ОДИН раз на показ (тяжёлый rich text)."""
        self.apply_html(compose_tip_html(raw))

    def apply_html(self, html: str) -> None:
        """Применить ГОТОВЫЙ html с адаптивной шириной (Задача 3).

        Ширина пузыря подстраивается под текст: идеальная ширина строк
        (без переноса), но не меньше ≈ поля + 24 символа и не больше
        TIP_MAX_W; текст заранее перенесён по словам ≤85 символов."""
        self._html = html
        self._doc.setHtml(html)
        self._doc.setTextWidth(-1.0)
        ideal = self._doc.idealWidth()
        fm = QFontMetricsF(self._base_font())
        min_content = fm.averageCharWidth() * TIP_MIN_CHARS
        self._content_w = max(0.0, min(max(ideal, min_content), TIP_MAX_W))
        self._doc.setTextWidth(self._content_w)
        size = self._doc.size()
        self.resize(int(size.width() + 2 * TIP_PAD),
                    int(size.height() + 2 * TIP_PAD))

    def content_html(self) -> str:
        """Собранный HTML (для тестов)."""
        return self._html

    # ---------- показ/скрытие с анимацией ----------
    def place_near(self, global_pos: QPointF, instant: bool | None = None) -> None:
        """Позиция +15/+15 от курсора с клампом к границам экрана,
        рост вниз ограниченной ширины."""
        instant = animations_disabled() if instant is None else instant
        pos = global_pos + TIP_OFFSET
        screen = QApplication.screenAt(pos.toPoint())
        if screen is None:
            screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else None
        w, h = self.width(), self.height()
        if avail is not None:
            if pos.x() + w > avail.right():
                pos.setX(max(avail.left(), global_pos.x() - w - TIP_OFFSET.x()))
            if pos.y() + h > avail.bottom():
                pos.setY(max(avail.top(), global_pos.y() - h - TIP_OFFSET.y()))
        self._final_pos = pos
        if instant:
            self.move(pos.toPoint())
            return
        # лёгкий подъём при появлении: от конечной точки вверх на TIP_SLIDE_PX
        start = QPointF(pos.x(), pos.y() - TIP_SLIDE_PX)
        self.move(start.toPoint())

    def show_animated(self, instant: bool | None = None) -> None:
        """Показ: fade 0→0,95 (+подъём уже применён в place_near)."""
        instant = animations_disabled() if instant is None else instant
        if instant:
            self._stop_anims()
            self.setWindowOpacity(TIP_OPACITY)
            self.show_instantly()
            return
        self._stop_anims()
        self.setWindowOpacity(0.0)
        self.show()
        self._anim_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_opacity.setDuration(FADE_IN_MS)
        self._anim_opacity.setStartValue(0.0)
        self._anim_opacity.setEndValue(TIP_OPACITY)
        self._anim_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_opacity.start()

    def hide_animated(self, instant: bool | None = None) -> None:
        """Скрытие: быстрый fade-out (мгновенно в offscreen-режиме)."""
        instant = animations_disabled() if instant is None else instant
        if instant or not self.isVisible():
            self._stop_anims()
            self.hide()
            return
        self._stop_anims()
        self._anim_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_opacity.setDuration(FADE_OUT_MS)
        self._anim_opacity.setStartValue(self.windowOpacity())
        self._anim_opacity.setEndValue(0.0)
        self._anim_opacity.finished.connect(self.hide)
        self._anim_opacity.start()

    def show_instantly(self) -> None:
        """Шов для тестов: показать в конечном состоянии немедленно."""
        self._stop_anims()
        self.setWindowOpacity(TIP_OPACITY)
        self.show()

    def _stop_anims(self) -> None:
        for anim in (self._anim_opacity, self._anim_pos):
            if anim is not None:
                anim.stop()
        self._anim_opacity = None
        self._anim_pos = None

    # ---------- отрисовка ----------
    def paintEvent(self, e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(TIP_PAD / 2, TIP_PAD / 2,
                   self.width() - TIP_PAD, self.height() - TIP_PAD)
        # мягкое свечение: широкая полупрозрачная рамка под основной
        p.setPen(QPen(TIP_GLOW, 3.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, TIP_RADIUS, TIP_RADIUS)
        # панель
        path = QPainterPath()
        path.addRoundedRect(r, TIP_RADIUS, TIP_RADIUS)
        p.fillPath(path, TIP_BG)
        p.setPen(QPen(TIP_BORDER, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, TIP_RADIUS, TIP_RADIUS)
        # контент
        p.translate(TIP_PAD, TIP_PAD)
        self._doc.setTextWidth(self._content_w)
        self._doc.drawContents(p)


class TooltipController(QObject):
    """Прикладной hover-контроллер: фильтр на QApplication.

    Читает ``widget.toolTip()`` при наведении (источник данных не
    меняется), держит dwell-таймер, перенацеливает единый ModernTooltip
    без мерцания и прячет его по Leave/клику/скрытию виджета.
    """

    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)
        self._app = app
        self.tip = ModernTooltip()
        self._hover_widget: QWidget | None = None
        self._dwell = QTimer(self)
        self._dwell.setSingleShot(True)
        self._dwell.setInterval(DWELL_MS)
        self._dwell.timeout.connect(self._show_for_hover)
        self._autohide = QTimer(self)
        self._autohide.setSingleShot(True)
        self._autohide.timeout.connect(self.hide_tip)
        # кэш собранного HTML: ключ (id виджета, хэш текста)
        self._cache: dict[tuple[int, int], str] = {}
        app.installEventFilter(self)

    # ---------- фильтр ----------
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        et = event.type()
        if et == QEvent.Type.ToolTip:
            # системный QToolTip подавлен: показываем СВОЮ панель и съедаем
            # событие (иначе на экране оказались бы обе подсказки)
            if isinstance(obj, QWidget) and obj is not self.tip:
                self._on_enter(obj)
                event.accept()
                return True
            return False
        if et in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
            if isinstance(obj, QWidget) and obj is not self.tip:
                self._on_enter(obj)
        elif et in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
            if isinstance(obj, QWidget) and obj is self._hover_widget:
                self._on_leave()
        elif et in (QEvent.Type.Hide, QEvent.Type.Close):
            if obj is self._hover_widget:
                self._on_leave()
        elif et in (QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress,
                    QEvent.Type.Wheel):
            if self.tip.isVisible():
                self.hide_tip()
        return False

    def _on_enter(self, widget: QWidget) -> None:
        text = widget.toolTip()
        if not text.strip():
            if self.tip.isVisible():
                self.hide_tip()          # ушли на виджет без подсказки
            self._hover_widget = None
            self._dwell.stop()
            return
        self._hover_widget = widget
        if self.tip.isVisible():
            # перенацеливание БЕЗ мерцания: контент и позицию меняем сразу
            self._apply_content(widget, text)
            self.tip.place_near(QPointF(QCursor.pos()))
            self._restart_autohide(widget)
            return
        self._dwell.start()

    def _on_leave(self) -> None:
        self._hover_widget = None
        self._dwell.stop()
        if self.tip.isVisible():
            self.hide_tip()

    # ---------- показ ----------
    def _apply_content(self, widget: QWidget, text: str) -> None:
        key = (id(widget), hash(text))
        html = self._cache.get(key)
        if html is None:
            html = compose_tip_html(text)
            if len(self._cache) > 256:
                self._cache.clear()
            self._cache[key] = html
        if html != self.tip.content_html():
            # переиспользуем кэш через тот же публичный путь (включая
            # адаптивную ширину пузыря, Задача 3)
            self.tip.apply_html(html)

    def _show_for_hover(self) -> None:
        w = self._hover_widget
        if w is None:
            return
        text = w.toolTip()
        if not text.strip():
            return
        self._apply_content(w, text)
        self.tip.place_near(QPointF(QCursor.pos()))
        self.tip.show_animated()
        self._restart_autohide(w)

    def _restart_autohide(self, widget: QWidget) -> None:
        """toolTipDuration > 0 – точный таймер; -1 (система) – не прячем."""
        d = widget.toolTipDuration()
        if d > 0:
            self._autohide.start(d)
        else:
            self._autohide.stop()

    # ---------- программный показ (холст/сцена) ----------
    def show_tip(self, text: str, global_pos=None, origin: QWidget | None = None,
                 instant: bool = True) -> None:
        """Показать подсказку программно (пины/валидатор/домино).

        Без dwell-задержки: это обратная связь, а не hover. instant=True –
        мгновенно (по умолчанию), иначе с анимацией появления."""
        if not text.strip():
            return
        self._dwell.stop()
        self._apply_content(origin or self.tip, text)
        pos = QPointF(QCursor.pos() if global_pos is None else global_pos)
        self.tip.place_near(pos, instant=instant)
        self.tip.show_animated(instant=instant)
        self._autohide.stop()

    def hide_tip(self, instant: bool | None = None) -> None:
        instant = animations_disabled() if instant is None else instant
        self._autohide.stop()
        self.tip.hide_animated(instant=instant)

    # ---------- состояние для тестов ----------
    def is_visible(self) -> bool:
        return self.tip.isVisible()

    def hover_widget(self) -> QWidget | None:
        return self._hover_widget


# ВНИМАНИЕ (грабли PySide, см. scroll.py): сильная ссылка на контроллер
# обязательна – без неё обёртка собирается GC и фильтр «молча» умирает.
_ACTIVE: TooltipController | None = None


def install_modern_tooltips(app: QApplication) -> TooltipController:
    """Установить контроллер подсказок на приложение (идемпотентно).

    Подключение – явный вызов (main.py после ответов сессии) или
    KUJI_MODERN_TOOLTIPS=1; скелет сессии 9 НЕ включает себя сам.
    """
    global _ACTIVE
    if _ACTIVE is not None:
        return _ACTIVE
    _ACTIVE = TooltipController(app)
    return _ACTIVE


def active_controller() -> TooltipController | None:
    """Текущий контроллер (или None – не установлен)."""
    return _ACTIVE


def scene_tip(global_pos, text: str, widget: QWidget | None = None) -> None:
    """Адаптер сцены/холста: замена QToolTip.showText (Задача 2.4).

    ЕДИНСТВЕННОЕ место репозитория, где допустим вызов QToolTip.showText –
    резервный путь, когда контроллер не установлен (скелет/тесты без
    установки). Показ мгновенный: это обратная связь, а не hover."""
    ctrl = _ACTIVE
    if ctrl is not None:
        ctrl.show_tip(text, global_pos=global_pos, origin=widget)
        return
    from PySide6.QtWidgets import QToolTip
    QToolTip.showText(global_pos, text, widget)


def hide_scene_tip() -> None:
    """Скрыть подсказку холста (замена QToolTip.hideText)."""
    ctrl = _ACTIVE
    if ctrl is not None:
        ctrl.hide_tip(instant=True)
        return
    from PySide6.QtWidgets import QToolTip
    QToolTip.hideText()
