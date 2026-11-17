"""Переиспользуемые жесты QGraphicsView: единая матрица управления
рабочим вьюпортом (TreeCanvas) и окном документа (DocumentView).

  колесо (без модификаторов) – ПЛАВНЫЙ зум к точке под курсором:
      6 микрошагов × 1.035 за 130 мс (≈ ×1.23 за щелчок), клампы 0.05…8.0;
  СКМ + движение – панорама XY (ClosedHandCursor), зум не сбивается.

Якорь зума реализован вручную (setTransform + компенсация ползунками):
точка сцены под курсором остаётся под курсором. Такой якорь работает
одинаково и со скрытыми ползунками вьюпорта, и с обычными ползунками
окна документа, и в offscreen-тестах с синтетическими событиями
(встроенный AnchorUnderMouse опирается на глобальную позицию курсора и
в offscreen бесполезен). Поэтому transformationAnchor вида миксин
принудительно ставит в NoAnchor – иначе якорь компенсируется дважды.

Подключение:

    class MyView(ViewportGestures, QGraphicsView):
        def __init__(...):
            super().__init__(...)
            self._init_gestures()

        def wheelEvent(self, e):
            self._gesture_wheel(e)          # зум к курсору

        def mousePressEvent(self, e):
            if self._gesture_mouse_press(e):    # СКМ – панорама
                return
            ...                                  # своя логика ЛКМ/ПКМ

        def mouseMoveEvent(self, e):
            if self._gesture_mouse_move(e):
                return
            ...

        def mouseReleaseEvent(self, e):
            if self._gesture_mouse_release(e):
                return
            ...
"""

from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QVariantAnimation
from PySide6.QtGui import QMouseEvent, QTransform
from PySide6.QtWidgets import QGraphicsView, QScroller

# плавный зум: 6 микрошагов по 1.035 за 130 мс → ~1.23 за щелчок колеса
ZOOM_STEPS = 6
ZOOM_PER_STEP = 1.035
ZOOM_MS = 130
MIN_SCALE, MAX_SCALE = 0.05, 8.0

# сенсорные жесты (Задача 5)
TOUCH_TAP_SLOP_PX = 12      # перемещение больше – это панорама, не тап
TOUCH_TAP_MS = 500          # дольше – это удержание, не тап
TOUCH_DOUBLE_TAP_MS = 350   # окно двойного тапа
TOUCH_DOUBLE_TAP_PX = 24

# совместимость: константа порога перетаскивания осталась в canvas.py


class ViewportGestures:
    """Миксин для QGraphicsView: плавный зум к курсору + СКМ-панорама.

    Не наследует QObject – подмешивается к QGraphicsView:

        class TreeCanvas(ViewportGestures, QGraphicsView): ...
    """

    # ---------- подключение ----------
    def _init_gestures(self) -> None:
        self._zoom_anim: QVariantAnimation | None = None
        self._zoom_anchor: QPointF | None = None
        self._pan_origin: QPoint | None = None
        # якорь зума считаем сами – встроенный должен быть выключен
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        # ---------- сенсорные жесты (Задача 5) ----------
        self._pinch_last: float | None = None
        self._touch_begin_pos: QPointF | None = None
        self._touch_begin_t: float = 0.0
        self._touch_moved: bool = False
        self._last_tap_t: float = 0.0
        self._last_tap_pos: QPointF = QPointF(-1e9, -1e9)
        # пинч-зум: жест перехватывается на самом view (event())
        self.grabGesture(Qt.GestureType.PinchGesture)
        # панорама пальцем с флик-инерцией: QScroller по касанию
        QScroller.grabGesture(self, QScroller.ScrollerGestureType.TouchGesture)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

    # ---------- сенсор: пинч-зум ----------
    def event(self, e) -> bool:
        if e.type() == QEvent.Type.Gesture and self._gesture_event(e):
            return True
        return super().event(e)

    def _gesture_event(self, e) -> bool:
        pinch = e.gesture(Qt.GestureType.PinchGesture)
        if pinch is None:
            return False
        e.accept(QEvent.Type.Gesture)
        if pinch.state() in (Qt.GestureState.GestureFinished,
                             Qt.GestureState.GestureCanceled):
            self.end_pinch()
        else:
            # centerPoint – в координатах view; якорь нужен в координатах вьюпорта
            vp = self.viewport().pos()
            self.apply_pinch(pinch.scaleFactor(),
                             QPointF(pinch.centerPoint().x() - vp.x(),
                                     pinch.centerPoint().y() - vp.y()))
        return True

    def apply_pinch(self, scale_factor: float, anchor_vp: QPointF) -> None:
        """Зум по параметрам QPinchGesture.

        scale_factor – суммарный масштаб от НАЧАЛА жеста; зум применяем
        отношением к предыдущему значению. Якорь – центр пинча: точка сцены
        под центром остаётся на месте.
        """
        base = self._pinch_last if self._pinch_last else 1.0
        ratio = (scale_factor / base) if base else 1.0
        self._pinch_last = scale_factor
        if abs(ratio - 1.0) < 1e-6:
            return
        self._zoom_anchor = QPointF(anchor_vp)
        try:
            self._zoom_step(self.transform().m11() * ratio)
        finally:
            self._zoom_anchor = None

    def end_pinch(self) -> None:
        """Завершение пинча: следующее касание начинает масштаб заново."""
        self._pinch_last = None

    # ---------- сенсор: тап = клик, панорама – QScroller ----------
    def viewportEvent(self, e) -> bool:
        t = e.type()
        if t in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate,
                 QEvent.Type.TouchEnd) and self._touch_event(e):
            return True
        return super().viewportEvent(e)

    def _touch_event(self, e) -> bool:
        """Одно касание: тап → клик (выбор), движение – панорама QScroller'а
        (он перехватывает касание раньше, и тогда сюда события не доходят).
        Два пальца – пинч (обрабатывается gesture-событием)."""
        pts = e.points()
        if len(pts) != 1:
            self._touch_moved = True      # мультитач – тапа не будет
            return False
        p = QPointF(pts[0].position())
        t = e.type()
        if t == QEvent.Type.TouchBegin:
            self._touch_begin_pos = QPointF(p)
            self._touch_begin_t = time.time()
            self._touch_moved = False
            e.accept()
            return True
        if self._touch_begin_pos is None:
            return False
        if t == QEvent.Type.TouchUpdate:
            if (p - self._touch_begin_pos).manhattanLength() > TOUCH_TAP_SLOP_PX:
                self._touch_moved = True
            e.accept()
            return True
        # TouchEnd
        tap = (not self._touch_moved
               and time.time() - self._touch_begin_t < TOUCH_TAP_MS)
        self._touch_begin_pos = None
        e.accept()
        if tap:
            self._emulate_tap(p)
        return True

    def _emulate_tap(self, local: QPointF) -> None:
        """Тап = клик ЛКМ; двойной тап – двойной клик (Задача 5)."""
        now = time.time()
        double = (now - self._last_tap_t < TOUCH_DOUBLE_TAP_MS
                  and (local - self._last_tap_pos).manhattanLength()
                  < TOUCH_DOUBLE_TAP_PX)
        self._last_tap_t, self._last_tap_pos = now, QPointF(local)
        press_type = (QEvent.Type.MouseButtonDblClick if double
                      else QEvent.Type.MouseButtonPress)
        g = local + QPointF(1, 1)
        press = QMouseEvent(press_type, local, g, Qt.MouseButton.LeftButton,
                            Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
        self.mousePressEvent(press)
        release = QMouseEvent(QEvent.Type.MouseButtonRelease, local, g,
                              Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                              Qt.KeyboardModifier.NoModifier)
        self.mouseReleaseEvent(release)

    # ---------- плавный зум колесом ----------
    def _gesture_wheel(self, e) -> None:
        """Колесо без модификаторов → плавный зум к точке под курсором."""
        e.accept()
        d = e.angleDelta().y()
        if d == 0:
            return
        total = ZOOM_PER_STEP ** (ZOOM_STEPS if d > 0 else -ZOOM_STEPS)
        self._animate_zoom(total, QPointF(e.position()))

    def _animate_zoom(self, total: float, anchor: QPointF | None = None) -> None:
        """Анимация смены масштаба в `total` раз от текущего.

        `anchor` – точка вьюпорта, которая остаётся на месте (под курсором).
        """
        if self._zoom_anim is not None:
            self._zoom_anim.stop()
            self._zoom_anim.deleteLater()
            self._zoom_anim = None
        start = self.transform().m11()
        self._zoom_anchor = anchor
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(ZOOM_MS)

        def on_step(progress: float) -> None:
            self._zoom_step(start * (total ** progress))

        anim.valueChanged.connect(on_step)
        anim.finished.connect(self._zoom_finished)
        self._zoom_anim = anim
        anim.start()

    def _zoom_step(self, target: float) -> None:
        if not (MIN_SCALE <= target <= MAX_SCALE):
            return
        cur = self.transform().m11()
        if cur == 0.0 or abs(target - cur) < 1e-12:
            return
        anchor = self._zoom_anchor
        if anchor is None:
            self.setTransform(QTransform().scale(target, target))
        else:
            # якорь: точка сцены под курсором остаётся под курсором.
            # ползунки QGraphicsView двигают контент 1:1 в пикселях вьюпорта:
            # чтобы точка уехала ЛЕВЕЕ (now правее anchor), скроллим вправо.
            sp = QPointF(self.mapToScene(anchor.toPoint()))
            self.setTransform(QTransform().scale(target, target))
            now = QPointF(self.mapFromScene(sp))
            hbar, vbar = self.horizontalScrollBar(), self.verticalScrollBar()
            hbar.setValue(hbar.value() + int(round(now.x() - anchor.x())))
            vbar.setValue(vbar.value() + int(round(now.y() - anchor.y())))
        self._zoom_applied(target)

    def _zoom_finished(self) -> None:
        if self._zoom_anim is not None:
            self._zoom_anim.deleteLater()
            self._zoom_anim = None
        self._zoom_anchor = None

    def _zoom_applied(self, scale: float) -> None:
        """Хук подкласса: масштаб изменился жестом (не fit-режимом).

        Например, DocumentView помечает масштаб «ручным» для QSettings.
        """

    # ---------- СКМ-панорама ----------
    def _gesture_mouse_press(self, e) -> bool:
        """СКМ – начать панораму. True, если событие обработано."""
        if e.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = e.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()
            return True
        return False

    def _gesture_mouse_move(self, e) -> bool:
        """Движение с зажатой СКМ – панорама XY. True, если обработано."""
        if self._pan_origin is None:
            return False
        pos = e.position().toPoint()
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - (pos.x() - self._pan_origin.x()))
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() - (pos.y() - self._pan_origin.y()))
        self._pan_origin = pos
        e.accept()
        return True

    def _gesture_mouse_release(self, e) -> bool:
        """Отпущена СКМ – завершить панораму. True, если обработано."""
        if (e.button() == Qt.MouseButton.MiddleButton
                and self._pan_origin is not None):
            self.viewport().unsetCursor()
            self._pan_origin = None
            e.accept()
            return True
        return False
