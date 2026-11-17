"""Страница «Схематический вид» панели «Документ» (pop-out окно, сессия 8):
лист документа (шапка эшелонов + сетка колонок + дерево) с той же матрицей
жестов, что и рабочий вьюпорт.

Управление (только внутри этого окна; окно read-only – правки лишь
в рабочем вьюпорте):
  колесо          – плавный зум к точке под курсором (миксин
                    ViewportGestures: 6 микрошагов × 1.035, 130 мс,
                    клампы 0.05…8.0);
  СКМ + движение  – панорама XY (ClosedHandCursor), зум не сбивается;
  Shift+колесо    – горизонтальная прокрутка (бонус);
  ползунки        – стандартные QScrollBar (низ + право, AsNeeded) –
                    вспомогательный орган;
  ЛКМ/ПКМ         – окно не редактирует и не выбирает.

«Вписать по ширине» (кнопка в шапке окна) и начальный вписанный масштаб
сохраняются; после ручного зума изменение размеров окна НЕ пере-вписывает
лист. PDF-экспорт по-прежнему берёт doc_scene – WYSIWYG не меняется.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QTransform
from PySide6.QtWidgets import QGraphicsView

from .canvas import TreeCanvasController
from .gestures import MAX_SCALE, MIN_SCALE, ViewportGestures
from .theme import APP_BG

_WHEEL_NOTCH_STEPS = 3  # «строк» прокрутки на один щелчок (Shift+колесо)


class DocumentView(ViewportGestures, QGraphicsView):
    """Представление doc_scene: тот же layout, что и в рабочем вьюпорте
    (правки узлов отражаются мгновенно), но свой transform и прокрутка."""

    # масштаб перешёл в «fit» или «ручной» (для памяти интерфейса, Задача 4)
    scale_mode_changed = Signal()

    def __init__(self, controller: TreeCanvasController, parent=None):
        super().__init__(controller.doc_scene, parent)
        self.controller = controller

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setRenderHints(QPainter.RenderHint.Antialiasing |
                            QPainter.RenderHint.TextAntialiasing)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setBackgroundBrush(QBrush(QColor(APP_BG)))
        self.setStyleSheet(
            "QGraphicsView { border: 1px solid #CBD5E1; background: #F8FAFC; }")
        # колесо – плавный зум к курсору, СКМ – панорама (как во вьюпорте)
        self._init_gestures()

        self._fitted_width: float | None = None
        self._fit_scale: float | None = None   # точный k последнего fit_width
        self._pending_fit = True
        # «ручной» масштаб (после зума колесом) – не пере-вписывать
        self._manual_scale = False

    # ---------- колесо: зум к курсору, Shift – горизонталь ----------
    def wheelEvent(self, e) -> None:
        e.accept()
        mods = e.modifiers()
        dy = e.angleDelta().y()
        dx = e.angleDelta().x()
        if mods & Qt.KeyboardModifier.ShiftModifier or dy == 0:
            # бонус: Shift+колесо / наклон колеса – горизонтальная прокрутка
            bar = self.horizontalScrollBar()
            delta = dy if dy != 0 else dx
            if delta == 0:
                return
            step = max(bar.singleStep(), 20)
            bar.setValue(int(bar.value() - (delta / 120.0) * step * _WHEEL_NOTCH_STEPS))
            return
        self._gesture_wheel(e)   # плавный зум к точке под курсором

    # окно документа только просматривают: мышь не взаимодействует с элементами
    def mousePressEvent(self, e) -> None:
        if self._gesture_mouse_press(e):    # СКМ – панорама
            return
        e.accept()

    def mouseMoveEvent(self, e) -> None:
        if self._gesture_mouse_move(e):
            return
        e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if self._gesture_mouse_release(e):
            return
        e.accept()

    def mouseDoubleClickEvent(self, e) -> None:
        e.accept()

    def contextMenuEvent(self, e) -> None:
        e.accept()

    # ---------- память масштаба (Задача 4) ----------
    def _zoom_applied(self, scale: float) -> None:
        """Зум жестом – масштаб стал «ручным» (любой, кроме fit)."""
        if not self._manual_scale:
            self._manual_scale = True
            self.scale_mode_changed.emit()

    def _zoom_finished(self) -> None:
        super()._zoom_finished()
        # записать окончательный ручной масштаб (не первый микрошаг анимации)
        if self._manual_scale:
            self.scale_mode_changed.emit()

    def scale_state(self) -> str | float:
        """"fit" или последний ручной коэффициент масштаба."""
        if not self._manual_scale:
            return "fit"
        return float(self.transform().m11())

    def apply_saved_scale(self, k: float) -> None:
        """Восстановить сохранённый ручной масштаб (без пере-fit)."""
        if not (MIN_SCALE <= k <= MAX_SCALE):
            self.fit_width()
            return
        self._pending_fit = False
        self._manual_scale = True
        self.setTransform(QTransform().scale(float(k), float(k)))

    # ---------- масштаб «вписать по ширине» ----------
    def fit_width(self) -> None:
        sr = self.sceneRect()
        if sr.isEmpty() or sr.width() <= 0:
            return
        avail = max(self.viewport().width() - 20, 40)  # запас на ползунки/рамку
        k = avail / sr.width()
        self.setTransform(QTransform().scale(k, k))
        self._fitted_width = sr.width()
        self._fit_scale = k
        self.horizontalScrollBar().setValue(0)
        if self._manual_scale:
            self._manual_scale = False
            self.scale_mode_changed.emit()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if self._pending_fit:
            self.fit_width()
            self._pending_fit = False

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        # pop-out окно документа (сессия 8) resize'ится пользователем за
        # края/углы: в режиме «fit» лист переписываем по новой ширине.
        # Переписываем ТОЛЬКО если масштаб ещё в точности равен последнему
        # вписанному: любой зум (жест, кнопка, программный setTransform)
        # ломает равенство – масштаб пользователя не трогаем.
        if (self.isVisible() and not self._manual_scale
                and not self._pending_fit and self._fit_scale is not None
                and abs(self.transform().m11() - self._fit_scale) < 1e-9):
            self.fit_width()

    # сессия 10: структурные пересборки делает TreeCanvasController.rebuild
    # (doc_scene наполняется заново); «вписать по ширине» поддерживается
    # в showEvent/resizeEvent.
