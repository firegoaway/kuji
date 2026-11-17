# -*- coding: utf-8 -*-
"""Левая панель: иерархия объектов (сессия 10, Задача 2).

Территория → Здание → [Пожарный отсек] → Помещение → Участок;
Наружная установка – под Территорией (уровень Здания). Под Участком
и установкой – служебная «Группа сценариев»: раскрывается в список
конкретных сценариев («Разгерметизация … – скорость сгорания … – тип
горения»). Выделение сценария показывает его дерево; выделение
помещения/здания – все деревья дочерних участков (Ctrl/Shift – выбор
нескольких узлов одного уровня).

Панель инструментов: 7 крупных кнопок, равномерно распределённых по
ширине (сессия 10, Задача 9; сессия 13, Задача 6 – седьмая кнопка
«Добавить дерево» правее «Добавить наружную установку»). Переименование
– F2/двойной клик/поле «Название». ПКМ – ТОЛЬКО переименовать /
удалить с поддеревом (кнопка «Удалить» – по умолчанию, Delete+Enter).
Delete удаляет ВСЁ выбранное (Ctrl/Shift-мультивыбор) через одно окно
подтверждения (Задача 6.2, сессия 13). Сессия 16, Задача 1: чистый
выбор строк причин удаляется КАК ПРИЧИНЫ с зависимыми ветвиями
(участок-владелец не затрагивается); строка сценария – безопасный
no-op; смешанный выбор удаляет только объекты.
"""

from __future__ import annotations

from PySide6.QtCore import (QEvent, QMimeData, QPoint, QPointF, QSize,
                            Qt, Signal)
from PySide6.QtGui import (QBrush, QColor, QCursor, QDrag, QKeySequence,
                           QShortcut)
from PySide6.QtWidgets import (QAbstractItemView, QApplication,
                               QHBoxLayout, QHeaderView, QLabel, QMenu,
                               QMessageBox, QPushButton, QSizePolicy,
                               QToolButton, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from ..core.kb import KnowledgeBase
from ..core.layout import fmt_q
from ..core.model import SCENARIO_TYPES, TreeModel
from ..core.objects import (AREA, BUILDING, COMPARTMENT, KIND_TITLES,
                            OUTDOOR, PARENT_RULES, ROOM, TERRITORY,
                            TREE_OWNER_KINDS, ObjNode, ObjectTree)
from .icons import (GLYPH_AREA, GLYPH_BUILDING, GLYPH_COMPARTMENT,
                    GLYPH_EVENT_ADD, GLYPH_GS_CAUSE, GLYPH_IZ_CAUSE,
                    GLYPH_OUTDOOR, GLYPH_PENCIL, GLYPH_PROPS, GLYPH_ROOM,
                    GLYPH_TERRITORY, GLYPH_TREE_ADD, GLYPH_TRASH,
                    glyph_icon)
from .modern_tooltip import hide_scene_tip, scene_tip
from .theme import ICON_PX_HIER, ui_font

BTN = 44


def _kind_glyph(kind: str) -> str:
    """Глиф вида объекта (территория/здание/…/установка; запас –
    «свойства»). Один источник для строк иерархии и карточки
    переноса (Задача 3, сессия 16)."""
    return {TERRITORY: GLYPH_TERRITORY, BUILDING: GLYPH_BUILDING,
            COMPARTMENT: GLYPH_COMPARTMENT, ROOM: GLYPH_ROOM,
            AREA: GLYPH_AREA, OUTDOOR: GLYPH_OUTDOOR}.get(
                kind, GLYPH_PROPS)

# MIME-метка собственного драга иерархии: вход чужих драгов (из других
# приложений) игнорируется, своих – принимается; метка также позволяет
# тестам синтезировать drag-события (offscreen не исполняет QDrag.exec)
_HIER_MIME = "application/x-kuji-hier"

# подсветка цели перетаскивания (Задача 3.3): допустимая – синяя,
# недопустимая – красная рамка-фон
_DROP_OK_BG = QColor("#DBEAFE")
_DROP_BAD_BG = QColor("#FEE2E2")


# параметры карточки переноса (Задача 3, сессия 16, LOCKED): глиф
# 16×16 + зазор 8 + однострочный заголовок, симметричные отступы 6/12,
# скругление 6, ширина ≤300, непрозрачность ~0.95, рамка 1 px #3B82F6
# (контрастная рамка ВМЕСТО тени – плоский канон проекта)
_DRAG_PAD_X = 12.0
_DRAG_PAD_Y = 6.0
_DRAG_ICON = 16.0
_DRAG_GAP = 8.0
_DRAG_MAX_W = 300.0
_DRAG_RADIUS = 6.0
_DRAG_FILL = QColor("#EFF6FF")
_DRAG_BORDER = QColor("#3B82F6")
_DRAG_TEXT = QColor("#0F172A")


def _drag_pixmap(glyph: str | None, text: str, dpr: float = 2.0):
    """Задача 3 (сессия 16): КАРТОЧКА переноса – [глиф 16×16] – 8 px –
    однострочный заголовок. Всё центрировано по вертикали в ОДНОМ
    draw-прямоугольнике (AlignVCenter|AlignLeft, без ручных сдвигов –
    прежний «+4 px» поверх AlignVCenter и давал видимый перекос
    текста). Отступы симметричные 6/12, скругление 6, непрозрачность
    0.95, плоский канон: светлая заливка #EFF6FF + контрастная рамка
    1 px #3B82F6 (тени/градиенты запрещены). Заголовок усекается по
    ПИКСЕЛЯМ (ElideRight, ширина карточки ≤300). QPixmap создается с
    devicePixelRatio (HiDPI-четкость); hotspot – QPoint(16, h//2):
    курсор держит карточку у ЛЕВОГО края – она висит ПРАВЕЕ курсора и
    не закрывает цель под ним. Возвращает (QPixmap, QPoint)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import (QFontMetrics, QPainter, QPainterPath,
                               QPen, QPixmap)

    f = ui_font(10)
    fm = QFontMetrics(f)
    has_icon = glyph is not None
    lead = (_DRAG_ICON + _DRAG_GAP) if has_icon else 0.0
    max_text = _DRAG_MAX_W - 2 * _DRAG_PAD_X - lead
    elided = fm.elidedText(text, Qt.TextElideMode.ElideRight,
                           int(max_text))
    tw = fm.horizontalAdvance(elided)
    w = 2 * _DRAG_PAD_X + lead + tw
    h = max(fm.height(), _DRAG_ICON if has_icon else 0.0) + 2 * _DRAG_PAD_Y
    ratio = max(1.0, float(dpr))
    pm = QPixmap(int(round(w * ratio)), int(round(h * ratio)))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setOpacity(0.95)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0),
                        _DRAG_RADIUS, _DRAG_RADIUS)
    p.fillPath(path, QBrush(_DRAG_FILL))
    p.setPen(QPen(_DRAG_BORDER, 1.0))
    p.drawPath(path)
    if has_icon:
        # векторный глиф той же машины (glyph_icon) в 16 px, растер
        # под devicePixelRatio – четкие кромки на HiDPI
        ipm = glyph_icon(glyph).pixmap(
            QSize(int(_DRAG_ICON * ratio), int(_DRAG_ICON * ratio)))
        ipm.setDevicePixelRatio(ratio)
        p.drawPixmap(QPointF(_DRAG_PAD_X, (h - _DRAG_ICON) / 2.0), ipm)
    p.setFont(f)
    p.setPen(_DRAG_TEXT)
    p.drawText(QRectF(_DRAG_PAD_X + lead, 0.0, tw + 2.0, h),
               int(Qt.AlignmentFlag.AlignLeft
                   | Qt.AlignmentFlag.AlignVCenter), elided)
    p.end()
    return pm, QPoint(16, int(h) // 2)


def _tool_button(tooltip_rich: str, plain_tip: str) -> QToolButton:
    b = QToolButton()
    b.setFixedSize(BTN + 4, BTN)
    b.setIconSize(QSize(ICON_PX_HIER, ICON_PX_HIER))
    b.setToolTip(tooltip_rich)
    b.setStatusTip(plain_tip)
    b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return b


class HierarchyToolbar(QWidget):
    """Горизонтальная панель кнопок добавления уровней иерархии;
    кнопки распределены по всей ширине (Задача 9)."""

    add_requested = Signal(str)
    tree_add_requested = Signal()      # Задача 6 (сессия 13): «Добавить дерево»

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("hierToolbar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.buttons: dict[str, QToolButton] = {}
        specs = [
            (TERRITORY, GLYPH_TERRITORY,
             "<b>Добавить территорию</b> – создается в корне иерархии"
             "<br>(доступно всегда, независимо от выделения)"),
            (BUILDING, GLYPH_BUILDING,
             "<b>Добавить здание</b> – в выбранную территорию"),
            (COMPARTMENT, GLYPH_COMPARTMENT,
             "<b>Добавить пожарный отсек</b> – в выбранное здание"),
            (ROOM, GLYPH_ROOM,
             "<b>Добавить помещение</b> – в отсек или напрямую в здание"),
            (AREA, GLYPH_AREA,
             "<b>Добавить участок</b> – локальная зона выбранного помещения"
             "<br>(тип: м² / линейный объект / аппарат – в свойствах)"),
            (OUTDOOR, GLYPH_OUTDOOR,
             "<b>Добавить наружную установку</b> – самостоятельный аппарат"
             " на территории<br>(деревья сценариев создаются прямо на ней)"),
        ]
        # равные растяжки: до первой, между кнопками и после последней
        for kind, glyph, tip in specs:
            lay.addStretch(1)
            # Задача 1 (сессия 14): строка статуса кнопки территории
            # говорит о создании в КОРНЕ иерархии
            plain = ("Добавить территорию – создается в корне иерархии"
                     if kind == TERRITORY else KIND_TITLES[kind])
            b = _tool_button(tip, plain)
            b.setIcon(glyph_icon(glyph))
            b.clicked.connect(lambda _=False, k=kind:
                              self.add_requested.emit(k))
            self.buttons[kind] = b
            lay.addWidget(b)
        # Задача 6 (сессия 13): кнопка «Добавить дерево» – ПРАВЕЕ кнопки
        # «Добавить наружную установку» (всего 7, раскладка пересчитана);
        # клик открывает меню пяти типов сценариев (гейтинг – в панели)
        lay.addStretch(1)
        self.btn_add_tree = _tool_button(
            "<b>Добавить дерево</b> – логическое дерево событий"
            " (5 типов сценариев)",
            "Добавить дерево")
        self.btn_add_tree.setIcon(glyph_icon(GLYPH_TREE_ADD))
        self.btn_add_tree.clicked.connect(
            lambda _=False: self.tree_add_requested.emit())
        lay.addWidget(self.btn_add_tree)
        lay.addStretch(1)

    def set_available(self, kinds: set[str], selected_title: str | None) -> None:
        for kind, b in self.buttons.items():
            ok = kind in kinds
            b.setEnabled(ok)
            if kind == TERRITORY:
                # Задача 1 (сессия 14): территория всегда доступна и
                # создается В КОРНЕ иерархии – выделение не важно
                b.setToolTip(
                    "<b>Добавить территорию</b> – создается в корне"
                    " иерархии (доступно всегда, независимо от выделения)")
                continue
            if not ok:
                # Задача 4: подсказки учитывают правило «соседа» – кнопка
                # активна и для объекта того же типа.
                # Задача 6.1 (сессия 13, LOCKED): единый скобочный шаблон
                # «Добавить X (выделите Y)» вместо тире
                need = {"building": "территорию или здание",
                        "compartment": "здание или пожарный отсек",
                        "room": "здание, отсек или помещение",
                        "area": "помещение или участок",
                        "outdoor": "территорию"}.get(kind, "родителя")
                b.setToolTip(f"{_ADD_LABELS[kind]} (выделите {need})")
            else:
                b.setToolTip(f"<b>{_ADD_LABELS[kind]}</b>"
                             "<br>(доступно при выборе: "
                             + (selected_title or "всегда") + ")")

    def set_tree_add_enabled(self, ok: bool) -> None:
        """Задача 6 (сессия 13): гейтинг кнопки «Добавить дерево» –
        активна на участке, наружной установке и помещении (на помещении
        сначала автоматически создается участок); подсказка неактивной
        кнопки – в том же скобочном шаблоне (LOCKED)."""
        self.btn_add_tree.setEnabled(ok)
        if ok:
            self.btn_add_tree.setToolTip(
                "<b>Добавить дерево</b> – логическое дерево событий"
                " (5 типов)<br>на выделенном участке или наружной"
                " установке; на помещении сначала создается участок")
        else:
            self.btn_add_tree.setToolTip(
                "Добавить дерево (выделите участок, наружную установку"
                " или помещение)")


GROUP_TITLE = "Группа сценариев"   # удалено (Задача 3.1); константа –
# только для чтения старых ui-словарей (hierarchy_groups_collapsed)


class _HierTree(QTreeWidget):
    """Задача 3 (сессия 15): drag-and-drop иерархии – причины под
    причину того же списка (И-гейт Q = Q(родитель)×Q(потомок)), отцепление
    на строке сценария), объекты под допустимого родителя (поддерево
    целиком, PARENT_RULES), деревья между владельцами (совпадение типа
    сценария). Задача 2 (сессия 16): отцепление ЧЕТЫРЕМЯ способами –
    строка сценария, строка владельца, ПКМ «Отцепить от родителя»,
    пустое место/крайняя зона строки причины (+подсказка «Отцепить» у
    курсора). Виджет НИКОГО не перемещает сам: валидацию и модельные
    операции делает HierarchyPanel (drop_kind/handle_drop); здесь – старт
    драга, подсветка целей (синяя – допустимо, красная плюс запрещающий
    курсор – нет) и передача дропа панели."""

    def __init__(self, panel: "HierarchyPanel", parent=None):
        super().__init__(parent)
        self._panel = panel
        self._hi: QTreeWidgetItem | None = None
        self._hi_bad = False
        # Задача 2 (сессия 16): подсказка «Отцепить» у курсора во время
        # драга; текст дублируется в атрибуте для офлайн-проверки
        self._detach_hint_on = False
        self._detach_hint_text: str | None = None
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    # ---------- драг ----------
    def startDrag(self, actions):  # noqa: N802
        it = self.currentItem()
        if it is None:
            return
        drag = QDrag(self)
        mime = QMimeData()             # payload не нужен: источник =
        mime.setData(_HIER_MIME, b"1")  # currentItem, цель = itemAt;
        drag.setMimeData(mime)          # метка – фильтр чужих драгов
        # Задача 3 (сессия 16): карточка несет ГЛИФ строки (причины –
        # по списку ГС/ИЗ, объект – по виду, сценарий – event-add) и
        # рисуется с devicePixelRatio экрана (HiDPI-четкость)
        pm, hot = _drag_pixmap(self._panel._row_glyph(it), it.text(0),
                               self._drag_dpr())
        drag.setPixmap(pm)
        drag.setHotSpot(hot)
        drag.exec(Qt.DropAction.MoveAction)  # noqa: RET503

    def _drag_dpr(self) -> float:
        """devicePixelRatio экрана виджета (для карточки переноса);
        запас – 2×, если экран неизвестен (offscreen-платформа)."""
        scr = self.screen() or QApplication.primaryScreen()
        return scr.devicePixelRatio() if scr is not None else 2.0

    def _set_highlight(self, it: QTreeWidgetItem | None, bad: bool) -> None:
        if self._hi is not None:
            self._hi.setBackground(0, QBrush())
        self._hi = it
        self._hi_bad = bad
        if it is not None:
            it.setBackground(0, QBrush(_DROP_BAD_BG if bad else _DROP_OK_BG))
        cur = (Qt.CursorShape.ForbiddenCursor if bad and it is not None
               else Qt.CursorShape.ArrowCursor)
        self.viewport().setCursor(cur)

    def _show_detach_hint(self) -> None:
        """Мини-подсказка «Отцепить» у курсора на допустимой цели
        отцепления (как «Привязать» у справочной ноды на холсте):
        способ отцепления должен быть ЗАМЕТНЫМ. Текст дублируется в
        _detach_hint_text – офлайн-проверка в тестах."""
        if self._detach_hint_on:
            return
        self._detach_hint_on = True
        self._detach_hint_text = "Отцепить"
        scene_tip(QCursor.pos(), "<b>Отцепить</b>", self)

    def _hide_detach_hint(self) -> None:
        if self._detach_hint_on:
            self._detach_hint_on = False
            self._detach_hint_text = None
            hide_scene_tip()

    def dragEnterEvent(self, e) -> None:  # noqa: N802
        # свой драг (источник – это дерево) или драг с меткой (тесты);
        # чужие драги (из других приложений) игнорируются
        if e.source() is self or e.mimeData().hasFormat(_HIER_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e) -> None:  # noqa: N802
        self._set_highlight(None, False)
        self._hide_detach_hint()
        super().dragLeaveEvent(e)

    def dragMoveEvent(self, e) -> None:  # noqa: N802
        # Задача 2 (сессия 16): допустимость зависит и от ПОЗИЦИИ внутри
        # строки (крайние 25% – отцепление, середина – привязка)
        pos = e.position().toPoint()
        target = self.itemAt(pos)
        kind = self._panel.drop_kind(self.currentItem(), target, pos)
        self._set_highlight(target, kind is None)
        if kind is None:
            self._hide_detach_hint()
            e.ignore()
        else:
            if kind == "detach":
                self._show_detach_hint()
            else:
                self._hide_detach_hint()
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:  # noqa: N802
        pos = e.position().toPoint()
        target = self.itemAt(pos)
        self._set_highlight(None, False)
        self._hide_detach_hint()
        if self._panel.drop_kind(self.currentItem(), target, pos) is not None:
            self._panel.handle_drop(self.currentItem(), target, pos)
        e.ignore()      # стандартное перемещение айтемов выключено

# винительный падеж для подписей кнопок «Добавить …» (Задача 6.1:
# точные строки подсказок неактивных кнопок – в скобочном шаблоне)
_ADD_LABELS = {
    TERRITORY: "Добавить территорию",
    BUILDING: "Добавить здание",
    COMPARTMENT: "Добавить пожарный отсек",
    ROOM: "Добавить помещение",
    AREA: "Добавить участок",
    OUTDOOR: "Добавить наружную установку",
}


class HierarchyPanel(QWidget):
    """Панель иерархии: объекты + строки сценариев с ПРИЧИНАМИ детьми
    (Задача 3.1/3.2, сессия 15: «Группа сценариев» и сгруппированные
    строки удалены)."""

    add_requested = Signal(str)                   # kind
    object_selected = Signal(object)              # ObjNode | None
    scenario_selected = Signal(dict)              # {owner_id, tree_id}
    cause_selected = Signal(str, str, str)        # tree_id, gs|iz, cid
    # Задача 1 (сессия 16): (tree_id, kind, cid) выбранных строк причин –
    # чистый выбор причин удаляется КАК ПРИЧИНЫ с зависимыми ветвями
    # (окно и удаление – в MainWindow). Сигнал несет ВЕСЬ список
    # маркеров, а не группу (tree_id, kind): одно окно подтверждения
    # хватает и на выборы из нескольких деревьев/списков
    causes_delete_requested = Signal(list)
    subtree_removed = Signal(list)                # удаленные узлы
    tree_changed = Signal()                       # структура изменилась
    add_tree_requested = Signal(str, str)         # (owner_id, scenario_type)
    status_message = Signal(str)                  # Задача 6: уведомления
    # сигнал props_requested удален (Задача 6, сессия 13): пункт «Свойства»
    # убран из контекстного меню, других потребителей не было

    def __init__(self, objects: ObjectTree, kb: KnowledgeBase,
                 parent=None):
        super().__init__(parent)
        self.objects = objects
        self.kb = kb
        self._selected: ObjNode | None = None
        self._scenario_trees: dict[str, list[TreeModel]] = {}
        self._ctx_map: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        cap = QLabel("ИЕРАРХИЯ ОБЪЕКТОВ")
        cap.setObjectName("caption")
        root.addWidget(cap)

        self.toolbar = HierarchyToolbar()
        self.toolbar.add_requested.connect(self.add_kind)
        self.toolbar.tree_add_requested.connect(self._on_add_tree_button)
        root.addWidget(self.toolbar)

        self.tree = _HierTree(self)
        self.tree.setObjectName("hierTree")
        self.tree.setHeaderHidden(True)
        # §9: усечений не должно быть – полное имя + горизонтальная
        # прокрутка при нехватке места
        self.tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Задача 1 (сессия 12): дизайн-проход – крупные цветные глифы
        # уровней, заметный отступ вложенности, комфортная высота строк
        # (min-height в QSS), мягкое наведение/выделение
        self.tree.setIndentation(20)
        self.tree.setIconSize(QSize(22, 22))
        # Задача 2 (сессия 11): попиксельный скролл (вертикаль и
        # горизонталь) – плавная анимация колеса без «прыжков» по строкам
        self.tree.setVerticalScrollMode(
            QTreeWidget.ScrollMode.ScrollPerPixel)
        self.tree.setHorizontalScrollMode(
            QTreeWidget.ScrollMode.ScrollPerPixel)
        self.tree.verticalScrollBar().setSingleStep(20)
        self.tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemSelectionChanged.connect(self._on_select)
        # Задача 6.2 (сессия 13, LOCKED): Ctrl/Shift-мультивыбор для
        # пакетного удаления (одно окно подтверждения на весь набор)
        self.tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setEditTriggers(
            QTreeWidget.EditTrigger.EditKeyPressed
            | QTreeWidget.EditTrigger.DoubleClicked)
        self.tree.itemChanged.connect(self._on_item_changed)
        # Задача 8 (сессия 12): после раскрытия/сворачивания ширина
        # контента меняется – пересчитываем колонку; Resize вьюпорта –
        # через фильтр (колонка не уже панели)
        self.tree.itemExpanded.connect(lambda _it: self._sync_column_width())
        self.tree.itemCollapsed.connect(lambda _it: self._sync_column_width())
        self.tree.viewport().installEventFilter(self)
        root.addWidget(self.tree, 1)

        QShortcut(QKeySequence("F2"), self.tree,
                  context=Qt.ShortcutContext.WidgetShortcut,
                  activated=self._rename_current)
        # Задача 10 (сессия 12): Delete удаляет выделенный объект, когда
        # фокус в дереве. Реализация – фильтр событий ВЬЮПОРТА (QTreeWidget
        # держит фокус во вьюпорте, а сам перехватывает Delete как
        # «клавишу редактирования» – QShortcut проигрывает этот спор):
        # нажатие Delete перехватывается до вида; пока открыт редактор
        # переименования, события идут в редактор, не во вьюпорт – там
        # Delete правит текст.
        # Задача 6.2 (сессия 13): фильтр ставится РОВНО ОДИН раз – выше по
        # коду уже был installEventFilter; дублирование вызывало повторный
        # вход обработчика Delete (кандидат в механизм «каскада»)
        QShortcut(QKeySequence("Delete"), self.tree,
                  context=Qt.ShortcutContext.WidgetShortcut,
                  activated=self._delete_current)

    # ---------------- построение дерева ----------------
    def eventFilter(self, obj, ev) -> bool:  # noqa: N802
        """Фильтр вьюпорта дерева: (1) Resize – колонка 0 не уже панели
        (Задача 8); (2) нажатие Delete – удалить текущий объект, если
        редактор переименования не открыт (Задача 10)."""
        if obj is self.tree.viewport():
            if ev.type() == QEvent.Type.Resize:
                self._sync_column_width()
                return super().eventFilter(obj, ev)
            if ev.type() == QEvent.Type.KeyPress \
                    and ev.key() == Qt.Key.Key_Delete \
                    and self.tree.state() != \
                    QAbstractItemView.State.EditingState:
                self._delete_current()
                ev.accept()
                return True                # Delete не доходит до вида
        return super().eventFilter(obj, ev)

    def _sync_column_width(self) -> None:
        """Ширина колонки 0 = max(ширина контента, ширина вьюпорта):
        длинные имена НЕ усекаются – ровно тогда, когда контент шире
        панели, появляется горизонтальный ползунок (Shift+колесо,
        плавный, Задача 8). Ширина контента – по метрикам шрифта
        (отступ уровня + колонка глифа + самый широкий текст)."""
        fm = self.tree.fontMetrics()
        ind = self.tree.indentation()
        icon_w = self.tree.iconSize().width() + 6
        widest = 0

        def rec(it: QTreeWidgetItem, depth: int) -> None:
            nonlocal widest
            need = ind * (depth + 1) + icon_w \
                + fm.horizontalAdvance(it.text(0)) + 16
            if need > widest:
                widest = need
            for i in range(it.childCount()):
                rec(it.child(i), depth + 1)

        for i in range(self.tree.topLevelItemCount()):
            rec(self.tree.topLevelItem(i), 0)
        self.tree.setColumnWidth(
            0, max(widest, self.tree.viewport().width()))

    def rebuild(self, scenario_trees: dict[str, list[TreeModel]] | None = None,
                ctx_map: dict | None = None) -> None:
        """Перестроить список; под владельцами – «Группа сценариев».
        Выделение сохраняется (без повторного сигнала выбора).

        Задачи 3/3.1 (сессия 14, LOCKED): состояние раскрытия переживает
        пересборку – перед clear() запоминаются oid СВЕРНУТЫХ объектов и
        oid владельцев свернутых «Групп сценариев», после заполнения
        состояние восстанавливается. Новые/неизвестные узлы раскрыты
        (кроме явно свернутых через collapse_node – новые участки и
        наружные установки). Раньше безусловный expandAll() разворачивал
        всё обратно на каждом клике."""
        if scenario_trees is not None:
            self._scenario_trees = scenario_trees
        if ctx_map is not None:
            self._ctx_map = ctx_map
        keep = self._current_marker()
        collapsed, scen_collapsed, causes_collapsed = \
            self._capture_expansion()
        self.tree.blockSignals(True)
        self.tree.clear()
        for t in self.objects.territories:
            it = self._make_item(t)
            self.tree.addTopLevelItem(it)
            self._fill_children(t, it)
        self._apply_expansion(collapsed, scen_collapsed, causes_collapsed)
        self.tree.blockSignals(False)
        self._restore_selection(keep)
        self._sync_toolbar()
        self._sync_column_width()      # Задача 8: ползунок при широком имени

    def _capture_expansion(self) -> tuple[set[str], set[str], set[tuple]]:
        """Снять состояние раскрытия: (oid свернутых объектов, tree_id
        свернутых строк сценариев, (tree_id, cid) свернутых строк
        причин). Задача 3 (сессия 15): «Группа сценариев» удалена –
        строки сценариев и причин раскрываются/сворачиваются сами и
        переживают пересборки; ключи стабильны (tree_id/cid)."""
        collapsed: set[str] = set()
        scen: set[str] = set()
        causes: set[tuple] = set()

        def rec(it: QTreeWidgetItem) -> None:
            oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
            data = it.data(0, Qt.ItemDataRole.UserRole)
            if oid:
                if not it.isExpanded():
                    collapsed.add(oid)
            elif isinstance(data, dict):
                if data.get("cause"):
                    if not it.isExpanded():
                        causes.add((data.get("tree_id", ""),
                                    data.get("cid", "")))
                elif data.get("tree_id") and not it.isExpanded():
                    scen.add(data["tree_id"])
            for i in range(it.childCount()):
                rec(it.child(i))

        for i in range(self.tree.topLevelItemCount()):
            rec(self.tree.topLevelItem(i))
        return collapsed, scen, causes

    def _apply_expansion(self, collapsed: set[str],
                         scen: set[str], causes: set[tuple]) -> None:
        """Восстановить раскрытие: всё раскрыто, КРОМЕ попавших в наборы
        (сигналы уже заблокированы – без лишних пересчетов)."""

        def rec(it: QTreeWidgetItem) -> None:
            oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
            data = it.data(0, Qt.ItemDataRole.UserRole)
            if oid:
                it.setExpanded(oid not in collapsed)
            elif isinstance(data, dict):
                if data.get("cause"):
                    it.setExpanded((data.get("tree_id", ""),
                                    data.get("cid", "")) not in causes)
                elif data.get("tree_id"):
                    it.setExpanded(data["tree_id"] not in scen)
            for i in range(it.childCount()):
                rec(it.child(i))

        for i in range(self.tree.topLevelItemCount()):
            rec(self.tree.topLevelItem(i))

    def collapse_node(self, node: ObjNode) -> None:
        """Задача 3 (LOCKED): свернуть узел объекта в дереве – новые
        участки и наружные установки добавляются СВЕРНУТЫМИ (переживает
        следующие пересборки через _capture_expansion)."""
        it = self._item_of(node)
        if it is not None:
            it.setExpanded(False)

    def collapsed_ids(self) -> list[str]:
        """Задача 3 (LOCKED 11б): oid свернутых объектов – для записи в
        файл проекта (ui-словарь формата 5)."""
        collapsed, _scen, _causes = self._capture_expansion()
        return sorted(collapsed)

    def collapsed_group_ids(self) -> list[str]:
        """tree_id свернутых строк сценариев (ui-словарь; имя ключа
        историческое – «hierarchy_groups_collapsed»)."""
        _collapsed, scen, _causes = self._capture_expansion()
        return sorted(scen)

    def collapsed_cause_ids(self) -> list[list[str]]:
        """(tree_id, cid) свернутых строк причин (ui-словарь, новое
        опциональное поле – старые файлы его не имеют)."""
        _collapsed, _scen, causes = self._capture_expansion()
        return sorted([t, c] for t, c in causes)

    def apply_collapsed(self, ids: list[str],
                        group_ids: list[str] | None = None,
                        cause_ids: list | None = None) -> None:
        """Задача 3 (LOCKED 11б): применить сохраненное состояние
        раскрытия после открытия проекта (неизвестные id игнорируются;
        group_ids = tree_id строк сценариев, cause_ids = пары
        [tree_id, cid] строк причин)."""
        want = {str(x) for x in ids or []}
        want_scen = {str(x) for x in group_ids or []}
        want_causes = {(str(t), str(c))
                       for t, c in (cause_ids or [])}
        for it, oid, data in self._iter_items():
            if oid and oid in want:
                it.setExpanded(False)
            elif isinstance(data, dict):
                if data.get("cause"):
                    if (data.get("tree_id", ""), data.get("cid", "")) \
                            in want_causes:
                        it.setExpanded(False)
                elif data.get("tree_id") in want_scen:
                    it.setExpanded(False)
        self._sync_column_width()

    def _iter_items(self):
        """Все QTreeWidgetItem-ы дерева: (item, oid, data-словарь
        строки сценария/причины)."""

        def rec(it):
            oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
            data = it.data(0, Qt.ItemDataRole.UserRole)
            yield it, oid, (data if isinstance(data, dict) else None)
            for i in range(it.childCount()):
                yield from rec(it.child(i))

        for i in range(self.tree.topLevelItemCount()):
            yield from rec(self.tree.topLevelItem(i))

    def _current_marker(self):
        """Маркер текущего выделения: (oid) или сценарий-словарь."""
        it = self.tree.currentItem()
        if it is None:
            return None
        data = it.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            return ("scenario", data)
        oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
        return ("oid", oid) if oid else None

    def _restore_selection(self, marker) -> None:
        if marker is None:
            return
        kind, payload = marker
        it = self._find_item(lambda it: (
            (kind == "scenario"
             and it.data(0, Qt.ItemDataRole.UserRole) == payload)
            or (kind == "oid"
                and it.data(0, Qt.ItemDataRole.UserRole + 1) == payload)))
        if it is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(it)
            self.tree.blockSignals(False)

    def _find_item(self, pred):
        def rec(it):
            if pred(it):
                return it
            for i in range(it.childCount()):
                r = rec(it.child(i))
                if r is not None:
                    return r
            return None
        for i in range(self.tree.topLevelItemCount()):
            r = rec(self.tree.topLevelItem(i))
            if r is not None:
                return r
        return None

    def _fill_children(self, node: ObjNode, parent_it: QTreeWidgetItem) -> None:
        for ch in node.children:
            it = self._make_item(ch)
            parent_it.addChild(it)
            self._fill_children(ch, it)
        if node.kind in TREE_OWNER_KINDS:
            self._add_scenario_rows(node, parent_it)

    # ---------- строки сценариев и причин (Задача 3.1/3.2) ----------
    def _add_scenario_rows(self, owner: ObjNode,
                           parent_it: QTreeWidgetItem) -> None:
        """Под владельцем – по одной строке на дерево (тип сценария),
        детьми – причины пользователя: ГС с префиксом «Образование ГС:»,
        ИЗ – коротким названием; зависимые ветви – под своей родительской
        строкой (цепи любой глубины, Задача 3.3)."""
        trees = self._scenario_trees.get(owner.id, [])
        ctx = self._ctx_map.get(owner.id)
        for tree in trees:
            st = self.kb.scenario_type_by_id(tree.scenario_type) or {}
            scen = QTreeWidgetItem([st.get("title", tree.scenario_type)])
            # Сессия 15/1: ItemIsSelectable ОБЯЗАТЕЛЕН – Qt не начинает
            # перетаскивание (и не делает строку текущей по клику) с
            # невыбираемых айтемов; до этого реальная мышь не таскала
            # вовсе, а тесты проходили через программный setCurrentItem
            scen.setFlags(Qt.ItemFlag.ItemIsEnabled
                          | Qt.ItemFlag.ItemIsSelectable
                          | Qt.ItemFlag.ItemIsDragEnabled)
            scen.setData(0, Qt.ItemDataRole.UserRole,
                         {"owner_id": owner.id, "tree_id": tree.tree_id})
            if ctx is not None:
                scen.setToolTip(0, "Q = "
                                + fmt_q(tree.total_q(self.kb, ctx))
                                + " год⁻¹")
            scen.setIcon(0, glyph_icon(GLYPH_EVENT_ADD))
            parent_it.addChild(scen)
            self._add_cause_rows(tree, scen, gs=True)
            self._add_cause_rows(tree, scen, gs=False)

    def _cause_row_title(self, c, gs: bool) -> str:
        rec = (self.kb.gs_by_id(c.ref) if gs
               else self.kb.iz_by_id(c.ref)) or {}
        t = rec.get("title", c.ref)
        if gs and c.flow and self.kb.flow_titles.get(c.flow):
            t += f" – {self.kb.flow_titles[c.flow]}"
        return t

    def _add_cause_rows(self, tree: TreeModel, scen_it: QTreeWidgetItem,
                        gs: bool) -> None:
        causes = tree.gs_causes if gs else tree.iz_causes
        prefix = "Образование ГС: " if gs else ""
        kind = "gs" if gs else "iz"
        made: dict[str, QTreeWidgetItem] = {}
        placing: set[str] = set()

        def make(c) -> QTreeWidgetItem:
            it = QTreeWidgetItem([prefix + self._cause_row_title(c, gs)])
            # Сессия 15/1: selectable – см. комментарий у строки сценария
            it.setFlags(Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsDragEnabled)
            it.setData(0, Qt.ItemDataRole.UserRole,
                       {"cause": True, "owner_id": tree.owner_id,
                        "tree_id": tree.tree_id, "kind": kind,
                        "cid": c.cid})
            # Сессия 16, Задача 4: у списков причин РАЗНЫЕ глифы –
            # ГС = облако (янтарь), ИЗ = пламя (красный); цвета =
            # классы нод холста (одна семантика – один цвет)
            it.setIcon(0, glyph_icon(GLYPH_GS_CAUSE if gs
                                     else GLYPH_IZ_CAUSE))
            it.setToolTip(0, "Зависимая ветвь: Q = Q(родитель) × Q(потомок)"
                          if c.parent else "Причина сценария")
            return it

        def place(c) -> QTreeWidgetItem:
            if c.cid in made:
                return made[c.cid]
            it = make(c)
            made[c.cid] = it
            parent_c = next((x for x in causes if x.cid == c.parent), None)
            # циклы (внешние правки файлов) разрываются: строка висит
            # верхним уровнем у сценария
            if parent_c is not None and parent_c.cid not in placing \
                    and parent_c.cid != c.cid:
                placing.add(c.cid)
                place(parent_c).addChild(it)
                placing.discard(c.cid)
            else:
                scen_it.addChild(it)
            return it

        for c in causes:
            place(c)

    def _expand_scenario_groups(self) -> None:
        """Совместимость: «Группа сценариев» удалена (Задача 3.1) –
        метод пуст, состояние раскрытия управляется _apply_expansion."""

    def _make_item(self, node: ObjNode) -> QTreeWidgetItem:
        it = QTreeWidgetItem([node.title])
        # Задача 3.4: объекты перетаскиваются (reparenting поддерева)
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable
                    | Qt.ItemFlag.ItemIsDragEnabled)
        it.setData(0, Qt.ItemDataRole.UserRole + 1, node.id)
        it.setToolTip(0, node.path_title())
        it.setIcon(0, glyph_icon(_kind_glyph(node.kind)))
        return it

    def _row_glyph(self, it) -> str | None:
        """Глиф строки для карточки переноса (Задача 3, сессия 16):
        причины – по списку (ГС = облако, ИЗ = пламя), строка
        сценария – event-add, объект – по виду; неизвестное – None
        (карточка без глифа)."""
        data = it.data(0, Qt.ItemDataRole.UserRole) if it is not None \
            else None
        if isinstance(data, dict):
            if data.get("cause"):
                return GLYPH_GS_CAUSE if data.get("kind") == "gs" \
                    else GLYPH_IZ_CAUSE
            return GLYPH_EVENT_ADD
        oid = it.data(0, Qt.ItemDataRole.UserRole + 1) if it is not None \
            else None
        node = self.objects.by_id(oid) if oid else None
        return _kind_glyph(node.kind) if node is not None else None

    # ---------------- выбор ----------------
    def _on_select(self) -> None:
        it = self.tree.currentItem()
        if it is None:
            self.object_selected.emit(None)
            self._sync_toolbar()
            return
        data = it.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):          # строка сценария / причина
            if data.get("cause"):
                # Задача 3.6: клик по строке причины – дерево остается на
                # холсте, инспектор открывает форму ноды ГС/ИЗ, нода
                # холста получает пунктирное выделение
                self.cause_selected.emit(data.get("tree_id", ""),
                                         data.get("kind", ""),
                                         data.get("cid", ""))
            else:
                self.scenario_selected.emit(data)
            self._sync_toolbar()
            return
        oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
        node = self.objects.by_id(oid) if oid else None
        if node is not None:
            # Задача 2 (сессия 14): выбор УЖЕ сделан кликом в дереве –
            # currentItem/selectedItems верны; setCurrentItem здесь
            # делал ClearAndSelect и СТИРАЛ Ctrl/Shift-мультивыбор.
            # Обновляется только панельное состояние (без сигналов).
            self._selected = node
            self.object_selected.emit(node)
        self._sync_toolbar()

    def select_object(self, node: ObjNode | None, emit: bool = True) -> None:
        self._selected = node
        # синхронизировать и дерево (программный выбор = клик в списке):
        # иначе после rebuild текущий элемент потеряется.
        # Задача 4 (сессия 17): в режиме ExtendedSelection setCurrentItem
        # НЕ снимает прежнее выделение – копирование/удаление видели бы
        # НАКОПЛЕННЫЙ мультивыбор; программный выбор всегда ОДИН объект
        # (снятие выделения + установка текущего, сигналы заблокированы)
        if node is not None:
            it = self._item_of(node)
            if it is not None:
                self.tree.blockSignals(True)
                self.tree.clearSelection()
                self.tree.setCurrentItem(it)
                self.tree.blockSignals(False)
        else:
            # Задача 4: очистка выбора – и текущий элемент дерева тоже,
            # иначе гейтинг кнопок «видит» устаревшее выделение
            self.tree.blockSignals(True)
            self.tree.clearSelection()
            self.tree.setCurrentItem(None)
            self.tree.blockSignals(False)
        if emit:
            self.object_selected.emit(node)
        self._sync_toolbar()

    def selected(self) -> ObjNode | None:
        return self._selected

    def selected_owner(self) -> ObjNode | None:
        """Владелец деревьев (участок/установка) для потока из БД."""
        if self._selected is None:
            return None
        if self._selected.kind in TREE_OWNER_KINDS:
            return self._selected
        return None

    def _gating_target(self) -> ObjNode | None:
        """Объект, по которому гейтятся кнопки панели (Задача 4):
        выделенный объект; строки сценариев и причин – как выбор их
        владельца (участка/установки)."""
        it = self.tree.currentItem()
        if it is not None:
            data = it.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                owner_id = data.get("owner_id", "")
                return self.objects.by_id(owner_id) if owner_id else None
            oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
            if oid:
                return self.objects.by_id(oid)
        return self._selected

    def _sync_toolbar(self) -> None:
        """Задача 4: «Добавить X» активен, если выделен (а) сам X –
        тогда создается СОСЕД X под тем же родителем, или (б) допустимый
        родитель X – ребёнок, как раньше. Наружная установка и территория
        сохраняют прежние правила (установка – только в территорию)."""
        kinds = {TERRITORY}
        target = self._gating_target()
        if target is not None:
            k = target.kind
            for kind, parents in (
                    (BUILDING, {TERRITORY}), (COMPARTMENT, {BUILDING}),
                    (ROOM, {BUILDING, COMPARTMENT}), (AREA, {ROOM}),
                    (OUTDOOR, {TERRITORY})):
                if k in parents:
                    kinds.add(kind)              # ребёнок под выделенным
            if k in (BUILDING, COMPARTMENT, ROOM, AREA):
                kinds.add(k)                     # сосед того же типа
        # Задача 6 (сессия 13): «Добавить дерево» – на участке/установке
        # напрямую, на ПОМЕЩЕНИИ – с автосозданием участка (обработчик)
        self.toolbar.set_tree_add_enabled(
            target is not None and target.kind in (AREA, OUTDOOR, ROOM))
        self.toolbar.set_available(kinds,
                                   target.title if target else None)

    # ---------------- добавление/удаление ----------------
    def _on_add_tree_button(self) -> None:
        """Задача 6 (сессия 13, LOCKED): меню пяти типов сценариев у
        кнопки «Добавить дерево»; выбранный тип уходит в _add_tree_for
        (отдельный метод – тестируемый шов без модального меню)."""
        target = self._gating_target()
        if target is None or target.kind not in (AREA, OUTDOOR, ROOM):
            return
        menu = QMenu(self)
        by_action = {}
        for st in SCENARIO_TYPES:
            rec = self.kb.scenario_type_by_id(st) or {}
            act = menu.addAction(glyph_icon(GLYPH_EVENT_ADD),
                                 rec.get("title", st))
            by_action[act] = st
        btn = self.toolbar.btn_add_tree
        chosen = menu.exec(btn.mapToGlobal(QPoint(0, btn.height() + 4)))
        if chosen is not None:
            self._add_tree_for(by_action[chosen])

    def _add_tree_for(self, stype: str) -> None:
        """Участок/наружная установка – дерево создается на них сразу;
        ПОМЕЩЕНИЕ – сначала автоматически создается «Участок N»
        (уведомление в статус-баре), дерево – на нем; выбранным
        становится новый участок (форма строится – умолчания пишутся
        в props по инварианту Задачи 2)."""
        target = self._gating_target()
        if target is None or target.kind not in (AREA, OUTDOOR, ROOM):
            return
        if target.kind == ROOM:
            node = self.objects.add_child(AREA, target)
            st_rec = self.kb.scenario_type_by_id(stype) or {}
            self.status_message.emit(
                f"Создан {node.title} – на нём создано дерево"
                f" «{st_rec.get('title', stype)}»")
            self.add_tree_requested.emit(node.id, stype)
            self.tree_changed.emit()
            self.rebuild()
            self.select_object(node, emit=True)
            self.collapse_node(node)   # Задача 3 (LOCKED): авто-участок свернут
        else:
            self.add_tree_requested.emit(target.id, stype)

    def add_kind(self, kind: str) -> None:
        """Задача 4: выделен объект того же типа – СОСЕД под тем же
        родителем; выделен допустимый родитель – ребёнок, как раньше.
        Задача 1 (сессия 14): территория ВСЕГДА создается в КОРНЕ
        иерархии, независимо от выделения (раньше уходила ребёнком к
        выделенному объекту – механизм вложенных территорий).
        Задача 3 (LOCKED): новые участки и наружные установки
        добавляются СВЕРНУТЫМИ (остальные новые объекты – раскрыты)."""
        target = self._gating_target()
        parent = None
        if kind == TERRITORY:
            parent = None                # только корень иерархии
        elif target is not None:
            if target.kind == kind and kind != OUTDOOR:
                parent = target.parent       # сосед (не территория)
            else:
                parent = target              # ребёнок (валидация в can_add)
        try:
            node = self.objects.add_child(kind, parent)
        except ValueError as exc:
            QMessageBox.information(self, "Иерархия", str(exc))
            return
        self._selected = node               # гейтинг/инспектор – сразу
        self.object_selected.emit(node)     # инспектор + _refresh (облегч.)
        self.tree_changed.emit()            # _refresh (полная пересборка)
        self.rebuild()
        # Задача 10 (сессия 12): currentItem – на НОВЫЙ узел (select_object
        # выше бежал до пересборки, когда узла в дереве ещё не было –
        # currentItem оставался пуст и Delete в дереве его не видел)
        self.select_object(node, emit=False)
        if kind in (AREA, OUTDOOR):
            self.collapse_node(node)        # Задача 3 (LOCKED)
        self._edit_item_of(node)

    def delete_object(self, node: ObjNode) -> None:
        """Удалить один объект с поддеревом (обычное окно подтверждения)."""
        self._delete_objects([node])

    def delete_objects(self, nodes: list[ObjNode]) -> None:
        """Пакетное удаление выбранных объектов (Задача 6.2, LOCKED):
        дедупликация потомков + ОДНО окно со списком названий."""
        self._delete_objects(nodes)

    def _delete_objects(self, nodes: list[ObjNode]) -> None:
        """Задача 6.2 (сессия 13, LOCKED): удаляется ТОЛЬКО выбранное
        (плюс потомки) – никогда ничего выше выбора. Один объект –
        обычное окно, несколько – ОДНО окно со списком. Выбор дерева
        сбрасывается явно (без сигналов) ДО удаления: во время
        пересборок currentItem пуст, и авто-повтор Delete либо гонки
        восстановления выбора не могут зацепить родителя – механизм
        «каскада до территории» закрыт."""
        nodes = self._dedupe_ancestors(nodes)
        if not nodes:
            return
        if len(nodes) == 1:
            if not self._confirm_delete(nodes[0]):
                return
        elif not self._confirm_multi_delete(nodes):
            return
        self._selected = None
        self.tree.blockSignals(True)
        self.tree.clearSelection()
        self.tree.setCurrentItem(None)
        self.tree.blockSignals(False)
        removed: list[ObjNode] = []
        for n in nodes:
            removed.extend(n.walk())
            self.objects.remove_subtree(n)
        self.subtree_removed.emit(removed)
        self.tree_changed.emit()
        self.rebuild()
        self.object_selected.emit(None)

    def _confirm_delete(self, node: ObjNode) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle("Удаление элемента иерархии")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Удалить «{node.title}» со всем поддеревом"
                    " (включая деревья сценариев)?")
        b_del = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        # «Удалить» – по умолчанию и в фокусе (сессия 10, Задача 8)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    def _confirm_multi_delete(self, nodes: list[ObjNode]) -> bool:
        """Задача 6.2 (LOCKED): ОДНО окно на пакет – все названия
        списком, кнопка «Удалить» по умолчанию (шов для тестов)."""
        box = QMessageBox(self)
        box.setWindowTitle("Удаление элементов иерархии")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Удалить {len(nodes)} объектов с поддеревьями?")
        names = "\n".join(f"• {n.title}" for n in nodes[:10])
        if len(nodes) > 10:
            names += f"\n… и ещё {len(nodes) - 10}"
        box.setInformativeText(names)
        b_del = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    def _selection_objects(self) -> list[ObjNode]:
        """Объекты РЕАЛЬНО выбранных строк-объектов (дедупликация,
        стабильный порядок сверху вниз; БЕЗ фолбэка на _selected)."""
        nodes: list[ObjNode] = []
        seen: set[str] = set()
        for it in self.tree.selectedItems():
            oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
            node = self.objects.by_id(oid) if oid else None
            if node is not None and node.id not in seen:
                seen.add(node.id)
                nodes.append(node)
        return nodes

    def _selection_causes(self) -> list[tuple[str, str, str]]:
        """Маркеры ВЫБРАННЫХ строк причин: (tree_id, kind, cid),
        дедупликация, стабильный порядок сверху вниз. Задача 1 (сессия
        16): чистый выбор причин удаляется как причины, а не объект."""
        out: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for it in self.tree.selectedItems():
            data = it.data(0, Qt.ItemDataRole.UserRole)
            if not (isinstance(data, dict) and data.get("cause")):
                continue
            m = (data.get("tree_id", ""), data.get("kind", ""),
                 data.get("cid", ""))
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out

    def selected_causes(self) -> list[tuple[str, str, str]]:
        """Маркеры выбранных строк причин (шов для мусорки главного
        окна и тестов)."""
        return self._selection_causes()

    def _scenario_rows_selected(self) -> bool:
        """В выборе (или текущей строкой) есть строки сценариев –
        безопасный no-op для Delete/мусорки (LOCKED, сессия 16)."""
        def _is_scen(it) -> bool:
            data = it.data(0, Qt.ItemDataRole.UserRole)
            return isinstance(data, dict) and not data.get("cause")

        for it in self.tree.selectedItems():
            if _is_scen(it):
                return True
        cur = self.tree.currentItem()
        return cur is not None and _is_scen(cur)

    def has_tree_rows_selected(self) -> bool:
        """В выборе иерархии есть строки сценариев/причин (главное окно
        запрещает легаси-удаление единственного дерева из ниоткуда)."""
        return bool(self._selection_causes()) or self._scenario_rows_selected()

    def _selected_deletable_nodes(self) -> list[ObjNode]:
        """Объекты иерархии для удаления/мусорки (Задача 1, сессия 16):
        только из РЕАЛЬНО выбранных строк-объектов; легаси-фолбэк на
        панельный `_selected` (выбор пуст после пересборки/удаления –
        удалить панельный объект, пока жив) работает ТОЛЬКО для чистых
        объектных потоков: в выборе нет строк причин/сценариев. Раньше
        фолбэк срабатывал на выборе строк причин и молча удалял УЧАСТОК
        (баг класса потери данных)."""
        nodes = self._selection_objects()
        if nodes:
            return nodes
        if self._selection_causes() or self._scenario_rows_selected():
            return []          # причины/сценарии – фолбэк запрещен
        if self._selected is not None \
                and self.objects.by_id(self._selected.id) is self._selected:
            return [self._selected]
        return []

    @staticmethod
    def _dedupe_ancestors(nodes: list[ObjNode]) -> list[ObjNode]:
        """Убрать узлы, являющиеся потомками других выбранных – их
        удалит удаление предка (дедупликация пакета)."""
        return [n for n in nodes
                if not any(o is not n and n.is_descendant_of(o)
                           for o in nodes)]

    # ---------------- переименование ----------------
    def _edit_item_of(self, node: ObjNode) -> None:
        it = self._item_of(node)
        if it is not None:
            self.tree.editItem(it, 0)

    def _item_of(self, node: ObjNode) -> QTreeWidgetItem | None:
        def rec(it):
            if it.data(0, Qt.ItemDataRole.UserRole + 1) == node.id:
                return it
            for i in range(it.childCount()):
                r = rec(it.child(i))
                if r is not None:
                    return r
            return None
        for i in range(self.tree.topLevelItemCount()):
            r = rec(self.tree.topLevelItem(i))
            if r is not None:
                return r
        return None

    def _rename_current(self) -> None:
        it = self.tree.currentItem()
        if it is not None and it.flags() & Qt.ItemFlag.ItemIsEditable:
            self.tree.editItem(it, 0)

    def _delete_current(self) -> None:
        """Delete в дереве иерархии (Задача 1, сессия 16): выбранные
        ОБЪЕКТЫ удаляются как раньше (одно окно на пакет; в смешанном
        выборе – только объекты, строки причин игнорируются); ЧИСТЫЙ
        выбор строк причин удаляется КАК ПРИЧИНЫ с зависимыми ветвями
        (окно и удаление – MainWindow через causes_delete_requested;
        объект-владелец не затрагивается никогда); текущая строка
        сценария – безопасный no-op. Пустой выбор – легаси-фолбэк:
        панельный объект, пока жив."""
        if self.tree.state() == QAbstractItemView.State.EditingState:
            return                      # редактор переименования ест Delete
        nodes = self._selection_objects()
        if nodes:
            self._delete_objects(self._dedupe_ancestors(nodes))
            return
        causes = self._selection_causes()
        if causes:
            self.causes_delete_requested.emit(causes)
            return
        if self._scenario_rows_selected():
            return          # строки сценариев: без окна и без удаления
        if self._selected is not None \
                and self.objects.by_id(self._selected.id) is self._selected:
            self._delete_objects([self._selected])

    def selected_objects(self) -> list[ObjNode]:
        """Все выбранные объекты иерархии (для мусорки/гейтинга)."""
        return self._selected_deletable_nodes()

    # ---------------- drag-and-drop (Задачи 3.3/3.4/3.5) ----------------
    def _tree_by_id(self, tree_id: str) -> TreeModel | None:
        for trees in self._scenario_trees.values():
            for t in trees:
                if t.tree_id == tree_id:
                    return t
        return None

    def _cause_by_cid(self, tree: TreeModel, kind: str, cid: str):
        causes = tree.gs_causes if kind == "gs" else tree.iz_causes
        return next((c for c in causes if c.cid == cid), None)

    def _scen_row_of(self, tree_id: str):
        """Строка сценария по tree_id (сессия 15/1 – общий помощник)."""
        for it, _oid, data in self._iter_items():
            if data and not data.get("cause") \
                    and data.get("tree_id") == tree_id:
                return it
        return None

    def _reveal_cause(self, tree_id: str, kind: str, cid: str,
                      parent_cid: str | None) -> None:
        """Сессия 15/1: после дропа – целевая строка (родитель) раскрыта,
        перенесенная строка выделена и видна (scrollToItem)."""
        row = self._cause_row_of(tree_id, kind, cid)
        if row is None:
            return
        if parent_cid:
            par = self._cause_row_of(tree_id, kind, parent_cid)
            if par is not None:
                par.setExpanded(True)
        self.tree.scrollToItem(row)
        self.tree.setCurrentItem(row)

    def _cause_row_of(self, tree_id: str, kind: str, cid: str):
        for it, _oid, data in self._iter_items():
            if data and data.get("cause") and data.get("tree_id") == tree_id \
                    and data.get("kind") == kind and data.get("cid") == cid:
                return it
        return None

    def _cause_descendant_cids(self, tree: TreeModel, kind: str,
                               cid: str) -> set[str]:
        """cid причины и всех её потомков (защита от циклов при драге)."""
        causes = tree.gs_causes if kind == "gs" else tree.iz_causes
        cids = {cid}
        grew = True
        while grew:
            grew = False
            for c in causes:
                if c.parent in cids and c.cid not in cids:
                    cids.add(c.cid)
                    grew = True
        return cids

    def _drop_zone(self, target_it, pos) -> str:
        """Зона позиции дропа внутри строки (Задача 2, сессия 16):
        «above» – верхние 25 % высоты строки, «below» – нижние 25 %,
        «on» – средние 50 %. Без цели/позиции – «on» (совместимость
        с программными вызовами швов без координат)."""
        if target_it is None or pos is None:
            return "on"
        r = self.tree.visualItemRect(target_it)
        if r.height() <= 0:
            return "on"
        rel = pos.y() - r.top()
        if rel < r.height() * 0.25:
            return "above"
        if rel > r.height() * 0.75:
            return "below"
        return "on"

    def drop_kind(self, drag_it, target_it, pos=None) -> str | None:
        """Тип дропа (Задача 2, сессия 16): «attach» – причина под
        причину ТОГО ЖЕ списка своего дерева (И-гейт), объект под
        допустимого родителя (PARENT_RULES), дерево на другого
        владельца; «detach» – отцепление причины на верхний уровень
        (строка сценария, строка владельца её дерева, пустое место,
        крайние зоны строки причины своего списка – БЕЗ изменения
        порядка строк, LOCKED); None – недопустимо (красная
        подсветка). Причина никогда не покидает свое дерево/список."""
        if drag_it is None or drag_it is target_it:
            return None
        ddata = drag_it.data(0, Qt.ItemDataRole.UserRole)
        tdata = target_it.data(0, Qt.ItemDataRole.UserRole) \
            if target_it is not None else None
        toid = target_it.data(0, Qt.ItemDataRole.UserRole + 1) \
            if target_it is not None else None
        tnode = self.objects.by_id(toid) if toid else None

        # (1) причина (Задача 3.3 + Задача 2 сессии 16)
        if isinstance(ddata, dict) and ddata.get("cause"):
            if target_it is None:
                return "detach"       # пустое место – отцепить (причины)
            if isinstance(tdata, dict):
                same = (tdata.get("tree_id") == ddata.get("tree_id")
                        and tdata.get("kind") == ddata.get("kind"))
                if tdata.get("cause"):
                    if self._drop_zone(target_it, pos) != "on":
                        # крайняя зона строки причины своего списка –
                        # отцепление; порядок строк НЕ меняется (LOCKED)
                        return "detach" if same else None
                    if not same:
                        return None  # только тот же список (ИЗ→ИЗ, ГС→ГС)
                    if tdata.get("cid") == ddata.get("cid"):
                        return None
                    tree = self._tree_by_id(ddata.get("tree_id", ""))
                    if tree is None:
                        return None
                    if tdata.get("cid") in self._cause_descendant_cids(
                            tree, ddata.get("kind", ""),
                            ddata.get("cid", "")):
                        return None
                    return "attach"
                # строка сценария СВОЕГО дерева – отцепление
                if tdata.get("tree_id") == ddata.get("tree_id") \
                        and tdata.get("owner_id") == ddata.get("owner_id"):
                    return "detach"
                return None
            # строка объекта: только ВЛАДЕЛЕЦ дерева причины – отцепить;
            # чужие объекты – красная подсветка (причины не переезжают)
            tree = self._tree_by_id(ddata.get("tree_id", ""))
            if tree is not None and tnode is not None \
                    and tnode.id == tree.owner_id:
                return "detach"
            return None

        # (2) дерево сценариев (Задача 3.5)
        if isinstance(ddata, dict) and ddata.get("tree_id"):
            tree = self._tree_by_id(ddata["tree_id"])
            if tree is not None and tnode is not None \
                    and tnode.kind in TREE_OWNER_KINDS \
                    and tnode.id != tree.owner_id:
                return "attach"
            return None

        # (3) объект иерархии (Задача 3.4)
        doid = drag_it.data(0, Qt.ItemDataRole.UserRole + 1)
        dnode = self.objects.by_id(doid) if doid else None
        if dnode is not None and tnode is not None \
                and tnode is not dnode \
                and not tnode.is_descendant_of(dnode) \
                and self.objects.can_add(dnode.kind, tnode):
            return "attach"
        return None

    def drop_ok(self, drag_it, target_it, pos=None) -> bool:
        """Допустимость дропа (подсветка цели); см. drop_kind –
        программные вызовы без позиции дают зону «on» (совместимость)."""
        return self.drop_kind(drag_it, target_it, pos) is not None

    def handle_drop(self, drag_it, target_it, pos=None) -> None:
        """Модельные операции дропа (Задача 2: отцепление – строка
        сценария/владельца, пустое место, крайняя зона); после каждой –
        tree_changed (полная пересборка и пересчет холста/матрицы/
        статуса)."""
        kind = self.drop_kind(drag_it, target_it, pos)
        if kind is None:
            return
        ddata = drag_it.data(0, Qt.ItemDataRole.UserRole)
        tdata = target_it.data(0, Qt.ItemDataRole.UserRole) \
            if target_it is not None else None
        toid = target_it.data(0, Qt.ItemDataRole.UserRole + 1) \
            if target_it is not None else None
        tnode = self.objects.by_id(toid) if toid else None

        if isinstance(ddata, dict) and ddata.get("cause"):
            tree = self._tree_by_id(ddata["tree_id"])
            cause = self._cause_by_cid(tree, ddata["kind"],
                                       ddata["cid"]) if tree else None
            if cause is None:
                return
            if kind == "attach" and isinstance(tdata, dict) \
                    and tdata.get("cause"):
                cause.parent = tdata["cid"]     # цель = родитель (И-гейт)
                self.status_message.emit(
                    "Зависимая ветвь: Q = Q(родитель) × Q(потомок)")
            else:
                cause.parent = None             # отцепить на верхний уровень
                self.status_message.emit(
                    "Причина отцеплена – независимая")
            self.tree_changed.emit()
            # Сессия 15/1: целевая строка РАСКРЫТА, перенесенная строка
            # ВЫДЕЛЕНА (после пересборки – айтемы новые)
            self._reveal_cause(ddata["tree_id"], ddata["kind"],
                               ddata["cid"],
                               tdata.get("cid")
                               if kind == "attach"
                               and isinstance(tdata, dict) else None)
            return

        if isinstance(ddata, dict) and ddata.get("tree_id"):
            tree = self._tree_by_id(ddata["tree_id"])
            if tree is not None and tnode is not None:
                tree.owner_id = tnode.id
                self.status_message.emit(
                    f"Дерево «{tree.title}» перемещено на «{tnode.title}»")
                self.tree_changed.emit()
                it = self._scen_row_of(tree.tree_id)
                if it is not None:
                    it.setExpanded(True)
                    self.tree.setCurrentItem(it)
            return

        doid = drag_it.data(0, Qt.ItemDataRole.UserRole + 1)
        dnode = self.objects.by_id(doid) if doid else None
        if dnode is not None and tnode is not None:
            # поддерево целиком: дети, деревья (owner_id не меняются),
            # их причины, зависимости, свернутость и смещения – с ним
            self.objects.move_subtree(dnode, tnode)
            self.rebuild()
            self.select_object(dnode, emit=True)   # выбор следует за ним
            self.tree_changed.emit()

    def _on_item_changed(self, it: QTreeWidgetItem, col: int) -> None:
        oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
        if not oid or col != 0:
            return
        node = self.objects.by_id(oid)
        if node is not None and it.text(0).strip():
            old = node.title
            self.objects.rename(node, it.text(0))
            if node.title != old:
                self.tree_changed.emit()
                self._sync_column_width()   # Задача 8: имя могло удлиниться

    # ---------------- контекстное меню ----------------
    def _detach_cause(self, tree_id: str, kind: str, cid: str) -> None:
        """Отцепить причину от родителя (Задача 2, сессия 16):
        parent = None, причина возвращается на верхний уровень под
        строку сценария; пересчет и выделение строки – как при дропе."""
        tree = self._tree_by_id(tree_id)
        cause = self._cause_by_cid(tree, kind, cid) if tree else None
        if cause is None or not cause.parent:
            return
        cause.parent = None
        self.status_message.emit("Причина отцеплена – независимая")
        self.tree_changed.emit()
        self._reveal_cause(tree_id, kind, cid, None)

    def _cause_context_actions(self, it) -> list[tuple[str, object]]:
        """Пункты ПКМ-меню строки причины (Задача 2): «Отцепить от
        родителя» – только когда причина ЗАВИСИМАЯ. Действия строятся
        ОТДЕЛЬНО от показа (menu.exec – только интерактивный путь):
        тесты вызывают колбэки напрямую."""
        data = it.data(0, Qt.ItemDataRole.UserRole) if it is not None \
            else None
        if not (isinstance(data, dict) and data.get("cause")):
            return []
        tree = self._tree_by_id(data.get("tree_id", ""))
        cause = self._cause_by_cid(tree, data.get("kind", ""),
                                   data.get("cid", "")) if tree else None
        if cause is None or not cause.parent:
            return []
        return [("Отцепить от родителя",
                 lambda: self._detach_cause(data.get("tree_id", ""),
                                            data.get("kind", ""),
                                            data.get("cid", "")))]

    def _context_menu(self, pos) -> None:
        """ПКМ: строки причин – «Отцепить от родителя» (Задача 2,
        сессия 16; действия строит _cause_context_actions – шов для
        тестов); объекты – ТОЛЬКО «Переименовать…» и «Удалить с
        поддеревом…» (Задача 6, сессия 13)."""
        it = self.tree.itemAt(pos)
        if it is None:
            return
        data = it.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("cause"):
            acts = self._cause_context_actions(it)
            if not acts:
                return
            menu = QMenu(self)
            by_action = {}
            for title, cb in acts:
                by_action[menu.addAction(title)] = cb
            chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if chosen is not None and chosen in by_action:
                by_action[chosen]()
            return
        oid = it.data(0, Qt.ItemDataRole.UserRole + 1)
        node = self.objects.by_id(oid) if oid else None
        if node is None:
            return
        menu = QMenu(self)
        self.select_object(node, emit=False)
        act_ren = menu.addAction(glyph_icon(GLYPH_PENCIL), "Переименовать…")
        act_del = menu.addAction(glyph_icon(GLYPH_TRASH),
                                 "Удалить с поддеревом…")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen is act_ren:
            self.tree.editItem(it, 0)
        elif chosen is act_del:
            self.delete_object(node)
