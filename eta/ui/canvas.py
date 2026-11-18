# -*- coding: utf-8 -*-
"""Холст логического дерева событий (сессия 10; сессия 12, Задача 11).

Структура дерева фиксирована (инвариант пяти типов сценариев), поэтому
холст не содержит редактора топологии: ноды выбираются кликом, их
КОНКРЕТНОЕ содержимое настраивается в инспекторе. Перетаскивание
(сессия 12) не меняет структуру – только ВИЗУАЛЬНОЕ смещение ноды
относительно автоматической раскладки (node_offsets, формат 5; экран и
PDF остаются WYSIWYG – смещение применяет compute_layout).

Управление вьюпортом:
  ЛКМ на ноде    – перетаскивание ноды (после порога ~5 px) или выбор
                   кликом «без движения»;
  ЛКМ на пустом  – панорама (как и СКМ);
  колесо         – плавный зум к курсору (миксин ViewportGestures);
  тач            – пинч-зум / тап-выбор / панорама с инерцией (миксин).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, QPointF, QRectF, QEvent, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPathItem,
                               QGraphicsScene, QGraphicsView, QRubberBand)

from ..core.layout import (ANN_SNAP_DIST, ANN_SNAP_GAP, Annotation,
                           LayoutBundle, compute_layout)
from ..core.model import TreeModel
from .gestures import ViewportGestures
from .modern_tooltip import hide_scene_tip, scene_tip
from .render import draw_annotation, draw_node, edge_path
from .theme import ACCENT

FREE, STICKY = "free", "sticky"
NODE_COLOR = "#475569"
# Задача 5 (сессия 13): запас рабочего прямоугольника сцены в свободном
# режиме – камеру можно увести далеко за дерево без всяких ограничений
FREE_MARGIN_PX = 100000.0
# Задача 5 (сессия 17, LOCKED): умное вписывание – поле 40–60 px (взято
# 48) и ПОТОЛОК апскейла 1,5×: маленькое дерево может вырасти до предела,
# но не дальше; большое вписывается целиком (даунскейл не ограничен)
FIT_PAD_PX = 48.0
FIT_MAX_ZOOM = 1.5


def _rect_gap(a: QRectF, b: QRectF) -> float:
    """Расстояние между прямоугольниками (0 – пересекаются/касаются)."""
    dx = max(b.left() - a.right(), a.left() - b.right(), 0.0)
    dy = max(b.top() - a.bottom(), a.top() - b.bottom(), 0.0)
    return max(dx, dy)


class _DocAnnotationItem(QGraphicsItem):
    """Неинтерактивная справочная нода для сцены документа/PDF."""

    def __init__(self, ann: Annotation):
        super().__init__()
        self.ann = ann
        self.setZValue(0)

    def boundingRect(self) -> QRectF:
        return self.ann.rect.adjusted(-2, -2, 2, 2)

    def paint(self, p: QPainter, *_a) -> None:
        draw_annotation(p, self.ann)


class AnnotationItem(QGraphicsItem):
    """Справочная (титульная) нода дерева (Задача 4, сессия 13):
    перетаскивается ЛКМ (тот же порог 5 px, что и ноды); рядом с нодой
    своего дерева подсвечивает кандидата и показывает мини-подсказку
    «Привязать»; отпускание рядом – магнитная привязка (по центру над
    нодой), вдали – свободная позиция (персистентно). НЕ выбирается и
    не удаляется Delete – живет и умирает вместе со своим деревом."""

    def __init__(self, ann: Annotation, controller: "TreeCanvasController"):
        super().__init__()
        self.ann = ann
        self.ctrl = controller
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)

    def boundingRect(self) -> QRectF:
        return self.ann.rect.adjusted(-2, -2, 2, 2)

    def paint(self, p: QPainter, *_a) -> None:
        draw_annotation(p, self.ann)

    def hoverEnterEvent(self, e) -> None:
        # Сессия 19 (п.1): всплывающие подсказки на холсте выключены и у
        # справочной ноды (см. NodeItem.hoverEnterEvent). Прежний код
        # показа оставлен закомментированным; якорем была позиция курсора
        # (сессия 19) – до этого панель ставилась в центр ноды и
        # перекрывала её же hover-зону, из-за чего подсказка мерцала.
        hide_scene_tip()
        # scene_tip(QCursor.pos(),
        #           "Справочная нода – перетащите; отпустите рядом"
        #           " с нодой дерева, чтобы привязать", self.ctrl.canvas)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e) -> None:
        hide_scene_tip()
        super().hoverLeaveEvent(e)


class _EdgeItem(QGraphicsPathItem):
    def __init__(self, geo):
        super().__init__(edge_path(geo))
        self.geo = geo
        # Задача 5 (сессия 17): ребро толще (вровень с render.draw_edge,
        # WYSIWYG) – крупное дерево требует весомых связей
        self.setPen(QPen(QColor(NODE_COLOR), 2.0))
        self.setZValue(-1)


class _DocNodeItem(QGraphicsItem):
    """Неинтерактивная нода для сцены документа/PDF."""

    def __init__(self, geo):
        super().__init__()
        self.geo = geo
        self.setZValue(0)

    def boundingRect(self) -> QRectF:
        return self.geo.rect.adjusted(-2, -2, 2, 2)

    def paint(self, p: QPainter, *_a) -> None:
        draw_node(p, self.geo)


class NodeItem(QGraphicsItem):
    """Нода дерева: выбор кликом, перетаскивание, подсказка при наведении."""

    def __init__(self, geo, controller: "TreeCanvasController"):
        super().__init__()
        self.geo = geo
        self.ctrl = controller
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

    def tip_text(self) -> str:
        title = " ".join(self.geo.title_lines)
        body = "<br>".join(self.geo.body_lines[:8])
        return f"<b>{title}</b>" + (f"<br>{body}" if body else "")

    def boundingRect(self) -> QRectF:
        return self.geo.rect.adjusted(-3, -3, 3, 3)

    def paint(self, p: QPainter, *_a) -> None:
        draw_node(p, self.geo)
        if self.isSelected():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(ACCENT), 2.0, Qt.PenStyle.DashLine))
            p.drawRoundedRect(self.geo.rect.adjusted(-3, -3, 3, 3), 9, 9)
        elif self.ctrl._attach_candidate is self:
            # Задача 4: кандидат магнитной привязки справочной ноды
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(ACCENT), 2.0, Qt.PenStyle.DashLine))
            p.drawRoundedRect(self.geo.rect.adjusted(-3, -3, 3, 3), 9, 9)

    def hoverEnterEvent(self, e) -> None:
        # Сессия 19 (замечание заказчика, п.1): ВСПЛЫВАЮЩИЕ ПОДСКАЗКИ НА
        # ХОЛСТЕ ВЫКЛЮЧЕНЫ – по наведению на ноду дерева пузырь больше не
        # показываем (он дублировал текст самой ноды). Код показа СОХРАНЁН
        # закомментированным – возврат одной раскомментированной строкой. hide_scene_tip() оставлен намеренно – он гасит
        # пузырь, если тот был показан другим путём (драг привязки).
        hide_scene_tip()
        # scene_tip(QCursor.pos(), self.tip_text(), self.ctrl.canvas)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e) -> None:
        hide_scene_tip()
        super().hoverLeaveEvent(e)


class TreeCanvasController(QObject):
    """Сцены (рабочая и документа) + раскладка + выбор нод."""

    node_selected = Signal(str)

    def __init__(self, canvas: "TreeCanvas", parent: QObject | None = None):
        super().__init__(parent)
        self.canvas = canvas
        self.work_scene = QGraphicsScene(self)
        self.doc_scene = QGraphicsScene(self)
        self.layout: LayoutBundle = LayoutBundle()
        self.trees: list[TreeModel] = []
        self._last_rebuild: tuple | None = None
        self._attach_candidate: NodeItem | None = None   # Задача 4

    # ---------- построение ----------
    def rebuild(self, trees: list[TreeModel], kb, ctx_map: dict,
                owner_titles: dict | None = None) -> None:
        self._last_rebuild = (trees, kb, ctx_map, owner_titles)
        self.trees = trees
        self.layout = compute_layout(trees, kb, ctx_map, owner_titles)
        for sc in (self.work_scene, self.doc_scene):
            sc.clear()
        self._attach_candidate = None
        for a in self.layout.annotations:
            self.work_scene.addItem(AnnotationItem(a, self))
            self.doc_scene.addItem(_DocAnnotationItem(a))
        for e in self.layout.edges:
            self.work_scene.addItem(_EdgeItem(e))
            self.doc_scene.addItem(_EdgeItem(e))
        for n in self.layout.nodes.values():
            self.work_scene.addItem(NodeItem(n, self))
            self.doc_scene.addItem(_DocNodeItem(n))
        # Задача 5 (сессия 13): у РАБОЧЕЙ сцены прямоугольник зависит от
        # режима обзора (свободный – с огромным запасом под безграничный
        # обзор, липкий – точный лист); сцена документа (лист для PDF)
        # ВСЕГДА держит точный габарит раскладки – экспорт не затронут
        self.work_scene.setSceneRect(self.canvas._view_scene_rect())
        self.doc_scene.setSceneRect(self.layout.scene_rect)

    def rebuild_last(self) -> None:
        """Пересобрать сцены с последними аргументами rebuild – после
        перетаскивания ноды (Задача 11); камера НЕ пере-вписывается."""
        if self._last_rebuild is not None:
            self.rebuild(*self._last_rebuild)

    # ---------- выбор ----------
    def select_node(self, node_id: str | None) -> None:
        """Программный выбор ОДНОЙ ноды (пунктир; строка причины в
        иерархии). Снимает прочее выделение."""
        for it in self.work_scene.items():
            if isinstance(it, NodeItem):
                it.setSelected(it.geo.node_id == node_id)
        if node_id:
            self.node_selected.emit(node_id)

    def selected_node(self) -> str | None:
        for it in self.work_scene.items():
            if isinstance(it, NodeItem) and it.isSelected():
                return it.geo.node_id
        return None

    def selected_nodes(self) -> list[str]:
        """Задача 6 (сессия 17): РЕАЛЬНОЕ множество выделенных нод
        (рамка/Ctrl+клик/групповое перетаскивание)."""
        return [it.geo.node_id for it in self.work_scene.items()
                if isinstance(it, NodeItem) and it.isSelected()]

    def set_selection(self, node_ids: list[str]) -> None:
        """Выделить РОВНО перечисленные ноды (остальные снять)."""
        want = set(node_ids)
        for it in self.work_scene.items():
            if isinstance(it, NodeItem):
                it.setSelected(it.geo.node_id in want)

    def node_item(self, node_id: str) -> NodeItem | None:
        """QGraphicsItem ноды по id (рабочая сцена) – для тестов/драга."""
        for it in self.work_scene.items():
            if isinstance(it, NodeItem) and it.geo.node_id == node_id:
                return it
        return None

    def tree_of_node(self, node_id: str) -> TreeModel | None:
        tid = node_id.split(":", 1)[0] if node_id else ""
        return next((t for t in self.trees if t.tree_id == tid), None)

    @staticmethod
    def node_kind(node_id: str) -> str:
        return node_id.split(":", 1)[1] if ":" in node_id else ""


class TreeCanvas(ViewportGestures, QGraphicsView):
    """Вьюпорт холста: зум колесом к курсору, липкий/свободный обзор,
    перетаскивание нод ЛКМ и панорама (сессия 12, Задача 11), жесты."""

    node_clicked = Signal(str)          # id ноды (клик ЛКМ без движения)
    empty_clicked = Signal()
    delete_requested = Signal()         # Delete при фокусе в холсте (Задача 10)
    tree_offsets_changed = Signal()     # ноду перетащили – оффсеты сохранены
    annotation_changed = Signal()       # Задача 4: справочную ноду тащили
    # Задача 6 (сессия 17): пользователь выделил МНОЖЕСТВО нод рамкой
    # (без открытия инспектора – «последней ноды» у рамки нет)
    nodes_selected = Signal(list)
    # Задача 2 (сессия 19, LOCKED): двойной клик ЛКМ по ноде ГС/ИЗ –
    # «Добавить причину…» для ДЕРЕВА ЭТОЙ НОДЫ (tree_id, вид «gs»/«iz»)
    node_add_cause_requested = Signal(str, str)

    DRAG_THRESHOLD_PX = 5.0             # порог «клик vs перетаскивание»

    # Задача 2 (сессия 19, LOCKED): виды нод, у которых есть причины
    CAUSE_KINDS = ("gs", "iz")

    # Задача 6 (LOCKED вариант 1): рамка выделения – translucent blue
    # rgba(59,130,246,0.12) + рамка 1 px #3B82F6 (плоский канон)
    RUBBER_QSS = ("QRubberBand { background: rgba(59,130,246,0.12);"
                  " border: 1px solid #3B82F6; }")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = STICKY
        self.setRenderHints(QPainter.RenderHint.Antialiasing
                            | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QBrush(QColor("#F8FAFC")))
        # Задача 11: жестовый миксин подключён полностью – плавный зум к
        # курсору (якорь вручную, NoAnchor), СКМ-панорама, пинч/тап
        # (в сессии 10 вызов _init_gestures потерялся – жесты умерли)
        self._init_gestures()
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.controller = TreeCanvasController(self)
        self.setScene(self.controller.work_scene)
        # Задача 10: Delete работает и на холсте (удаляется дерево
        # выделенной ноды – через MainWindow._delete_selection).
        # Реализация – фильтр событий ВЬЮПОРТА: QGraphicsView держит
        # фокус во вьюпорте, и синтетические/системные нажатия доходят
        # туда напрямую; шорткат-контексты на сценах ненадежны.
        # Задача 6 (сессия 17): туда же – Пробел (панорама Пробел+ЛКМ)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().installEventFilter(self)
        # подсказка управления холстом (Задача 6: смена модели ЛКМ)
        # Сессия 19 (п.1): на холсте не показываем НИ ОДНОГО всплывающего
        # пузыря, поэтому view-level toolTip выключен (текст сохранён
        # ниже и продублирован в statusTip – он читается в строке
        # состояния и экран не закрывает).
        self.setStatusTip("ЛКМ по пустому месту и протяните – рамка"
                          " выделения; Пробел + ЛКМ или СКМ – панорама;"
                          " колесо – масштаб; двойной клик по ноде ГС/ИЗ –"
                          " добавить причину")
        # self.setToolTip("Рамка выделения: ЛКМ по пустому месту и"
        #                 " протянуть; Ctrl/Shift + ЛКМ – добавить/убрать"
        #                 " ноду из выделения; панорама: Пробел + ЛКМ или"
        #                 " СКМ; масштаб – колесо; двойной клик по ноде"
        #                 " ГС/ИЗ – добавить причину")
        # состояние ЛКМ: перетаскивание ноды / справочной ноды / рамка
        self._press_item: NodeItem | None = None
        self._press_pos = QPointF()
        self._last_pos = QPointF()
        self._dragging_node = False
        self._drag_delta = QPointF()    # накопленное смещение (сцена)
        # Задача 6: группы – тащатся ВСЕ выделенные ноды вместе
        self._drag_items: list[NodeItem] = []
        self._press_lmb_pos = QPoint()  # старт ЛКМ на пустом (клик/рамка)
        self._rubber: QRubberBand | None = None
        self._rubber_origin: QPoint | None = None
        self._rubber_shown = False
        # Задача 6: Пробел + ЛКМ – панорама (куртор «рука»)
        self._space_held = False
        self._space_pan_origin: QPoint | None = None
        # Задача 4: состояние перетаскивания справочной ноды
        self._press_ann: AnnotationItem | None = None
        self._dragging_ann = False

    # ---------- режимы обзора ----------
    def set_mode(self, mode: str) -> None:
        was = self._mode
        self._mode = mode
        # Задача 5 (сессия 13): смена режима меняет диапазон ползунков
        # (свободный – сцена с огромным запасом, липкий – точный лист)
        if mode != was:
            self._apply_view_scene_rect()

    def _view_scene_rect(self) -> QRectF:
        """Прямоугольник РАБОЧЕЙ сцены: в свободном режиме лист вырос на
        ±FREE_MARGIN_PX (ползунки огромны – обзор без ограничений), в
        липком – точный габарит раскладки. Сцена документа (лист/PDF)
        НЕ трогается: экспорт всегда вписывает layout.scene_rect."""
        r = self.controller.layout.scene_rect
        if self._mode == FREE and not r.isEmpty():
            return r.adjusted(-FREE_MARGIN_PX, -FREE_MARGIN_PX,
                              FREE_MARGIN_PX, FREE_MARGIN_PX)
        return r

    def _apply_view_scene_rect(self) -> None:
        self.controller.work_scene.setSceneRect(self._view_scene_rect())

    def mode(self) -> str:
        return self._mode

    def clamp_to_mode(self) -> None:
        """Публичный кламп «липкого» режима (Задача 12): окно вызывает
        после смены режима; учитывает и перетащенные ноды (scene_rect
        растёт вместе с оффсетами, Задача 11)."""
        self._clamp_to_mode()

    # ---------- масштаб и вписывание ----------
    def wheelEvent(self, e) -> None:
        # Задача 11: единый плавный зум к курсору из жестового миксина
        self._gesture_wheel(e)

    def zoom(self, factor: float) -> None:
        """Кнопки ±: плавный зум вокруг центра вьюпорта."""
        c = QPointF(self.viewport().width() / 2.0,
                    self.viewport().height() / 2.0)
        self._animate_zoom(factor, c)

    def zoom_level(self) -> float:
        return self.transform().m11()

    def set_zoom_level(self, z: float) -> None:
        z = max(0.08, min(6.0, z))
        self._zoom_anchor = QPointF(self.viewport().width() / 2.0,
                                    self.viewport().height() / 2.0)
        try:
            self._zoom_step(z)
        finally:
            self._zoom_anchor = None

    def fit_tree(self) -> None:
        """Задача 5 (сессия 17, LOCKED): вписать дерево с полем 48 px;
        ПОТОЛОК апскейла 1,5× – маленькое дерево заполняет холст, но не
        раздувается дальше; крупное вписывается целиком (уменьшение не
        ограничено). После клампа – недеформированное центрирование."""
        rect = self.controller.layout.scene_rect
        if rect.isEmpty():
            return
        self.fitInView(rect.adjusted(-FIT_PAD_PX, -FIT_PAD_PX,
                                     FIT_PAD_PX, FIT_PAD_PX),
                       Qt.AspectRatioMode.KeepAspectRatio)
        if self.zoom_level() > FIT_MAX_ZOOM:
            self.set_zoom_level(FIT_MAX_ZOOM)
            self.centerOn(rect.center())
        self._clamp_to_mode()

    def _clamp_to_mode(self) -> None:
        """Липкий обзор: камера не уходит за границы дерева (+ перета-
        щенные ноды – scene_rect учитывает оффсеты). Задача 5 (сессия 17):
        поле клампа = полю вписывания (48 px) – поведение согласовано."""
        if self._mode != STICKY:
            return
        rect = self.controller.layout.scene_rect.adjusted(
            -FIT_PAD_PX, -FIT_PAD_PX, FIT_PAD_PX, FIT_PAD_PX)
        if rect.isEmpty():
            return
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        dx = dy = 0.0
        if visible.width() <= rect.width():
            if visible.left() < rect.left():
                dx = rect.left() - visible.left()
            elif visible.right() > rect.right():
                dx = rect.right() - visible.right()
        if visible.height() <= rect.height():
            if visible.top() < rect.top():
                dy = rect.top() - visible.top()
            elif visible.bottom() > rect.bottom():
                dy = rect.bottom() - visible.bottom()
        if dx or dy:
            self.translate(dx, dy)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._clamp_to_mode()

    # ---------- мышь: ноды/рамка/панорама (Задачи 11 и 6) ----------
    def eventFilter(self, obj, ev) -> bool:  # noqa: N802
        """Фильтр вьюпорта: Delete (Задача 10) и Пробел (Задача 6,
        сессия 17: Пробел+ЛКМ – панорама, курсор «рука»).

        Задача 2 (сессия 18): при KUJI_DEBUG_KEYS=1 каждый KeyPress/
        KeyRelease пишется в qa_artifacts\\key_debug.log – видно,
        доходят ли клавиши до фокуса вьюпорта холста на реальной
        Windows (инструментарий диагностики Alt/Ctrl/Пробел)."""
        if obj is self.viewport():
            from .latin_keys import key_debug_log
            if ev.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
                key_debug_log("canvas-vp", ev, obj)
            if ev.type() == QEvent.Type.KeyPress \
                    and ev.key() == Qt.Key.Key_Delete:
                self.delete_requested.emit()
                ev.accept()
                return True
            if ev.type() == QEvent.Type.KeyPress \
                    and ev.key() == Qt.Key.Key_Space \
                    and not ev.isAutoRepeat():
                self._space_held = True
                self.viewport().setCursor(
                    Qt.CursorShape.OpenHandCursor)
                key_debug_log("canvas-vp", ev, obj, note="space: pan on")
                ev.accept()
                return True
            if ev.type() == QEvent.Type.KeyRelease \
                    and ev.key() == Qt.Key.Key_Space \
                    and not ev.isAutoRepeat():
                self._space_held = False
                self._space_pan_origin = None
                if not self._dragging_node:
                    self.viewport().unsetCursor()
                key_debug_log("canvas-vp", ev, obj, note="space: pan off")
                ev.accept()
                return True
        return super().eventFilter(obj, ev)

    def work_items(self):
        return self.controller.work_scene.items()

    # ---------- Пробел на уровне приложения (Задача 2, сессия 18) ----------
    def _app_space_pan(self, on: bool) -> None:
        """Обратная связь глобальной готовности панорамы: курсор «рука».
        Сам флаг читается в mousePressEvent (space_pan_active) – фокус
        может стоять в иерархии/инспекторе, а панорама обязана
        вооружаться и там (доставка Пробела сфокусированному виджету –
        измеренная форма реальной Windows)."""
        if self._dragging_node or self._space_pan_origin is not None:
            return
        self.viewport().setCursor(
            Qt.CursorShape.OpenHandCursor if on
            else Qt.CursorShape.ArrowCursor)

    def _pan_armed(self) -> bool:
        """Панорама вооружена: Пробел у фокуса холста ИЛИ глобально."""
        from .latin_keys import space_pan_active
        return self._space_held or space_pan_active()

    def mousePressEvent(self, e) -> None:
        if self._gesture_mouse_press(e):     # СКМ – панорама
            return
        if e.button() == Qt.MouseButton.LeftButton:
            # Задача 6 (LOCKED): Пробел+ЛКМ – панорама (рука); Задача 2
            # (сессия 18): и при ГЛОБАЛЬНОМ удержании Пробела (фокус в
            # другом виджете) – space_pan_active
            if self._pan_armed():
                self._space_pan_origin = e.position().toPoint()
                self.viewport().setCursor(
                    Qt.CursorShape.ClosedHandCursor)
                e.accept()
                return
            it = self.itemAt(e.position().toPoint())
            if isinstance(it, NodeItem):
                self._press_item = it
                self._press_pos = QPointF(e.position())
                self._last_pos = QPointF(e.position())
                self._dragging_node = False
                self._drag_delta = QPointF()
                # Задача 6: тащим ГРУППУ, если взятая нода уже выделена
                sel = self.controller.selected_nodes()
                self._drag_items = ([x for x in self.work_items()
                                     if isinstance(x, NodeItem)
                                     and x.isSelected()]
                                    if it.geo.node_id in sel and len(sel) > 1
                                    else [it])
            elif isinstance(it, AnnotationItem):
                # Задача 4: перетаскивание справочной ноды (порог тот же)
                self._press_ann = it
                self._press_pos = QPointF(e.position())
                self._last_pos = QPointF(e.position())
                self._dragging_ann = False
            else:
                # Задача 6 (LOCKED вариант 1): ЛКМ на пустом – РАМКА
                # выделения (панорама ушла на СКМ + Пробел+ЛКМ); клик
                # без движения по-прежнему снимает выделение
                self._press_lmb_pos = e.position().toPoint()
                self._rubber_origin = e.position().toPoint()
                self._rubber_shown = False
            e.accept()
            return
        super().mousePressEvent(e)

    def work_items(self):
        return self.controller.work_scene.items()

    def mouseMoveEvent(self, e) -> None:
        if self._gesture_mouse_move(e):      # СКМ-панорама миксина
            return
        pos = QPointF(e.position())
        if self._space_pan_origin is not None:   # Пробел+ЛКМ – панорама
            cur = pos.toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value()
                - (cur.x() - self._space_pan_origin.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value()
                - (cur.y() - self._space_pan_origin.y()))
            self._space_pan_origin = cur
            e.accept()
            return
        if self._press_ann is not None:      # Задача 4: справочная нода
            if not self._dragging_ann:
                if (pos - self._press_pos).manhattanLength() \
                        >= self.DRAG_THRESHOLD_PX:
                    self._dragging_ann = True
                    self.viewport().setCursor(
                        Qt.CursorShape.ClosedHandCursor)
            if self._dragging_ann:
                d_view = pos - self._last_pos
                z = self.transform().m11()
                if z:
                    self._press_ann.moveBy(d_view.x() / z, d_view.y() / z)
                    self._update_attach_candidate(self._press_ann)
            self._last_pos = pos
            e.accept()
            return
        if self._press_item is not None:
            if not self._dragging_node:
                if (pos - self._press_pos).manhattanLength() \
                        >= self.DRAG_THRESHOLD_PX:
                    self._dragging_node = True
                    self.viewport().setCursor(
                        Qt.CursorShape.ClosedHandCursor)
            if self._dragging_node:
                d_view = pos - self._last_pos
                z = self.transform().m11()
                if z:
                    d = QPointF(d_view.x() / z, d_view.y() / z)
                    # Задача 6: группа тащится ЦЕЛИКОМ – одна дельта
                    for item in self._drag_items:
                        self._move_node_item(item, d)
                    self._drag_delta = QPointF(self._drag_delta + d)
            self._last_pos = pos
            e.accept()
            return
        if self._rubber_origin is not None:
            cur = pos.toPoint()
            if not self._rubber_shown \
                    and (cur - self._press_lmb_pos).manhattanLength() \
                    >= self.DRAG_THRESHOLD_PX:
                self._rubber_shown = True
                if self._rubber is None:
                    self._rubber = QRubberBand(
                        QRubberBand.Shape.Rectangle, self.viewport())
                    self._rubber.setStyleSheet(self.RUBBER_QSS)
                self._rubber.setGeometry(QRectF(
                    QPointF(self._rubber_origin),
                    QPointF(self._press_lmb_pos)).toAlignedRect())
                self._rubber.show()
            if self._rubber_shown and self._rubber is not None:
                self._rubber.setGeometry(QRectF(
                    QPointF(self._rubber_origin),
                    QPointF(cur)).normalized().toAlignedRect())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._gesture_mouse_release(e):
            return
        if e.button() == Qt.MouseButton.LeftButton:
            if self._space_pan_origin is not None:    # Пробел+ЛКМ – конец
                self._space_pan_origin = None
                self.viewport().setCursor(
                    Qt.CursorShape.OpenHandCursor
                    if self._space_held
                    else Qt.CursorShape.ArrowCursor)
                e.accept()
                return
            if self._press_ann is not None:      # Задача 4
                item = self._press_ann
                self._press_ann = None
                hide_scene_tip()
                moved = self._dragging_ann
                self._dragging_ann = False
                self.viewport().unsetCursor()
                if moved:
                    self._commit_annotation_drag(item)
                e.accept()
                return
            if self._press_item is not None:
                item = self._press_item
                self._press_item = None
                if self._dragging_node:
                    self._dragging_node = False
                    self.viewport().unsetCursor()
                    self._commit_node_drag(self._drag_items,
                                           self._drag_delta)
                    self._drag_items = []
                else:
                    # клик без движения: выбор ноды → инспектор.
                    # Задача 6: Ctrl/Shift+клик ДОБАВЛЯЕТ/убирает ноду
                    # из выделения; инспектор – последняя нода
                    if e.modifiers() & (Qt.KeyboardModifier.ControlModifier
                                        | Qt.KeyboardModifier
                                        .ShiftModifier):
                        item.setSelected(not item.isSelected())
                        self.node_clicked.emit(item.geo.node_id)
                    else:
                        self.controller.select_node(item.geo.node_id)
                        self.node_clicked.emit(item.geo.node_id)
                e.accept()
                return
            if self._rubber_origin is not None:
                moved = self._rubber_shown
                origin = self._rubber_origin
                self._rubber_origin = None
                self._rubber_shown = False
                if self._rubber is not None:
                    self._rubber.hide()
                if moved:
                    # выделение = все ноды, пересекающие рамку (в коорд.
                    # сцены; справочные ноды НЕ выделяются рамкой)
                    r = QRectF(QPointF(origin),
                               QPointF(e.position())).normalized()
                    sr = self.mapToScene(r.toAlignedRect()).boundingRect()
                    ids = [it.geo.node_id for it in self.work_items()
                           if isinstance(it, NodeItem)
                           and it.sceneBoundingRect().intersects(sr)]
                    self.controller.set_selection(ids)
                    if ids:
                        self.nodes_selected.emit(ids)
                    else:
                        self.controller.select_node(None)
                        self.empty_clicked.emit()
                else:
                    self.controller.select_node(None)
                    self.empty_clicked.emit()
                e.accept()
                return
        super().mouseReleaseEvent(e)

    # ---------- двойной клик: добавить причину (Задача 2, сессия 19) ----
    def mouseDoubleClickEvent(self, e) -> None:
        """Задача 2 (сессия 19, LOCKED): двойной клик ЛКМ по ноде ГС или ИЗ
        РАБОЧЕГО холста равен нажатию «Добавить причину…» в инспекторе
        ЭТОЙ ноды: тот же диалог, то же дерево, та же цепочка отмены.

        Безопасный no-op во всех прочих случаях: ноды вещества, окислителя
        и пожара, справочные ноды (`AnnotationItem`) и пустое место.
        Последовательность Qt (Press → Release → DoubleClick → Release)
        такова, что ПЕРВЫЙ Release уже выбрал ноду и показал её форму,
        поэтому выбор здесь только дополняется (идемпотентно, без второго
        щелчка по инспектору). Оффсеты нод не трогаются: драг требует
        движения не менее DRAG_THRESHOLD_PX, а DoubleClick его не делает.
        Лист «Документ» не затронут – там другие элементы (`_DocNodeItem`).
        """
        if (e.button() == Qt.MouseButton.LeftButton
                and not self._pan_armed()):
            it = self.itemAt(e.position().toPoint())
            if isinstance(it, NodeItem):
                nid = it.geo.node_id
                kind = self.controller.node_kind(nid)
                if kind in self.CAUSE_KINDS:
                    tree = self.controller.tree_of_node(nid)
                    if tree is not None:
                        # контекст инспектора – по кликнутной ноде: форма
                        # этого дерева должна быть показана ДО диалога
                        if self.controller.selected_node() != nid:
                            self.controller.select_node(nid)
                            self.node_clicked.emit(nid)
                        self.node_add_cause_requested.emit(tree.tree_id,
                                                           kind)
                    e.accept()
                    return
        super().mouseDoubleClickEvent(e)

    # ---------- перетаскивание ноды ----------
    def _move_node_item(self, item: NodeItem, d: QPointF) -> None:
        """Видимое смещение ноды и её рёбер (координаты сцены).
        Задача 5 (сессия 15): протокол геометрии соблюден – нода ходит
        setPos (Qt сам зовет prepareGeometryChange), ребро мутирует
        ТОЛЬКО через setPath (QGraphicsPathItem внутри вызывает
        prepareGeometryChange); boundingRect ноды производен от
        NodeGeo.rect (+3 px), который решают метрики layout.make_node –
        рёбра начинаются/кончаются на тех же прямоугольниках, к widened
        рамкам кривые не прилипают."""
        item.setPos(item.pos() + d)
        nid = item.geo.node_id
        for ei in self.controller.work_scene.items():
            if isinstance(ei, _EdgeItem) and (ei.geo.src == nid
                                              or ei.geo.dst == nid):
                if ei.geo.src == nid:
                    ei.geo.p1 = QPointF(ei.geo.p1 + d)
                    if ei.geo.c1 is not None:
                        ei.geo.c1 = QPointF(ei.geo.c1 + d)
                if ei.geo.dst == nid:
                    ei.geo.p2 = QPointF(ei.geo.p2 + d)
                    if ei.geo.c2 is not None:
                        ei.geo.c2 = QPointF(ei.geo.c2 + d)
                ei.setPath(edge_path(ei.geo))

    def _commit_node_drag(self, items: list, delta: QPointF) -> None:
        """Задача 11: смещение сохраняется в дереве (node_offsets) и
        раскладка пересобирается – экран и PDF строго WYSIWYG, кламп
        «липкого» режима видит выросший scene_rect. Задача 6 (сессия
        17): ГРУППОВОЕ перетаскивание – одна дельта на каждую ноду
        набора, ОДНА пересборка и ОДИН сигнал (одна точка отката)."""
        if not items or delta.isNull():
            self.controller.rebuild_last()
            return
        moved_trees = set()
        for item in items:
            nid = item.geo.node_id
            tree = self.controller.tree_of_node(nid)
            slot = self.controller.node_kind(nid)
            if tree is None or not slot:
                continue
            off = dict(tree.node_offsets or {})
            dx, dy = off.get(slot, (0.0, 0.0))
            off[slot] = [float(dx + delta.x()), float(dy + delta.y())]
            tree.node_offsets = off
            moved_trees.add(tree.tree_id)
        self.controller.rebuild_last()
        self.clamp_to_mode()
        if moved_trees:
            self.tree_offsets_changed.emit()

    # ---------- перетаскивание справочной ноды (Задача 4, сессия 13) ----
    def _update_attach_candidate(self, ann_item: AnnotationItem) -> None:
        """Пока справочная нода тащится: ближайшая нода ЕЁ дерева в
        пределах порога (ANN_SNAP_DIST) подсвечивается акцентной
        пунктирной рамкой + мини-подсказка «Привязать» у курсора."""
        rect = ann_item.sceneBoundingRect()
        best: NodeItem | None = None
        best_d: float | None = None
        for it in self.controller.work_scene.items():
            if isinstance(it, NodeItem) and \
                    it.geo.node_id.split(":", 1)[0] == ann_item.ann.tree_id:
                d = _rect_gap(rect, it.geo.rect)
                if d <= ANN_SNAP_DIST and (best_d is None or d < best_d):
                    best, best_d = it, d
        if best is not self.controller._attach_candidate:
            prev = self.controller._attach_candidate
            self.controller._attach_candidate = best
            if prev is not None:
                prev.update()
            if best is not None:
                best.update()
        if best is not None:
            scene_tip(QCursor.pos(), "<b>Привязать</b>", self)
        else:
            hide_scene_tip()

    def _commit_annotation_drag(self, item: AnnotationItem) -> None:
        """Позиция справочной ноды сохраняется в дереве: отпускание
        рядом с нодой – МАГНИТНАЯ привязка (по центру над нодой,
        офсет от левого-верхнего угла ноды), вдали – свободная позиция
        (офсет от позиции по умолчанию). Раскладка пересобирается –
        экран и PDF остаются WYSIWYG."""
        tree = next((t for t in self.controller.trees
                     if t.tree_id == item.ann.tree_id), None)
        cand = self.controller._attach_candidate
        self.controller._attach_candidate = None
        if cand is not None:
            cand.update()
        hide_scene_tip()
        if tree is None:
            self.controller.rebuild_last()
            return
        ann = item.ann
        if cand is not None:
            slot = self.controller.node_kind(cand.geo.node_id)
            w, h = ann.rect.width(), ann.rect.height()
            nr = cand.geo.rect
            tree.annotation = {"attached": slot,
                               "offset": [(nr.width() - w) / 2.0,
                                          -(h + ANN_SNAP_GAP)]}
        else:
            rect = item.sceneBoundingRect()
            tree.annotation = {
                "attached": None,
                "offset": [rect.left() - ann.default_pos.x(),
                           rect.top() - ann.default_pos.y()]}
        self.controller.rebuild_last()
        self.clamp_to_mode()
        self.annotation_changed.emit()
