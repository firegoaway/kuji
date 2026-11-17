# -*- coding: utf-8 -*-
"""Окно «База данных» (сессия 11 – чистовая полировка).

Вкладки:
  * «Шаблоны оборудования» – карточки для «Применить на холсте» (Задача 3):
    кнопка активна ТОЛЬКО при выделенном Участке или Наружной установке;
    цель показывается плашкой «Цель: …» (без цели плашка скрыта – Задача 4);
    выбранная карточка подсвечивается рамкой (Задача 4); двойной клик =
    кнопка;
  * «Разновидности ГС», «Разновидности ИЗ», «Типы горения» –
    редакторы-таблицы: столбцы подгоняются под самое широкое содержимое,
    длинные тексты переносятся по словам (не шире 85 символов);
  * «Защитные средства» – инженерная таблица «Наименование средства |
    Коэффициент | Примечание» с математической типографикой (k, PFD,
    индексы/степени) – только чтение; примечание собирается по канону
    сессии 11: «формула (пункт источника) – краткое описание»;
  * «Таблицы типовых частот» – вложенные под-вкладки П1.3/П1.4/П2.1,
    каждая таблица на всю ширину своей под-вкладки (Задача 3).

Скролл всех таблиц – попиксельный (Задача 2): плавная анимация колеса
из scroll.py проходит промежуточные значения пикселей, а не границы
строк. Нижняя панель окна: «Сохранить» (основная) и «Закрыть» справа
(Задача 1a).
"""

from __future__ import annotations

import html as _html

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFrame,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QPushButton, QScrollArea,
                               QSplitter, QTabWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ..core.kb import KnowledgeBase
from .controls import wrap_text85, wide_combo
from .icons import (GLYPH_EVENT_ADD, GLYPH_HELP, apply_to_canvas_icon,
                    glyph_icon)
from .switch import ToggleSwitch
from .theme import BORDER, PEDALS_CAPTION, TEXT_SECONDARY, math


def _caption(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("caption")
    lab.setWordWrap(True)
    return lab


def _format_table(t: QTableWidget) -> None:
    """Задача 7 (сессия 13): столбцы – под САМОЕ широкое содержимое
    (никогда не сжимаются, потолка нет); когда суммарная ширина больше
    вьюпорта, появляется горизонтальный ползунок (AsNeeded). Строки –
    по перенесённому тексту (перенос уже вставлен ≤85 символов по
    словам, см. wrap_text85). Вьюжет-ячейки (QLabel) resizeColumns
    не видит – учитываем их sizeHint явно."""
    t.setWordWrap(True)
    t.horizontalHeader().setStretchLastSection(False)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    t.resizeColumnsToContents()
    for c in range(t.columnCount()):
        extra = 0
        for r in range(t.rowCount()):
            w = t.cellWidget(r, c)
            if w is not None:
                extra = max(extra, w.sizeHint().width())
        if extra:
            t.setColumnWidth(c, max(t.columnWidth(c), extra + 16))
    t.resizeRowsToContents()
    for c in range(t.columnCount()):
        t.horizontalHeader().setSectionResizeMode(
            c, QHeaderView.ResizeMode.Interactive)


def _pixel_scroll(view: QAbstractItemView) -> None:
    """Задача 2 (сессия 11): попиксельный скролл – вертикаль И горизонталь.

    Без этого единица прокрутки – целая строка/столбец, и плавная анимация
    колеса «прилипает» к границам строк, пропуская ячейки. Режим живёт
    на вьюхе и переживает сброс содержимого, но вызов после каждой
    перезагрузки дешёв и страхует от пересоздания модели.
    """
    view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.verticalScrollBar().setSingleStep(20)


def _keep_scroll_pos(table: QTableWidget, rebuild) -> None:
    """Перезагрузить содержимое таблицы без скачка прокрутки (Задача 2):
    запомнить позицию ползунка, пересобрать строки и вернуть позицию
    (в пределах нового диапазона) – первая видимая строка остаётся
    на месте, насколько это возможно."""
    bar = table.verticalScrollBar()
    pos = bar.value()
    rebuild()
    bar.setValue(max(bar.minimum(), min(bar.maximum(), pos)))


class _TemplateCard(QFrame):
    """Карточка шаблона: название, категория, тип сценария, состав
    (подписи переносятся – без усечений)."""

    card_clicked = Signal(object)
    card_double_clicked = Signal(object)

    def __init__(self, rec: dict, kb: KnowledgeBase, parent=None):
        super().__init__(parent)
        self.rec = rec
        self.setObjectName("kbCard")
        # Задача 4: фон/рамка карточки рисуются QSS – обязателен флаг
        # стилизованного фона, иначе свойства [selected="true"] не красятся
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("selected", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        st = kb.scenario_type_by_id(rec.get("scenario_type", "")) or {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        # Задача 5: названия шаблонов содержат «< 450 м³» – экранируем
        # спецсимволы HTML, иначе парсер rich text «глотает» </b> и
        # карточка/подсказка печатаются целиком полужирным
        title = QLabel(f"<b>{_html.escape(rec.get('title', rec['id']))}</b>")
        title.setWordWrap(True)
        lay.addWidget(title)
        meta = QLabel(
            f"{_html.escape(rec.get('category', ''))} · "
            f"{_html.escape(st.get('title', ''))}"
            f"<br>разновидностей ГС: {len(rec.get('gs_causes', []))}"
            f" · разновидностей ИЗ: {len(rec.get('iz_causes', []))}")
        meta.setStyleSheet(f"color: {TEXT_SECONDARY};")
        meta.setWordWrap(True)
        lay.addWidget(meta)
        gs_titles = [(kb.gs_by_id(g) or {}).get("title", g)
                     for g in rec.get("gs_causes", [])]
        gs_lines = "<br>".join(_html.escape(f"• {t}") for t in gs_titles[:8])
        if len(gs_titles) > 8:
            gs_lines += f"<br>… ещё {len(gs_titles) - 8}"
        self.setToolTip(f"<b>{_html.escape(rec.get('title', ''))}</b>"
                        f"<br>Тип участка: "
                        f"{_html.escape(rec.get('site_type', ''))}"
                        f"<br>Разновидности ГС:"
                        f"<br>{gs_lines}")

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self)
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.card_double_clicked.emit(self)
        super().mouseDoubleClickEvent(e)


class TemplatesTab(QWidget):
    """«Шаблоны оборудования» (Задача 10, сессия 15 – РЕДАКТИРУЕМЫЕ):
    слева карточки, справа ФОРМА РЕДАКТИРОВАНИЯ выбранного шаблона –
    «Название», «Категория», «Тип сценария», списки «Разновидности ГС»
    (добавление из библиотеки ГС, включая развернутые строки по
    диапазонам расхода – Задача 8) и «Разновидности ИЗ». Правки пишутся
    в запись сразу; «Сохранить» – как у остальных библиотек (kb.save);
    карточка и состав обновляются живьем. Кнопки [Добавить]/[Удалить]
    шаблон – в нижней панели ОКНА БД (слева, единообразно); удаление
    предупреждает количеством использующих шаблон деревьев."""

    equipment_applied = Signal(str)          # id шаблона
    dirty_changed = Signal(bool)

    def __init__(self, kb: KnowledgeBase, parent=None):
        super().__init__(parent)
        self.kb = kb
        self.usage = None                    # (section, id) → N деревьев
        self.selected_id: str | None = None
        self._owner_ok = False
        self._dirty = False
        self._cards: list[_TemplateCard] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по названию или категории…")
        self.search.textChanged.connect(lambda _t: self.rebuild_cards())
        root.addWidget(self.search)

        split = QSplitter(Qt.Orientation.Horizontal)
        scroll_host = QWidget()
        self.cards_lay = QVBoxLayout(scroll_host)
        self.cards_lay.setContentsMargins(0, 0, 8, 0)
        self.cards_lay.setSpacing(4)
        self.cards_lay.addStretch(1)
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setWidget(scroll_host)
        split.addWidget(self.cards_scroll)

        # ---------- форма редактирования (Задача 10 + Задача 2 15/1) ------
        form_host = QWidget()
        fh = QVBoxLayout(form_host)
        fh.setContentsMargins(4, 4, 4, 4)
        fh.setSpacing(6)
        fh.addWidget(_caption("СОСТАВ ШАБЛОНА"))
        # Задача 2 (сессия 15/1): форма ДОСТУПНА ТОЛЬКО после «Редакти-
        # ровать»; кнопка превращается в «Сохранить» + «Отмена»; сохранение
        # применяет правки, отмена возвращает снимок записи
        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.setObjectName("primary")
        self.btn_edit.clicked.connect(self._begin_edit)
        self.btn_save_form = QPushButton("Сохранить")
        self.btn_save_form.setObjectName("primary")
        self.btn_save_form.clicked.connect(self._commit_edit)
        self.btn_cancel_form = QPushButton("Отмена")
        self.btn_cancel_form.clicked.connect(self._cancel_edit)
        self.btn_save_form.setVisible(False)
        self.btn_cancel_form.setVisible(False)
        _edit_row = QHBoxLayout()
        _edit_row.addStretch(1)
        _edit_row.addWidget(self.btn_cancel_form)
        _edit_row.addWidget(self.btn_save_form)
        _edit_row.addWidget(self.btn_edit)
        fh.addLayout(_edit_row)
        self._editing = False
        self._backup: dict | None = None
        self._backup_id: str | None = None
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        form = QWidget()
        fl = QVBoxLayout(form)
        fl.setContentsMargins(0, 4, 0, 4)
        fl.setSpacing(6)
        self.ed_title = QLineEdit()
        self.ed_title.setPlaceholderText("Название шаблона")
        self.ed_title.textEdited.connect(self._edit_title)
        fl.addWidget(QLabel("Название:"))
        fl.addWidget(self.ed_title)
        self.ed_category = QLineEdit()
        self.ed_category.setPlaceholderText("Категория")
        self.ed_category.textEdited.connect(self._edit_category)
        fl.addWidget(QLabel("Категория:"))
        fl.addWidget(self.ed_category)
        self.cb_type = wide_combo()
        for st in ("tgm", "gg", "gzh", "lvzh", "dust"):
            rec = kb.scenario_type_by_id(st) or {}
            self.cb_type.addItem(rec.get("title", st), st)
        self.cb_type.currentIndexChanged.connect(self._edit_type)
        fl.addWidget(QLabel("Тип сценария:"))
        fl.addWidget(self.cb_type)

        def _list_block(caption: str, on_add, on_remove) -> QWidget:
            host = QWidget()
            hl = QVBoxLayout(host)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(4)
            hl.addWidget(_caption(caption))
            lw = QListWidget()
            lw.setSelectionMode(
                QListWidget.SelectionMode.ExtendedSelection)
            _pixel_scroll(lw)
            hl.addWidget(lw, 1)
            btns = QHBoxLayout()
            b_add = QPushButton("Добавить…")
            b_add.setObjectName("primary")
            b_add.clicked.connect(on_add)
            b_del = QPushButton("Убрать")
            b_del.clicked.connect(on_remove)
            btns.addWidget(b_add)
            btns.addWidget(b_del)
            btns.addStretch(1)
            hl.addLayout(btns)
            host._list = lw            # type: ignore[attr-defined]
            host._btn_add = b_add      # type: ignore[attr-defined]
            host._btn_del = b_del      # type: ignore[attr-defined]
            return host

        self.gs_block = _list_block("РАЗНОВИДНОСТИ ГС",
                                    self._add_gs_row, self._remove_gs_rows)
        self.gs_list: QListWidget = self.gs_block._list
        self.iz_block = _list_block("РАЗНОВИДНОСТИ ИЗ",
                                    self._add_iz_row, self._remove_iz_rows)
        self.iz_list: QListWidget = self.iz_block._list
        fl.addWidget(self.gs_block, 1)
        fl.addWidget(self.iz_block, 1)
        self.form_scroll.setWidget(form)
        fh.addWidget(self.form_scroll, 1)
        split.addWidget(form_host)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        split.setSizes([520, 460])
        root.addWidget(split, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.hint = QLabel("")
        self.hint.setObjectName("targetBadge")
        self.hint.setVisible(False)
        bottom.addWidget(self.hint)
        bottom.addStretch(1)
        self.btn_apply = QPushButton("Применить на холсте")
        self.btn_apply.setObjectName("primary")
        self.btn_apply.setIcon(apply_to_canvas_icon())
        self.btn_apply.clicked.connect(self._apply)
        bottom.addWidget(self.btn_apply)
        root.addLayout(bottom)

        self.rebuild_cards()
        self.set_owner_available(False, "")

    # ---------- данные/отображение ----------
    def _rec(self) -> dict | None:
        return next((r for r in self.kb.equipment_templates
                     if r["id"] == self.selected_id), None)

    def rebuild_cards(self) -> None:
        text = self.search.text().strip().lower()
        while self.cards_lay.count() > 1:
            item = self.cards_lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        self._cards = []
        for rec in self.kb.equipment_templates:
            if text and text not in rec.get("title", "").lower() \
                    and text not in rec.get("category", "").lower():
                continue
            card = _TemplateCard(rec, self.kb)
            card.card_clicked.connect(self._on_card)
            card.card_double_clicked.connect(self._on_card_dbl)
            self.cards_lay.insertWidget(self.cards_lay.count() - 1, card)
            self._cards.append(card)
        self._mark_selected()
        self._load_form()

    def _mark_selected(self) -> None:
        """Задача 4: подсветить карточку текущего selected_id. Свойство
        selected=true/false + переполировка – состояние применяется
        живьём, без пересоздания карточек."""
        for card in self._cards:
            on = "true" if card.rec.get("id") == self.selected_id else "false"
            if card.property("selected") != on:
                card.setProperty("selected", on)
                card.style().unpolish(card)
                card.style().polish(card)

    def scroll_to_selected(self) -> None:
        """Показать выбранную карточку в зоне видимости (для QA-снимков
        и после применения фильтра поиска)."""
        for card in self._cards:
            if card.rec.get("id") == self.selected_id:
                self.cards_scroll.ensureWidgetVisible(card, 12, 12)
                return

    # ---------- режим редактирования (Задача 2, сессия 15/1) ----------
    def _snapshot_of(self, rec: dict) -> dict:
        return {"title": rec.get("title", ""),
                "category": rec.get("category", ""),
                "scenario_type": rec.get("scenario_type", ""),
                "gs_causes": list(rec.get("gs_causes", [])),
                "iz_causes": list(rec.get("iz_causes", []))}

    def _restore_backup_into(self, rec: dict) -> None:
        b = self._backup or {}
        rec["title"] = b.get("title", rec.get("title", ""))
        rec["category"] = b.get("category", rec.get("category", ""))
        rec["scenario_type"] = b.get("scenario_type",
                                     rec.get("scenario_type", ""))
        rec["gs_causes"] = list(b.get("gs_causes",
                                      rec.get("gs_causes", [])))
        rec["iz_causes"] = list(b.get("iz_causes",
                                      rec.get("iz_causes", [])))

    def _set_edit_mode(self, on: bool) -> None:
        self._editing = on
        for w in (self.ed_title, self.ed_category, self.cb_type,
                  self.gs_list, self.iz_list,
                  self.gs_block._btn_add, self.gs_block._btn_del,
                  self.iz_block._btn_add, self.iz_block._btn_del):
            w.setEnabled(on and self._rec() is not None)
        self.btn_edit.setVisible(not on)
        self.btn_save_form.setVisible(on)
        self.btn_cancel_form.setVisible(on)

    def _begin_edit(self) -> None:
        rec = self._rec()
        if rec is None or self._editing:
            return
        self._backup = self._snapshot_of(rec)
        self._backup_id = rec.get("id")
        self._set_edit_mode(True)

    def _commit_edit(self) -> None:
        """«Сохранить»: правки уже в записи – фиксируем их (dirty для
        «Сохранить» окна БД) и выходим из режима редактирования."""
        rec = self._rec()
        if rec is None or not self._editing:
            return
        if self._backup is not None \
                and self._snapshot_of(rec) != self._backup:
            self._mark_dirty()
        else:
            self.kb.reindex()      # состав мог измениться и вернуться
        self._backup = None
        self._backup_id = None
        self._set_edit_mode(False)

    def _cancel_edit(self) -> None:
        """«Отмена»: вернуть снимок записи (правки отброшены) и выйти."""
        if self._backup is not None and self._backup_id is not None:
            rec = next((r for r in self.kb.equipment_templates
                        if r.get("id") == self._backup_id), None)
            if rec is not None:
                self._restore_backup_into(rec)
                self.kb.reindex()
                self.rebuild_cards()   # карточка/списки – к снимку
        self._backup = None
        self._backup_id = None
        self._set_edit_mode(False)

    def _form_changed(self) -> None:
        """Правка внутри режима: живой предпросмотр карточки и списков,
        индексы БД свежие; dirty НЕ поднимается (его поднимает
        «Сохранить»)."""
        self.kb.reindex()
        self.rebuild_cards()
    # ---------- форма выбранного шаблона ----------
    def _entry_title(self, entry: str, gs: bool) -> str:
        ref, _sep, flow = str(entry).partition("#")
        rec = (self.kb.gs_by_id(ref) if gs else self.kb.iz_by_id(ref)) or {}
        title = rec.get("title", ref)
        if gs and flow and self.kb.flow_titles.get(flow):
            title += f" – {self.kb.flow_titles[flow]}"
        return title

    def _fill_list(self, lw: QListWidget, entries: list, gs: bool) -> None:
        lw.blockSignals(True)
        lw.clear()
        for e in entries:
            it = QListWidgetItem(self._entry_title(e, gs))
            it.setData(Qt.ItemDataRole.UserRole, str(e))
            lw.addItem(it)
        lw.blockSignals(False)

    def _load_form(self) -> None:
        rec = self._rec()
        # смена шаблона в режиме редактирования: правки НЕ применяются
        # молча – возвращаем снимок редактируемого (как «Отмена») и
        # грузим выбранный. Пересборка ТОГО ЖЕ шаблона (карточка после
        # правки) сессию редактирования НЕ рвет
        if self._editing and self._backup is not None \
                and self._backup_id is not None \
                and (rec is None or rec.get("id") != self._backup_id):
            prev = next((r for r in self.kb.equipment_templates
                         if r.get("id") == self._backup_id), None)
            if prev is not None:
                self._restore_backup_into(prev)
                self.kb.reindex()
            self._backup = None
            self._backup_id = None
            self._set_edit_mode(False)
        on = rec is not None and self._editing
        for w in (self.ed_title, self.ed_category, self.cb_type,
                  self.gs_list, self.iz_list,
                  self.gs_block._btn_add, self.gs_block._btn_del,
                  self.iz_block._btn_add, self.iz_block._btn_del):
            w.setEnabled(on)
        if rec is None:
            self.ed_title.blockSignals(True)
            self.ed_title.clear()
            self.ed_title.blockSignals(False)
            self.ed_category.blockSignals(True)
            self.ed_category.clear()
            self.ed_category.blockSignals(False)
            self.cb_type.blockSignals(True)
            self.cb_type.setCurrentIndex(0)
            self.cb_type.blockSignals(False)
            self.gs_list.clear()
            self.iz_list.clear()
            return
        self.ed_title.blockSignals(True)
        self.ed_title.setText(rec.get("title", ""))
        self.ed_title.blockSignals(False)
        self.ed_category.blockSignals(True)
        self.ed_category.setText(rec.get("category", ""))
        self.ed_category.blockSignals(False)
        self.cb_type.blockSignals(True)
        self.cb_type.setCurrentIndex(max(
            0, self.cb_type.findData(rec.get("scenario_type", "gg"))))
        self.cb_type.blockSignals(False)
        self._fill_list(self.gs_list, rec.get("gs_causes", []), gs=True)
        self._fill_list(self.iz_list, rec.get("iz_causes", []), gs=False)

    def _edit_title(self, text: str) -> None:
        rec = self._rec()
        if self._editing and rec is not None and text.strip() \
                and text != rec.get("title"):
            rec["title"] = text.strip()
            self._form_changed()

    def _edit_category(self, text: str) -> None:
        rec = self._rec()
        if self._editing and rec is not None and text.strip() \
                and text != rec.get("category"):
            rec["category"] = text.strip()
            self._form_changed()

    def _edit_type(self, _i: int) -> None:
        rec = self._rec()
        if self._editing and rec is not None:
            st = self.cb_type.currentData()
            if st and st != rec.get("scenario_type"):
                rec["scenario_type"] = st
                self._form_changed()

    # ---------- списки ГС/ИЗ ----------
    def _add_gs_row(self) -> None:
        """Добавление из библиотеки ГС: строки развернуты по диапазонам
        расхода (Задача 8) для ГГ/ГЖ/ЛВЖ; ТГМ/Пыль – по записи."""
        from .inspector_panel import _CausePickerDialog
        rec = self._rec()
        if not self._editing or rec is None:
            return
        stype = rec.get("scenario_type", "gg")
        records = []
        for g in self.kb.gs_for(stype):
            if stype in ("gg", "gzh", "lvzh"):
                for flow in self.kb.flow_variants(g):
                    r = dict(g)
                    r["flow"] = flow
                    r["row_title"] = self.kb.flow_row_title(g, flow)
                    records.append(r)
            else:
                records.append(g)
        dlg = _CausePickerDialog(records, self)
        if dlg.exec() == _CausePickerDialog.Accepted and dlg.selected_id:
            entry = dlg.selected_id + \
                (f"#{dlg.selected_flow}" if dlg.selected_flow else "")
            rec.setdefault("gs_causes", []).append(entry)
            self._form_changed()
            self._fill_list(self.gs_list, rec.get("gs_causes", []),
                            gs=True)

    def _remove_gs_rows(self) -> None:
        rec = self._rec()
        if not self._editing or rec is None:
            return
        gone = {it.data(Qt.ItemDataRole.UserRole)
                for it in self.gs_list.selectedItems()}
        if gone:
            rec["gs_causes"] = [e for e in rec.get("gs_causes", [])
                                if str(e) not in gone]
            self._form_changed()
            self._fill_list(self.gs_list, rec.get("gs_causes", []),
                            gs=True)

    def _add_iz_row(self) -> None:
        from .inspector_panel import _CausePickerDialog
        rec = self._rec()
        if not self._editing or rec is None:
            return
        dlg = _CausePickerDialog(self.kb.iz_all(), self)
        if dlg.exec() == _CausePickerDialog.Accepted and dlg.selected_id:
            rec.setdefault("iz_causes", []).append(dlg.selected_id)
            self._form_changed()
            self._fill_list(self.iz_list, rec.get("iz_causes", []),
                            gs=False)

    def _remove_iz_rows(self) -> None:
        rec = self._rec()
        if not self._editing or rec is None:
            return
        gone = {it.data(Qt.ItemDataRole.UserRole)
                for it in self.iz_list.selectedItems()}
        if gone:
            rec["iz_causes"] = [e for e in rec.get("iz_causes", [])
                                if str(e) not in gone]
            self._form_changed()
            self._fill_list(self.iz_list, rec.get("iz_causes", []),
                            gs=False)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.dirty_changed.emit(True)
        self.kb.reindex()        # индексы БД видят правки сразу
        self.rebuild_cards()     # живой предпросмотр карточки

    # ---------- карточки ----------
    def _on_card(self, card: _TemplateCard) -> None:
        self.selected_id = card.rec["id"]
        self._mark_selected()
        self._load_form()
        self._sync_apply()

    def _on_card_dbl(self, card: _TemplateCard) -> None:
        self.selected_id = card.rec["id"]
        self._mark_selected()
        self._load_form()
        self._sync_apply()
        self._apply()

    def _apply(self) -> None:
        """Задача 3: применение возможно только при выделенном участке
        или наружной установке."""
        if self.selected_id and getattr(self, "_owner_ok", False):
            self.equipment_applied.emit(self.selected_id)

    def _sync_apply(self) -> None:
        self.btn_apply.setEnabled(
            getattr(self, "_owner_ok", False)
            and self.selected_id is not None)

    def set_owner_available(self, available: bool, owner_title: str = "") -> None:
        self._owner_ok = available
        self._sync_apply()
        if available:
            self.hint.setText(f"Цель: {owner_title}" if owner_title else "")
            self.btn_apply.setToolTip(
                "<b>Применить на холсте</b> – создать дерево выбранного"
                " типа на выделенном участке/установке"
                "<br>(двойной клик по карточке – то же самое)")
        else:
            self.hint.setText("")
            self.btn_apply.setToolTip(
                "<b>Применить на холсте</b> – выделите участок или"
                " наружную установку в иерархии объектов")
        self.hint.setVisible(bool(self.hint.text()))

    # ---------- кнопки нижней панели окна БД (Задача 10.2) ----------
    def _new_record(self) -> dict:
        import uuid as _uuid
        # умолчания нового шаблона – подтверждены заказчиком (Q&A)
        return {"id": f"eq-{_uuid.uuid4().hex[:8]}",
                "title": "Новый шаблон оборудования",
                "scenario_type": "gg", "category": "Прочее",
                "gs_causes": [], "iz_causes": []}

    def add_record(self) -> None:
        rec = self._new_record()
        self.kb.equipment_templates.append(rec)
        self.selected_id = rec["id"]
        self._mark_dirty()
        self.scroll_to_selected()
        # новый шаблон сразу готов к правке (режим «Редактировать» включен)
        self._begin_edit()

    def _confirm_delete_tpl(self, title: str, used: int) -> bool:
        """Шов подтверждения удаления шаблона (тестируется подменой)."""
        box = QMessageBox(self)
        box.setWindowTitle("Удаление шаблона")
        box.setIcon(QMessageBox.Icon.Question)
        if used > 0:
            box.setText(f"Удалить шаблон «{title}»? Его состав используют"
                        f" {used} деревьев проекта – ссылки останутся,"
                        " но шаблон пропадет из списка.")
        else:
            box.setText(f"Удалить шаблон «{title}»?")
        b_del = box.addButton("Удалить",
                              QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    def delete_current_record(self) -> None:
        rec = self._rec()
        if rec is None:
            return
        used = self.usage("equipment_templates", rec.get("id", "")) \
            if self.usage is not None else 0
        if self._confirm_delete_tpl(rec.get("title", ""), used):
            self.kb.equipment_templates.remove(rec)
            self.selected_id = None
            self._mark_dirty()

    # ---------- жизненный цикл ----------
    def flush(self) -> None:
        pass          # правки пишутся в kb.data сразу (сохранил – на диск)

    def reload(self) -> None:
        """Перечитать после «Сохранить» (kb.reload уже сделан окном)."""
        if self._rec() is None:
            self.selected_id = None
        self._backup = None
        self._backup_id = None
        self._set_edit_mode(False)
        self._dirty = False
        self.dirty_changed.emit(False)
        self.rebuild_cards()


class FireModesTab(QWidget):
    """Задача 8 (сессия 13): «Таблица типовых режимов пожара» –
    СПРАВОЧНАЯ таблица (только чтение): «Режим пожара | Базовая частота
    | Примечание». Строки (сокращенные названия – подтверждено
    заказчиком): пожар по поверхности (множитель a₁·F по табл.
    П1.3/П1.4), факельное горение, пожар-вспышка, пролив, сгорание
    (взрыв) ТВС, дефлаграция/детонация пылевоздушной смеси (все – «по
    табл. П2.1 (по расходу и среде)»), огненный шар 2,5·10⁻⁵ год⁻¹
    (прил. № 1, п. 5). Числа – инженерный формат (запятая, юникод-
    степени), никогда 2.5e-05. Правила Задачи 7 обязательны."""

    def __init__(self, kb, parent=None):
        super().__init__(parent)
        self.kb = kb
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(_caption(
            "ТИПОВЫЕ РЕЖИМЫ ПОЖАРА (прил. № 2, табл. П2.1)"))
        self.table = QTableWidget(0, 3)
        for i, head in enumerate(("Режим пожара", "Базовая частота",
                                  "Примечание")):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(head))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        _pixel_scroll(self.table)
        root.addWidget(self.table, 1)

        p21_note = ("условная вероятность воспламенения выбирается по"
                    " массовому расходу (<1 / 1–50 / >50 кг/с / полный"
                    " разрыв) и среде (газ / двухфазная / жидкость) по"
                    " прил. № 2 к Приказу МЧС России № 533, табл. П2.1")
        rows = [
            ("Пожар по поверхности",
             "a₁·F (табл. П1.3/П1.4)",
             "множитель ТГМ: a₁·F по площади и типу здания (наружной"
             " установки) – табл. П1.3/П1.4 прил. № 1 к Приказу МЧС"
             " России № 533"),
            ("Факельное горение",
             "по табл. П2.1 (по расходу и среде)", p21_note),
            ("Пожар-вспышка",
             "по табл. П2.1 (по расходу и среде)", p21_note),
            ("Пролив",
             "по табл. П2.1 (по расходу и среде)", p21_note),
            ("Сгорание (взрыв) ТВС",
             "по табл. П2.1 (по расходу и среде)", p21_note),
            ("Дефлаграция пылевоздушной смеси",
             "по табл. П2.1 (по расходу и среде)", p21_note),
            ("Детонация пылевоздушной смеси",
             "по табл. П2.1 (по расходу и среде)", p21_note),
            ("Огненный шар (диффузионное горение)",
             _fmt_eng(2.5e-5) + " год⁻¹",
             "частота внешнего воздействия на аппарат (Приказ МЧС России"
             " № 533, прил. № 1, п. 5)"),
        ]
        for title, freq, note in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(title))
            self.table.setItem(r, 1, QTableWidgetItem(freq))
            self.table.setItem(r, 2, QTableWidgetItem(wrap_text85(note)))
        _format_table(self.table)


# =====================================================================
# Задачи 9/10 (сессия 13): редактируемые библиотеки ИЗ/ГС
# =====================================================================
def _fmt_eng(v: float) -> str:
    """Инженерный формат частоты «3,2·10⁻⁵» (запятая, надстрочные
    степени; никогда 3.2e-05). 0 → «0»."""
    from ..core.layout import fmt_q
    return fmt_q(float(v))


class _NoteEditor(QDialog):
    """Небольшой редактор примечания: многострочное поле + ЖИВОЙ
    предпросмотр мини-нотации (индексы/степени, перенос ≤85 символов).
    Вызов – exec(); результат – accepted() + get_text()."""

    def __init__(self, initial: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Примечание (мини-нотация)")
        self.setMinimumSize(560, 360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)
        self.edit = QPlainTextEdit(initial)
        lay.addWidget(self.edit, 1)
        lay.addWidget(QLabel("Предпросмотр (мини-нотация → типографика):"))
        self.preview = QLabel("")
        self.preview.setTextFormat(Qt.TextFormat.RichText)
        self.preview.setWordWrap(True)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.preview, 1)
        btn = QPushButton("ОК")
        btn.setObjectName("primary")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)
        self.edit.textChanged.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        self.preview.setText("<br>".join(
            math(ln) for ln in wrap_text85(self.edit.toPlainText())
            .split("\n")))

    def text(self) -> str:
        return self.edit.toPlainText()


class _NumberEditor(QDialog):
    """Редактор числового поля (λ / частота): поле ввода в инженерной
    записи + подсказка с текущим значением; некорректный ввод
    подсвечивается. Задача 7 (сессия 14): принимаются ОБЕ записи –
    экспоненциальная («3,2e-5», «3.2e-5») и каретка («3,2^-5», где
    m^e = m×10^e); отображение всегда инженерное («3,2·10⁻⁵»)."""

    def __init__(self, title: str, value: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)
        lay.addWidget(QLabel(f"Текущее значение: {_fmt_eng(value)}"))
        self.edit = QLineEdit(f"{value:g}".replace(".", ","))
        lay.addWidget(self.edit)
        self.hint = QLabel("Допускается запись вида 3,2e-5, 3.2e-5 или"
                           " 3,2^-5 (каретка – умножить на 10 в степени)")
        self.hint.setObjectName("caption")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)
        btn = QPushButton("ОК")
        btn.setObjectName("primary")
        btn.clicked.connect(self._try_accept)
        lay.addWidget(btn)
        self._value: float | None = None

    def _try_accept(self) -> None:
        from .theme import parse_sci
        v = parse_sci(self.edit.text())
        if v is None or v < 0:
            self.hint.setText("Некорректное число – введите, например,"
                              " 3,2e-5 или 3,2^-5")
            return
        self._value = v
        self.accept()

    def value(self) -> float | None:
        return self._value


class _LibraryTab(QWidget):
    """Общий каркас редактируемой библиотеки (Задачи 9/10/0, сессия 13).

    Таблица из трёх колонок: наименование (правится прямо в ячейке),
    числовое поле (инженерный формат, правка диалогом по двойному
    клику) и примечание (мини-нотация, rich-рендер QLabel, правка
    диалогом с живым предпросмотром). Кнопки «Добавить запись» /
    «Удалить запись» – в нижней панели ОКНА БД (слева); класс
    предоставляет add_record()/delete_current_record(). Правки
    сохраняются штатным «Сохранить» (kb.save()); удаление записи,
    используемой деревьями, предупреждается (шов _confirm_delete_rec).
    Правила Задачи 7: авто-ширины столбцов, горизонтальный ползунок,
    перенос ≤85 символов по словам (длинное слово – по слогам)."""

    dirty_changed = Signal(bool)
    NUM_NONE = None          # запись без числового поля (например, p13)

    def __init__(self, section: str, columns: list[str], title: str,
                 kb: KnowledgeBase, parent=None):
        super().__init__(parent)
        self.section = section
        self.kb = kb
        self.usage = None                # (kind, id) → сколько деревьев
        self._dirty = False
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(_caption(title))
        self.table = QTableWidget(0, len(columns))
        for i, head in enumerate(columns):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(head))
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed)
        _pixel_scroll(self.table)
        root.addWidget(self.table, 1)
        self.table.itemChanged.connect(self._on_title_edited)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.reload()

    # ---------- источник данных ----------
    def records(self) -> list[dict]:
        return self.kb.data.get(self.section, [])

    def reload(self) -> None:
        def _rebuild() -> None:
            # Задача 8 (сессия 15): сигналы БЛОКИРУЮТСЯ на время сборки –
            # setItem вызывает itemChanged, и обработчик _on_title_edited
            # ПИСАЛ текст строки обратно в запись. Раньше это было
            # незаметно (текст строки = названию записи), теперь строки ГС
            # развернуты по диапазонам расхода и обратная запись
            # мутировала бы название записи на каждом rebuild
            self.table.blockSignals(True)
            try:
                self.table.setRowCount(0)
                for rec in self.records():
                    self._append_row(rec)
                _format_table(self.table)
                _pixel_scroll(self.table)
            finally:
                self.table.blockSignals(False)
        _keep_scroll_pos(self.table, _rebuild)
        self._dirty = False
        self.dirty_changed.emit(False)

    # ---------- заполнение (переопределяют наследники) ----------
    def _append_row(self, rec: dict) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        title_item = QTableWidgetItem(wrap_text85(rec.get("title", "")))
        self.table.setItem(r, 0, title_item)
        num_lbl = QLabel(self._num_text(rec))
        num_lbl.setTextFormat(Qt.TextFormat.RichText)
        num_lbl.setWordWrap(False)
        self.table.setCellWidget(r, 1, num_lbl)
        note_lbl = QLabel(self._note_html(rec))
        note_lbl.setTextFormat(Qt.TextFormat.RichText)
        note_lbl.setWordWrap(False)
        note_lbl.setAlignment(Qt.AlignmentFlag.AlignTop
                              | Qt.AlignmentFlag.AlignLeft)
        self.table.setCellWidget(r, 2, note_lbl)
        # Задача 9 (сессия 18): колонка «Источник» – запись реестра
        src_lbl = QLabel(self._source_html(rec))
        src_lbl.setTextFormat(Qt.TextFormat.RichText)
        src_lbl.setWordWrap(False)
        src_lbl.setAlignment(Qt.AlignmentFlag.AlignTop
                             | Qt.AlignmentFlag.AlignLeft)
        self.table.setCellWidget(r, 3, src_lbl)
        self._fit_row_height(r)

    def _fit_row_height(self, r: int) -> None:
        lines = 1
        for c in (1, 2, 3):
            w = self.table.cellWidget(r, c)
            if w is not None:
                lines = max(lines, w.text().count("<br") + 1)
        self.table.setRowHeight(r, max(28, 17 * lines + 10))

    # ---------- значения (переопределяют наследники) ----------
    def _num_field(self, rec: dict) -> str | None:
        """Ключ числового поля записи (lam/q/q_per_m) или None."""
        return None

    def _num_text(self, rec: dict) -> str:
        return "–"

    def _note_text(self, rec: dict) -> str:
        return rec.get("note", "")

    def _note_html(self, rec: dict) -> str:
        return "<br>".join(math(ln)
                           for ln in wrap_text85(self._note_text(rec))
                           .split("\n"))

    def _source_html(self, rec: dict) -> str:
        """Колонка «Источник»: название записи реестра (id → title),
        пусто – «–» (Задача 9)."""
        t = self.kb.source_title(rec.get("source"))
        return _html.escape(wrap_text85(t).replace("\n", "<br>")
                            if t else "–")

    def _new_record(self) -> dict:      # pragma: no cover - переопределяют
        raise NotImplementedError

    # ---------- правка ----------
    def _on_title_edited(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        rec = self.records()[item.row()] \
            if item.row() < len(self.records()) else None
        if rec is None:
            return
        text = item.text().replace("\n", " ").strip()
        if text and text != rec.get("title"):
            rec["title"] = text
            self._mark_dirty()

    def _on_double_click(self, r: int, c: int) -> None:
        rec = self.records()[r] if r < len(self.records()) else None
        if rec is None:
            return
        if c == 1:
            field = self._num_field(rec)
            if field is None:
                return
            dlg = _NumberEditor(self.windowTitle(), float(rec.get(field, 0)))
            if dlg.exec() and dlg.value() is not None:
                self._set_number(rec, field, dlg.value())
        elif c == 2:
            dlg = _NoteEditor(self._note_text(rec), self)
            if dlg.exec():
                self._set_note(rec, dlg.text())
        elif c == 3:
            # Задача 9: источник записи – комбо над реестром
            dlg = _SourceEditor(self.kb, rec.get("source", ""), self)
            if dlg.exec():
                self._set_source(rec, dlg.current_id())

    # ---------- швы для тестов (без модальных диалогов) ----------
    def _set_number(self, rec: dict, field: str, value: float) -> None:
        rec[field] = float(value)
        self._mark_dirty()
        self.reload()

    def _set_note(self, rec: dict, text: str) -> None:
        rec["note"] = text.strip()
        self._mark_dirty()
        self.reload()

    def _set_source(self, rec: dict, src_id: str) -> None:
        """Шов привязки источника (Задача 9): id записи реестра или
        пусто (без источника)."""
        rec["source"] = src_id or ""
        self._mark_dirty()
        self.reload()

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.dirty_changed.emit(True)
        # индексы БД обязаны видеть правки сразу (поиск по id в двигателе
        # и счетчик использования); сессия 13, Задачи 0/9/10
        self.kb.reindex()

    def _confirm_delete_rec(self, title: str, used: int) -> bool:
        """Шов подтверждения удаления записи (в т.ч. с предупреждением
        об использовании деревьями)."""
        box = QMessageBox(self)
        box.setWindowTitle("Удаление записи")
        box.setIcon(QMessageBox.Icon.Question)
        if used > 0:
            box.setText(f"Удалить запись «{title}»? Запись используется"
                        f" в {used} деревьях – ссылки будут потеряны.")
        else:
            box.setText(f"Удалить запись «{title}»?")
        b_del = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    # ---------- кнопки нижней панели окна БД ----------
    def add_record(self) -> None:
        rec = self._new_record()
        self.records().append(rec)
        self._mark_dirty()
        self.reload()
        self.table.scrollToBottom()

    def delete_current_record(self) -> None:
        r = self.table.currentRow()
        if r < 0 or r >= len(self.records()):
            return
        rec = self.records()[r]
        used = self.usage(self.section, rec.get("id", "")) \
            if self.usage is not None else 0
        if self._confirm_delete_rec(rec.get("title", ""), used):
            self.records().pop(r)
            self._mark_dirty()
            self.reload()

    # ---------- сохранение ----------
    def flush(self) -> None:
        pass          # правки пишутся в kb.data сразу (сохранил – на диск)


class IZLibraryTab(_LibraryTab):
    """Задача 9 (сессия 13): «Источники зажигания (ИЗ)» – редактируемая
    библиотека причин появления ИЗ. Колонки «Наименование ИЗ | λ, год⁻¹ |
    Примечание»; λ в инженерном формате («3,2·10⁻⁵»); «Удар молнии» –
    расчётная величина N_у.м·(1 − η_МЗ) по свойствам здания/установки;
    записи с прямой вероятностью – «P = <знач> (вероятность)». Источники
    живут внутри примечания; новая запись – только 3 видимых поля,
    остальное (id iz-<uuid8>, lam) генерируется автоматически."""

    def __init__(self, kb, parent=None):
        super().__init__(
            "iz_causes",
            ["Наименование ИЗ", "λ, год⁻¹", "Примечание", "Источник"],
            "БИБЛИОТЕКА ПРИЧИН ПОЯВЛЕНИЯ ИСТОЧНИКОВ ЗАЖИГАНИЯ (ИЗ)",
            kb, parent)

    def _num_field(self, rec: dict) -> str | None:
        if rec.get("mode") == "lightning" or "p" in rec:
            return None              # расчётная величина / вероятность
        return "lam"

    def _num_text(self, rec: dict) -> str:
        if rec.get("mode") == "lightning":
            return math("расчётная величина")
        if "p" in rec:
            pv = f"{float(rec['p']):g}".replace(".", ",")
            return math(f"P = {pv} (вероятность)")
        return math(_fmt_eng(rec.get("lam", 0.0)) + " год⁻¹")

    def _note_text(self, rec: dict) -> str:
        if rec.get("note"):
            return rec["note"]
        src = self.kb.source_title(rec.get("source"))
        if rec.get("mode") == "lightning":
            return (f"рассчитывается по свойствам здания/установки:"
                    f" N_у.м·(1 − η_МЗ) ({src})" if src else
                    "рассчитывается по свойствам здания/установки:"
                    " N_у.м·(1 − η_МЗ)")
        return src

    def _new_record(self) -> dict:
        import uuid as _uuid
        return {"id": f"iz-{_uuid.uuid4().hex[:8]}",
                "title": "Новый источник зажигания",
                "lam": 1e-5, "note": "",
                "source": ""}


class GSLibraryTab(_LibraryTab):
    """Задача 10 (сессия 13): «Горючие среды (ГС)» – редактируемая
    библиотека причин возникновения ГС. Колонки «Наименование ГС |
    Частота, год⁻¹ | Примечание»: П1.1 – инженерный формат; трубопроводы
    П1.2 – удельная частота × L; «Поверхность (ТГМ)» – a₁·F по табл.
    П1.3/П1.4. Новая запись: 3 видимых поля + авто (id gs-<uuid8>,
    kind p11, applies/site_kinds – доступность в выборе причин).
    Задача 8 (сессия 15, LOCKED): каждая разгерметизационная запись
    развернута в СТРОКИ ПО ДИАПАЗОНАМ массового расхода истечения
    (kb.flow_variants: «отверстие …» – три диапазона, «полное
    разрушение»/«разрыв» – одна строка «полный разрыв», direct/ТГМ –
    одна строка). Правка названия/частоты/примечания меняет ЗАПИСЬ
    (все её строки); удаление удаляет запись со всеми строками."""

    def __init__(self, kb, parent=None):
        super().__init__(
            "gs_causes",
            ["Наименование ГС", "Частота, год⁻¹", "Примечание", "Источник"],
            "БИБЛИОТЕКА ПРИЧИН ВОЗНИКНОВЕНИЯ ГОРЮЧИХ СРЕД (ГС)",
            kb, parent)
        self._row_recs: list[dict] = []      # строка таблицы → запись
        self._row_flows: list = []           # строка таблицы → диапазон

    # ---------- развертка по диапазонам расхода ----------
    def reload(self) -> None:
        def _rebuild() -> None:
            # Задача 8 (сессия 15): блокируем itemChanged на время сборки –
            # иначе развернутая строка (с суффиксом диапазона) писалась бы
            # обратно в название ЗАПИСИ (см. комментарий _LibraryTab.reload)
            self.table.blockSignals(True)
            try:
                self._row_recs = []
                self._row_flows = []
                self.table.setRowCount(0)
                for rec in self.records():
                    for flow in self.kb.flow_variants(rec):
                        self._append_row(rec, flow)
                _format_table(self.table)
                _pixel_scroll(self.table)
            finally:
                self.table.blockSignals(False)
        _keep_scroll_pos(self.table, _rebuild)
        self._dirty = False
        self.dirty_changed.emit(False)

    def _append_row(self, rec: dict, flow=None) -> None:
        self._row_recs.append(rec)
        self._row_flows.append(flow)
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(wrap_text85(
            self.kb.flow_row_title(rec, flow))))
        num_lbl = QLabel(self._num_text(rec))
        num_lbl.setTextFormat(Qt.TextFormat.RichText)
        num_lbl.setWordWrap(False)
        self.table.setCellWidget(r, 1, num_lbl)
        note_lbl = QLabel(self._note_html(rec))
        note_lbl.setTextFormat(Qt.TextFormat.RichText)
        note_lbl.setWordWrap(False)
        note_lbl.setAlignment(Qt.AlignmentFlag.AlignTop
                              | Qt.AlignmentFlag.AlignLeft)
        self.table.setCellWidget(r, 2, note_lbl)
        # Задача 9 (сессия 18): колонка «Источник» (у всех строк записи)
        src_lbl = QLabel(self._source_html(rec))
        src_lbl.setTextFormat(Qt.TextFormat.RichText)
        src_lbl.setWordWrap(False)
        src_lbl.setAlignment(Qt.AlignmentFlag.AlignTop
                             | Qt.AlignmentFlag.AlignLeft)
        self.table.setCellWidget(r, 3, src_lbl)
        self._fit_row_height(r)

    def _rec_at(self, row: int) -> dict | None:
        return self._row_recs[row] if 0 <= row < len(self._row_recs) \
            else None

    # ---------- правка (запись, не строка развертки) ----------
    def _on_title_edited(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        rec = self._rec_at(item.row())
        if rec is None:
            return
        text = item.text().replace("\n", " ").strip()
        # Задача 8: строка развернута – суффикс диапазона расхода не
        # пишется в название ЗАПИСИ (иначе на следующей сборке он
        # задвоился бы)
        for fl in self.kb.flow_titles.values():
            suf = f" – {fl}"
            if text.endswith(suf):
                text = text[:-len(suf)].rstrip()
                break
        if text and text != rec.get("title"):
            rec["title"] = text
            self._mark_dirty()

    def _on_double_click(self, r: int, c: int) -> None:
        rec = self._rec_at(r)
        if rec is None:
            return
        if c == 1:
            field = self._num_field(rec)
            if field is None:
                return
            dlg = _NumberEditor(self.windowTitle(), float(rec.get(field, 0)))
            if dlg.exec() and dlg.value() is not None:
                self._set_number(rec, field, dlg.value())
        elif c == 2:
            dlg = _NoteEditor(self._note_text(rec), self)
            if dlg.exec():
                self._set_note(rec, dlg.text())
        elif c == 3:
            # Задача 9 (сессия 18): источник записи – комбо над реестром
            dlg = _SourceEditor(self.kb, rec.get("source", ""), self)
            if dlg.exec():
                self._set_source(rec, dlg.current_id())

    # ---------- кнопки нижней панели окна БД ----------
    def add_record(self) -> None:
        rec = self._new_record()
        self.records().append(rec)
        self._mark_dirty()
        self.reload()
        self.table.scrollToBottom()

    def delete_current_record(self) -> None:
        rec = self._rec_at(self.table.currentRow())
        if rec is None:
            return
        used = self.usage(self.section, rec.get("id", "")) \
            if self.usage is not None else 0
        if self._confirm_delete_rec(rec.get("title", ""), used):
            self.records().remove(rec)
            self._mark_dirty()
            self.reload()

    def _num_field(self, rec: dict) -> str | None:
        kind = rec.get("kind", "p11")
        if kind == "p12":
            return "q_per_m"
        if kind in ("p11", "direct"):
            return "q"
        return None                    # p13: множитель a₁·F – не число

    def _num_text(self, rec: dict) -> str:
        kind = rec.get("kind", "p11")
        if kind == "p13":
            return math("a₁·F (табл. П1.3/П1.4)")
        if kind == "p12":
            return math(_fmt_eng(rec.get("q_per_m", 0.0))
                        + " м⁻¹·год⁻¹ × L")
        return math(_fmt_eng(rec.get("q", 0.0)) + " год⁻¹")

    def _note_text(self, rec: dict) -> str:
        if rec.get("note"):
            return rec["note"]
        kind = rec.get("kind", "p11")
        src = self.kb.source_title(rec.get("source"))
        if kind == "p12":
            return (f"L – длина прокладки, м; задается на ноде ГС"
                    f" (или в свойствах участка) ({src})" if src else
                    "L – длина прокладки, м; задается на ноде ГС"
                    " (или в свойствах участка)")
        if kind == "p13":
            return (f"базовая частота – множитель a₁·F по площади и типу"
                    f" здания/наружной установки ({src})" if src else
                    "базовая частота – множитель a₁·F по площади и типу"
                    " здания/наружной установки")
        return src

    def _new_record(self) -> dict:
        import uuid as _uuid
        return {"id": f"gs-{_uuid.uuid4().hex[:8]}",
                "title": "Новая причина ГС",
                "kind": "p11", "q": 1e-5, "note": "",
                # доступность в выборе причин ГС: сценарии разгерметизации
                # (ГГ/ГЖ/ЛВЖ/Пыль) на аппаратных участках – документировано
                # в отчете сессии 13
                "applies": ["gg", "gzh", "lvzh", "dust"],
                "site_kinds": ["apparatus"],
                "source": ""}


# носители защитных средств (Задача 0, сессия 13): отображаемые названия
TARGET_TITLES = {"gs": "Нода ГС", "iz": "Нода ИЗ",
                 "room": "Помещение", "building": "Здание"}


def _measure_coef(m: dict) -> str:
    """Коэффициент меры в таблице: числовые значения остаются числами,
    терминология – по канону сессии 11 (русский термин, латинская
    аббревиатура в скобках; без слова «барьер»). Столбец – QLabel
    rich text, мини-нотация допустима. Переопределение пользователя –
    в rec["coef"] (Задача 0)."""
    if m.get("coef"):
        return m["coef"]
    if m.get("type") == "k":
        kv = f"{float(m.get('k', 1.0)):g}".replace(".", ",")
        return f"k = {kv}"
    if m.get("type") == "lambda_k" and "k" in m:
        return f"{m['k']:g}".replace(".", ",")
    if "p_success" in m:
        if m["p_success"] == 0.0:
            # достоверное событие: множитель не «отказ защиты»,
            # а сама условная вероятность воспламенения
            return "P_воспл = 1"
        return f"1 − {m['p_success']:g}".replace(".", ",") + \
            " (вероятность отказа по запросу)"
    if m.get("type") == "sil":
        return "по уровню полноты безопасности (SIL)"
    if m.get("type") == "pfd_avg":
        return "PFD_avg ≈ λ_DU·T/2"
    if m.get("type") == "voting":
        return "по схеме резервирования"
    if "eta_levels" in m:
        return "η = 0,98…0,80"
    return "–"


def _measure_note(m: dict, kb: KnowledgeBase | None = None) -> str:
    """Примечание по канону сессии 11: «формула (источник) – описание».
    Задача 9 (сессия 18): источник записи разрешается через РЕЕСТР
    (id → название). Задача 7 (сессия 13): перенос ≤85 символов по
    словам со слоговым разбиением; мини-нотация → rich text построчно.
    Переопределение пользователя – в rec["note"] (Задача 0)."""
    if m.get("note"):
        plain = m["note"]
    else:
        formula = (m.get("formula") or "").strip()
        source = kb.source_title(m.get("source")) if kb is not None \
            else str(m.get("source") or "").strip()
        notes = (m.get("notes") or "").strip()
        head = f"{formula} ({source})" if (formula and source) \
            else (formula or source)
        plain = f"{head} – {notes}" if (head and notes) else (head or notes)
    return "<br>".join(math(ln) for ln in wrap_text85(plain).split("\n"))


class MeasuresLibraryTab(QWidget):
    """Задача 0 (сессия 13): «Защитные средства» – РЕДАТИРУЕМАЯ
    библиотека мер. Четыре колонки: «Наименование средства |
    Коэффициент | Носитель | Примечание» (носитель – отдельная
    колонка, подтверждено заказчиком). Наименование правится прямо в
    ячейке; коэффициент: записи с числом (k / p_success) – числовой
    редактор, правка ВЛИЯЕТ на расчет (движок читает запись БД);
    структурные записи (SIL, ТО, срезка ветвей, молниезащита) – текст
    мини-нотации; носитель – выбор из четырех значений (место
    переключателя); примечание – мини-нотация с живым предпросмотром.
    Новая запись – переключатель с универсальным множителем k
    (type "k") на выбранном носителе; ключ педали и остальное
    генерируются автоматически. Правила Задачи 7 обязательны."""

    dirty_changed = Signal(bool)
    # числовые поля коэффициентов, влияющие на расчет (педаль → ключ)
    _ENGINE_NUM = {"wear": "k", "hermetic": "k", "vibro_control": "k",
                   "drain": "p_success", "leak_detectors": "p_success"}

    def __init__(self, kb, parent=None):
        super().__init__(parent)
        self.kb = kb
        self.usage = None
        self._dirty = False
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(_caption(PEDALS_CAPTION))
        self.table = QTableWidget(0, 5)
        for i, head in enumerate(("Наименование средства", "Коэффициент",
                                  "Носитель", "Примечание", "Источник")):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(head))
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed)
        _pixel_scroll(self.table)
        root.addWidget(self.table, 1)
        self.table.itemChanged.connect(self._on_title_edited)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.reload()

    # ---------- данные ----------
    def records(self) -> list[dict]:
        return self.kb.data.get("property_modifiers", [])

    def reload(self) -> None:
        def _rebuild() -> None:
            # Задача 8 (сессия 15): сигналы БЛОКИРУЮТСЯ на время сборки –
            # setItem вызывает itemChanged, и обработчик _on_title_edited
            # ПИСАЛ текст строки обратно в запись. Раньше это было
            # незаметно (текст строки = названию записи), теперь строки ГС
            # развернуты по диапазонам расхода и обратная запись
            # мутировала бы название записи на каждом rebuild
            self.table.blockSignals(True)
            try:
                self.table.setRowCount(0)
                for rec in self.records():
                    self._append_row(rec)
                _format_table(self.table)
                _pixel_scroll(self.table)
            finally:
                self.table.blockSignals(False)
        _keep_scroll_pos(self.table, _rebuild)
        self._dirty = False
        self.dirty_changed.emit(False)

    def _append_row(self, rec: dict) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(
            wrap_text85(rec.get("title", rec.get("pedal", rec["id"])))))
        coef = QLabel(math(_measure_coef(rec)))
        coef.setTextFormat(Qt.TextFormat.RichText)
        coef.setWordWrap(False)
        self.table.setCellWidget(r, 1, coef)
        tgt = QLabel(TARGET_TITLES.get(rec.get("target"), "Нода ГС"))
        tgt.setWordWrap(False)
        self.table.setCellWidget(r, 2, tgt)
        note = QLabel(_measure_note(rec, self.kb))
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setWordWrap(False)
        note.setAlignment(Qt.AlignmentFlag.AlignTop
                          | Qt.AlignmentFlag.AlignLeft)
        self.table.setCellWidget(r, 3, note)
        # Задача 9 (сессия 18): колонка «Источник»
        src = self.kb.source_title(rec.get("source"))
        src_lbl = QLabel(_html.escape(wrap_text85(src).replace("\n", "<br>")
                                      if src else "–"))
        src_lbl.setTextFormat(Qt.TextFormat.RichText)
        src_lbl.setWordWrap(False)
        src_lbl.setAlignment(Qt.AlignmentFlag.AlignTop
                             | Qt.AlignmentFlag.AlignLeft)
        self.table.setCellWidget(r, 4, src_lbl)
        self._fit_row_height(r)

    def _fit_row_height(self, r: int) -> None:
        lines = 1
        for c in (1, 3, 4):
            w = self.table.cellWidget(r, c)
            if w is not None:
                lines = max(lines, w.text().count("<br") + 1)
        self.table.setRowHeight(r, max(28, 17 * lines + 10))

    # ---------- коэффициент: число (влияет на расчет) или текст ----------
    def _num_field(self, rec: dict) -> str | None:
        if rec.get("type") == "k":
            return "k"
        return self._ENGINE_NUM.get(rec.get("pedal"))

    def _on_title_edited(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        rec = self.records()[item.row()] \
            if item.row() < len(self.records()) else None
        if rec is None:
            return
        text = item.text().replace("\n", " ").strip()
        if text and text != rec.get("title"):
            rec["title"] = text
            self._mark_dirty()

    def _on_double_click(self, r: int, c: int) -> None:
        rec = self.records()[r] if r < len(self.records()) else None
        if rec is None:
            return
        if c == 1:
            field = self._num_field(rec)
            if field is not None:
                dlg = _NumberEditor("Коэффициент",
                                    float(rec.get(field, 1.0)), self)
                if dlg.exec() and dlg.value() is not None:
                    self._set_number(rec, field, dlg.value())
            else:
                # структурная мера: коэффициент – текст мини-нотации
                dlg = _NoteEditor(_measure_coef(rec), self)
                if dlg.exec():
                    self._set_coef_text(rec, dlg.text())
        elif c == 2:
            items = list(TARGET_TITLES.items())
            dlg = QDialog(self)
            dlg.setWindowTitle("Носитель")
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(12, 12, 12, 12)
            cb = wide_combo()
            for key, title in items:
                cb.addItem(title, key)
            cb.setCurrentIndex(max(0, cb.findData(
                rec.get("target", "gs"))))
            lay.addWidget(cb)
            btn = QPushButton("ОК")
            btn.setObjectName("primary")
            btn.clicked.connect(dlg.accept)
            lay.addWidget(btn)
            if dlg.exec():
                self._set_target(rec, cb.currentData())
        elif c == 3:
            dlg = _NoteEditor((rec.get("note") or _measure_note(rec, self.kb)
                               .replace("<br>", "\n")), self)
            if dlg.exec():
                self._set_note(rec, dlg.text())
        elif c == 4:
            # Задача 9 (сессия 18): источник меры – комбо над реестром
            dlg = _SourceEditor(self.kb, rec.get("source", ""), self)
            if dlg.exec():
                self._set_source(rec, dlg.current_id())

    # ---------- швы для тестов (без модальных диалогов) ----------
    def _set_number(self, rec: dict, field: str, value: float) -> None:
        rec[field] = float(value)
        rec.pop("coef", None)          # числовое значение важнее текста
        self._mark_dirty()
        self.reload()

    def _set_coef_text(self, rec: dict, text: str) -> None:
        rec["coef"] = text.strip()
        self._mark_dirty()
        self.reload()

    def _set_target(self, rec: dict, target: str) -> None:
        rec["target"] = target
        self._mark_dirty()
        self.reload()

    def _set_note(self, rec: dict, text: str) -> None:
        rec["note"] = text.strip()
        self._mark_dirty()
        self.reload()

    def _set_source(self, rec: dict, src_id: str) -> None:
        """Шов привязки источника меры (Задача 9)."""
        rec["source"] = src_id or ""
        self._mark_dirty()
        self.reload()

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.dirty_changed.emit(True)
        # индексы БД обязаны видеть правки сразу (поиск по id в двигателе
        # и счетчик использования); сессия 13, Задачи 0/9/10
        self.kb.reindex()

    def _confirm_delete_rec(self, title: str, used: int) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle("Удаление записи")
        box.setIcon(QMessageBox.Icon.Question)
        if used > 0:
            box.setText(f"Удалить запись «{title}»? Запись используется"
                        f" в {used} деревьях – ссылки будут потеряны.")
        else:
            box.setText(f"Удалить запись «{title}»?")
        b_del = box.addButton("Удалить",
                              QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    # ---------- кнопки нижней панели окна БД ----------
    def _new_record(self) -> dict:
        import uuid as _uuid
        pid = f"pm-{_uuid.uuid4().hex[:8]}"
        return {"id": pid, "pedal": pid,
                "title": "Новое защитное средство",
                "type": "k", "k": 1.0, "target": "gs",
                "formula": "F_вых = F_вх · k", "note": "",
                "source": "", "notes": ""}

    def add_record(self) -> None:
        rec = self._new_record()
        self.records().append(rec)
        self._mark_dirty()
        self.reload()
        self.table.scrollToBottom()

    def delete_current_record(self) -> None:
        r = self.table.currentRow()
        if r < 0 or r >= len(self.records()):
            return
        rec = self.records()[r]
        used = self.usage(self.section_name(), rec.get("id", "")) \
            if self.usage is not None else 0
        if self._confirm_delete_rec(rec.get("title", ""), used):
            self.records().pop(r)
            self._mark_dirty()
            self.reload()

    def section_name(self) -> str:
        return "property_modifiers"

    def flush(self) -> None:
        pass      # правки пишутся в kb.data сразу (сохранил – на диск)


class MethodTablesTab(QWidget):
    """«Таблицы типовых частот» (Задача 3, сессия 11) – вложенные
    под-вкладки П1.3/П1.4/П2.1, только чтение. Каждая таблица занимает
    всю площадь своей под-вкладки (растянутые столбцы, попиксельный
    скролл). Подпись П1.4 – корректная формула a·F^b через math()."""

    def __init__(self, kb, parent=None):
        super().__init__(parent)
        self.kb = kb
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        root.addWidget(_caption(
            "ТАБЛИЦЫ ТИПОВЫХ ЧАСТОТ (ТОЛЬКО ЧТЕНИЕ)"))

        def mk_table(rows: int, headers: list[str]) -> QTableWidget:
            t = QTableWidget(rows, len(headers))
            t.setHorizontalHeaderLabels(headers)
            t.verticalHeader().setVisible(False)
            t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            t.setWordWrap(True)
            _pixel_scroll(t)              # Задача 2: попиксельный скролл
            return t

        def finish_table(t: QTableWidget) -> None:
            """Задача 7 (сессия 13): авто-ширины по содержимому без
            сжатия столбцов, горизонтальный ползунок AsNeeded."""
            _format_table(t)

        def page(caption_rich: str, table: QTableWidget) -> QWidget:
            """Под-вкладка: подпись с формулой (rich) + таблица на всё."""
            host = QWidget()
            lay = QVBoxLayout(host)
            lay.setContentsMargins(0, 6, 0, 0)
            lay.setSpacing(4)
            lab = QLabel(caption_rich)
            lab.setObjectName("caption")
            lab.setTextFormat(Qt.TextFormat.RichText)
            lab.setWordWrap(True)
            lay.addWidget(lab)
            lay.addWidget(table, 1)
            return host

        # --- под-вкладка 1: П1.3 ------------------------------------------
        t13 = mk_table(len(kb.p13), ["Тип здания/помещения",
                                     math("a₁, м⁻²·год⁻¹")])
        for i, r in enumerate(kb.p13):
            t13.setItem(i, 0, QTableWidgetItem(r["title"]))
            t13.setItem(i, 1, QTableWidgetItem(f"{r['a1']:g}"))
        finish_table(t13)

        # --- под-вкладка 2: П1.4 (формула приведена к виду Q = a·F^b) ----
        t14 = mk_table(len(kb.p14), ["Тип здания/помещения",
                                     "a", "b"])
        for i, r in enumerate(kb.p14):
            t14.setItem(i, 0, QTableWidgetItem(r["title"]))
            t14.setItem(i, 1, QTableWidgetItem(f"{r['a']:g}"))
            t14.setItem(i, 2, QTableWidgetItem(f"{r['b']:g}"))
        finish_table(t14)

        # --- под-вкладка 3: П2.1 ------------------------------------------
        t21 = mk_table(12, ["Расход", "Среда", "Мгновенное",
                            "Последующее", "С изб. давлением"])
        flows = ("small", "mid", "big", "rupt")
        titles = {"small": "< 1 кг/с", "mid": "1–50 кг/с",
                  "big": "> 50 кг/с", "rupt": "полный разрыв"}
        r = 0
        for f in flows:
            for medium, label in (("gas", "газ"),
                                  ("twophase", "двухфазная"),
                                  ("liquid", "жидкость")):
                vals = kb.p21.get(f, {}).get(medium, ["", "", ""])
                t21.setItem(r, 0, QTableWidgetItem(titles[f]))
                t21.setItem(r, 1, QTableWidgetItem(label))
                for c, v in enumerate(vals):
                    t21.setItem(r, 2 + c,
                                QTableWidgetItem(f"{v:g}"))
                r += 1
        finish_table(t21)

        # Задача 3: каждая таблица – в своей под-вкладке
        self.sub = QTabWidget()
        self.sub.setObjectName("kbSubTabs")     # компактный стиль в theme.py
        self.sub.addTab(
            page(f"Частоты пожаров в зданиях ({math('Q = a₁·F')})", t13),
            "П1.3 – частоты пожаров")
        self.sub.addTab(
            page(f"При F > 10 000 м² ({math('Q = a·F^b')})", t14),
            "П1.4 – при F > 10 000 м²")
        self.sub.addTab(
            page("Условные вероятности воспламенения", t21),
            "П2.1 – условные вероятности воспламенения")
        root.addWidget(self.sub, 1)


class _SourceEditor(QDialog):
    """Задача 9 (сессия 18): выбор источника записи из РЕЕСТРА. Комбо
    над реестром + строка «Без источника» + быстрое добавление нового
    источника («Добавить источник…»). Вызов – exec(); результат –
    current_id() (пустая строка = без источника)."""

    def __init__(self, kb: KnowledgeBase, current: str, parent=None):
        super().__init__(parent)
        self.kb = kb
        self.setWindowTitle("Источник записи")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)
        lay.addWidget(QLabel("Нормативный или справочный источник:"))
        self.combo = wide_combo()
        self._fill(current)
        lay.addWidget(self.combo)
        hint = QLabel("Источник печатается в разделе «Нормативные ссылки"
                      " и справочные данные» отчета для записей,"
                      " участвующих в расчете.")
        hint.setObjectName("caption")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        row = QHBoxLayout()
        b_add = QPushButton("Добавить источник…")
        b_add.clicked.connect(self._quick_add)
        row.addWidget(b_add)
        row.addStretch(1)
        b_ok = QPushButton("ОК")
        b_ok.setObjectName("primary")
        b_ok.clicked.connect(self.accept)
        b_no = QPushButton("Без источника")
        b_no.clicked.connect(self._clear_and_accept)
        row.addWidget(b_no)
        row.addWidget(b_ok)
        lay.addLayout(row)

    def _fill(self, current: str) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("– Без источника –", "")
        for s in self.kb.sources:
            self.combo.addItem(s.get("title", s.get("id", "")),
                               s.get("id", ""))
        idx = self.combo.findData(current or "")
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo.blockSignals(False)

    def _quick_add(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, "Новый источник",
            "Наименование источника (документ, таблица, пункт):")
        if not ok:
            return
        text = text.strip()
        if not text:
            return
        import uuid as _uuid
        rec = {"id": f"src-{_uuid.uuid4().hex[:8]}", "title": text}
        self.kb.data.setdefault("sources", []).append(rec)
        self.kb.reindex()
        self._fill(rec["id"])

    def _clear_and_accept(self) -> None:
        self.combo.setCurrentIndex(0)
        self.accept()

    def current_id(self) -> str:
        return str(self.combo.currentData() or "")


# =====================================================================
# Задача 13 (сессия 18): справка «Базы данных» – мини-нотация формул
# документируется ТОЛЬКО тем, что реально поддерживает рендерер
# (math_text.math) и числовой ввод (numfmt.parse_eng). Каждый пример
# проверяется smoke-блоком 25: math(ввод) == ожидание.
# =====================================================================
HELP_EXAMPLES: list[tuple[str, str]] = [
    ("F_зд", "F<sub>зд</sub>"),                 # нижний индекс – одно слово
    ("N_{у.м}", "N<sub>у.м</sub>"),             # сложный индекс – в скобках
    ("λ_DU", "λ<sub>DU</sub>"),                 # латиница в индексе
    ("10^-2", "10<sup>-2</sup>"),               # верхний индекс – степень
    ("a·F^b", "a·F<sup>b</sup>"),
    ("Q = \\lambda·L", "Q = λ·L"),              # макрос \lambda
    ("PFD_{avg} = \\lambda_DU·T/2",
     "PFD<sub>avg</sub> = λ<sub>DU</sub>·T/2"),
    ("9·10⁻⁵ год⁻¹", "9·10⁻⁵ год⁻¹"),           # юникод-степени – как есть
]

HELP_NUMBER_INPUT = ["3,2e-5", "3.2e-5", "3,2^-5", "6,2·10^-4"]


def _help_text() -> str:
    """Текст справки «Базы данных» (Задача 13): короткая, один экран,
    нумерованные разделы. Формулы – в мини-нотации ИСХОДНИКА (примеры
    HELP_EXAMPLES); окно рендерит их через math(). Шов тестируется без
    exec: непустой текст, заголовки разделов, примеры-источники."""
    lines = [
        "1. Что такое «База данных»",
        "Вкладки: шаблоны оборудования, горючие среды (ГС), источники"
        " зажигания (ИЗ), типовые режимы пожара, таблицы типовых частот,"
        " защитные средства, источники. При удалении записи, которую"
        " используют деревья проекта, выводится предупреждение.",
        "",
        "2. Добавление, правка и удаление записей",
        "Кнопки «Добавить запись» и «Удалить запись» внизу окна работают"
        " на редактируемых вкладках. Название правится прямо в ячейке;"
        " частота, коэффициент и примечание – двойным кликом по ячейке."
        " «Сохранить» записывает правки в файл базы. Вкладка «Источники» –"
        " реестр нормативных документов; привязка записи к источнику –"
        " двойной клик по колонке «Источник».",
        "",
        "3. Формульная запись (мини-нотация)",
        "Нижний индекс – подчеркивание: F_зд; сложный индекс – в фигурных"
        " скобках: N_{у.м}. Верхний индекс (степень) – крышка: 10^-2,"
        " a·F^b. Греческие буквы и знак умножения можно писать макросами:"
        " \\lambda – λ, \\cdot – ·. Примеры:",
    ]
    for src, _out in HELP_EXAMPLES:
        lines.append(f"    {src}")
    lines += [
        "Числа в инженерной записи: 9·10⁻⁵. В числовых полях допускаются"
        " равнозначные варианты ввода (каретка означает «умножить на 10"
        " в степени»):",
        "Ввод: " + ", ".join(HELP_NUMBER_INPUT),
        "",
        "4. Как записи попадают в расчет и отчет",
        "Причины добавляются в инспекторе дерева; частоты и коэффициенты"
        " берутся из записей базы. Раздел отчета «Нормативные ссылки"
        " и справочные данные» формируется по реестру источников: печатаются"
        " только источники записей, участвующих в расчете проекта.",
    ]
    return "\n".join(lines)


class KBHelpWindow(QDialog):
    """Окно справки «Базы данных» (Задача 13): НЕмодальное, плоский
    канон; контент строится из _help_text() (шов), формулы рендерятся
    math() в настоящие индексы/степени; ширина по чтению, скролл."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справка: База данных")
        self.setModal(False)
        self.resize(600, 520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 8, 0)
        bl.setSpacing(6)
        for ln in _help_text().split("\n"):
            lab = QLabel()
            lab.setTextFormat(Qt.TextFormat.RichText)
            lab.setWordWrap(True)
            if not ln.strip():
                lab.setText("&nbsp;")
            elif ln.strip().startswith(("1.", "2.", "3.", "4.")):
                lab.setText(f"<b>{math(ln.strip())}</b>")
            elif ln.startswith("Ввод:"):
                # синтаксис ЧИСЛОВОГО ввода – буквально (без math():
                # каретка здесь – то, что печатают, а не степень)
                lab.setText(f"<code>{_html.escape(ln)}</code>")
            elif ln.strip().startswith("    "):
                src = ln.strip()
                rendered = math(src)
                lab.setText(f"<code>{_html.escape(src)}</code>"
                            f" &nbsp;→&nbsp; {rendered}")
            else:
                lab.setText(math(ln))
            bl.addWidget(lab)
        bl.addStretch(1)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        btn = QPushButton("Закрыть")
        btn.setObjectName("primary")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)


class SourcesTab(QWidget):
    """Задача 9 (сессия 18): «Источники» – РЕЕСТР нормативных и справоч-
    ных источников базы. Таблица «Наименование» (правится прямо в
    ячейке, как у библиотек ГС/ИЗ); добавление/удаление – кнопками
    нижней панели окна «База данных». Удаление источника, на который
    ссылаются записи, предупреждается; подтверждение ОЧИЩАЕТ привязки
    этих записей (висячих ссылок не остаётся)."""

    dirty_changed = Signal(bool)

    def __init__(self, kb: KnowledgeBase, parent=None):
        super().__init__(parent)
        self.kb = kb
        self._dirty = False
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(_caption("РЕЕСТР ИСТОЧНИКОВ (НОРМАТИВНЫЕ ССЫЛКИ"
                                " И СПРАВОЧНЫЕ ДАННЫЕ)"))
        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("Наименование"))
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed)
        _pixel_scroll(self.table)
        root.addWidget(self.table, 1)
        self.table.itemChanged.connect(self._on_title_edited)
        self.reload()

    # ---------- данные ----------
    def records(self) -> list[dict]:
        return self.kb.data.get("sources", [])

    def reload(self) -> None:
        def _rebuild() -> None:
            self.table.blockSignals(True)
            try:
                self.table.setRowCount(0)
                for rec in self.records():
                    self._append_row(rec)
                _format_table(self.table)
                _pixel_scroll(self.table)
            finally:
                self.table.blockSignals(False)
        _keep_scroll_pos(self.table, _rebuild)
        self._dirty = False
        self.dirty_changed.emit(False)

    def _append_row(self, rec: dict) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(wrap_text85(
            rec.get("title", rec.get("id", "")))))

    def _on_title_edited(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        rec = self.records()[item.row()] \
            if item.row() < len(self.records()) else None
        if rec is None:
            return
        text = item.text().replace("\n", " ").strip()
        if text and text != rec.get("title"):
            rec["title"] = text
            self._mark_dirty()

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.dirty_changed.emit(True)
        self.kb.reindex()      # source_title видит новое название сразу

    # ---------- кнопки нижней панели окна БД ----------
    def _new_record(self) -> dict:
        import uuid as _uuid
        return {"id": f"src-{_uuid.uuid4().hex[:8]}",
                "title": "Новый источник"}

    def add_record(self) -> None:
        rec = self._new_record()
        self.records().append(rec)
        self._mark_dirty()
        self.reload()
        self.table.scrollToBottom()
        self.table.editItem(self.table.item(self.table.rowCount() - 1, 0))

    def _confirm_delete_src(self, title: str, used: int) -> bool:
        """Шов подтверждения удаления источника (тестируется подменой)."""
        box = QMessageBox(self)
        box.setWindowTitle("Удаление источника")
        box.setIcon(QMessageBox.Icon.Question)
        if used > 0:
            box.setText(f"Удалить источник «{title}»? На него ссылаются"
                        f" {used} записей – их привязки будут очищены.")
        else:
            box.setText(f"Удалить источник «{title}»?")
        b_del = box.addButton("Удалить",
                              QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_del)
        b_del.setFocus()
        box.exec()
        return box.clickedButton() is b_del

    def delete_current_record(self) -> None:
        r = self.table.currentRow()
        if r < 0 or r >= len(self.records()):
            return
        rec = self.records()[r]
        sid = rec.get("id", "")
        used = self.kb.source_records_of(sid)
        if self._confirm_delete_src(rec.get("title", ""), used):
            # подтверждено: снять привязки записей (без висячих ссылок)
            for sec in ("gs_causes", "iz_causes", "property_modifiers"):
                for rrec in self.kb.data.get(sec, []):
                    if rrec.get("source") == sid:
                        rrec["source"] = ""
            self.records().pop(r)
            self._mark_dirty()
            self.reload()

    def flush(self) -> None:
        pass      # правки пишутся в kb.data сразу (сохранил – на диск)


class KBWindow(QDialog):
    """Окно «База данных» с вкладками новой схемы."""

    equipment_applied = Signal(str)

    def __init__(self, kb: KnowledgeBase, parent=None, usage=None):
        super().__init__(parent)
        self.kb = kb
        # Задачи 9/10/0: счетчик использования записи деревьями проекта
        # ((section, id) → N) – для предупреждения при удалении
        self.usage = usage
        self.setWindowTitle("База данных")
        self.resize(1020, 640)
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.templates_tab = TemplatesTab(kb)
        # Задача 10 (сессия 15): шаблоны редактируемы – счетчик
        # использования для предупреждения при удалении, как у библиотек
        self.templates_tab.usage = usage
        self.templates_tab.equipment_applied.connect(
            self.equipment_applied.emit)
        self.tabs.addTab(self.templates_tab, "Шаблоны оборудования")
        # Задача 10: редактируемая библиотека ГС
        self.gs_tab = GSLibraryTab(kb)
        self.gs_tab.usage = usage
        self.tabs.addTab(self.gs_tab, "Горючие среды (ГС)")
        # Задача 9: редактируемая библиотека ИЗ
        self.iz_tab = IZLibraryTab(kb)
        self.iz_tab.usage = usage
        self.tabs.addTab(self.iz_tab, "Источники зажигания (ИЗ)")
        self.ft_tab = FireModesTab(kb)
        self.tabs.addTab(self.ft_tab,
                            "Таблица типовых режимов пожара")
        self.tabs.addTab(MethodTablesTab(kb), "Таблицы типовых частот")
        self.mod_tab = MeasuresLibraryTab(kb)
        self.mod_tab.usage = usage
        self.tabs.addTab(self.mod_tab, "Защитные средства")
        # Задача 9 (сессия 18): реестр источников (на него ссылаются
        # записи ГС/ИЗ/мер; печатается в разделе «Нормативные ссылки
        # и справочные данные» отчета)
        self.sources_tab = SourcesTab(kb)
        self.tabs.addTab(self.sources_tab, "Источники")
        root.addWidget(self.tabs, 1)

        # Задача 1a: нижняя панель – справа «Сохранить» (основная) и
        # «Закрыть». Задачи 9/10/0 (сессия 13): СЛЕВА – «Добавить запись»
        # и «Удалить запись» текущей библиотеки (видны только на
        # редактируемых вкладках).
        bottom = QHBoxLayout()
        self.btn_add_rec = QPushButton("Добавить запись")
        self.btn_add_rec.clicked.connect(self._add_record_current)
        bottom.addWidget(self.btn_add_rec)
        self.btn_del_rec = QPushButton("Удалить запись")
        self.btn_del_rec.clicked.connect(self._delete_record_current)
        bottom.addWidget(self.btn_del_rec)
        bottom.addStretch(1)
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self._save_all)
        bottom.addWidget(self.btn_save)
        # Задача 13 (сессия 18): круглая кнопка «?» слева от «Закрыть» –
        # окно справки (мини-нотация формул, реальные примеры)
        self.btn_help = QPushButton()
        self.btn_help.setIcon(glyph_icon(GLYPH_HELP))
        self.btn_help.setToolTip("Справка по работе с базой данных")
        self.btn_help.setFixedSize(30, 30)
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help.setStyleSheet(
            f"QPushButton {{ border: 1px solid {BORDER}; border-radius:"
            f" 15px; background: #FFFFFF; }}"
            f" QPushButton:hover {{ border-color: #2563EB; }}")
        self.btn_help.clicked.connect(self._open_help)
        bottom.addWidget(self.btn_help)
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self._close_clicked)
        bottom.addWidget(self.btn_close)
        root.addLayout(bottom)
        self.tabs.currentChanged.connect(self._sync_record_buttons)
        self._sync_record_buttons()

    # ---------- библиотечные записи (Задачи 9/10/0) ----------
    def _library_tab(self) -> _LibraryTab | None:
        w = self.tabs.currentWidget()
        if isinstance(w, _LibraryTab):
            return w
        # Задача 0: библиотека мер – отдельный класс
        return w if hasattr(w, "add_record") \
            and hasattr(w, "delete_current_record") \
            else None

    def _sync_record_buttons(self) -> None:
        lib = self._library_tab()
        self.btn_add_rec.setVisible(lib is not None)
        self.btn_del_rec.setVisible(lib is not None)

    def _add_record_current(self) -> None:
        lib = self._library_tab()
        if lib is not None:
            lib.add_record()

    def _delete_record_current(self) -> None:
        lib = self._library_tab()
        if lib is not None:
            lib.delete_current_record()

    # ---------- жизненный цикл ----------
    @property
    def _dirty_count(self) -> int:
        """Число вкладок с несохранёнными правками (Задачи 9/10/0:
        редактируемые библиотеки входят в подсчёт наравне с прочими)."""
        return sum(1 for i in range(self.tabs.count())
                   if getattr(self.tabs.widget(i), "_dirty", False))

    def _close_clicked(self) -> None:
        self.close()

    # ---------- справка (Задача 13, сессия 18) ----------
    def _open_help(self) -> None:
        """Круглая «?»: НЕмодальное окно справки (один экземпляр)."""
        if getattr(self, "_help_win", None) is None:
            self._help_win = KBHelpWindow(self)
        self._help_win.show()
        self._help_win.raise_()

    def _reload_all(self) -> None:
        """Перечитать базу с диска и пересобрать все вкладки. Кнопки
        «Перечитать» больше нет (Задача 1a) – метод внутренний:
        вызывается после сохранения."""
        self.kb.reload()
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if hasattr(t, "reload"):
                t.reload()
        self.templates_tab.rebuild_cards()

    def _save_all(self) -> None:
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if hasattr(t, "flush"):
                t.flush()
        self.kb.save()
        self._reload_all()

    def _ask_close_guard(self) -> str:
        """Диалог при закрытии с несохранёнными правками (шов для тестов)."""
        box = QMessageBox(self)
        box.setWindowTitle("База данных")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Несохранённых правок: {self._dirty_count}. "
                    "Сохранить их перед закрытием?")
        b_save = box.addButton("Сохранить", QMessageBox.ButtonRole.AcceptRole)
        b_discard = box.addButton("Не сохранять",
                                  QMessageBox.ButtonRole.DestructiveRole)
        b_cancel = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(b_cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is b_save:
            return "save"
        if clicked is b_discard:
            return "discard"
        return "cancel"

    def hideEvent(self, e) -> None:
        # Задача 1 (сессия 18): размер/положение запоминаются при скрытии
        # ЛЮБЫМ путём – не только closeEvent (например, скрытие дочерним
        # окном при закрытии главного окна без close диалога)
        # Сессия 20 (п.3): запись через app_settings – явный INI + sync()
        from . import app_settings as _as
        _as.write_value("ui/kb_geometry", self.saveGeometry())
        super().hideEvent(e)

    def closeEvent(self, e: QCloseEvent) -> None:
        if self._dirty_count > 0:
            choice = self._ask_close_guard()
            if choice == "cancel":
                e.ignore()
                return
            if choice == "save":
                self._save_all()
        # Задача 11 (сессия 13): запомнить размер/положение окна БД –
        # восстановление при следующем создании (ui/kb_geometry)
        # Сессия 20 (п.3): запись через app_settings – явный INI + sync()
        from . import app_settings as _as
        _as.write_value("ui/kb_geometry", self.saveGeometry())
        e.accept()
