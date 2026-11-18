# -*- coding: utf-8 -*-
"""Главное окно Kuji (сессия 10).

Компоновка: слева – иерархия объектов (с «Группой сценариев» под
участками/установками), центр – холст логического дерева (фиксированная
структура из пяти нод), справа – инспектор свойств. Панель «Документ»
(матрица/лист) – в отдельном pop-out окне (сессия 8, сохранено).

Поток данных: иерархия → выбор участка/сценария → деревья TreeModel →
compute_layout → холст и отчет (WYSIWYG). Расчет: Q_участок,k = Σ Q_сценариев
× Kσ (инвариантная формула пяти типов сценариев).
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication,
                                QFileDialog, QHBoxLayout,
                               QLabel, QMainWindow, QMessageBox,
                               QSplitter, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .. import APP_TITLE, __version__
from ..core.filenames import new_session_uid, report_docx_name
from ..core.kb import KnowledgeBase
from ..core.layout import fmt_q
from ..core.matrix import build_matrix
from ..core.model import (GSCause, IZCause, CalcContext, TreeModel,
                          _new_cid, tgm_level_value)
from ..core.objects import (KIND_TITLES, ObjectTree, ObjNode, TERRITORY,
                            TREE_OWNER_KINDS, add_denied_message,
                            tgm_levels)
from ..core.serializer import (UnsupportedFormatError, load_project,
                               save_project)
from . import app_settings as _as
from .canvas import TreeCanvas
from .doc_window import DocumentWindow
from .docview import DocumentView
from .hierarchy_panel import HierarchyPanel
from .inspector_panel import InspectorPanel
from .kb_window import KBWindow
from .latin_keys import install_latin_key_filter
from .left_toolbar import ViewportToolbar

# Задача 4 (сессия 17, LOCKED): глубина истории отмены
UNDO_DEPTH = 50

# Задача 4: действия «Правка» – ЕДИНЫЕ на приложение (родитель – сам
# QApplication), создаются ОДИН раз и dispatch'атся в АКТИВНОЕ окно
# (или последнее созданное). Пер-оконные ApplicationShortcut-действия
# при нескольких окнах дают НЕОДНОЗНАЧНОСТЬ шорткатов (Qt запускает
# действие первого окна) – единый набор её исключает; в реальном
# приложении окно одно, но тестовые прогоны держат несколько окон
_EDIT_ACTIONS: dict | None = None
_ACTIVE_MAIN: "MainWindow | None" = None


def _register_main_window(win: "MainWindow") -> None:
    global _ACTIVE_MAIN
    _ACTIVE_MAIN = win


def _unregister_main_window(win: "MainWindow") -> None:
    global _ACTIVE_MAIN
    if _ACTIVE_MAIN is win:
        _ACTIVE_MAIN = None


def _edit_target() -> "MainWindow | None":
    """Адресат команд «Правка»: последнее созданное живое окно (в
    приложении оно одно; тестовые прогоны держат несколько –
    последним создано то, что сейчас проверяется), иначе активное."""
    m = _ACTIVE_MAIN
    if m is not None and m.isVisible():
        return m
    app = QApplication.instance()
    if app is not None:
        aw = app.activeWindow()
        if isinstance(aw, MainWindow):
            return aw
    return m


def _ensure_edit_actions() -> dict:
    global _EDIT_ACTIONS
    if _EDIT_ACTIONS is not None:
        return _EDIT_ACTIONS
    from PySide6.QtWidgets import QApplication as _QApp
    app = _QApp.instance()
    undo = QAction("Отменить", app)
    undo.setShortcut(QKeySequence.StandardKey.Undo)
    undo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    undo.setStatusTip("Отменить последнее действие (Ctrl+Z)")
    redo = QAction("Вернуть", app)
    redo.setShortcut(QKeySequence.StandardKey.Redo)
    redo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    redo.setStatusTip("Вернуть отменённое действие (Ctrl+Y)")
    copy = QAction("Копировать", app)
    copy.setShortcut(QKeySequence.StandardKey.Copy)
    copy.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    copy.setStatusTip("Копировать выделенные объекты иерархии"
                      " с поддеревьями и деревьями (Ctrl+C)")
    paste = QAction("Вставить", app)
    paste.setShortcut(QKeySequence.StandardKey.Paste)
    paste.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    paste.setStatusTip("Вставить скопированные объекты под выделенный"
                       " элемент (Ctrl+V)")
    undo.triggered.connect(
        lambda: (_edit_target()._undo() if _edit_target() else None))
    redo.triggered.connect(
        lambda: (_edit_target()._redo() if _edit_target() else None))
    copy.triggered.connect(
        lambda: (_edit_target()._copy_selection() if _edit_target()
                 else None))
    paste.triggered.connect(
        lambda: (_edit_target()._paste_clipboard() if _edit_target()
                 else None))
    _EDIT_ACTIONS = {"undo": undo, "redo": redo, "copy": copy,
                     "paste": paste}
    return _EDIT_ACTIONS


def migrate_qsettings() -> None:
    """Одноразовая миграция настроек старого «Freq ETA 533» → «Kuji ETA 533»
    (ключи ui/*; флаг ui/migrated не даёт повторяться)."""
    from PySide6.QtCore import QSettings
    new = QSettings()
    if new.value("ui/migrated", False):
        return
    old = QSettings(QSettings.Format.NativeFormat,
                    QSettings.Scope.UserScope, "GraphiczD", "Freq ETA 533")
    # ВАЖНО (сессия 19): старый магазин читается ЯВНО из реестра, иначе
    # после перевода приложения на INI этот вызов искал бы
    # %APPDATA%\GraphiczD\Freq ETA 533.ini и не нашёл бы ничего.
    for key in old.allKeys():
        if key.startswith("ui/"):
            new.setValue(key, old.value(key))
    new.setValue("ui/migrated", True)
    new.sync()


class MainWindow(QMainWindow):
    def __init__(self, kb: KnowledgeBase, restore_ui: bool = True):
        super().__init__()
        self.kb = kb
        self.objects = ObjectTree()
        self.trees: list[TreeModel] = []
        self._project_path: str = ""
        # Задача 1 (сессия 19, LOCKED): UID несохраненного проекта для
        # имени отчета «Отчет-РЧП-<UID>.docx» – ОДИН на документную
        # сессию (переиспользуется при каждом открытии диалога экспорта),
        # перегенерируется командой «Новый проект» и при перезапуске.
        self._report_uid = new_session_uid()
        # Диалог экспорта модальный: флаг не даёт возобновившейся цепочке
        # ShortcutOverride открыть его второй раз за одно нажатие (сессия 19)
        self._export_running = False
        self._dirty = False
        self._selected_scenario: dict | None = None
        # Задача 1 (сессия 16): нода холста выделена КЛИКОМ ПОЛЬЗОВАТЕЛЯ
        # (true) или программно – пунктиром при клике по строке причины
        # (false). Delete/мусорка удаляют ДЕРЕВО только в первом случае:
        # чистый выбор строк причин удаляет причины, а не дерево
        self._canvas_sel_by_click = False
        # Задача 4 (сессия 17, LOCKED): раскладко-независимость буквенных
        # шорткатов – приложенческий фильтр Ctrl/Alt + кириллица → латиница
        install_latin_key_filter()
        # Задача 4: undo/redo (снапшоты формата 5 в памяти, глубина 50) и
        # буфер обмена иерархии (поддеревья объектов вместе с деревьями)
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []
        self._undo_base: str = ""
        self._undo_reset()
        self._clip: list[dict] = []

        self.setWindowTitle(f"{APP_TITLE} – логические деревья событий"
                            f" (Методика № 533)")
        self.resize(1500, 920)

        # ---------- центр: левая панель инструментов + холст ----------
        self.canvas = TreeCanvas()
        # Задача 2 (сессия 18): Пробел отслеживается на уровне приложения
        # (доставляется только сфокусированному виджету) – холст получает
        # обратную связь «рука» и флаг панорамы
        from .latin_keys import add_space_pan_consumer
        add_space_pan_consumer(self.canvas._app_space_pan)
        self.left_toolbar = ViewportToolbar()
        center = QWidget()
        clay = QHBoxLayout(center)
        clay.setContentsMargins(0, 0, 0, 0)
        clay.setSpacing(0)
        clay.addWidget(self.left_toolbar)
        clay.addWidget(self.canvas, 1)

        # ---------- панель «Документ»: матрица + схематический лист ----------
        self.doc_stack = QStackedWidget()
        self.matrix_table = QTableWidget()
        self.matrix_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        # Задача 2 (сессия 11): попиксельный скролл матрицы – единица
        # прокрутки пиксель, а не строка (плавная анимация колеса)
        self.matrix_table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.matrix_table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.matrix_table.verticalScrollBar().setSingleStep(20)
        self.doc_stack.addWidget(self.matrix_table)
        self.doc_view = DocumentView(self.canvas.controller)
        self.doc_stack.addWidget(self.doc_view)
        self._doc_host = QWidget()          # скрытый хост панели документа
        dh = QVBoxLayout(self._doc_host)
        dh.setContentsMargins(0, 0, 0, 0)
        self._doc_mode_label = QLabel("МАТРИЧНЫЙ ВИД")
        self._doc_mode_label.setObjectName("caption")
        dh.addWidget(self._doc_mode_label)
        dh.addWidget(self.doc_stack)
        self.doc_window: DocumentWindow | None = None

        # ---------- левая панель: иерархия ----------
        self.hierarchy = HierarchyPanel(self.objects, kb)

        # ---------- правая панель: инспектор ----------
        self.inspector = InspectorPanel(kb)
        self.inspector.set_owner_getter(
            lambda: self.hierarchy.selected_owner())

        # Задача 9 (сессия 12): границы трёх панелей перетаскиваемы –
        # QSplitter; минимальные ширины 320/500/360 сохранены, центр
        # растягивается (stretch 1), боковые панели – нет; сворачивание
        # панелей за ползунком запрещено. QSS ручек – theme.py.
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # Задача 1 (сессия 18): имя сплиттера – сохранённое состояние
        # валидируется и переживает любой путь выхода
        self.splitter.setObjectName("mainSplitter")
        for i, (w, min_w) in enumerate(((self.hierarchy, 320),
                                        (center, 500),
                                        (self.inspector, 360))):
            self.splitter.addWidget(self._panel(w, min_w))
            self.splitter.setCollapsible(i, False)
            self.splitter.setStretchFactor(i, 1 if i == 1 else 0)
        self.splitter.setSizes([320, 500, 360])
        # Задача 1 (сессия 18): память панелей – saveState/saveGeometry
        # пишутся не только в closeEvent, но и по splitterMoved с дебаунсом
        # ~300 мс (QTimer singleShot): состояние переживает ЛЮБОЙ выход –
        # крах, убийство процесса, модальный диалог, блокирующий закрытие
        self._ui_save_timer = QTimer(self)
        self._ui_save_timer.setSingleShot(True)
        self._ui_save_timer.setInterval(300)
        self._ui_save_timer.timeout.connect(self._persist_ui_state)
        self.splitter.splitterMoved.connect(
            lambda *_a: self._ui_save_timer.start())
        root = QWidget()
        rlay = QHBoxLayout(root)
        rlay.setContentsMargins(6, 6, 6, 6)
        rlay.setSpacing(0)
        rlay.addWidget(self.splitter)
        self.setCentralWidget(root)

        self.status_label = QLabel("")
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(QLabel(f"v{__version__}"))

        self._build_actions()
        self._wire()
        self._update_title()
        self._refresh()
        # Задача 4: это окно – адресат команд «Правка» (последнее созданное)
        _register_main_window(self)
        if restore_ui:
            self._restore_ui()

    # ============================ каркас ============================
    @staticmethod
    def _panel(widget: QWidget, min_w: int) -> QWidget:
        host = QWidget()
        host.setObjectName("panel")
        host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        host.setMinimumWidth(min_w)
        lay = QHBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(widget)
        return host

    def _build_actions(self) -> None:
        m_file = self.menuBar().addMenu("Файл")
        self.act_new = QAction("Новый проект")
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(self._new_project)
        m_file.addAction(self.act_new)
        self.act_open = QAction("Открыть…")
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._open_project_dialog)
        m_file.addAction(self.act_open)
        self.act_save = QAction("Сохранить")
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._save_project)
        m_file.addAction(self.act_save)
        # Сессия 19 (запрос заказчика 17.11.2026): «Сохранить как…» –
        # канонический Ctrl+Shift+S (StandardKey.SaveAs) плюс кириллический
        # близнец Ctrl+Shift+Ы; на реальной Windows комбинацию доставляет
        # реестр latin_keys (Shift разрешён с сессии 19)
        self.act_save_as = QAction("Сохранить как…")
        self.act_save_as.setShortcuts([
            QKeySequence(QKeySequence.StandardKey.SaveAs),
            QKeySequence("Ctrl+Shift+Ы")])
        self.act_save_as.triggered.connect(self._save_project_as)
        m_file.addAction(self.act_save_as)
        self.act_export = QAction("Экспорт в DOCX…")
        # Задача 3 (сессия 13): латинская + кириллическая (У) –
        # независимость от раскладки; Задача 2 (сессия 18): реестр
        # доставляет Ctrl+E через ShortcutOverride на реальной Windows
        self.act_export.setShortcuts([QKeySequence("Ctrl+E"),
                                      QKeySequence("Ctrl+У")])
        self.act_export.triggered.connect(self._export_docx)
        m_file.addAction(self.act_export)
        m_file.addSeparator()
        act_quit = QAction("Выход")
        act_quit.setShortcuts([QKeySequence("Ctrl+Q"),
                               QKeySequence("Ctrl+Й")])
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        # Задача 4 (сессия 17, LOCKED): меню «Правка» – отмена/возврат и
        # буфер обмена иерархии; ДЕЙСТВИЯ ЕДИНЫЕ на приложение (см.
        # _ensure_edit_actions) – Ctrl+Z/Y/C/V срабатывают в ОБЕИХ
        # раскладках через фильтр latin_keys и без неоднозначности
        # шорткатов при нескольких окнах
        m_edit = self.menuBar().addMenu("Правка")
        _ed = _ensure_edit_actions()
        self.act_undo = _ed["undo"]
        self.act_redo = _ed["redo"]
        self.act_copy = _ed["copy"]
        self.act_paste = _ed["paste"]
        m_edit.addAction(self.act_undo)
        m_edit.addAction(self.act_redo)
        m_edit.addSeparator()
        m_edit.addAction(self.act_copy)
        m_edit.addAction(self.act_paste)

        m_view = self.menuBar().addMenu("Вид")
        self.act_matrix = QAction("Матричный вид")
        self.act_matrix.setCheckable(True)
        self.act_matrix.setChecked(True)
        self.act_matrix.triggered.connect(lambda: self.set_doc_view_mode("matrix"))
        m_view.addAction(self.act_matrix)
        self.act_schema = QAction("Схематический вид (лист)")
        self.act_schema.setCheckable(True)
        self.act_schema.triggered.connect(
            lambda: self.set_doc_view_mode("schematic"))
        m_view.addAction(self.act_schema)
        self.act_doc_window = QAction("Окно «Документ»")
        self.act_doc_window.setShortcuts([QKeySequence("Ctrl+D"),
                                          QKeySequence("Ctrl+В")])
        self.act_doc_window.triggered.connect(self.open_doc_window)
        m_view.addAction(self.act_doc_window)
        # Задача 3 (сессия 13): «Показать всё» не зависит от раскладки
        # клавиатуры: на русской раскладке та же физическая клавиша дает
        # «Ф», а Qt матчит ярлыки по итоговому тексту → регистрируем
        # ЛАТИНСКУЮ и КИРИЛЛИЧЕСКУЮ последовательности-близнецы. Контекст
        # ApplicationShortcut – действие живо и при фокусе в окне Базы
        # данных / pop-out «Документ» (не только в главном окне)
        self.act_fit = QAction("Показать всё")
        self.act_fit.setShortcuts([QKeySequence("Alt+A"),
                                   QKeySequence("Alt+Ф")])
        self.act_fit.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut)
        self.act_fit.triggered.connect(self.canvas.fit_tree)
        m_view.addAction(self.act_fit)
        act_del = QAction("Удалить выделенное")
        act_del.setShortcut(QKeySequence("Delete"))
        act_del.triggered.connect(self._delete_selection)
        self.addAction(act_del)

        m_kb = self.menuBar().addMenu("База данных")
        self.act_kb = QAction("База данных…")
        self.act_kb.setShortcut(QKeySequence("F9"))
        self.act_kb.triggered.connect(self._open_kb_window)
        m_kb.addAction(self.act_kb)

        # Задача 2 (сессия 18): реестр буквенных шорткатов – на реальной
        # Windows Ctrl/Alt+буква доставляется ТОЛЬКО как ShortcutOverride
        # (измерено key_debug.log), кастомные QKeySequence картой шортка-
        # тов не активируются – фильтр latin_keys запускает их сам.
        # StandardKey (Ctrl+N/O/S) работают штатно и в реестр не входят.
        from .latin_keys import register_letter_action
        register_letter_action("Ctrl+E", self, self.act_export)
        register_letter_action("Ctrl+D", self, self.act_doc_window)
        register_letter_action("Ctrl+Q", self, act_quit)
        register_letter_action("Alt+A", self, self.act_fit)
        # Сессия 19: «Сохранить как…» – Ctrl+Shift+S (кириллический
        # близнец Ы доставляется тем же реестром, Shift больше не исключён)
        register_letter_action("Ctrl+Shift+S", self, self.act_save_as)

    def _wire(self) -> None:
        h = self.hierarchy
        h.object_selected.connect(self._on_object_selected)
        h.scenario_selected.connect(self._on_scenario_selected)
        h.cause_selected.connect(self._on_cause_selected)
        # Задача 1 (сессия 16): чистый выбор строк причин – Delete/мусорка
        # удаляют ПРИЧИНЫ с зависимыми ветвями (никогда не объект)
        h.causes_delete_requested.connect(self._on_causes_delete_requested)
        h.add_tree_requested.connect(self._add_tree)
        h.subtree_removed.connect(self._on_subtree_removed)
        h.tree_changed.connect(lambda: self._refresh())
        # Задача 6 (сессия 13): уведомления панели иерархии (автосоздание
        # участка под дерево) – в статус-бар; сигнал props_requested
        # упразднен вместе с пунктом «Свойства» контекстного меню
        h.status_message.connect(
            lambda m: self.statusBar().showMessage(m, 8000))
        # Задача 4 (сессия 17): швы мутаций → точки отката (_undo_push
        # кладет на стек ДО-состояние из _undo_base – момент вызова
        # относительно записи не критичен, повторы коалесцируются)
        h.tree_changed.connect(lambda: self._undo_push())
        self.canvas.node_clicked.connect(self._on_canvas_node)
        self.canvas.empty_clicked.connect(self._on_canvas_empty)
        self.canvas.delete_requested.connect(self._delete_selection)
        # Задача 6 (сессия 17): рамка выделила МНОЖЕСТВО нод – выбор
        # пользователя (как клик), без смены инспектора
        self.canvas.nodes_selected.connect(
            self._on_canvas_nodes_selected)
        # Задача 2 (сессия 19, LOCKED): двойной клик по ноде ГС/ИЗ –
        # «Добавить причину…» для дерева этой ноды (тот же диалог)
        self.canvas.node_add_cause_requested.connect(
            self._on_node_add_cause)
        ins = self.inspector
        ins.object_props_changed.connect(lambda _o: self._refresh())
        ins.object_title_changed.connect(
            lambda _o, _t: self._refresh())
        ins.tree_changed.connect(lambda: self._refresh())
        # Задача 4 (сессия 17): правки свойств/дерева из инспектора –
        # точки отката (после записи; ДО-состояние берется из базы)
        ins.object_props_changed.connect(lambda _o: self._undo_push())
        ins.object_title_changed.connect(
            lambda _o, _t: self._undo_push())
        ins.tree_changed.connect(lambda: self._undo_push())
        # Задача 5 (сессия 14): формы комнаты/участка спрашивают
        # эффективные площадь/тип ТГМ (каскад участок → помещение →
        # здание) у главного окна – единственный источник
        ins.set_tgm_view(self.tgm_view)
        ins.add_gs_requested.connect(self._add_gs_cause)
        ins.remove_gs_requested.connect(self._remove_gs_cause)
        ins.add_iz_requested.connect(self._add_iz_cause)
        ins.remove_iz_requested.connect(self._remove_iz_cause)
        lt = self.left_toolbar
        lt.zoom_in_requested.connect(lambda: self.canvas.zoom(1.25))
        lt.zoom_out_requested.connect(lambda: self.canvas.zoom(1 / 1.25))
        lt.fit_requested.connect(self.canvas.fit_tree)
        lt.doc_window_requested.connect(self._toggle_doc_window)
        lt.delete_requested.connect(self._delete_selection)

        # Задача 12 (сессия 12): режимы «липкий/свободный обзор» – сигнал
        # mode_requested НИЧЕМ не был соединён (регрессия сессии 10):
        # теперь кнопки-переключатели синхронны и режим доходит до холста
        def _apply_mode(mode: str) -> None:
            self.canvas.set_mode(mode)
            self.left_toolbar.set_mode(mode)
            self.canvas.clamp_to_mode()
        lt.mode_requested.connect(_apply_mode)
        # Задача 11: перетаскивание нод и кнопка «Авторазметка»
        lt.autolayout_requested.connect(self._auto_layout)
        self.canvas.tree_offsets_changed.connect(
            self._on_tree_offsets_changed)
        # Задача 4 (сессия 13): перетащили справочную ноду – проект изменен
        # Задача 4 (сессия 17): и точка отката (позиция ноды – в снапшоте)
        self.canvas.annotation_changed.connect(
            lambda: (self._undo_push(), self._mark_dirty()))

    # ============================ контексты ============================
    def ctx_map(self) -> dict[str, CalcContext]:
        """CalcContext для каждого владельца деревьев (участок/установка):
        здание – ближайший предок (или сама установка), помещение –
        ближайший предок, сайт – собственные свойства.

        Задача 5 (сессия 14): tgm_chain – цепочка СОБСТВЕННЫХ props
        уровней каскада ТГМ (objects.tgm_levels): участок → помещение →
        здание; наружная установка – [она сама]. Слитые
        effective_properties остаются для молниезащиты/вентиляции/мер
        (явность значений ТГМ видна только в цепочке уровней)."""
        out: dict[str, CalcContext] = {}
        for owner in self.objects.tree_owners():
            building = owner.nearest("building")
            if building is None and owner.kind == "outdoor":
                building = owner          # установка сама себе «здание»
            room = owner.nearest("room")
            out[owner.id] = CalcContext(
                building_props=(self.objects.effective_properties(building)
                                if building is not None else {}),
                room_props=(self.objects.effective_properties(room)
                            if room is not None else {}),
                site_props=self.objects.effective_properties(owner),
                owner_kind=owner.kind,
                tgm_chain=[dict(lv.props) for lv in tgm_levels(owner)])
        return out

    def tgm_view(self, node) -> dict:
        """Задача 5 (сессия 14): эффективные значения ТГМ для ФОРМ уровня.
        Задача 1 (сессия 15): значение уровня – по его типу (участок/м²,
        линейный м, аппарат м³ – tgm_level_value), первый явный уровень
        цепочки (objects.tgm_levels). Возвращает {f, f_kind, type13,
        type14, t_kind} (None – нигде не задано; *_kind – тип уровня-
        источника для подписи «наследуется от …»)."""
        levels = tgm_levels(node)
        out = {"f": None, "f_kind": None,
               "type13": None, "type14": None, "t_kind": None}
        for lv in levels:
            if out["f"] is None:
                v = tgm_level_value(lv.props)
                if v is not None:
                    out["f"] = v
                    out["f_kind"] = lv.kind
            for key, name in (("p13_type", "type13"),
                              ("p14_type", "type14")):
                if out[name] is None and lv.props.get(key):
                    out[name] = lv.props.get(key)
                    if out["t_kind"] is None:
                        out["t_kind"] = lv.kind
            if out["f"] is not None and out["type13"] is not None \
                    and out["type14"] is not None:
                break
        return out

    def _owner_titles(self) -> dict[str, str]:
        return {o.id: o.title for o in self.objects.tree_owners()}

    def trees_by_owner(self) -> dict[str, list[TreeModel]]:
        out: dict[str, list[TreeModel]] = {}
        for t in self.trees:
            out.setdefault(t.owner_id, []).append(t)
        return out

    def _current_trees(self) -> list[TreeModel]:
        """Деревья, показываемые на холсте: выбранный сценарий → его
        дерево; участок/установка → их деревья; контейнер → деревья
        дочерних владельцев; ничего → все деревья проекта."""
        if self._selected_scenario is not None:
            tid = self._selected_scenario.get("tree_id")
            return [t for t in self.trees if t.tree_id == tid]
        node = self.hierarchy.selected()
        if node is not None:
            owners = self.objects.owners_in(node)
            ids = {o.id for o in owners}
            trees = [t for t in self.trees if t.owner_id in ids]
            return trees
        return list(self.trees)

    # ============================ обновление ============================
    def _refresh(self, rebuild_hierarchy: bool = True) -> None:
        """Обновление панелей. Задача 2 (сессия 14): смена ВЫДЕЛЕНИЯ
        больше НЕ перестраивает дерево иерархии (rebuild_hierarchy=False
        из _on_object_selected/_on_scenario_selected) – Ctrl/Shift-
        мультивыбор переживает клики, свернутые узлы не разворачиваются.
        Структурные изменения всегда идут с полной пересборкой."""
        cmap = self.ctx_map()
        titles = self._owner_titles()
        if rebuild_hierarchy:
            self.hierarchy.rebuild(self.trees_by_owner(), cmap)
        trees = self._current_trees()
        self.canvas.controller.rebuild(trees, self.kb, cmap, titles)
        self.canvas.fit_tree()
        self._refresh_matrix(trees, cmap, titles)
        self._update_status()
        self._update_kb_apply_hint()
        self._update_trash()

    def _refresh_matrix(self, trees, cmap, titles) -> None:
        data = build_matrix(trees, self.kb, cmap, titles)
        self.matrix_table.setColumnCount(len(data.header()))
        self.matrix_table.setHorizontalHeaderLabels(data.header())
        self.matrix_table.setRowCount(len(data.rows))
        for r, row in enumerate(data.rows):
            # Задача 7 (сессия 14): Q – инженерная запись «3,24·10⁻⁶»
            # (раньше сырой «3,240e-06»); формула приходит из матрицы
            # без табличных ссылок и в инженерной записи
            vals = [str(r + 1), row.title, row.scenario_type, row.name,
                    fmt_q(row.q),
                    row.formula]
            for c, v in enumerate(vals):
                self.matrix_table.setItem(r, c, QTableWidgetItem(v))
        self.matrix_table.resizeColumnsToContents()

    def _update_status(self) -> None:
        cmap = self.ctx_map()
        parts = []
        for t in self._current_trees():
            ctx = cmap.get(t.owner_id)
            if ctx is None:
                ctx = CalcContext()
            parts.append(f"{fmt_q(t.total_q(self.kb, ctx))} год⁻¹")
        self.status_label.setText(
            "Q_В: " + ("; ".join(parts) if parts else "–"))

    def _update_kb_apply_hint(self) -> None:
        """Задача 3: «Применить на холсте» активна только при выделенном
        участке или наружной установке."""
        owner = self.hierarchy.selected_owner()
        if self.kb_window is not None:
            self.kb_window.templates_tab.set_owner_available(
                owner is not None, owner.title if owner else "")

    # ============================ выбор ============================
    def _on_object_selected(self, node) -> None:
        self._selected_scenario = None
        if node is not None:
            self._show_object(node)
        # Задача 2 (сессия 14): выбор БЕЗ пересборки дерева – мультивыбор
        # и свернутые узлы переживают клики
        self._refresh(rebuild_hierarchy=False)

    def _on_scenario_selected(self, data: dict) -> None:
        """Строка сценария в иерархии (Задача 3.1: группа и сгруппированные
        строки удалены, строка = дерево): показать его дерево; частота
        дерева – в инспекторе ноды «Возникновение пожара» и статус-баре."""
        self._selected_scenario = data
        tree = next((t for t in self.trees
                     if t.tree_id == data.get("tree_id")), None)
        if tree is not None:
            self.inspector.show_tree_node(tree, "fire")
            cmap = self.ctx_map()
            ctx = cmap.get(tree.owner_id, CalcContext())
            self.status_label.setText(
                f"Сценарий: {tree.title} –"
                f" Q = {fmt_q(tree.total_q(self.kb, ctx))} год⁻¹")
        self._refresh(rebuild_hierarchy=False)

    def _on_cause_selected(self, tree_id: str, kind: str,
                           cid: str) -> None:
        """Задача 3.6 (LOCKED): клик по строке причины – дерево остается
        на холсте (показывается именно оно), инспектор открывает форму
        ноды ГС/ИЗ, нода холста получает пунктирное выделение."""
        tree = next((t for t in self.trees if t.tree_id == tree_id), None)
        if tree is None:
            return
        self._selected_scenario = {"tree_id": tree_id,
                                   "owner_id": tree.owner_id}
        self.inspector.show_tree_node(tree, kind if kind in ("gs", "iz")
                                      else "gs")
        self._refresh(rebuild_hierarchy=False)
        self.canvas.controller.select_node(f"{tree_id}:{kind}")
        # пунктир ноды – ПРОГРАММНОЕ выделение (не клик по холсту):
        # мусорка/Delete удаляют причины, а не дерево этой ноды
        self._canvas_sel_by_click = False
        self._update_trash()

    def _on_canvas_node(self, node_id: str) -> None:
        tree = self.canvas.controller.tree_of_node(node_id)
        kind = self.canvas.controller.node_kind(node_id)
        if tree is not None and kind:
            self.inspector.show_tree_node(tree, kind)
        # выделение ноды поставил КЛИК ПОЛЬЗОВАТЕЛЯ по холсту
        self._canvas_sel_by_click = True
        self._update_trash()

    def _on_node_add_cause(self, tree_id: str, kind: str) -> None:
        """Задача 2 (сессия 19, LOCKED): двойной клик по ноде ГС/ИЗ на
        холсте = кнопка «Добавить причину…» инспектора, но для ДЕРЕВА
        КЛИКНУТОЙ ноды. Диалог, accept-путь и отмена – общие с
        инспектором (`inspector.pick_cause_for` → add_gs_requested /
        add_iz_requested → _add_gs_cause / _add_iz_cause)."""
        if kind not in ("gs", "iz"):
            return
        tree = next((t for t in self.trees if t.tree_id == tree_id), None)
        if tree is None:
            return
        self.inspector.pick_cause_for(tree, kind)

    def _on_canvas_nodes_selected(self, ids: list) -> None:
        """Задача 6 (сессия 17): пользователь выделил ноды рамкой –
        выбор считается СДЕЛАННЫМ ПОЛЬЗОВАТЕЛЕМ (Delete/мусорка
        удаляют деревья-владельцы); инспектор не меняется."""
        self._canvas_sel_by_click = True
        self._update_trash()

    def _on_canvas_empty(self) -> None:
        """Клик по пустому месту холста: снять выделение ноды, показать
        свойства текущего объекта иерархии (как раньше), обновить
        мусорку (Задача 10)."""
        self.canvas.controller.select_node(None)
        self._canvas_sel_by_click = False
        self._show_object(self.hierarchy.selected())
        self._update_trash()

    def _auto_layout(self) -> None:
        """Задача 11: «Авторазметка» – сбросить ручные смещения нод у
        показанных деревьев и пересчитать раскладку (сцена + PDF).
        Задача 4 (сессия 13): привязанные справочные ноды следуют за
        своими нодами автоматически; СВОБОДНЫЕ возвращаются в позицию
        по умолчанию (состояние «без правок»)."""
        trees = self._current_trees()
        dirty = any(t.node_offsets for t in trees) or any(
            t.annotation is not None and t.annotation.get("attached") is None
            for t in trees)
        if not dirty:
            return
        for t in trees:
            t.node_offsets = None
            if t.annotation is not None \
                    and t.annotation.get("attached") is None:
                t.annotation = None
        self._mark_dirty()
        self._refresh()

    def _on_tree_offsets_changed(self) -> None:
        """Перетащили ноду: сцены уже пересобраны холстом (WYSIWYG),
        частоты не изменились – помечаем проект изменённым.
        Задача 4 (сессия 17): смещения нод входят в снапшот – точка
        отката сразу после коммита перетаскивания."""
        self._undo_push()
        self._mark_dirty()

    def _show_object(self, node) -> None:
        if node is not None:
            self.inspector.show_object(node)

    # ============================ деревья ============================
    def _add_tree(self, owner_id: str, scenario_type: str) -> None:
        owner = self.objects.by_id(owner_id)
        if owner is None:
            return
        title = (self.kb.scenario_type_by_id(scenario_type) or {}
                 ).get("title", scenario_type)
        tree = TreeModel(scenario_type, owner_id, title=title)
        self.trees.append(tree)
        self._undo_push()          # Задача 4 (сессия 17)
        self._mark_dirty()
        self._refresh()

    def _remove_trees_of(self, owner_ids: set[str]) -> None:
        self.trees = [t for t in self.trees
                      if t.owner_id not in owner_ids]

    def _on_subtree_removed(self, removed) -> None:
        self._undo_push()          # Задача 4 (сессия 17): до-состояние в базе
        self._remove_trees_of({n.id for n in removed})
        self._selected_scenario = None
        self._mark_dirty()
        self._refresh()

    # причины ГС/ИЗ из инспектора
    def _current_tree(self) -> TreeModel | None:
        if self._selected_scenario is not None:
            tid = self._selected_scenario.get("tree_id")
            return next((t for t in self.trees if t.tree_id == tid), None)
        trees = self._current_trees()
        return trees[0] if len(trees) == 1 else None

    def _inspected_tree(self) -> TreeModel | None:
        """Задача 9 (сессия 15): дерево, чья нода открыта в инспекторе, –
        ВСЕ операции с причинами идут через него (раньше _current_tree()
        при двух и более деревьях одного владельца возвращал None и
        добавление причины молча терялось). Фолбэк – прежний выбор."""
        tree = self.inspector.current_tree()
        if tree is not None and tree in self.trees:
            return tree
        return self._current_tree()

    def _add_gs_cause(self, ref: str, flow: object = None) -> None:
        """Задача 8 (сессия 15): flow – диапазон расхода выбранной строки
        (None – вся запись, как раньше)."""
        tree = self._inspected_tree()
        if tree is not None:
            tree.gs_causes.append(GSCause(ref=ref, flow=flow))
            self._undo_push()      # Задача 4 (сессия 17)
            self.inspector.show_tree_node(tree, "gs")
            self._mark_dirty()
            self._refresh()

    def _cause_subtree(self, causes: list, idx: int) -> list:
        """Задача 3.3: причина по индексу и ВСЕ её потомки («Убрать»
        удаляет ветвь целиком; подтверждение перечисляет цепь)."""
        if not (0 <= idx < len(causes)):
            return []
        root = causes[idx]
        cids = {root.cid}
        grew = True
        while grew:
            grew = False
            for c in causes:
                if c.parent in cids and c.cid not in cids:
                    cids.add(c.cid)
                    grew = True
        return [c for c in causes if c.cid in cids]

    def _confirm_remove_chain(self, chain: list, kb) -> bool:
        """Шов подтверждения удаления причины с зависимыми ветвями
        (тестируется подменой; модальный QMessageBox не блокирует
        offscreen-прогоны)."""
        box = QMessageBox(self)
        box.setWindowTitle("Удаление причины")
        box.setIcon(QMessageBox.Icon.Question)
        names = "\n".join(
            f"• {(kb.gs_by_id(c.ref) or kb.iz_by_id(c.ref) or {})
                 .get('title', c.ref)}" + (" (зависимая ветвь)"
                                           if c.parent else "")
            for c in chain[:10])
        if len(chain) > 10:
            names += f"\n… и ещё {len(chain) - 10}"
        box.setText(f"Удалить причину с зависимыми ветвями"
                    f" ({len(chain)})?")
        box.setInformativeText(names)
        b_del = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    def _remove_gs_cause(self, idx: int) -> None:
        tree = self._inspected_tree()
        if tree is not None and 0 <= idx < len(tree.gs_causes):
            chain = self._cause_subtree(tree.gs_causes, idx)
            if len(chain) > 1 and not self._confirm_remove_chain(
                    chain, self.kb):
                return
            cids = {c.cid for c in chain}
            tree.gs_causes = [c for c in tree.gs_causes
                              if c.cid not in cids]
            self._undo_push()      # Задача 4 (сессия 17)
            self.inspector.show_tree_node(tree, "gs")
            self._mark_dirty()
            self._refresh()

    def _add_iz_cause(self, ref: str) -> None:
        tree = self._inspected_tree()
        if tree is not None:
            tree.iz_causes.append(IZCause(ref=ref))
            self._undo_push()      # Задача 4 (сессия 17)
            self.inspector.show_tree_node(tree, "iz")
            self._mark_dirty()
            self._refresh()

    def _remove_iz_cause(self, idx: int) -> None:
        tree = self._inspected_tree()
        if tree is not None and 0 <= idx < len(tree.iz_causes):
            chain = self._cause_subtree(tree.iz_causes, idx)
            if len(chain) > 1 and not self._confirm_remove_chain(
                    chain, self.kb):
                return
            cids = {c.cid for c in chain}
            tree.iz_causes = [c for c in tree.iz_causes
                              if c.cid not in cids]
            self._undo_push()      # Задача 4 (сессия 17)
            self.inspector.show_tree_node(tree, "iz")
            self._mark_dirty()
            self._refresh()

    # ---- Задача 1 (сессия 16): Delete/мусорка на строках причин ----
    def _cause_chain_from(self, causes: list, root) -> list:
        """Цепь причины по её cid (аналог _cause_subtree без индекса –
        иерархия передает маркеры, а не индексы списков)."""
        cids = {root.cid}
        grew = True
        while grew:
            grew = False
            for c in causes:
                if c.parent in cids and c.cid not in cids:
                    cids.add(c.cid)
                    grew = True
        return [c for c in causes if c.cid in cids]

    def _on_causes_delete_requested(self, markers: list) -> None:
        """Delete/мусорка на чистом выборе строк причин (LOCKED):
        удаляются ПРИЧИНЫ с зависимыми ветвями; объект-владелец
        (участок/установка) не затрагивается никогда."""
        self._delete_selected_causes(markers)

    def _delete_selected_causes(self, markers: list) -> None:
        """Одно окно подтверждения на ВЕСЬ набор (LOCKED): собираются
        цепи всех выбранных причин (дедупликация – потомок, выбранный
        вместе с родителем, уже внутри его цепи), затем удаление по
        cid; инспектор перестраивается, если показывал форму ноды
        затронутого дерева."""
        groups: dict[tuple[str, str], set[str]] = {}
        for m in markers:
            tree_id, kind, cid = m
            groups.setdefault((tree_id, kind), set()).add(cid)
        chains: list = []
        affected: list[tuple[TreeModel, str]] = []
        for (tree_id, kind), want in groups.items():
            tree = next((t for t in self.trees if t.tree_id == tree_id),
                        None)
            if tree is None:
                continue
            causes = tree.gs_causes if kind == "gs" else tree.iz_causes
            seen: set[str] = set()
            found = False
            for c in causes:
                if c.cid in want and c.cid not in seen:
                    chain = self._cause_chain_from(causes, c)
                    seen |= {x.cid for x in chain}
                    chains.extend(chain)
                    found = True
            if found:
                affected.append((tree, kind))
        if not chains:
            return
        if not self._confirm_remove_causes(chains, self.kb):
            return
        gone = {c.cid for c in chains}
        for tree, _kind in affected:
            tree.gs_causes = [c for c in tree.gs_causes
                              if c.cid not in gone]
            tree.iz_causes = [c for c in tree.iz_causes
                              if c.cid not in gone]
        self._mark_dirty()
        self._refresh()
        # инспектор показывал форму ноды затронутого дерева – обновить
        # список причин (удаленные строки должны исчезнуть)
        itree = self.inspector.current_tree()
        ikind = self.inspector.current_node_kind()
        if itree is not None and ikind in ("gs", "iz") \
                and any(t is itree and k == ikind for t, k in affected):
            self.inspector.show_tree_node(itree, ikind)

    def _confirm_remove_causes(self, chain: list, kb) -> bool:
        """Шов подтверждения удаления ВЫБРАННЫХ причин (Delete/мусорка):
        ОДНО окно на весь набор, облик и семантика – как у
        _confirm_remove_chain (тестируется подменой)."""
        box = QMessageBox(self)
        box.setWindowTitle("Удаление причин")
        box.setIcon(QMessageBox.Icon.Question)
        names = "\n".join(
            f"• {(kb.gs_by_id(c.ref) or kb.iz_by_id(c.ref) or {})
                 .get('title', c.ref)}" + (" (зависимая ветвь)"
                                           if c.parent else "")
            for c in chain[:10])
        if len(chain) > 10:
            names += f"\n… и ещё {len(chain) - 10}"
        box.setText(f"Удалить выбранные причины с зависимыми"
                    f" ветвями ({len(chain)})?")
        box.setInformativeText(names)
        b_del = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    # ============================ база данных ============================
    kb_window: KBWindow | None = None

    def _open_kb_window(self) -> None:
        if self.kb_window is None:
            # Задачи 9/10 (сессия 13): счетчик использования записи
            # библиотеки деревьями проекта – для предупреждения удаления
            def _usage(section: str, rec_id: str) -> int:
                n = 0
                if section == "property_modifiers":
                    # Задача 0: сколько деревьев/объектов включили меру
                    ped = (self.kb.modifier_by_pedal(rec_id) or {}
                           ).get("pedal", "")
                    if ped:
                        for t in self.trees:
                            if t.gs_pedals.get(ped) or t.iz_pedals.get(ped):
                                n += 1
                        for o in self.objects.all_nodes():
                            if o.props.get("pedals", {}).get(ped):
                                n += 1
                    return n
                if section == "equipment_templates":
                    # Задача 10 (сессия 15): сколько деревьев используют
                    # состав шаблона (ссылки на его разновидности ГС/ИЗ)
                    tpl = self.kb.template_by_id(rec_id) or {}
                    refs = {str(e).split("#")[0]
                            for e in tpl.get("gs_causes", [])}
                    refs |= set(tpl.get("iz_causes", []))
                    for t in self.trees:
                        if any(c.ref in refs for c in t.gs_causes) \
                                or any(c.ref in refs for c in t.iz_causes):
                            n += 1
                    return n
                for t in self.trees:
                    if section == "iz_causes" and any(
                            c.ref == rec_id for c in t.iz_causes):
                        n += 1
                    if section == "gs_causes" and any(
                            c.ref == rec_id for c in t.gs_causes):
                        n += 1
                return n

            self.kb_window = KBWindow(self.kb, self, usage=_usage)
            self.kb_window.equipment_applied.connect(
                self._apply_library_equipment)
            # Задача 11 (сессия 13): запомненные размер/положение окна БД
            geo = _as.read_value("ui/kb_geometry")
            if geo is not None:
                self.kb_window.restoreGeometry(geo)
        self._update_kb_apply_hint()
        self.kb_window.show()
        self.kb_window.raise_()

    def _apply_library_equipment(self, template_id: str) -> None:
        """Задача 3: шаблон применяется ТОЛЬКО к выделенному участку
        или наружной установке (кнопка в КЗ неактивна иначе)."""
        owner = self.hierarchy.selected_owner()
        if owner is None:
            QMessageBox.information(
                self, "Применение шаблона",
                "Выделите участок или наружную установку в иерархии"
                " объектов, затем примените шаблон.")
            return
        rec = self.kb.template_by_id(template_id)
        if rec is None:
            return
        # Сессия 14/1 (решение заказчика): состав шаблона НЕ фильтруется
        # по типу участка – как и в выборе причин, применимость решает
        # пользователь (раньше «скрытые» разновидности молча выбрасывались)
        available = {g["id"] for g in self.kb.gs_for(
            rec.get("scenario_type", "gg"))}
        # Задача 8/10 (сессия 15): элемент списка шаблона – «ref» или
        # «ref#диапазон» (строка развертки); парсим и применяем с flow
        pairs = []
        for entry in rec.get("gs_causes", []):
            ref, _sep, flow = str(entry).partition("#")
            if ref in available:
                pairs.append((ref, flow if flow in ("small", "mid", "big",
                                                    "rupt") else None))
        dropped = len(rec.get("gs_causes", [])) - len(pairs)
        tree = TreeModel(rec.get("scenario_type", "gg"), owner.id,
                         title=rec.get("title", "Шаблон"))
        tree.gs_causes = [GSCause(ref=g, flow=f) for g, f in pairs]
        tree.iz_causes = [IZCause(ref=i) for i in rec.get("iz_causes", [])]
        self.trees.append(tree)
        self._undo_push()          # Задача 4 (сессия 17)
        self._mark_dirty()
        self._refresh()
        if dropped:
            self.statusBar().showMessage(
                f"Шаблон применён; {dropped} разновидностей ГС скрыто –"
                " не соответствует типу участка", 8000)

    # ============================ документ ============================
    def set_doc_view_mode(self, mode: str) -> None:
        self.act_matrix.setChecked(mode == "matrix")
        self.act_schema.setChecked(mode == "schematic")
        self.doc_stack.setCurrentIndex(0 if mode == "matrix" else 1)
        self._doc_mode_label.setText(
            "МАТРИЧНЫЙ ВИД" if mode == "matrix" else "СХЕМАТИЧЕСКИЙ ВИД")

    def open_doc_window(self) -> None:
        if self.doc_window is None:
            self.doc_window = DocumentWindow(self._doc_host)
            self.doc_window.closed.connect(self._on_doc_window_closed)
            self.left_toolbar.set_doc_window_open(True)
            # Задача 1 (сессия 13): _on_doc_window_closed прячет хост
            # (hide() ставит явный флаг «скрыт») – без show() повторное
            # открытие показывало ПУСТОЕ окно: layout перенял панель, но
            # явный флаг скрытия пережил reparent. Снимаем флаг всегда.
            self._doc_host.show()
            # Задача 11 (сессия 13): запомненные размер/положение pop-out
            # окна (авто-открытия при старте НЕТ – только память)
            geo = _as.read_value("ui/doc_geometry")
            if geo is not None:
                self.doc_window.restoreGeometry(geo)
        self.doc_window.show()
        self.doc_window.raise_()
        QTimer.singleShot(0, self.doc_view.fit_width)

    def _toggle_doc_window(self) -> None:
        if self.doc_window is not None and self.doc_window.isVisible():
            self.doc_window.close()
        else:
            self.open_doc_window()

    def _on_doc_window_closed(self) -> None:
        # Задача 11 (сессия 13): пока окно живо (closeEvent → closed →
        # сюда), запоминаем его размер/положение для следующего открытия
        if self.doc_window is not None:
            _as.write_value("ui/doc_geometry",
                            self.doc_window.saveGeometry())
        # вернуть панель в скрытый хост главного окна
        self._doc_host.setParent(self)
        self._doc_host.hide()
        self.doc_window = None
        self.left_toolbar.set_doc_window_open(False)

    # ============================ удаление ============================
    def _delete_selection(self) -> None:
        """Задача 10 (сессия 12); приоритеты Задачи 1 (сессия 16): (1)
        чистый выбор строк причин иерархии – удаляются ПРИЧИНЫ с
        зависимыми ветвями (приоритетнее ноды холста: клик по строке
        причины ставит на ноде ПРОГРАММНЫЙ пунктир); (2) нода холста,
        выделенная КЛИКОМ пользователя, – удаляется её ДЕРЕВО-ВЛАДЕЛЕЦ
        (решение №5 Q&A; отдельные ноды фиксированной структуры
        неудаляемы); (3) объекты иерархии (в смешанном выборе – только
        они); (4) единственное текущее дерево – только когда в выборе
        иерархии нет строк сценариев/причин (строки сценариев –
        безопасный no-op, LOCKED). Подтверждения – существующие швы."""
        causes = self.hierarchy.selected_causes()
        nodes = self.hierarchy.selected_objects()
        if causes and not nodes:
            self._delete_selected_causes(causes)
            return
        sel_ids = self.canvas.controller.selected_nodes()
        if self._canvas_sel_by_click and len(sel_ids) > 1:
            # Задача 6 (LOCKED вариант 1): НЕСКОЛЬКО выделенных нод –
            # удаляются ВСЕ деревья-владельцы, ОДНО окно со списком
            trees = []
            for nid in sel_ids:
                t = self.canvas.controller.tree_of_node(nid)
                if t is not None and t not in trees:
                    trees.append(t)
            if trees and self._confirm_trees_delete(trees):
                for t in trees:
                    self.trees.remove(t)
                self._undo_push()      # Задача 4 (сессия 17)
                self._selected_scenario = None
                self._canvas_sel_by_click = False
                self._mark_dirty()
                self._refresh()
            return
        nid = self.canvas.controller.selected_node()
        if nid and self._canvas_sel_by_click:
            tree = self.canvas.controller.tree_of_node(nid)
            if tree is not None and self._confirm_tree_delete(tree):
                self.trees.remove(tree)
                self._undo_push()      # Задача 4 (сессия 17)
                self._selected_scenario = None
                self._canvas_sel_by_click = False
                self._mark_dirty()
                self._refresh()
            return
        if nodes:
            # Задача 6.2 (сессия 13): удаляется всё выбранное (плюс
            # потомки) – пакет через ОДНО окно подтверждения
            self.hierarchy.delete_objects(nodes)
            return
        if self.hierarchy.has_tree_rows_selected():
            return          # строки сценариев: без окна и без удаления
        tree = self._current_tree()
        if tree is not None and self._confirm_tree_delete(tree):
            self.trees.remove(tree)
            self._undo_push()          # Задача 4 (сессия 17)
            self._selected_scenario = None
            self._mark_dirty()
            self._refresh()

    def _update_trash(self) -> None:
        """Задача 10; Задача 1 (сессия 16): мусорка включена для
        выбранных строк причин, реально выбранных объектов иерархии
        (кроме корня-территории) и нод холста, выделенных КЛИКОМ или
        РАМКОЙ пользователя (пунктир от клика по строке причины – не в
        счет); чистый выбор строки сценария выключает мусорку (безопасный
        no-op, LOCKED)."""
        nodes = self.hierarchy.selected_objects()
        obj_ok = any(n.kind != TERRITORY for n in nodes)
        cause_ok = bool(self.hierarchy.selected_causes())
        canvas_ok = (bool(self.canvas.controller.selected_nodes())
                     and self._canvas_sel_by_click)
        self.left_toolbar.set_trash_enabled(obj_ok or cause_ok or canvas_ok)

    def _confirm_trees_delete(self, trees: list) -> bool:
        """Задача 6 (сессия 17, LOCKED): шов группового удаления – ОДНО
        окно со списком деревьев-владельцев выделенных нод (облик как у
        _confirm_tree_delete; тестируется подменой)."""
        box = QMessageBox(self)
        box.setWindowTitle("Удаление деревьев")
        box.setIcon(QMessageBox.Icon.Question)
        names = "\n".join(f"• {t.title}" for t in trees[:10])
        if len(trees) > 10:
            names += f"\n… и ещё {len(trees) - 10}"
        box.setText(f"Удалить деревья ({len(trees)}) со всеми"
                    " сценариями?")
        box.setInformativeText(names)
        b_del = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    def _confirm_tree_delete(self, tree: TreeModel) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle("Удаление дерева")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Удалить дерево «{tree.title}» со всеми сценариями?")
        b_del = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    # ============ undo/redo + буфер иерархии (Задача 4, сессия 17) =========
    def _undo_snapshot(self) -> str:
        """Полное состояние модели (формат 5, в памяти): объекты +
        деревья. Сравнимая строка – основа коалесценции и глубины."""
        return json.dumps(
            {"objects": self.objects.to_dict(),
             "trees": [t.to_dict() for t in self.trees]},
            ensure_ascii=False, sort_keys=True)

    def _undo_reset(self) -> None:
        """Сброс истории (новый/открытый проект, старт): базой становится
        текущее состояние, стеки пусты."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._undo_base = self._undo_snapshot()

    def _undo_push(self) -> None:
        """Точка отката: вызывается швами мутаций (до или после записи –
        не критично: на стек ложится ДО-состояние из _undo_base, новым
        базовым становится текущее состояние). Повторные вызовы без
        изменения состояния и вызовы, чья база уже на вершине стека,
        коалесцируются – потоки valueChanged не плодят дубликаты.
        Новое действие очищает redo (LOCKED)."""
        snap = self._undo_snapshot()
        if snap == self._undo_base:
            return                      # состояние не изменилось
        if not (self._undo_stack and self._undo_stack[-1] == self._undo_base):
            self._undo_stack.append(self._undo_base)
            if len(self._undo_stack) > UNDO_DEPTH:
                self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._undo_base = snap

    def _undo(self) -> None:
        if not self._undo_stack:
            self.statusBar().showMessage("Отменять нечего", 4000)
            return
        keep = self.hierarchy._current_marker()
        self._redo_stack.append(self._undo_snapshot())
        state = self._undo_stack.pop()
        self._restore_snapshot(state, keep)
        self._undo_base = state

    def _redo(self) -> None:
        if not self._redo_stack:
            self.statusBar().showMessage("Возвращать нечего", 4000)
            return
        keep = self.hierarchy._current_marker()
        self._undo_stack.append(self._undo_snapshot())
        if len(self._undo_stack) > UNDO_DEPTH:
            self._undo_stack.pop(0)
        state = self._redo_stack.pop()
        self._restore_snapshot(state, keep)
        self._undo_base = state

    def _restore_snapshot(self, state: str, keep=None) -> None:
        """Восстановление: словари формата 5 грузятся обратно в модель,
        полный _refresh; выбор иерархии возвращается, если маркер жив
        (объект/строка сценария пережили откат – tree_id сохраняются)."""
        d = json.loads(state)
        self.objects.load_from_dict(d["objects"])
        self.trees = [TreeModel.from_dict(t) for t in d["trees"]]
        self._selected_scenario = None
        self._canvas_sel_by_click = False
        self._refresh()
        if keep is not None:
            self.hierarchy._restore_selection(keep)
        self._sync_inspector_alive()
        self._mark_dirty()

    def _sync_inspector_alive(self) -> None:
        """Форма инспектора ссылается на умерший объект/дерево –
        показать форму живого выделения иерархии (или ничего)."""
        ins = self.inspector
        if ins.current_tree() is not None \
                and ins.current_tree() not in self.trees:
            self._show_object(self.hierarchy.selected())
            return
        obj = ins._obj
        if obj is not None and self.objects.by_id(obj.id) is not obj:
            self._show_object(self.hierarchy.selected())

    # ---------- буфер обмена иерархии (Ctrl+C/Ctrl+V, LOCKED) ----------
    def _copy_selection(self) -> None:
        """Копировать ВЫБРАННЫЕ строки-объекты (мультивыбор – с
        дедупликацией потомков, как при удалении) ПОДДЕРЕВЬЯМИ:
        потомки + их деревья с причинами и зависимостями. Глубокая
        копия с СВЕЖИМИ oid/tree_id/cid (сохранение соответствия
        parent), корень получает суффикс « (копия)», node_offsets
        сбрасываются. Строки причин/сценариев – безопасный no-op."""
        nodes = self.hierarchy._dedupe_ancestors(
            self.hierarchy._selection_objects())
        if not nodes:
            return
        self._clip = [self._clip_subtree(n) for n in nodes]
        self.statusBar().showMessage(
            f"Скопировано объектов: {len(self._clip)}"
            " – Ctrl+V, чтобы вставить", 8000)

    def _clip_subtree(self, node: ObjNode) -> dict:
        def nd(n: ObjNode) -> dict:
            d = {"id": n.id, "kind": n.kind, "title": n.title,
                 "props": json.loads(json.dumps(n.props,
                                                ensure_ascii=False))}
            if n.children:
                d["children"] = [nd(c) for c in n.children]
            return d

        owner_ids = {n.id for n in node.walk()
                     if n.kind in TREE_OWNER_KINDS}
        item = {"node": nd(node),
                "trees": [t.to_dict() for t in self.trees
                          if t.owner_id in owner_ids]}
        item["node"]["title"] += " (копия)"
        return self._remap_clip_ids(item)

    @staticmethod
    def _remap_clip_ids(item: dict) -> dict:
        """Глубокая копия снапшота буфера со СВЕЖИМИ идентификаторами:
        повторные вставки не конфликтуют; деревья следуют за новыми
        oid владельцев, причины сохраняют связи parent (cid-карта).
        Ручные смещения нод сбрасываются – чистая авторазметка."""
        item = json.loads(json.dumps(item, ensure_ascii=False))
        oid_map: dict[str, str] = {}

        def walk_nd(d: dict) -> None:
            old = str(d.get("id", ""))
            new = uuid.uuid4().hex[:10]
            oid_map[old] = new
            d["id"] = new
            for ch in d.get("children", []):
                walk_nd(ch)

        walk_nd(item["node"])
        for td in item["trees"]:
            td["id"] = uuid.uuid4().hex[:10]
            td["owner"] = oid_map.get(td.get("owner"), td.get("owner"))
            cid_map: dict[str, str] = {}
            for key in ("gs_causes", "iz_causes"):
                for c in td.get(key, []):
                    cid_map[str(c.get("cid", ""))] = _new_cid()
            for key in ("gs_causes", "iz_causes"):
                for c in td.get(key, []):
                    if c.get("cid") in cid_map:
                        c["cid"] = cid_map[c["cid"]]
                    if c.get("parent"):
                        c["parent"] = cid_map.get(c.get("parent"),
                                                  c.get("parent"))
            td.pop("node_offsets", None)     # чистая авторазметка
        return item

    def _paste_clipboard(self) -> None:
        """Вставить под ТЕКУЩИЙ ВЫБРАННЫЙ объект (can_add корневого вида;
        иначе информационное окно как у add_kind), без выбора – в корень
        иерархии (только территории). Повторные вставки разрешены;
        вставленные корни выделяются, вставка отменяема (Ctrl+Z)."""
        if not self._clip:
            return
        target = self.hierarchy.selected()
        pasted: list[ObjNode] = []
        for proto in self._clip:
            kind = proto["node"]["kind"]
            if not self.objects.can_add(kind, target):
                QMessageBox.information(self, "Иерархия",
                                        add_denied_message(kind))
                continue
            pasted.append(self._clip_attach(self._remap_clip_ids(proto),
                                            target))
        if not pasted:
            return
        self._undo_push()
        self._mark_dirty()
        self._refresh()
        # вставленные корни выделены; текущий (инспектор) – последний
        for n in pasted:
            it = self.hierarchy._item_of(n)
            if it is not None:
                it.setSelected(True)
        self.hierarchy.select_object(pasted[-1], emit=True)

    def _clip_attach(self, item: dict, parent: ObjNode | None) -> ObjNode:
        """Перенос снапшота буфера в живую модель: рекурсивная сборка
        ObjNode (идентификаторы уже свежие), деревья – TreeModel."""
        def build(d: dict, parent_node: ObjNode | None) -> ObjNode:
            n = ObjNode(d["kind"], d.get("title", ""), d.get("id"))
            n.props.update(json.loads(json.dumps(d.get("props") or {},
                                                  ensure_ascii=False)))
            if parent_node is None:
                self.objects.territories.append(n)
            else:
                n.parent = parent_node
                parent_node.children.append(n)
            for ch in d.get("children", []):
                build(ch, n)
            return n

        root = build(item["node"], parent)
        for td in item.get("trees", []):
            self.trees.append(TreeModel.from_dict(td))
        self.objects.changed.emit()
        return root

    # ============================ проекты ============================
    def _project_dir_or_desktop(self) -> str:
        """Общий хвост цепочки предзаполнения: папка проекта → Рабочий
        стол (оба проверяются на существование). Задача 12 (сессия 18),
        Задача 1 (сессия 19)."""
        if self._project_path:
            d = os.path.dirname(self._project_path)
            if d and Path(d).is_dir():
                return d
        return str(Path.home() / "Desktop")

    def _dir_hint(self) -> str:
        """Задача 12 (сессия 18, LOCKED): папка предзаполнения ПРОЕКТНЫХ
        файловых диалогов (сохранить/открыть) – цепочка «ui/last_dir →
        папка проекта → Рабочий стол». Сессия 19 (Задача 1, LOCKED):
        экспорт в DOCX больше НЕ использует этот ключ, у него своя
        память export/last_dir (_export_dir_hint)."""
        last = str(_as.read_value("ui/last_dir", "") or "")
        if last and Path(last).is_dir():
            return last
        return self._project_dir_or_desktop()

    def _remember_dir(self, path: str) -> None:
        """Задача 12: запомнить папку успешного сохранения/открытия
        ПРОЕКТА (ключ ui/last_dir). Экспорт – только export/last_dir
        (Задача 1, сессия 19), иначе отчет уводил бы «Открыть проект»
        в папку отчетов. Запись сразу уходит на диск (sync) – сессия 19."""
        d = os.path.dirname(str(path))
        if d:
            _as.write_value("ui/last_dir", d)

    def _export_dir_hint(self) -> str:
        """Задача 1 (сессия 19, LOCKED): папка предзаполнения экспорта
        DOCX – собственный ключ export/last_dir (исходники проектов и
        отчеты живут в РАЗНЫХ папках), фолбэк – папка проекта →
        Рабочий стол."""
        last = str(_as.read_value("export/last_dir", "") or "")
        if last and Path(last).is_dir():
            return last
        return self._project_dir_or_desktop()

    def _remember_export_dir(self, path: str) -> None:
        """Задача 1 (сессия 19, LOCKED): запомнить папку отчета – после
        УСПЕШНОГО экспорта и после выбора пути в «Обзор…» (в т. ч. если
        диалог затем отменен). Ключ ui/last_dir не трогает.

        Сессия 19 (п.3): запись идёт через `app_settings.write_value`, то
        есть с немедленным `sync()` в ЯВНЫЙ INI-файл. Прежняя схема
        (реестр + кэш Qt до разрушения последнего QSettings) на машине
        заказчика теряла значения: перезапуск не помнил ни папку экспорта,
        ни размеры окон."""
        d = os.path.dirname(os.path.abspath(str(path)))
        if d:
            _as.write_value("export/last_dir", d)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._update_title()

    def _update_title(self) -> None:
        name = Path(self._project_path).stem if self._project_path \
            else "Новый проект"
        self.setWindowTitle(
            f"{name}{'*' if self._dirty else ''} – {APP_TITLE}"
            f" – логические деревья событий (Методика № 533)")

    def _confirm_for(self, action_text: str) -> bool:
        if not self._dirty:
            return True
        box = QMessageBox(self)
        box.setWindowTitle(f"{APP_TITLE} – несохранённые изменения")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Проект изменён. {action_text}?")
        b_save = box.addButton("Сохранить", QMessageBox.ButtonRole.AcceptRole)
        b_discard = box.addButton("Не сохранять",
                                  QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_save)
        box.exec()
        clicked = box.clickedButton()
        if clicked is b_save:
            self._save_project()
            return not self._dirty
        return clicked is b_discard

    def _new_project(self) -> None:
        if not self._confirm_for("Создать новый проект"):
            return
        self.objects.clear()
        self.trees = []
        self._project_path = ""
        # Задача 1 (сессия 19, LOCKED): новый документ – новый UID имени
        # отчета (прежний относится к закрытому документу)
        self._report_uid = new_session_uid()
        self._dirty = False
        self._selected_scenario = None
        self._undo_reset()          # Задача 4 (сессия 17): новая история
        self._update_title()
        self._refresh()

    def _open_project_dialog(self) -> None:
        if not self._confirm_for("Открыть другой проект"):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", self._dir_hint(),
            "Проекты Kuji (*.kuji.json *.json)")
        if not path:
            return
        try:
            data = load_project(path)
        except UnsupportedFormatError as exc:
            QMessageBox.warning(self, "Формат проекта", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Открытие проекта", f"Ошибка: {exc}")
            return
        self._remember_dir(path)          # Задача 12 (сессия 18)
        self._load_project_data(path, data)

    def _load_project_data(self, path: str, data: dict) -> None:
        """Применить прочитанный проект формата 5 (шов для тестов без
        файлового диалога). Задача 1.2 (сессия 14): load_from_dict
        чинит поврежденную структуру – при фактическом ремонте
        показывается сообщение статус-бара. Задача 3 (LOCKED 11б):
        сохраненное состояние раскрытия иерархии применяется после
        загрузки (неизвестные id игнорируются; без сохраненного
        состояния всё раскрыто)."""
        repair = self.objects.load_from_dict(data["objects"])
        self.trees = data["trees"]
        self._project_path = path
        self._dirty = False
        self._selected_scenario = None
        self._undo_reset()          # Задача 4 (сессия 17): открытый файл – база
        self._update_title()
        self._refresh()
        ui = data.get("ui") or {}
        self.hierarchy.apply_collapsed(
            ui.get("hierarchy_collapsed") or [],
            ui.get("hierarchy_groups_collapsed") or [],
            ui.get("hierarchy_causes_collapsed") or [])
        if repair:
            self._report_repair(repair)

    def _report_repair(self, repair: dict) -> None:
        """Задача 1.2: уведомление об автоматическом ремонте файла."""
        n_t = int(repair.get("lifted_territories", 0))
        n_other = int(repair.get("moved_nodes", 0)) - n_t
        msg = ""
        if n_t > 0:
            msg = (f"Файл содержит вложенные территории – {n_t}"
                   " территорий перемещены в корень иерархии")
            if n_other > 0:
                msg += f"; исправлено размещений: {n_other}"
        elif n_other > 0:
            msg = (f"Структура иерархии исправлена – перемещено"
                   f" объектов: {n_other}")
        if msg:
            self.statusBar().showMessage(msg, 8000)

    def _write_project(self, path: str) -> bool:
        """Записать проект в КОНКРЕТНЫЙ путь – общий хвост «Сохранить» и
        «Сохранить как…» (сессия 19, запрос заказчика): ui-словарь
        состояния раскрытия иерархии (LOCKED 11б: поле опциональное,
        формат 5), память папки проектов (ui/last_dir), сброс «изменено»
        и заголовок. True – файл записан и проект живет под этим путём."""
        ui = {
            "hierarchy_collapsed": self.hierarchy.collapsed_ids(),
            "hierarchy_groups_collapsed":
                self.hierarchy.collapsed_group_ids(),
            "hierarchy_causes_collapsed":
                self.hierarchy.collapsed_cause_ids(),
        }
        try:
            save_project(path, self.objects, self.trees,
                         project_name=Path(path).stem, ui=ui)
        except Exception as exc:  # noqa: BLE001 – русская диагностика
            QMessageBox.warning(self, "Сохранение проекта", f"Ошибка: {exc}")
            return False
        self._project_path = path
        self._remember_dir(path)          # Задача 12 (сессия 18)
        self._dirty = False
        self._update_title()
        return True

    def _save_project(self) -> None:
        if not self._project_path:
            # У проекта ещё нет имени – «Сохранить» законно спрашивает
            # путь (тот же диалог, что «Сохранить как…»)
            self._save_project_as()
            return
        self._write_project(self._project_path)

    def _save_project_as(self) -> None:
        """Сессия 19 (запрос заказчика, Ctrl+Shift+S / Ctrl+Shift+Ы):
        «Сохранить как…» – ВСЕГДА спрашивает новый путь; после успешной
        записи текущий проект продолжает работать под новым именем
        (каноническая семантика Save As, откат не затронут – файловые
        операции в историю изменений не пишутся)."""
        base = Path(self._project_path).name if self._project_path \
            else "проект.kuji.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить проект как",
            str(Path(self._dir_hint()) / base),
            "Проекты Kuji (*.kuji.json)")
        if not path:
            return
        self._write_project(path)

    def _export_docx(self) -> None:
        """Задачи 10/11 (сессия 18, LOCKED): единый DOCX-отчет –
        диалог формата листа схем + пути; сборка через встроенный
        pandoc по ГОСТ-шаблону; подсказка статус-бара «DOCX: …».

        Задача 1 (сессия 19, LOCKED): имя файла – «Отчет-РЧП-<база
        проекта | UID>.docx», папка – собственная память export/last_dir.
        Задача 3 (сессия 19, LOCKED): после успешного экспорта (диалог
        уже закрыт) окно спрашивает, открыть ли отчет."""
        from .dialogs import DocxExportDialog
        if self._export_running:
            # Защита от повторного входа: модальный exec() держит вложенный
            # цикл событий, и возобновившаяся после его закрытия цепочка
            # родителей ShortcutOverride могла бы открыть диалог ВТОРОЙ РАЗ
            # (замечено заказчиком 17.11.2026; корень исправлен в
            # latin_keys._dispatch_letter, это – второй пояс)
            return
        self._export_running = True
        try:
            dlg = DocxExportDialog(
                parent=self,
                # Задача 1: умное имя (сохраненный проект – его база имени,
                # несохраненный – UID документной сессии)
                suggested_name=report_docx_name(self._project_path,
                                                self._report_uid),
                start_dir=self._export_dir_hint(),
                remember_dir=self._remember_export_dir)
            dlg.set_project_data(self.objects, self.trees, self.kb,
                                 self.ctx_map(), self._owner_titles(),
                                 self.canvas)
            accepted = dlg.exec() == DocxExportDialog.Accepted
            out = (dlg.exported_path or str(dlg.path_edit.text())) \
                if accepted else ""
        finally:
            self._export_running = False
        if accepted:
            self._after_docx_export(out)

    def _after_docx_export(self, path: str) -> None:
        """Задачи 1/3 (сессия 19): что делает окно ПОСЛЕ успешного
        экспорта – память папки отчетов, подсказка статус-бара и вопрос
        об открытии. Вынесено из `_export_docx` отдельным методом:
        offscreen-тесты прогоняют всю цепочку без модального диалога."""
        out = str(path or "").strip()
        if not out:
            return
        # Задача 1 (LOCKED): успешный экспорт обновляет ТОЛЬКО
        # export/last_dir (ui/last_dir – про проекты, блок изоляции)
        self._remember_export_dir(out)
        self.statusBar().showMessage(f"DOCX: {out}", 8000)
        # Задача 3 (LOCKED): вопрос об открытии – только по факту
        # созданного файла; оба шага – швы для offscreen-тестов
        if Path(out).is_file() and self._ask_open_report(out):
            if not self._open_path(out):
                QMessageBox.information(
                    self, "Экспорт завершен",
                    "Не удалось открыть отчет автоматически."
                    f" Файл сохранен: {out}")

    def _ask_open_report(self, path: str) -> bool:
        """Задача 3 (сессия 19, LOCKED): «Отчет сформирован. Желаете
        открыть его сейчас?» – Да/Нет. Шов: offscreen-тесты подменяют
        метод, модалка в прогоне не крутится."""
        box = QMessageBox(self)
        box.setWindowTitle("Экспорт завершен")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("Отчет сформирован. Желаете открыть его сейчас?")
        yes = box.addButton("Да", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Нет", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(yes)
        box.exec()
        return box.clickedButton() is yes

    def _open_path(self, path: str) -> bool:
        """Задача 3 (сессия 19): открыть отчёт системным приложением по
        умолчанию. Шов для тестов; False – файл открыть не удалось (тогда
        окно сообщает путь, чтобы пользователь открыл его сам).

        Сессия 19, раунд замечаний: Word показывал «в документе
        Normal.dotm обнаружено содержимое, которое не удалось прочитать»
        ТОЛЬКО при открытии из программы, а тот же файл из Проводника
        открывался штатно. Сам пакет отчёта чист (следов чужого шаблона в
        нём нет – это проверяют export_docx, QA и тесты), значит дело в
        способе запуска. QDesktopServices.openUrl отдаёт ShellExecute
        URL-форму пути, os.startfile – обычный путь, но в обоих случаях
        WINWORD.EXE порождается НАШИМ процессом и наследует его окружение:
        PATH с каталогами встроенного Python и PySide6, рабочую папку
        проекта и COM-контекст GUI-потока Qt. Проводник же запускает Word
        из своей чистой среды Windows.

        Поэтому порядок такой: (1) explorer.exe как брокер – ровно тот же
        путь, что и при двойном щелчке; (2) os.startfile; (3) запасной
        QDesktopServices. Выбранный способ пишется в key_debug.log строкой
        «open-report | …», чтобы любая повторная жалоба шла с данными."""
        target = os.path.abspath(str(path))
        if os.name == "nt":
            if self._launch_via_explorer(target):
                return True
            if self._launch_via_startfile(target):
                return True
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        ok = bool(QDesktopServices.openUrl(QUrl.fromLocalFile(target)))
        self._log_open_attempt(f"QDesktopServices → {target} ok={ok}")
        return ok

    def _launch_via_explorer(self, path: str) -> bool:
        """Открыть файл через explorer.exe (брокер Проводника). Шов: тесты
        подменяют метод, чтобы никогда не порождать настоящие процессы.

        Окружение передаётся очищенным от каталогов встроенного Python и
        PySide6, чтобы Word не подхватывал наши библиотеки вместо своих."""
        import subprocess
        explorer = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"), "explorer.exe")
        env = os.environ.copy()
        noise = ("runtime", "pyside", "shiboken", "qt")
        env["PATH"] = os.pathsep.join(
            p for p in env.get("PATH", "").split(os.pathsep)
            if p and not any(n in p.lower() for n in noise))
        try:
            subprocess.Popen([explorer, os.path.normpath(path)],
                             cwd=os.path.dirname(path) or None, env=env,
                             close_fds=True, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             creationflags=0x08000000)   # CREATE_NO_WINDOW
        except OSError as exc:
            self._log_open_attempt(f"explorer.exe отказал ({exc});"
                                   f" пробую os.startfile → {path}")
            return False
        self._log_open_attempt(f"explorer.exe → {path}")
        return True

    def _launch_via_startfile(self, path: str) -> bool:
        """Обычный ShellExecute из нашего процесса (второй пояс). Шов."""
        try:
            os.startfile(path, "open")
        except (OSError, AttributeError) as exc:
            self._log_open_attempt(f"os.startfile отказал ({exc});"
                                   f" пробую QDesktopServices → {path}")
            return False
        self._log_open_attempt(f"os.startfile → {path}")
        return True

    @staticmethod
    def _log_open_attempt(text: str) -> None:
        """Строка о том, ЧЕМ именно открыли отчёт (KUJI_DEBUG_KEYS=1)."""
        try:
            from .latin_keys import debug_line
            debug_line(f"open-report | {text}")
        except Exception:  # noqa: BLE001 – диагностика не важнее экспорта
            pass

    # ============================ настройки ============================
    def _persist_ui_state(self) -> None:
        """Задача 1 (сессия 18): единая точка сохранения состояния
        интерфейса (геометрия окна + пропорции главного сплиттера) –
        вызывается из closeEvent И по дебаунсу splitterMoved, чтобы
        размеры панелей переживала любой путь выхода.

        Сессия 19 (п.3): хранилище – явный INI (`app_settings`), и
        сохранение завершается `sync()`. Без sync Qt вправе держать
        значения в кэше до разрушения последнего объекта QSettings, а
        завершённый «сверху» процесс их терял – именно так на машине
        заказчика перестали запоминаться окна и папки."""
        st = _as.settings()
        st.setValue("ui/geometry", self.saveGeometry())
        st.setValue("ui/splitter", self.splitter.saveState())
        st.sync()

    def _restore_ui(self) -> None:
        st = _as.settings()
        geo = st.value("ui/geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        # Задача 9: сохранённые пропорции панелей (QSplitter); байты
        # валидируются самим restoreState (False – мусорные/чужие байты:
        # остаются умолчания [320, 500, 360] из конструктора).
        # Задача 1 (сессия 18, измерено пробой offscreen): restoreState
        # ДО показа окна ЗАТИРАЕТСЯ первым layout-проходом показа (после
        # show() возвращались умолчания) – применяем и в конструкторе,
        # и ОТЛОЖЕННО (singleShot(0) срабатывает после первого layout
        # показанного окна; тестам достаточно pump())
        state = st.value("ui/splitter")
        if state is not None:
            self.splitter.restoreState(state)
            QTimer.singleShot(
                0, lambda: self.splitter.restoreState(state))

    def closeEvent(self, e) -> None:
        if not self._confirm_for("Закрыть приложение"):
            e.ignore()
            return
        _unregister_main_window(self)     # Задача 4 (сессия 17)
        self._persist_ui_state()          # Задача 1 (сессия 18)
        if self.doc_window is not None:
            self.doc_window.close()
        super().closeEvent(e)
