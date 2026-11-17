"""Скролл во всех окнах приложения: колесо – ВЕРТИКАЛЬ с плавной
анимацией (сессия 10.1, §13), Shift+колесо – горизонталь (Задача 7).

Исключения – зумящиеся вьюпорты (рабочий холст TreeCanvas и окно
документа DocumentView): у них колесо = плавный зум к курсору, а
Shift+колесо в окне документа уже работает как горизонталь сам по себе.

Установка (после создания QApplication, до показа окон):

    from eta.ui.scroll import install_scroll_wide
    install_scroll_wide(app)
"""

from __future__ import annotations

from PySide6.QtCore import (QEasingCurve, QEvent, QObject, Qt,
                            QVariantAnimation)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication,
                               QScrollBar, QWidget)

# Сессия 12, Задача 8: горизонтальная прокрутка колесом – ТА ЖЕ плавная
# анимация, что и вертикальная (SMOOTH_NOTCH_PX пикселей на дискрету).
SMOOTH_MS = 150            # длительность плавной прокрутки
SMOOTH_NOTCH_PX = 60       # базовый пиксельный шаг на дискрету колеса


def _owner_scroll_area(obj: QObject) -> QAbstractScrollArea | None:
    """Область прокрутки, которой принадлежит получатель события.

    События Wheel приходят на viewport() области (дочерний виджет),
    реже – на саму область.
    """
    if isinstance(obj, QAbstractScrollArea):
        return obj
    if isinstance(obj, QWidget):
        parent = obj.parentWidget()
        if isinstance(parent, QAbstractScrollArea):
            return parent
    return None


class ScrollWideFilter(QObject):
    """Приложенческий фильтр: плавное колесо (вертикаль) и
    Shift+колесо (горизонталь) везде, кроме зумящихся вьюпортов."""

    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)
        self._app = app
        app.installEventFilter(self)
        # анимации плавной прокрутки (ползунок → QVariantAnimation);
        # сильные ссылки обязательны (грабли PySide GC)
        self._smooth: dict[int, tuple[QVariantAnimation, float, float]] = {}

    # ---------- плавная вертикальная прокрутка ----------
    def _smooth_scroll(self, bar: QScrollBar, delta: float) -> None:
        key = id(bar)
        running = self._smooth.get(key)
        if running is not None:
            anim, _s, _t = running
            start = float(bar.value())
            anim.stop()
        else:
            start = float(bar.value())
        lo, hi = float(bar.minimum()), float(bar.maximum())
        target = max(lo, min(hi, start - (delta / 120.0) * SMOOTH_NOTCH_PX))
        if abs(target - start) < 0.5:
            return
        anim = QVariantAnimation(self)
        anim.setDuration(SMOOTH_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def _apply(v, bar=bar, s=start, t=target):
            bar.setValue(int(round(s + (t - s) * float(v))))

        anim.valueChanged.connect(_apply)
        anim.finished.connect(lambda: self._smooth.pop(key, None))
        self._smooth[key] = (anim, start, target)
        anim.start()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() != QEvent.Type.Wheel:
            return False
        area = _owner_scroll_area(obj)
        if area is None:
            return False
        # зумящиеся вьюпорты не трогаем: холст и окно документа
        # обрабатывают колесо сами (зум / своя горизонталь)
        cname = type(area).__name__
        if cname in ("TreeCanvas", "DocumentView"):
            return False

        dy = event.angleDelta().y()
        dx = event.angleDelta().x()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            hbar = area.horizontalScrollBar()
            delta = dy if dy != 0 else dx
            if delta == 0:
                return False
            if hbar.maximum() > hbar.minimum():
                # Задача 8 (сессия 12): плавная попиксельная горизонталь –
                # та же анимация, что у вертикали (промежуточные пиксели)
                self._smooth_scroll(hbar, delta)
            else:
                # горизонтального диапазона нет – прокручиваем вертикаль,
                # чтобы курсор над областью не «замолкал»
                vbar = area.verticalScrollBar()
                if vbar.maximum() <= vbar.minimum():
                    return False
                self._smooth_scroll(vbar, delta)
            event.accept()
            return True

        # обычное колесо: плавная вертикальная прокрутка (§13)
        if dy == 0 or dy is None:
            return False
        vbar = area.verticalScrollBar()
        if vbar.maximum() <= vbar.minimum():
            return False
        self._smooth_scroll(vbar, dy)
        event.accept()
        return True


# ВНИМАНИЕ (грабли PySide): сильная ссылка на Python-объект фильтра
# обязательна – без неё обёртка собирается GC, C++-объект переживает
# (родитель – приложение), а переопределённый eventFilter перестаёт
# вызываться: фильтр «молча» умирает.
_ACTIVE_FILTER: ScrollWideFilter | None = None


def install_scroll_wide(app: QApplication) -> ScrollWideFilter:
    """Установить скролл-фильтр на приложение (идемпотентно)."""
    global _ACTIVE_FILTER
    if _ACTIVE_FILTER is not None:
        return _ACTIVE_FILTER
    _ACTIVE_FILTER = ScrollWideFilter(app)
    return _ACTIVE_FILTER
