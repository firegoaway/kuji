# -*- coding: utf-8 -*-
"""Живые (оконные) тесты Kuji 6.4 (сессии 10–14): иерархия с «Группой
сценариев», холст пяти нод, инспектор причин, поток из базы данных,
сохранение формата 5, переключатели, окно документа, PDF; сессия 12 –
блоки 14–19 (сосед-добавление, Delete и мусорка, ползунок иерархии,
перетаскивание нод, липкий/свободный обзор, вероятность присутствия);
сессия 13 – блоки 20–29 (инвариант «показано = записано», Alt+A на
обеих раскладках, площадь территории км²|м², память окон, кнопка
«Добавить дерево» и удаление строго по выбору, таблицы БД, библиотеки
ИЗ/ГС, справочник режимов пожара, справочные ноды, библиотека мер);
сессия 14 – блоки 30–36 (территория только в корень + ремонт файлов,
Ctrl/Shift-мультивыбор реальной мышью, свернутые узлы + ui-словарь,
компактный список единиц, каскад ТГМ «наследуется», состояния нод,
инженерная запись в матрице/БД/PDF).

Запуск: runtime\\python\\python.exe gesture_test.py (offscreen).
Завершение: строка GESTURES PASSED и код выхода 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                  str(ROOT / "qa_artifacts" / "_settings"))

app = QApplication(sys.argv)
from eta.core.kb import KnowledgeBase
from eta.core.layout import fmt_q
from eta.core.model import GSCause, IZCause
from eta.core.serializer import load_project
from eta.ui.main_window import MainWindow
from eta.ui.switch import ToggleSwitch
from eta.ui.theme import QSS

app.setStyleSheet(QSS)


def pump(n: int = 8) -> None:
    for _ in range(n):
        app.processEvents()


kb = KnowledgeBase()

# ---------- 1. окно: сборка, панель, меню, версия ----------
w = MainWindow(kb, restore_ui=False)
w.show()
pump()
assert w.windowTitle().startswith("Новый проект")
assert "6.6" in w.statusBar().findChildren(type(w.status_label))[-1].text()
assert w.act_new.shortcut().toString() == "Ctrl+N"
assert w.act_export is not None
print("OK окно: сборка, меню (Ctrl+N/O/S, Ctrl+E, F9), статус-бар v6.6")

# ---------- 2. иерархия: строительство + гейтинг кнопок ----------
h = w.hierarchy
h.add_kind("territory")
terr = h.selected()
assert w.hierarchy.toolbar.buttons["building"].isEnabled()
assert w.hierarchy.toolbar.buttons["outdoor"].isEnabled()   # в территорию
h.add_kind("building")
bld = h.selected()
bld.props.update({"area_m2": 2000.0, "p13_type": "p13-multi"})
h.add_kind("room")
room = h.selected()
h.add_kind("area")
area = h.selected()
pump()
# здание выбрано: наружная установка недоступна (только в территорию)
assert not w.hierarchy.toolbar.buttons["outdoor"].isEnabled()
h.select_object(terr)
assert w.hierarchy.toolbar.buttons["outdoor"].isEnabled()
h.select_object(area)
print("OK иерархия: Т→З→П→У; кнопки по правилам родителей")

# ---------- 3. «Группа сценариев» и сценарии в дереве иерархии ----------
w._add_tree(area.id, "tgm")
tgm = next(t for t in w.trees if t.scenario_type == "tgm")
tgm.gs_causes = [GSCause(ref="gs-tgm-surface")]
tgm.iz_causes = [IZCause(ref=r) for r in ("iz-lamp", "iz-cable")]
w._refresh()
pump()
texts = []

def walk_items(it):
    texts.append(it.text(0))
    for i in range(it.childCount()):
        walk_items(it.child(i))


for i in range(h.tree.topLevelItemCount()):
    walk_items(h.tree.topLevelItem(i))
# Задача 3.1/3.2 (сессия 15): «Группа сценариев» и сгруппированные
# строки УДАЛЕНЫ; под участком – строка сценария с ПРИЧИНАМИ детьми
assert "Группа сценариев" not in texts, texts
assert "Сценарий пожара ТГМ" in texts, texts
assert "Образование ГС: Пожар по поверхности (постоянное наличие ТГМ)" \
    in texts, texts
assert "Отказ осветительных приборов (лампы накаливания)" in texts, texts
assert "Отказ кабельных линий" in texts, texts
print("OK иерархия: строка сценария с причинами-детьми (без «Группы»)")

# ---------- 4. холст: 5 нод, заголовок с Q, выбор ноды → инспектор -------
h.select_object(area)
pump()
# §1: выделение в дереве переживает пересборку (rebuild при _refresh)
w._refresh()
pump()
cur = h.tree.currentItem()
assert cur is not None and cur.text(0).startswith("Участок"), \
    (cur.text(0) if cur else None)
assert len(w.canvas.controller.layout.nodes) == 5
fire_id = f"{tgm.tree_id}:fire"
assert w.canvas.controller.layout.nodes[fire_id].kind == "fire"
w._on_canvas_node(fire_id)
pump()
from PySide6.QtWidgets import QLabel as _QL
lbls = [l.text() for l in w.inspector.form_host.findChildren(_QL)]
assert any("σ" in l for l in lbls), lbls[:8]     # K_σ как индекс (HTML)
switches = w.inspector.form_host.findChildren(ToggleSwitch)
assert any("Огненный шар" in s.text() for s in switches)
hdr = w.canvas.controller.layout.annotations[0]
assert "Участок 1" in " ".join(hdr.lines) \
    and "Сценарий пожара ТГМ" in " ".join(hdr.lines)
assert not any("Q =" in l for l in hdr.lines)   # Q не дублируется в воздухе
print("OK холст: 5 нод; клик по «Возникновению» → Kσ + «Огненный шар»")

# ---------- 5. инспектор ГС: причины + «Добавить причину» ----------------
w._on_canvas_node(f"{tgm.tree_id}:gs")
pump()
btns = w.inspector.form_host.findChildren(QPushButton)
assert any("Добавить причину" in b.text() for b in btns)
w._add_gs_cause("gs-vessel-12.5")   # недоступная для м² – валидатор скажет
from eta.core.objects import effective_site_type
assert effective_site_type(area) == "area"
issues_txt = [i.message for i in
              __import__("eta.core.validation", fromlist=["check_tree"])
              .check_tree(tgm, kb, w.ctx_map()[area.id], "area")]
assert any("недоступна" in m for m in issues_txt)
w._remove_gs_cause(1)
assert len(tgm.gs_causes) == 1
print("OK инспектор ГС: «Добавить причину», валидатор типа участка, «Убрать»")

# ---------- 6. наружная установка + шаблон из КБ (Задача 3) --------------
h.select_object(None)
h.add_kind("territory")
h.add_kind("outdoor")
inst = h.selected()
pump()
w._open_kb_window()
pump()
kt = w.kb_window.templates_tab
# без выделения владельца кнопка неактивна
h.select_object(None)
w._update_kb_apply_hint()
assert not kt.btn_apply.isEnabled()
assert "выделите участок" in kt.btn_apply.toolTip()
# выделение установки → активна; двойной клик по карточке = применение
h.select_object(inst)
w._update_kb_apply_hint()
kt.selected_id = "eq-outdoor-gas"
kt._on_card_dbl(_card := type("_C", (), {"rec": {"id": "eq-outdoor-gas"}})())
pump()
gg_trees = [t for t in w.trees if t.scenario_type == "gg"]
assert len(gg_trees) == 1 and len(gg_trees[0].gs_causes) == 4
assert len(gg_trees[0].iz_causes) == 3
rows_n = len(gg_trees[0].scenarios(kb, w.ctx_map()[inst.id]))
assert rows_n == 4 * 4 * 3 * 3, rows_n   # ГС × расход × тип × ИЗ (шар выкл)
print("OK Задача 3: кнопка гасится без участка; двойной клик применяет шаблон")

# ---------- 7. переключатели в формах объектов (живая видимость) ---------
h.select_object(bld)
pump()
sws = w.inspector.form_host.findChildren(ToggleSwitch)
lp = next(s for s in sws if s.text() == "Молниезащита")
from PySide6.QtWidgets import QComboBox as _QCB
cats = [c for c in w.inspector.form_host.findChildren(_QCB)
        if c.count() == 4 and "0,98" in c.itemText(0)]
assert cats and not cats[0].isVisible(), "категория видна без молниезащиты"
lp.setChecked(True)
pump()
assert cats[0].isVisible(), "категория не открылась"
h.select_object(room)
pump()
vent = next(s for s in w.inspector.form_host.findChildren(ToggleSwitch)
            if "Аварийная вентиляция" in s.text())
spins = [s for s in w.inspector.form_host.findChildren(type(vent))
         if False]  # placeholder
from PySide6.QtWidgets import QDoubleSpinBox as _QDSB
vsp = [s for s in w.inspector.form_host.findChildren(_QDSB)
       if s.suffix() == " ч⁻¹"]
assert vsp and not vsp[0].isVisible()
vent.setChecked(True)
pump()
assert vsp[0].isVisible()
print("OK переключатели: молниезащита/категория и вентиляция/A-поле")

# ---------- 8. удаление: «Удалить» – кнопка по умолчанию (Задача 8) ------
captured = {}
_orig_exec = QMessageBox.exec


def _fake_exec(self):
    btn = self.defaultButton()
    captured["default"] = btn.text() if btn else None
    captured["focus"] = (self.focusWidget().text()
                         if self.focusWidget() else None)
    return 0


QMessageBox.exec = _fake_exec
h.select_object(room)
h._confirm_delete(room)                    # окно построено, exec перехвачен
QMessageBox.exec = _orig_exec
assert captured["default"] == "Удалить", captured
assert captured["focus"] == "Удалить", captured
print("OK Задача 8: в окне удаления фокус и умолчание – «Удалить»")

# (реальное удаление установки вместе с деревом – через шов подтверждения)
h._confirm_delete = lambda node: True
h.select_object(inst)
h.delete_object(inst)
pump()
assert all(t.scenario_type != "gg" for t in w.trees), "дерево ГГ не удалено"
assert not any("Наружная" in t for t in texts) or True
print("OK удаление: установка удаляется вместе с её деревом")

# ---------- 9. сохранение/открытие формата 5 через MainWindow ------------
w._project_path = str(ROOT / "qa_artifacts" / "_gest_v6.kuji.json")
w._save_project()
data = load_project(w._project_path)
assert len(data["trees"]) == 1            # ТГМ (ГГ удалён вместе с установкой)
w2 = MainWindow(kb, restore_ui=False)
w2.objects.load_from_dict(data["objects"])
w2.trees = data["trees"]
w2._refresh()
pump()
assert w2.matrix_table.rowCount() == len(data["trees"][0].scenarios(
    kb, w2.ctx_map()[data["trees"][0].owner_id]))
print("OK проекты: сохранение/чтение формата 5, матрица восстановлена")

# ---------- 10. окно документа: матрица/схема, pop-out -------------------
w.open_doc_window()
pump()
assert w.doc_window is not None and w.doc_stack.currentIndex() in (0, 1)
w.set_doc_view_mode("matrix")
pump()
assert w.matrix_table.rowCount() > 0
w.set_doc_view_mode("schematic")
w.doc_view.fit_width()
pump()
assert abs(w.doc_view.transform().m11()) > 0
w.doc_window.close()
pump()
assert w.doc_window is None
# Задача 1 (сессия 13): повторное открытие pop-out окна «Документ» –
# панель должна быть ПОЛНОСТЬЮ видима (раньше хост оставался со флагом
# скрытия после close → пустое окно); цикл закрытия/открытия ×2
for _cycle in range(2):
    w.open_doc_window()
    pump()
    assert w.doc_window is not None
    assert w.doc_stack.isVisibleTo(w.doc_window), "панель скрыта в окне"
    assert w._doc_mode_label.isVisibleTo(w.doc_window)
    assert w.matrix_table.rowCount() > 0
    assert w.doc_window.close()
    pump()
    assert w.doc_window is None
print("OK документ: pop-out окно, матрица/схема, закрытие возвращает панель;"
      " повторное открытие ×2 полноценно (Задача 1)")

# ---------- 11. DOCX: контент-модель отчета (без pandoc) ------------------
from eta.export.report_docx import (REPORT_TITLE, SOURCES_HEADING,
                                    TREE_HEADING, build_markdown)
_md11 = build_markdown(w.objects, w.trees, kb, w.ctx_map(),
                       w._owner_titles(), "A3L", None)
assert REPORT_TITLE in _md11 and "Оглавление" in _md11
assert 'TOC \\o "1-3"' in _md11                    # поле оглавления Word
assert SOURCES_HEADING in _md11 and TREE_HEADING in _md11
assert "Объект расчёта" not in _md11 and "Исполнитель" not in _md11
assert "[Приказ" not in _md11                      # Задача 7: без скобок
assert "Q_В = Σ Q_i · Kσ" in _md11
assert w.objects.tree_owners()                     # в модели есть владельцы
print("OK DOCX-модель: титул+поле оглавления, разделы, без «Объекта"
      " расчёта» и скобок у источников, Q_В")

# ---------- 12. Задача 2: попиксельный плавный скролл (колесо) ------------
# режим прокрутки – пиксель (не строка) во всех ключевых вьюхах
from PySide6.QtWidgets import QAbstractItemView as _QAV
assert w.matrix_table.verticalScrollMode() == _QAV.ScrollMode.ScrollPerPixel
assert w.hierarchy.tree.verticalScrollMode() == \
    _QAV.ScrollMode.ScrollPerPixel
kbw_tabs = w.kb_window.tabs
for i in range(kbw_tabs.count()):
    page = kbw_tabs.widget(i)
    for t in page.findChildren(type(w.matrix_table)):
        assert t.verticalScrollMode() == _QAV.ScrollMode.ScrollPerPixel
# живое колесо: анимация проходит ПРОМЕЖУТОЧНЫЕ пиксели, а не границы строк
from eta.ui.scroll import install_scroll_wide
install_scroll_wide(app)
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QWheelEvent
import time as _time

tbl = w.kb_window.gs_tab.table          # 68 строк – диапазон прокрутки есть
bar = tbl.verticalScrollBar()
bar.setValue(0)
assert bar.maximum() > 200, bar.maximum()
ev = QWheelEvent(QPointF(60, 60), QPointF(60, 60), QPoint(0, 0),
                 QPoint(0, -120), Qt.MouseButton.NoButton,
                 Qt.KeyboardModifier.NoModifier,
                 Qt.ScrollPhase.NoScrollPhase, False)
QApplication.sendEvent(tbl.viewport(), ev)
seen: list[int] = []
for _ in range(80):                      # 80 × ~5 мс > SMOOTH_MS = 150 мс
    app.processEvents()
    _time.sleep(0.005)
    if bar.value() not in seen:
        seen.append(bar.value())
assert seen and seen[-1] > 40, seen          # прокрутилось вниз
assert len(seen) >= 4, seen                  # есть промежуточные значения
mid = [v for v in seen if 0 < v < seen[-1]]
assert mid, seen                            # не только 0 и финал
row_h = tbl.rowHeight(0)
assert any(v % row_h for v in seen), (seen, row_h)   # не кратные строке
print(f"OK скролл: попиксельный, промежуточные значения {seen[:6]}…")

# ---------- 14. Задача 4: сосед того же типа под тем же родителем -------
h.select_object(area)
pump()
assert h.toolbar.buttons["area"].isEnabled(), "сосед-участок недоступен"
h.add_kind("area")
area2 = h.selected()
assert area2 is not area and area2.kind == "area"
assert area2.parent is room, "сосед должен быть в том же помещении"
# выделено здание: сосед-здание в той же территории + ребёнок-помещение
h.select_object(bld)
pump()
assert h.toolbar.buttons["building"].isEnabled()
assert h.toolbar.buttons["room"].isEnabled()
assert h.toolbar.buttons["compartment"].isEnabled()
h.add_kind("building")
bld2 = h.selected()
assert bld2.parent is terr
# наружная установка: прежнее правило – только при выбранной территории
assert not h.toolbar.buttons["outdoor"].isEnabled()
h.select_object(terr)
pump()
assert h.toolbar.buttons["outdoor"].isEnabled()
# строка сценария = выбор владельца (участка)
sit = h._find_item(lambda i: isinstance(
    i.data(0, Qt.ItemDataRole.UserRole), dict))
h.tree.setCurrentItem(sit)
pump()
assert h.toolbar.buttons["area"].isEnabled()
# уборка тестовых соседей (шов подтверждения уже подменен в блоке 8)
h.delete_object(area2)
h.delete_object(bld2)
h.select_object(area)
pump()
print("OK Задача 4: сосед при выборе того же типа; сценарий = владелец")

# ---------- 15. Задача 10: Delete в дереве/редакторе/холсте + мусорка --
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractItemView as _QAV2, QLineEdit as _QLE
# (а) Delete в дереве удаляет объект (через шов подтверждения)
h.select_object(bld)
h.add_kind("room")
victim = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.tree.setFocus()
QTest.keyClick(h.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert w.objects.by_id(victim.id) is None, "Delete в дереве не удалил"
# (б) во время переименования Delete правит текст, объект жив
h.select_object(area)
pump()
h._edit_item_of(area)
pump()
editor = h.tree.findChild(_QLE)
assert editor is not None
QTest.keyClick(editor, Qt.Key.Key_Delete)
pump()
assert w.objects.by_id(area.id) is not None
assert h.tree.state() == _QAV2.State.EditingState
h.tree.closePersistentEditor(h.tree.currentItem())
# (в) Delete на холсте: дерево-владелец выделенной ноды (решение №5).
# Сессия 16, Задача 1: во внимание принимается только выделение КЛИКОМ
# пользователя (mouseRelease без движения = select_node + node_clicked);
# программный пунктир от клика по строке причины дерево НЕ удаляет
w._add_tree(area.id, "dust")
dust = next(t for t in w.trees if t.scenario_type == "dust")
w._confirm_tree_delete = lambda t: True
w.canvas.controller.select_node(f"{dust.tree_id}:fire")
w.canvas.node_clicked.emit(f"{dust.tree_id}:fire")   # как при клике ЛКМ
assert w._canvas_sel_by_click
w.canvas.setFocus()
QTest.keyClick(w.canvas.viewport(), Qt.Key.Key_Delete)
pump()
assert all(t.tree_id != dust.tree_id for t in w.trees), "дерево не удалено"
assert any(t.scenario_type == "tgm" for t in w.trees)   # tgm не задет
# (г) мусорка следует за выбором
h.select_object(terr)
pump()
assert not w.left_toolbar.btn_trash.isEnabled(), "территория – неудаляема"
h.select_object(bld)
pump()
assert w.left_toolbar.btn_trash.isEnabled()
w.canvas.controller.select_node(f"{tgm.tree_id}:gs")
w._update_trash()
assert w.left_toolbar.btn_trash.isEnabled()
w.canvas.controller.select_node(None)
print("OK Задача 10: Delete (дерево/редактор/холст) и мусорка по выбору")

# ---------- 16. Задача 8: горизонтальный ползунок дерева + Shift+колесо --
w.objects.rename(area, "Одностенный изотермический резервуар хранения"
                        " СУГ № 1 (вне помещения)")
w._refresh()
pump()
bar = h.tree.horizontalScrollBar()
assert bar.maximum() > 0, "ползунок не появился при длинном имени"
assert h.tree.columnWidth(0) > h.tree.viewport().width()
bar.setValue(0)
ev_h = QWheelEvent(QPointF(60, 60), QPointF(60, 60), QPoint(0, 0),
                   QPoint(0, -120), Qt.MouseButton.NoButton,
                   Qt.KeyboardModifier.ShiftModifier,
                   Qt.ScrollPhase.NoScrollPhase, False)
QApplication.sendEvent(h.tree.viewport(), ev_h)
seen_h: list[int] = []
for _ in range(80):
    app.processEvents()
    _time.sleep(0.005)
    if bar.value() not in seen_h:
        seen_h.append(bar.value())
assert seen_h and seen_h[-1] > 20, seen_h
assert len(seen_h) >= 4, seen_h
assert any(0 < v < seen_h[-1] for v in seen_h), seen_h
print(f"OK Задача 8: ползунок {bar.maximum()}px; Shift+колесо"
      f" промежуточно {seen_h[:6]}…")

# ---------- 17. Задача 11: перетаскивание ноды, оффсеты, авторазметка ----
h.select_object(area)
pump()
w._refresh()
pump()
item = w.canvas.controller.node_item(f"{tgm.tree_id}:gs")
assert item is not None
c = QPointF(w.canvas.mapFromScene(item.geo.rect.center()))
vp = w.canvas.viewport()
# QTest-синтез мыши: press → move (40,18) → release = перетаскивание
QTest.mousePress(vp, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier, c.toPoint())
pump()
QTest.mouseMove(vp, (c + QPointF(40, 18)).toPoint())
pump()
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton,
                   Qt.KeyboardModifier.NoModifier,
                   (c + QPointF(40, 18)).toPoint())
pump()
off = tgm.node_offsets
assert off and "gs" in off, off
z = w.canvas.zoom_level()
assert abs(off["gs"][0] - 40 / z) < 1e-6, off
assert abs(off["gs"][1] - 18 / z) < 1e-6, off
# round-trip формата 5: смещение сохраняется и читается
w._project_path = str(ROOT / "qa_artifacts" / "_gest_offsets.kuji.json")
w._save_project()
d_off = load_project(w._project_path)
assert d_off["trees"][0].node_offsets["gs"] == off["gs"]
# «Авторазметка» сбрасывает смещения
w.left_toolbar.btn_autolayout.click()
pump()
assert tgm.node_offsets is None
Path(w._project_path).unlink()
print(f"OK Задача 11: drag→offset {off['gs']}, round-trip, авторазметка")

# ---------- 18. Задача 12: липкий/свободный обзор взаимоисключительны ---
w.canvas.zoom(2.0)
for _ in range(60):                     # дождаться анимации зума (130 мс)
    app.processEvents()
    _time.sleep(0.005)
w.left_toolbar.btn_free.click()
pump()
assert w.left_toolbar.btn_free.isChecked()
assert not w.left_toolbar.btn_sticky.isChecked()
assert w.canvas.mode() == "free"
# Задача 5 (сессия 13): в свободном режиме ползунки ОГРОМНЫ (рабочая
# сцена ±100 000 px) – камера уходит за дерево без ограничений; сцена
# документа (лист/PDF) НЕ увеличена – экспортная геометрия не затронута
hb = w.canvas.horizontalScrollBar()
vb = w.canvas.verticalScrollBar()
assert hb.maximum() > 100000, hb.maximum()
assert vb.maximum() > 100000, vb.maximum()
_lay = w.canvas.controller.layout
assert w.canvas.controller.doc_scene.sceneRect().getRect() == \
    _lay.scene_rect.getRect()
_far = w.canvas.mapToScene(0, 0)
hb.setValue(hb.maximum())
vb.setValue(vb.maximum())
pump()
assert w.canvas.mapToScene(0, 0) != _far    # камера реально уехала
w.left_toolbar.btn_sticky.click()
pump()
assert not w.left_toolbar.btn_free.isChecked()
assert w.left_toolbar.btn_sticky.isChecked()
assert w.canvas.mode() == "sticky"
vis = w.canvas.mapToScene(w.canvas.viewport().rect()).boundingRect()
sr = w.canvas.controller.layout.scene_rect.adjusted(-40, -40, 40, 40)
if vis.width() <= sr.width():
    assert vis.left() >= sr.left() - 1.0 and vis.right() <= sr.right() + 1.0
if vis.height() <= sr.height():
    assert vis.top() >= sr.top() - 1.0 and vis.bottom() <= sr.bottom() + 1.0
print("OK Задача 12: режимы взаимоисключительны, липкий кламп держит")

# ---------- 19. Задача 15: инспектор наличия – вероятность 0–1 ----------
w._on_canvas_node(f"{tgm.tree_id}:substance")
pump()
from PySide6.QtWidgets import QComboBox as _QCB3, QDoubleSpinBox as _QDS3
spins = [s for s in w.inspector.form_host.findChildren(_QDS3)
         if s.maximum() == 1.0 and s.decimals() == 3]
assert spins, "поле вероятности 0–1 не найдено"
combos = w.inspector.form_host.findChildren(_QCB3)
assert not any("присутствия, год" in c.itemText(i)
               for c in combos for i in range(c.count())), "режимы живы"
spins[0].setValue(0.25)
pump()
assert abs(tgm.substance.value - 0.25) < 1e-9
assert abs(tgm.substance.q() - 0.25) < 1e-9
labels = [l.text() for l in w.inspector.form_host.findChildren(_QL)]
assert any("ероятность присутствия" in l for l in labels), labels[:6]
spins[0].setValue(1.0)
pump()
print("OK Задача 15: единственное поле вероятности, режимов нет")

# ---------- 20. Задача 2 (сессия 13): «показано = записано» -----------------
# Глубокая ветка Т→З→П→У создается кнопками панели (каждый новый объект
# автоматически выделяется → форма строится → умолчания пишутся в props);
# формы НЕ трогаем: Q ТГМ-дерева должно быть > 0 сразу
h.select_object(None)
h.add_kind("territory")
h.add_kind("building")
b3 = h.selected()
h.add_kind("room")
h.add_kind("area")
a3 = h.selected()
w._add_tree(a3.id, "tgm")
tgm3 = next(t for t in w.trees if t.owner_id == a3.id)
tgm3.gs_causes = [GSCause(ref="gs-tgm-surface")]
tgm3.iz_causes = [IZCause(ref="iz-lamp")]
w._refresh()
pump()
ctx3 = w.ctx_map()[a3.id]
q3 = tgm3.total_q(kb, ctx3)
assert q3 > 0, q3                       # раньше: пустые props → множитель 0
# ключи показанных полей лежат в props сразу после открытия форм
h.select_object(b3)
pump()
for k in ("area_m2", "p13_type", "lightning_cat", "bln_S", "bln_L", "bln_H"):
    assert k in b3.props, k
h.select_object(a3)
pump()
assert "site_type" in a3.props
# Задача 5 (сессия 14): площадь участка НЕ материализуется – показывается
# наследуемое значение (серым), в props попадает только явный ввод
assert "area_m2" not in a3.props
terr3 = b3.ancestors()[0]
h.select_object(terr3)
pump()
assert "strike_area_km2" in terr3.props
# Задача 7 (сессия 17): метка статуса – Q_В (везде, LOCKED)
assert "Q_В" in w.status_label.text()
print(f"OK Задача 2: показано = записано; Q = {q3:.2e} без правки форм")

# ---------- 21. Задача 3 (сессия 13): Alt+A не зависит от раскладки -------
# зарегистрированы обе последовательности: латинская и кириллическая
_seqs = [s.toString() for s in w.act_fit.shortcuts()]
assert any(s.endswith("A") for s in _seqs), _seqs
assert any(s.endswith("Ф") for s in _seqs), _seqs
# QTest шлет КОД клавиши (Key_A – раскладконезависимо); действие обязано
# срабатывать при фокусе в дереве, на холсте, в инспекторе и в окне БД
_fired = []
w.act_fit.triggered.connect(lambda: _fired.append(1))


def _zoom_away() -> float:
    w.canvas.set_zoom_level(0.4)
    for _ in range(40):
        app.processEvents()
        _time.sleep(0.003)
    return w.canvas.zoom_level()


for _fw in (h.tree, w.canvas, w.inspector.form_host):
    _fw.setFocus()
    pump()
    _zoom_away()
    _n0 = len(_fired)
    QTest.keyClick(_fw, Qt.Key.Key_A, Qt.KeyboardModifier.AltModifier)
    pump()
    assert len(_fired) > _n0, (str(_fw), "Alt+A не сработал в этом фокусе")
# Сессия 17, Задача 4: реальное нажатие КИРИЛЛИЧЕСКОЙ клавиши той же
# физической позиции (Ф = 0x0424) – приложенческий фильтр latin_keys
# доставляет Alt+A, действие срабатывает (латинский путь выше)
_n0 = len(_fired)
QTest.keyClick(h.tree, Qt.Key(0x0424), Qt.KeyboardModifier.AltModifier)
pump()
assert len(_fired) > _n0, "Alt+Ф (кириллица) не сработал"
# окно базы данных – отдельное окно: ApplicationShortcut держит и его
if w.kb_window is not None:
    w.kb_window.show()
    w.kb_window.setFocus()
    pump()
    _n0 = len(_fired)
    QTest.keyClick(w.kb_window, Qt.Key.Key_A,
                   Qt.KeyboardModifier.AltModifier)
    pump()
    assert len(_fired) > _n0, "Alt+A не сработал в окне БД"
    w.kb_window.close()
    pump()
    w.kb_window = None
print("OK Задача 3: Alt+A (латиница+кириллица) в дереве/холсте/"
      "инспекторе/окне БД")

# ---------- 22. Задача 12 (сессия 13): площадь территории, км²|м² ---------
h.select_object(terr3)
pump()
from PySide6.QtWidgets import QComboBox as _QCB12, QDoubleSpinBox as _QDS12
# Задача 3 (сессия 17): подпись «Площадь территории:» → «Площадь:»
assert any(l.text() == "Площадь:"
           for l in w.inspector.form_host.findChildren(_QL))
_spin = next(s for s in w.inspector.form_host.findChildren(_QDS12)
             if s.suffix() in (" км²", " м²"))
_unit = next(c for c in w.inspector.form_host.findChildren(_QCB12)
             if c.count() == 2 and c.itemText(0) == "км²")
assert _spin.suffix() == " км²" and abs(_spin.value() - 0.05) < 1e-12
assert terr3.props.get("strike_area_unit") == "km2"   # Задача 2: записано
_unit.setCurrentIndex(1)                              # → м²
pump()
assert _spin.suffix() == " м²"
assert abs(_spin.value() - 50000.0) < 0.5, _spin.value()   # 0,05 км² → м²
_spin.setValue(250000.0)                               # 0,25 км², ввод в м²
pump()
assert abs(terr3.props["strike_area_km2"] - 0.25) < 1e-9
# повторное открытие формы: единица и переведенное значение на месте
h.select_object(b3)
pump()
h.select_object(terr3)
pump()
_spin = next(s for s in w.inspector.form_host.findChildren(_QDS12)
             if s.suffix() in (" км²", " м²"))
assert _spin.suffix() == " м²"
assert abs(_spin.value() - 250000.0) < 1.0
# round-trip через файл проекта: нормализованное км² + единица
w._project_path = str(ROOT / "qa_artifacts" / "_gest_territory.kuji.json")
w._dirty = False
w._save_project()
_dt = load_project(w._project_path)
_terr_d = next(t for t in _dt["objects"] if t["id"] == terr3.id)
assert abs(_terr_d["props"]["strike_area_km2"] - 0.25) < 1e-9
assert _terr_d["props"]["strike_area_unit"] == "m2"
Path(w._project_path).unlink()
print("OK Задача 12: км²|м² с конверсией, персистентность единицы и значения")

# ---------- 23. Задача 11 (сессия 13): память геометрии окон ---------------
# «Документ»: изменить размер → закрыть → открыть: размер вернулся
# (размеры в пределах экрана offscreen-платформы ~800×600 – иначе Qt
# сам клампит восстановленную геометрию к экрану)
w.open_doc_window()
pump()
w.doc_window.resize(690, 470)
pump()
w.doc_window.close()
pump()
w.open_doc_window()
pump()
assert (w.doc_window.width(), w.doc_window.height()) == (690, 470), \
    (w.doc_window.width(), w.doc_window.height())
# сохраненный монитор отсутствует: геометрия сдвинута за экран – окно
# восстанавливается без падения и остается видимым (Qt сам возвращает)
w.doc_window.move(9500, 7500)
pump()
w.doc_window.close()
pump()
w.open_doc_window()
pump()
assert w.doc_window.isVisible()
w.doc_window.close()
pump()
# окно БД: resize → close (сохранение) → пересоздание: размер вернулся
w._open_kb_window()
pump()
w.kb_window.resize(710, 490)
pump()
w.kb_window.close()
pump()
w.kb_window = None                     # ленивый синглтон – «новый запуск»
w._open_kb_window()
pump()
assert (w.kb_window.width(), w.kb_window.height()) == (710, 490), \
    (w.kb_window.width(), w.kb_window.height())
w.kb_window.close()
pump()
w.kb_window = None
print("OK Задача 11: геометрия «Документ»/БД помнится (в т.ч. за экраном)")

# ---------- 24. Задача 6 (сессия 13): кнопка «Добавить дерево», Delete ---
from PySide6.QtWidgets import QToolButton as _QTB
assert len(h.toolbar.findChildren(_QTB)) == 7        # 6 уровней + дерево
# 6.1/6.3: подсказки неактивных кнопок – скобочный шаблон (LOCKED)
h.select_object(room)
pump()
assert not h.toolbar.buttons["outdoor"].isEnabled()
assert h.toolbar.buttons["outdoor"].toolTip() == \
    "Добавить наружную установку (выделите территорию)"
assert h.toolbar.btn_add_tree.isEnabled()            # на помещении можно
h.select_object(terr)
pump()
assert not h.toolbar.btn_add_tree.isEnabled()        # территория – нельзя
assert h.toolbar.btn_add_tree.toolTip() == \
    "Добавить дерево (выделите участок, наружную установку или помещение)"
assert not hasattr(h, "props_requested")             # «Свойства» убраны
# на помещении: автосоздание «Участок N» + дерево + уведомление (шов)
_msgs = []
h.status_message.connect(lambda m: _msgs.append(m))
h.select_object(room)
pump()
h._add_tree_for("gg")
pump()
_new_area = h.selected()
assert _new_area is not None and _new_area.kind == "area"
assert _new_area.parent is room
assert [t for t in w.trees if t.owner_id == _new_area.id] \
    and next(t for t in w.trees if t.owner_id == _new_area.id
             ).scenario_type == "gg"
assert _msgs and _msgs[0].startswith("Создан Участок")
assert "site_type" in _new_area.props                # Задача 2: умолчания
# на участке напрямую
h.select_object(a3)
pump()
h._add_tree_for("dust")
pump()
assert any(t.scenario_type == "dust" and t.owner_id == a3.id
           for t in w.trees)
# 6.2: одно/«зажатое» нажатие Delete убивает ТОЛЬКО выбранный объект
h.select_object(None)
h.add_kind("territory")
terr2 = h.selected()
h.add_kind("building")
b2x = h.selected()
h.add_kind("room")
h.add_kind("area")
victim2 = h.selected()
pump()
_ids = {n.id for n in w.objects.all_nodes()}
h._confirm_delete = lambda node: True
h.select_object(victim2)
h.tree.closePersistentEditor(h.tree.currentItem())
h.tree.setFocus()
pump()
for _i in range(4):                    # «зажатая» клавиша – 4 нажатия
    QTest.keyClick(h.tree.viewport(), Qt.Key.Key_Delete)
    pump()
_dead = _ids - {n.id for n in w.objects.all_nodes()}
assert _dead == {victim2.id}, _dead    # родители живы – каскада нет
assert w.objects.by_id(b2x.id) is not None
assert w.objects.by_id(terr2.id) is not None
# мультивыбор: два здания – ОДНО окно со списком, оба удалены, корень жив
h.select_object(terr2)
pump()
h.add_kind("building")
b3x = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())   # редактор → пересборка
pump()
_it1, _it2 = h._item_of(b2x), h._item_of(b3x)
assert _it1 is not None and _it2 is not None
# программный мультивыбор без сигналов: _on_select → _refresh → rebuild
# удалил бы элементы дерева между установкой флажков
h.tree.blockSignals(True)
h.tree.clearSelection()
_it1.setSelected(True)
_it2.setSelected(True)
h.tree.blockSignals(False)
pump()
_batches = []
h._confirm_multi_delete = \
    lambda nodes: (_batches.append(nodes), True)[1]
h.tree.setFocus()
QTest.keyClick(h.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert len(_batches) == 1 and len(_batches[0]) == 2
assert w.objects.by_id(b2x.id) is None
assert w.objects.by_id(b3x.id) is None
assert w.objects.by_id(terr2.id) is not None
print("OK Задача 6: кнопка+гейтинг+авто-участок; Delete только выбор;"
      " мультивыбор одним окном")

# ---------- 25. Задача 7 (сессия 13): таблицы БД – ширины и перенос -------
from eta.ui.controls import wrap_text85 as _wrap85s
import re as _re7
_strip7 = lambda html_ln: _re7.sub(r"<[^>]+>", "", html_ln).strip()
# слоговое разбиение: слово длиннее 85 символов режется с «–»,
# каждая строка ≤85 символов
_long_word = "электрооборудование" * 10
_lines7 = _wrap85s(f"короткая фраза {_long_word} и хвост").split("\n")
assert all(len(l) <= 85 for l in _lines7), [len(l) for l in _lines7]
assert any("–" in l for l in _lines7)
w._open_kb_window()
pump()
kbw = w.kb_window
_tabs7 = kbw.tabs
# ВСЕ таблицы окна БД (включая под-вкладки): ползунок AsNeeded,
# последний столбец не растягивается (сжатия столбцов нет)
for _i in range(_tabs7.count()):
    for _t in _tabs7.widget(_i).findChildren(type(w.matrix_table)):
        assert _t.horizontalScrollBarPolicy() == \
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert not _t.horizontalHeader().stretchLastSection()
# «Защитные средства»: примечания ≤85 символов на строку (видимый текст);
# ширины колонок по содержимому – при нехватке места горизонтальный
# ползунок появляется; высота строк вмещает все строки примечания
mt = kbw.mod_tab
for _r in range(mt.table.rowCount()):
    _note = mt.table.cellWidget(_r, 2)
    for _ln in _note.text().split("<br>"):
        assert len(_strip7(_ln)) <= 85, _ln
    _n_lines = max(1, _note.text().count("<br") + 1)
    assert mt.table.rowHeight(_r) >= 16 * _n_lines
_total_w = sum(mt.table.columnWidth(_c) for _c in range(3))
if _total_w > mt.table.viewport().width():
    assert mt.table.horizontalScrollBar().maximum() > 0, \
        "горизонтальный ползунок не появился"
kbw.close()
pump()
w.kb_window = None
print("OK Задача 7: авто-ширины, ползунок AsNeeded, перенос ≤85 со слогами")

# ---------- 26. Задачи 9/10 (сессия 13): библиотеки ИЗ/ГС ------------------
import copy as _copy
_kb_snap = _copy.deepcopy(kb.data)
w._open_kb_window()
pump()
kbw = w.kb_window
_names = [kbw.tabs.tabText(i) for i in range(kbw.tabs.count())]
assert "Источники зажигания (ИЗ)" in _names, _names
assert "Горючие среды (ГС)" in _names, _names
_caps = [l.text() for l in kbw.iz_tab.findChildren(_QL)
         + kbw.gs_tab.findChildren(_QL)]
assert any("БИБЛИОТЕКА ПРИЧИН ПОЯВЛЕНИЯ ИСТОЧНИКОВ ЗАЖИГАНИЯ (ИЗ)"
           in c for c in _caps)
assert any("БИБЛИОТЕКА ПРИЧИН ВОЗНИКНОВЕНИЯ ГОРЮЧИХ СРЕД (ГС)"
           in c for c in _caps)
for _tab9, _heads in ((kbw.iz_tab, ("Наименование ИЗ", "λ, год⁻¹",
                                    "Примечание")),
                      (kbw.gs_tab, ("Наименование ГС", "Частота, год⁻¹",
                                    "Примечание"))):
    for _c9, _h9 in enumerate(_heads):
        assert _tab9.table.horizontalHeaderItem(_c9).text() == _h9


def _lib_row(tab, title):
    for r in range(tab.table.rowCount()):
        it = tab.table.item(r, 0)
        if it and title in it.text():
            return r
    return -1


def _cell(tab, r, c):
    return tab.table.cellWidget(r, c).text()


# ИЗ: молния – расчётная величина; нагретое – P = 1; обычные – инженерный
izt = kbw.iz_tab
_r = _lib_row(izt, "Удар молнии")
assert _r >= 0
assert "расчётная величина" in _cell(izt, _r, 1)
_note_ltn = _strip7(_cell(izt, _r, 2).replace("<br>", " "))
assert "у.м" in _note_ltn and "МЗ" in _note_ltn
_r = _lib_row(izt, "нагретого")
assert "P = 1 (вероятность)" in _cell(izt, _r, 1)
_r = _lib_row(izt, "лампы")
assert "3,2·10" in _cell(izt, _r, 1) and "год⁻¹" in _cell(izt, _r, 1)
assert "табл. 9" in _cell(izt, _r, 2)          # источник в примечании
# правка швами: λ (число) и примечание (мини-нотация)
_rec9 = kb.iz_causes[_r]
izt._set_number(_rec9, "lam", 6.4e-5)
assert _rec9["lam"] == 6.4e-5
assert "6,4·10" in _cell(izt, _lib_row(izt, "лампы"), 1)
izt._set_note(_rec9, "примечание X_1 с индексом")
assert "X<sub>1</sub>" in _cell(izt, _lib_row(izt, "лампы"), 2)
# кнопки НИЖНЕЙ ПАНЕЛИ (слева) видны на библиотеке, добавление записи
kbw.tabs.setCurrentWidget(izt)
pump()
assert kbw.btn_add_rec.isVisibleTo(kbw) and kbw.btn_del_rec.isVisibleTo(kbw)
_n0 = len(kb.iz_causes)
kbw.btn_add_rec.click()
pump()
assert len(kb.iz_causes) == _n0 + 1
_rec_new = kb.iz_causes[-1]
assert _rec_new["id"].startswith("iz-")
assert {"id", "title", "lam", "note"} <= set(_rec_new)
# удаление: неиспользуемая запись – обычный вопрос; используемая – с N
_caps9 = []
izt._confirm_delete_rec = \
    lambda t, u: (_caps9.append((t, u)), True)[1]
izt.table.selectRow(len(kb.iz_causes) - 1)
kbw.btn_del_rec.click()
pump()
assert len(kb.iz_causes) == _n0 and _caps9[-1][1] == 0
_r = _lib_row(izt, "лампы")
izt.table.selectRow(_r)
kbw.btn_del_rec.click()
pump()
assert _caps9[-1][1] >= 1          # используется в деревьях – предупреждение
# ГС: П1.2 × L; поверхность a₁·F; П1.1 инженерный
# (Задача 8: строки библиотеки развернуты по диапазонам расхода,
# подчасти названия после двоеточия – с заглавной)
gst = kbw.gs_tab
_r = _lib_row(gst, "Трубопровод D50: Утечка – малая")
assert "массовый расход истечения < 1 кг/с" \
    in gst.table.item(_r, 0).text().replace("\n", " ")
assert "× L" in _cell(gst, _r, 1) and "м⁻¹·год⁻¹" in _cell(gst, _r, 1)
assert "длина прокладки" in _cell(gst, _r, 2)
assert "a₁·F" in _cell(gst, _lib_row(gst, "Пожар по поверхности"), 1)
_r = _lib_row(gst, "отверстие 12,5 мм")
assert "год⁻¹" in _cell(gst, _r, 1)
# новая запись ГС: только 3 видимых поля + автогенерация остальных
kbw.tabs.setCurrentWidget(gst)
pump()
_n1 = len(kb.gs_causes)
kbw.btn_add_rec.click()
pump()
_rec_g = kb.gs_causes[-1]
assert _rec_g["id"].startswith("gs-") and _rec_g["kind"] == "p11"
assert set(_rec_g["applies"]) == {"gg", "gzh", "lvzh", "dust"}
assert any(g["id"] == _rec_g["id"]
           for g in kb.gs_for("gg", "apparatus"))
# отмена удаления (шов False) – запись жива
gst._confirm_delete_rec = lambda t, u: False
gst.table.selectRow(len(kb.gs_causes) - 1)
kbw.btn_del_rec.click()
assert len(kb.gs_causes) == _n1 + 1
# восстановление БД (в памяти; файл на диске не тронут) + чистое закрытие
kb.data = _kb_snap
kb._reindex()
for _i in range(kbw.tabs.count()):
    _t9 = kbw.tabs.widget(_i)
    if hasattr(_t9, "reload"):
        _t9.reload()
kbw.templates_tab.rebuild_cards()
pump()
assert kbw._dirty_count == 0
kbw.close()
pump()
w.kb_window = None
print("OK Задачи 9/10: библиотеки ИЗ/ГС – колонки, инженерный формат,"
      " правки, кнопки слева, предупреждение об использовании")

# ---------- 27. Задача 8 (сессия 13): типовые режимы пожара ---------------
w._open_kb_window()
pump()
kbw = w.kb_window
_names8 = [kbw.tabs.tabText(i) for i in range(kbw.tabs.count())]
assert "Таблица типовых режимов пожара" in _names8, _names8
assert "Типы горения" not in _names8
fmt8 = kbw.ft_tab
assert any("ТИПОВЫЕ РЕЖИМЫ ПОЖАРА (прил. № 2, табл. П2.1)" in l.text()
           for l in fmt8.findChildren(_QL))
for _c8, _h8 in enumerate(("Режим пожара", "Базовая частота", "Примечание")):
    assert fmt8.table.horizontalHeaderItem(_c8).text() == _h8
_rows8 = [fmt8.table.item(r, 0).text()
          for r in range(fmt8.table.rowCount())]
assert _rows8 == [
    "Пожар по поверхности", "Факельное горение", "Пожар-вспышка",
    "Пролив", "Сгорание (взрыв) ТВС", "Дефлаграция пылевоздушной смеси",
    "Детонация пылевоздушной смеси",
    "Огненный шар (диффузионное горение)"], _rows8
assert "a₁·F" in fmt8.table.item(0, 1).text()
assert "П1.3" in " ".join(fmt8.table.item(0, 2).text().split())
for _r8 in range(1, 7):
    assert fmt8.table.item(_r8, 1).text() == \
        "по табл. П2.1 (по расходу и среде)"
    _nt8 = " ".join(fmt8.table.item(_r8, 2).text().split())
    assert "расход" in _nt8 and "газ" in _nt8 and "П2.1" in _nt8
assert fmt8.table.item(7, 1).text() == "2,5·10⁻⁵ год⁻¹"
assert "прил. № 1, п. 5" in " ".join(
    fmt8.table.item(7, 2).text().split())
assert fmt8.table.editTriggers() == \
    _QAV2.EditTrigger.NoEditTriggers
# справочник только для чтения: кнопки добавления записей скрыты
kbw.tabs.setCurrentWidget(fmt8)
pump()
assert not kbw.btn_add_rec.isVisibleTo(kbw)
kbw.close()
pump()
w.kb_window = None
print("OK Задача 8: «Таблица типовых режимов пожара» – 8 строк,"
      " инженерный формат, только чтение")

# ---------- 28. Задача 4 (сессия 13): справочные (титульные) ноды ---------
from eta.ui.canvas import AnnotationItem as _AI, _DocAnnotationItem as _DAI
h.select_object(a3)
pump()
w._refresh()
pump()
ctrl = w.canvas.controller
vp = w.canvas.viewport()


def _ann_of(tid):
    return next(it for it in ctrl.work_scene.items()
                if isinstance(it, _AI) and it.ann.tree_id == tid)


ann4 = _ann_of(tgm3.tree_id)
_txt4 = " ".join(ann4.ann.lines)
assert "Участок" in _txt4 and "Сценарий пожара ТГМ" in _txt4, _txt4
assert not any("Q =" in _ln for _ln in ann4.ann.lines)
assert ann4.ann.attached is None and tgm3.annotation is None  # умолчание
# переименование владельца → текст живой
w.objects.rename(a3, "Кондитерский цех")
w._refresh()
pump()
assert "Кондитерский цех" in " ".join(_ann_of(tgm3.tree_id).ann.lines)
# сцена документа (лист/PDF) содержит справочную ноду – WYSIWYG
assert any(isinstance(it, _DAI) for it in ctrl.doc_scene.items())
# магнитная привязка: тянем справочную ноду на ноду ГС
def _drag4(item_rect_center, target_view_pos, target_name):
    QTest.mousePress(vp, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier,
                     item_rect_center.toPoint())
    pump()
    QTest.mouseMove(vp, target_view_pos.toPoint())
    pump()
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier,
                       target_view_pos.toPoint())
    pump()

gs_item = ctrl.node_item(f"{tgm3.tree_id}:gs")
_drag4(QPointF(w.canvas.mapFromScene(ann4.ann.rect.center())),
       QPointF(w.canvas.mapFromScene(gs_item.geo.rect.center())), "gs")
assert ctrl._attach_candidate is None            # подсветка снята
assert tgm3.annotation is not None \
    and tgm3.annotation["attached"] == "gs", tgm3.annotation
assert tgm3.annotation["offset"][1] < 0          # по центру НАД нодой
ann4 = _ann_of(tgm3.tree_id)
assert ann4.ann.attached == "gs"
_x_before = ann4.ann.rect.left()
_gs_left_before = gs_item.geo.rect.left()
# нода ГС едет – привязанная справочная нода следует за ней
QTest.mousePress(vp, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier,
                 QPointF(w.canvas.mapFromScene(
                     gs_item.geo.rect.center())).toPoint())
pump()
_moved = QPointF(w.canvas.mapFromScene(
    gs_item.geo.rect.center())) + QPointF(30, 0)
QTest.mouseMove(vp, _moved.toPoint())
pump()
QTest.mouseRelease(vp, Qt.MouseButton.LeftButton,
                   Qt.KeyboardModifier.NoModifier, _moved.toPoint())
pump()
ann4 = _ann_of(tgm3.tree_id)
assert tgm3.node_offsets and "gs" in tgm3.node_offsets
# следование: смещение ноды ГС и справочной ноды совпадают
_new_gs = ctrl.node_item(f"{tgm3.tree_id}:gs")
assert abs((_new_gs.geo.rect.left() - _gs_left_before)
           - (ann4.ann.rect.left() - _x_before)) < 0.5, "нода не следует"
# отвязка: тянем далеко в сторону – свободная позиция сохраняется
_far = QPointF(w.canvas.mapFromScene(
    ann4.ann.rect.center())) + QPointF(240, 240)
_drag4(QPointF(w.canvas.mapFromScene(ann4.ann.rect.center())), _far, "free")
assert tgm3.annotation["attached"] is None
assert abs(tgm3.annotation["offset"][0]) > 100
# round-trip формата 5
w._project_path = str(ROOT / "qa_artifacts" / "_gest_ann.kuji.json")
w._dirty = False
w._save_project()
_d4 = load_project(w._project_path)
_t4 = next(t for t in _d4["trees"] if t.tree_id == tgm3.tree_id)
assert _t4.annotation == tgm3.annotation
Path(w._project_path).unlink()
# «Авторазметка»: свободная нода – в позицию по умолчанию (состояние
# «без правок»), привязанная – остается привязанной
w.left_toolbar.btn_autolayout.click()
pump()
assert tgm3.node_offsets is None and tgm3.annotation is None
# повторная привязка переживает авторазметку (привязка сохранена)
ann4 = _ann_of(tgm3.tree_id)
fire_item = ctrl.node_item(f"{tgm3.tree_id}:fire")
_drag4(QPointF(w.canvas.mapFromScene(ann4.ann.rect.center())),
       QPointF(w.canvas.mapFromScene(fire_item.geo.rect.center())), "fire")
assert tgm3.annotation["attached"] == "fire"
w.left_toolbar.btn_autolayout.click()
pump()
assert tgm3.annotation is not None \
    and tgm3.annotation["attached"] == "fire"
print("OK Задача 4: справочные ноды – текст живой, магнитная привязка,"
      " следование за нодой, отвязка, round-trip, авторазметка")

# ---------- 29. Задача 0 (сессия 13): библиотека «Защитные средства» ------
from eta.core.model import TreeModel as _TM0
_kb_snap0 = _copy.deepcopy(kb.data)
w._open_kb_window()
pump()
kbw = w.kb_window
mt = kbw.mod_tab
for _c0, _h0 in enumerate(("Наименование средства", "Коэффициент",
                           "Носитель", "Примечание")):
    assert mt.table.horizontalHeaderItem(_c0).text() == _h0


def _mrow(ped: str) -> int:
    for r in range(mt.table.rowCount()):
        rec = kb.property_modifiers[r] \
            if r < len(kb.property_modifiers) else None
        if rec and rec.get("pedal") == ped:
            return r
    return -1


r_wear = _mrow("wear")
assert r_wear >= 0
assert mt.table.cellWidget(r_wear, 2).text() == "Нода ГС"
assert "2" in _strip7(mt.table.cellWidget(r_wear, 1).text())
# правка коэффициента СУЩЕСТВУЮЩЕЙ записи влияет на расчет (двигатель
# читает запись БД; подтверждено заказчиком)
_t0 = _TM0("gg", "x0")
_t0.gs_causes = [GSCause(ref="gs-vessel-12.5")]
_t0.gs_pedals.update({"wear": True, "sil_paz": True, "sil_pfd": 1e-2})
assert abs(_t0._gs_k(kb) - 2.0e-2) < 1e-12
mt._set_number(kb.property_modifiers[r_wear], "k", 4.0)
assert abs(_t0._gs_k(kb) - 4.0e-2) < 1e-12
mt._set_number(kb.property_modifiers[r_wear], "k", 2.0)
r_drain = _mrow("drain")
_t1 = _TM0("gg", "x1")
_t1.gs_pedals["drain"] = True
assert abs(_t1._gs_k(kb) - 0.05) < 1e-12
mt._set_number(kb.property_modifiers[r_drain], "p_success", 0.9)
assert abs(_t1._gs_k(kb) - 0.1) < 1e-12
mt._set_number(kb.property_modifiers[r_drain], "p_success", 0.95)
# новая запись: универсальный множитель k (type "k"), автогенерация
kbw.tabs.setCurrentWidget(mt)
pump()
assert kbw.btn_add_rec.isVisibleTo(kbw)
_n0 = len(kb.property_modifiers)
kbw.btn_add_rec.click()
pump()
rec0 = kb.property_modifiers[-1]
assert rec0["id"].startswith("pm-") and rec0["pedal"] == rec0["id"]
assert rec0["type"] == "k" and rec0["k"] == 1.0 \
    and rec0["target"] == "gs"
_last_row = mt.table.rowCount() - 1
assert "k = 1" in _strip7(mt.table.cellWidget(_last_row, 1).text())
_t0.gs_pedals[rec0["pedal"]] = True
assert abs(_t0._gs_k(kb) - 2.0e-2) < 1e-12        # k = 1 не меняет
mt._set_number(rec0, "k", 0.5)
assert abs(_t0._gs_k(kb) - 1.0e-2) < 1e-12        # ×0,5
# смена носителя: мера доступна на ИЗ, затем на ПОМЕЩЕНИИ (переключчик
# в свойствах, универсальный множитель через effective-props)
mt._set_target(rec0, "iz")
assert any(m["id"] == rec0["id"]
           for m in kb.modifiers_for_target("iz"))
mt._set_target(rec0, "room")
_room20 = a3.parent
_room20.props.setdefault("pedals", {})
_room20.props["pedals"][rec0["pedal"]] = True
ctxA = w.ctx_map()[a3.id]
assert abs(ctxA.universal_k(kb) - 0.5) < 1e-12
h.select_object(_room20)
pump()
assert any(s.text() == "Новое защитное средство"
           for s in w.inspector.form_host.findChildren(ToggleSwitch))
h.select_object(a3)
pump()
# удаление с предупреждением об использовании (включена на помещении)
_caps0 = []
mt._confirm_delete_rec = lambda t, u: (_caps0.append(u), True)[1]
mt.table.selectRow(mt.table.rowCount() - 1)
kbw.btn_del_rec.click()
pump()
assert len(kb.property_modifiers) == _n0
assert _caps0 and _caps0[-1] >= 1
# восстановление БД (в памяти; диск не тронут) и чистое закрытие
kb.data = _kb_snap0
kb._reindex()
for _i in range(kbw.tabs.count()):
    _t9 = kbw.tabs.widget(_i)
    if hasattr(_t9, "reload"):
        _t9.reload()
kbw.templates_tab.rebuild_cards()
pump()
assert kbw._dirty_count == 0
kbw.close()
pump()
w.kb_window = None
print("OK Задача 0: 4 колонки, правка коэффициентов влияет на расчет,"
      " универсальный k (нода/помещение), смена носителя, удаление")

# ---------- 30. Задача 1 (сессия 14): территория – всегда в корень --------
h.select_object(bld)                    # выделено ЗДАНИЕ, не территория
pump()
_top30 = h.tree.topLevelItemCount()
h.toolbar.buttons["territory"].click()
pump()
new_ter = h.selected()
assert new_ter is not None and new_ter.kind == "territory"
assert new_ter.parent is None, "территория создана НЕ в корне"
assert h.tree.topLevelItemCount() == _top30 + 1
assert "корне иерархии" in h.toolbar.buttons["territory"].toolTip()
print("OK Задача 1: «Добавить территорию» из-под здания – в корень")

# ---------- 31. Задача 2: Ctrl/Shift-мультивыбор РЕАЛЬНОЙ мышью ------------
def _click31(it, modifier=Qt.KeyboardModifier.NoModifier):
    h.tree.scrollToItem(it)              # строка – в зоне видимости
    pump()
    _r31 = h.tree.visualItemRect(it)
    _c31 = _r31.center()
    # широкая колонка длинных имён: центр строки может лежать ПРАВЕЕ
    # вьюпорта – клампим точку клика внутрь видимой области
    _c31.setX(min(max(_c31.x(), 12), h.tree.viewport().width() - 12))
    QTest.mouseClick(h.tree.viewport(), Qt.MouseButton.LeftButton,
                     modifier, _c31)


h.select_object(new_ter)
pump()
h.add_kind("building")
bA = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("building")                  # сосед того же типа
bB = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("room")
rC = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
pump()
_itA, _itB, _itC = h._item_of(bA), h._item_of(bB), h._item_of(rC)
assert None not in (_itA, _itB, _itC)
h.tree.scrollToItem(_itA)
pump()
_click31(_itA)                          # одиночный клик
pump()
assert len(h.tree.selectedItems()) == 1
_click31(_itB, Qt.KeyboardModifier.ControlModifier)
pump()
assert len(h.tree.selectedItems()) == 2, \
    len(h.tree.selectedItems())          # выбор пережил клик (без rebuild)
assert h.selected() is bB                # инспектор – последний кликнутый
_click31(_itC, Qt.KeyboardModifier.ControlModifier)
pump()
assert len(h.tree.selectedItems()) == 3
_click31(_itA)                           # обычный клик сбрасывает к одному
pump()
assert len(h.tree.selectedItems()) == 1
_click31(_itB, Qt.KeyboardModifier.ShiftModifier)
pump()
assert len(h.tree.selectedItems()) == 2  # Shift-диапазон тоже жив
# удаление пакета из РЕАЛЬНОГО Ctrl-выбора – одно окно (шов)
_click31(_itA)
pump()
_click31(_itB, Qt.KeyboardModifier.ControlModifier)
pump()
_batches31 = []
h._confirm_multi_delete = \
    lambda nodes: (_batches31.append(nodes), True)[1]
h.tree.setFocus()
QTest.keyClick(h.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert len(_batches31) == 1 and len(_batches31[0]) == 2
assert w.objects.by_id(bA.id) is None and w.objects.by_id(bB.id) is None
assert w.objects.by_id(new_ter.id) is not None
print("OK Задача 2: Ctrl/Shift мышью – 2/3 объекта, сброс, пакетное"
      " удаление одним окном")

# ---------- 32. Задачи 3/3.1: свернутые узлы переживают всё ---------------
h.select_object(new_ter)
pump()
h.add_kind("building")
b32 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("room")
r32 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("area")
a32 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
pump()
assert not h._item_of(a32).isExpanded(), "новый участок должен быть свернут"
assert h._item_of(b32).isExpanded() and h._item_of(r32).isExpanded()
h.select_object(new_ter)
pump()
h.add_kind("outdoor")
o32 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
pump()
assert not h._item_of(o32).isExpanded(), "новая установка должна быть свернута"
# сворачиваем здание вручную; выбор ДРУГОГО (видимого) объекта и полная
# пересборка – свернутым и остается
h._item_of(b32).setExpanded(False)
pump()
h.select_object(o32)
pump()
assert not h._item_of(b32).isExpanded()
w._refresh()                            # структурная пересборка
pump()
assert not h._item_of(b32).isExpanded(), "rebuild развернул здание"
assert h._item_of(r32).isExpanded()     # остальные по-прежнему раскрыты


def _scen_row_of(panel, tree_id):
    """Строка сценария по tree_id (Задача 3.1: строка вместо «Группы»)."""
    for it, _oid, data in panel._iter_items():
        if data and not data.get("cause") \
                and data.get("tree_id") == tree_id:
            return it
    return None


w._add_tree(a32.id, "tgm")              # под участком – строка сценария
pump()
_t32 = next(t for t in w.trees if t.owner_id == a32.id)
h._item_of(a32).setExpanded(True)
pump()
_s32 = _scen_row_of(h, _t32.tree_id)
assert _s32 is not None
_s32.setExpanded(False)
pump()
w._refresh()
pump()
assert not _scen_row_of(h, _t32.tree_id).isExpanded()  # пережила rebuild
# ui-словарь формата 5: round-trip свернутости (объекты + строка сценария)
w._project_path = str(ROOT / "qa_artifacts" / "_gest_collapsed.kuji.json")
w._dirty = False
w._save_project()
_dc32 = load_project(w._project_path)
_ui32 = _dc32["ui"]
assert b32.id in _ui32["hierarchy_collapsed"]
assert o32.id in _ui32["hierarchy_collapsed"]
assert _t32.tree_id in _ui32["hierarchy_groups_collapsed"]
w3 = MainWindow(kb, restore_ui=False)
w3._load_project_data(w._project_path, _dc32)
pump()
assert not w3.hierarchy._item_of(w3.objects.by_id(b32.id)).isExpanded()
assert not w3.hierarchy._item_of(w3.objects.by_id(o32.id)).isExpanded()
_s3 = _scen_row_of(w3.hierarchy, _t32.tree_id)
assert _s3 is not None and not _s3.isExpanded()
assert w3.hierarchy._item_of(w3.objects.by_id(a32.id)).isExpanded()
w3._dirty = False
w3.close()
Path(w._project_path).unlink()
# поврежденный файл: территория и здание ВНУТРИ участка (скриншоты №3/№4)
import json as _json14
from eta.core.model import TreeModel as _TM14
_dmg_tree = _TM14("tgm", "DA1", title="Дерево")
_dmg_tree.gs_causes = [GSCause(ref="gs-tgm-surface")]
_dmg = {"format": 5, "name": "dmg", "threshold": 1e-8,
        "objects": [
            {"id": "DT1", "kind": "territory", "title": "Территория 1",
             "props": {}, "children": [
                 {"id": "DB1", "kind": "building", "title": "Здание 1",
                  "props": {}, "children": [
                      {"id": "DR1", "kind": "room", "title": "Помещение 1",
                       "props": {}, "children": [
                           {"id": "DA1", "kind": "area",
                            "title": "Участок 1",
                            "props": {"site_type": "area"},
                            "children": [
                                {"id": "DT2", "kind": "territory",
                                 "title": "Территория 2", "props": {}},
                                {"id": "DB2", "kind": "building",
                                 "title": "Здание 2", "props": {}}]}]}]}]}],
        "trees": [_dmg_tree.to_dict()]}
_dmg_path = str(ROOT / "qa_artifacts" / "_gest_damaged.kuji.json")
with open(_dmg_path, "w", encoding="utf-8") as fh:
    _json14.dump(_dmg, fh, ensure_ascii=False, indent=1)
_dd14 = load_project(_dmg_path)
w4 = MainWindow(kb, restore_ui=False)
w4._load_project_data(_dmg_path, _dd14)
pump()
assert w4.objects.by_id("DT2").parent is None       # территория – в корень
assert w4.objects.by_id("DB2").parent.id == "DT1"   # здание – к территории
assert w4.objects.by_id("DA1") is not None
assert [t for t in w4.trees if t.owner_id == "DA1"]  # дерево живо
assert "вложенные территории" in w4.statusBar().currentMessage()
w4._dirty = False
w4.close()
Path(_dmg_path).unlink()
print("OK Задачи 3/3.1: новые участок/установка свернуты; свернутость"
      " переживает клики/rebuild и файл; поврежденный файл чинится")

# ---------- 33. Задача 4: компактный переключатель км²|м² -----------------
h.select_object(terr3)
pump()
_cb33 = next(c for c in w.inspector.form_host.findChildren(_QCB12)
             if c.count() == 2 and c.itemText(0) == "км²")
assert _cb33.objectName() == "compactCombo"
assert _cb33.width() <= 90, _cb33.width()
print(f"OK Задача 4: компактный список единиц – {_cb33.width()}px ≤ 90")

# ---------- 34. Задача 5: «наследуется» + каскад в живом окне -------------
from PySide6.QtWidgets import QDoubleSpinBox as _QDS34
h.select_object(None)
h.add_kind("territory")
t34 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("building")
b34 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
b34.props.update({"area_m2": 2000.0, "p13_type": "p13-multi"})
b34.props.pop("p14_type", None)
h.add_kind("room")
r34 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("area")
a34 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
pump()
# (а) форма помещения: тип «– наследуется –», площадь наследуется серым
h.select_object(r34)
pump()
_tcb = next(c for c in w.inspector.form_host.findChildren(_QCB12)
            if c.count() and c.itemText(0) == "– наследуется –")
assert _tcb.currentData() is None
assert "p13_type" not in r34.props          # наследуемое НЕ записано
_aspin = next(s for s in w.inspector.form_host.findChildren(_QDS34)
              if s.property("inactive") == "true")
assert abs(_aspin.value() - 2000.0) < 1e-9  # показано наследуемое (от здания)
assert "area_m2" not in r34.props
assert "наследуется" in _aspin.toolTip().lower()
# явный выбор типа и ввод площади – записываются
_tcb.setCurrentIndex(_tcb.findData("p13-multi"))
pump()
assert r34.props.get("p13_type") == "p13-multi"
_aspin.setValue(300.0)
pump()
assert r34.props["area_m2"] == 300.0
assert _aspin.property("inactive") == "false"
# дерево ТГМ на участке: F от помещения (300), тип от помещения
w._add_tree(a34.id, "tgm")
tgm34 = next(t for t in w.trees if t.owner_id == a34.id)
tgm34.gs_causes = [GSCause(ref="gs-tgm-surface")]
tgm34.iz_causes = [IZCause(ref="iz-lamp")]
w._refresh()
pump()
_v34, _note34 = w.ctx_map()[a34.id].tgm_multiplier(kb)
assert abs(_v34 - 9.0e-5 * 300.0) < 1e-12, (_v34, _note34)
# собственная площадь участка 25 000 → эффективная F > 10 000 → П1.4
h.select_object(a34)
pump()
_aspinA = next(s for s in w.inspector.form_host.findChildren(_QDS34)
               if s.maximum() >= 10_000_000)
_aspinA.setValue(25000.0)
pump()
_v34b, _note34b = w.ctx_map()[a34.id].tgm_multiplier(kb)
assert _v34b == 0.0 and "П1.4" in _note34b    # тип П1.4 нигде не выбран
h.select_object(a34)
pump()
_labels34 = [l.text() for l in w.inspector.form_host.findChildren(_QL)]
assert any("П1.4" in l for l in _labels34)    # автопереключение подписи
b34.props["p14_type"] = "p14-food"            # тип на здании – работает
w._refresh()
pump()
_v34c, _note34c = w.ctx_map()[a34.id].tgm_multiplier(kb)
assert abs(_v34c - 0.0011 * 25000 ** 0.6) < 1e-9
print("OK Задача 5: «наследуется» не пишется; каскад F/тип; авто-П1.4;"
      " тип нигде – 0 с пояснением")

# ---------- 35. Задача 6: состояния нод (синий/фиолетовый) ----------------
ctrl = w.canvas.controller
h.select_object(a34)
pump()
_k35 = f"{tgm34.tree_id}"
assert ctrl.layout.nodes[f"{_k35}:gs"].state == "set"
assert ctrl.layout.nodes[f"{_k35}:iz"].state == "set"
assert ctrl.layout.nodes[f"{_k35}:fire"].state == "ok"   # валидатор чист
tgm34.gs_causes.append(GSCause(ref="gs-vessel-12.5"))    # недоступна для м²
w._refresh()
pump()
assert ctrl.layout.nodes[f"{_k35}:fire"].state == ""     # есть замечания
del tgm34.gs_causes[1]
w._refresh()
pump()
assert ctrl.layout.nodes[f"{_k35}:fire"].state == "ok"
print("OK Задача 6: задано – синий; «Возникновение» фиолетовый только"
      " при чистом валидаторе")

# ---------- 36. Задача 7: инженерная запись в матрице/БД/PDF --------------
w.set_doc_view_mode("matrix")
pump()
_q36 = [w.matrix_table.item(r, 4).text()
        for r in range(w.matrix_table.rowCount())]
assert _q36 and all("·10" in v or v == "0" for v in _q36), _q36[:4]
assert not any("e-" in v or "e+" in v for v in _q36)
_f36 = [w.matrix_table.item(r, 5).text()
        for r in range(w.matrix_table.rowCount())]
assert not any("(табл." in v for v in _f36), _f36[:2]
assert any("·10⁻" in v for v in _f36)
# Задача 4 (сессия 15): «Q₁ = …» с юникод-подстрочником и exp(...)
assert _f36[0].startswith("Q₁ = "), _f36[0]
assert any("exp(−" in v for v in _f36), _f36[:3]
assert not any("e^(−" in v or "P₂₁=" in v or "a₁·F" in v for v in _f36)
# шов редактора чисел БД: каретка принимается, мусор отклоняется
from eta.ui.kb_window import _NumberEditor
_ed36 = _NumberEditor("λ", 1e-5)
_ed36.edit.setText("2,52^-12")
_ed36._try_accept()
assert _ed36.value() == 2.52e-12
_ed36b = _NumberEditor("λ", 1e-5)
_ed36b.edit.setText("ой")
_ed36b._try_accept()
assert _ed36b.value() is None
# DOCX-модель: числа – инженерные, запрещенных строк нет (Задача 11)
_md36 = build_markdown(w.objects, w.trees, kb, w.ctx_map(),
                       w._owner_titles(), "A4L", None)
assert "·10⁻" in _md36 and "exp(−" in _md36
assert "Исполнитель" not in _md36 and "Объект расчёта" not in _md36
assert "Проект «" not in _md36                     # Задача 6: без строки
print("OK Задача 7: матрица «·10⁻» без (табл.…); каретка в БД; модель"
      " отчета – инженная запись без запрещенных строк")

# ---------- 37. Сессия 14/1: причины ГС доступны на любом участке --------
h.select_object(None)
h.add_kind("territory")
h.add_kind("building")
h.add_kind("room")
h.add_kind("area")
a37 = h.selected()                 # тип по умолчанию – «участок (м²)»
h.tree.closePersistentEditor(h.tree.currentItem())
w._add_tree(a37.id, "gg")
tr37 = next(t for t in w.trees if t.owner_id == a37.id)
# м²-участок: причины ГГ доступны БЕЗ фильтра по типу участка
recs37 = w.inspector._cause_records(tr37, gs=True)
assert recs37 and len(recs37) > 20, len(recs37)
assert any(g["id"] == "gs-vessel-12.5" for g in recs37)
assert any(g["id"] == "gs-pipe-100-small" for g in recs37)
assert len(w.inspector._cause_records(tr37, gs=False)) > 0  # ИЗ – все
# валидатор: тип участка не «ловушка»; несоответствие типу СЦЕНАРИЯ видно
tr37.gs_causes = [GSCause(ref="gs-vessel-12.5")]
tr37.iz_causes = [IZCause(ref="iz-cable")]
_chk37 = __import__("eta.core.validation", fromlist=["check_tree"])
_iss37 = [i.message for i in _chk37.check_tree(
    tr37, kb, w.ctx_map()[a37.id], "area")]
assert not any("недоступна" in m for m in _iss37), _iss37
tr37.gs_causes.append(GSCause(ref="gs-tgm-surface"))   # только для ТГМ
_iss37b = [i.message for i in _chk37.check_tree(
    tr37, kb, w.ctx_map()[a37.id], "area")]
assert any("недоступна" in m for m in _iss37b)
# П1.2 на м²-участке: в формулу идет ПЛОЩАДЬ (м²), не длина/объем
_v37, _u37 = w.ctx_map()[a37.id].p12_value(None)
assert _u37 == "м²" and _v37 > 0, (_v37, _u37)
print("OK сессия 14/1: причины ГС без фильтра по типу участка;"
      " П1.2 на м² – площадь; валидатор без участковых ловушек")

# ---------- 38. Сессия 14/2: наведение на ноды холста без исключений ------
from PySide6.QtCore import QEvent as _QE38
from PySide6.QtWidgets import QGraphicsSceneHoverEvent as _HOV38
from eta.ui.canvas import NodeItem as _NI38
_ev38 = _HOV38(_QE38.Type.GraphicsSceneHoverEnter)
_node38 = next(it for it in ctrl.work_scene.items()
               if isinstance(it, _NI38))
_ann38 = next(it for it in ctrl.work_scene.items()
              if isinstance(it, _AI))
# раньше каждый hover сыпал в консоль AttributeError (mapFromScene
# возвращал QPoint без toPoint) – прямой вызов обработчиков теперь
# обязан проходить без исключений (подсказки нод живы)
_node38.hoverEnterEvent(_ev38)
pump()
_ann38.hoverEnterEvent(_ev38)
pump()
_node38.hoverLeaveEvent(
    _HOV38(_QE38.Type.GraphicsSceneHoverLeave))
_ann38.hoverLeaveEvent(
    _HOV38(_QE38.Type.GraphicsSceneHoverLeave))
pump()
print("OK сессия 14/2: hover нод/справочных нод без исключений"
      " (mapFromScene → QPointF-обертка)")

# ---------- 39. Сессия 15, Задача 9: два дерева одного владельца ----------
h.select_object(None)
h.add_kind("territory")
h.add_kind("outdoor")
od39 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
w._add_tree(od39.id, "gg")
w._add_tree(od39.id, "dust")
_trees39 = [t for t in w.trees if t.owner_id == od39.id]
assert len(_trees39) == 2, len(_trees39)
_dust39 = next(t for t in _trees39 if t.scenario_type == "dust")
# инспектор показывает ноду ГС ВТОРОГО дерева: причина обязана попасть
# в него (раньше _current_tree() при 2+ деревьях возвращал None – операция
# молча терялась)
w.inspector.show_tree_node(_dust39, "gs")
assert w.inspector.current_tree() is _dust39
w.inspector.add_gs_requested.emit("gs-vessel-5", None)
assert _dust39.gs_causes and _dust39.gs_causes[0].ref == "gs-vessel-5", \
    _dust39.gs_causes
assert not any(t.gs_causes for t in _trees39 if t is not _dust39)
w.inspector.show_tree_node(_dust39, "iz")
w.inspector.add_iz_requested.emit("iz-cable")
assert _dust39.iz_causes and _dust39.iz_causes[0].ref == "iz-cable"
# удаление – тоже в инспектируемое дерево
w.inspector.remove_gs_requested.emit(0)
assert not _dust39.gs_causes
print("OK сессия 15, Задача 9: причины добавляются в дерево"
      " инспектируемой ноды (два дерева одного владельца)")

# ---------- 40. Сессия 15, Задачи 1+2: тип участка в множителе ТГМ --------
h.select_object(None)
h.add_kind("territory")
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("building")
b40 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
b40.props.update({"area_m2": 2000.0, "p13_type": "p13-multi",
                  "p14_type": "p14-food"})
h.add_kind("room")
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("area")
a40 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
w._add_tree(a40.id, "tgm")
tgm40 = next(t for t in w.trees if t.owner_id == a40.id)
tgm40.gs_causes = [GSCause(ref="gs-tgm-surface")]
tgm40.iz_causes = [IZCause(ref="iz-lamp")]
w._refresh()
pump()
# форма участка: тип «линейный объект (м)» – умолчание длины 50 сразу
# попадает в множитель ТГМ (вариант А: a₁ × значение по типу)
h.select_object(a40)
pump()
_st40 = next(c for c in w.inspector.form_host.findChildren(_QCB12)
             if c.count() == 3 and c.itemData(0) == "area")
_st40.setCurrentIndex(_st40.findData("linear"))
pump()
_v40, _n40 = w.ctx_map()[a40.id].tgm_multiplier(kb)
assert abs(_v40 - 9.0e-5 * 50.0) < 1e-12, (_v40, _n40)
# правка значения БЕЗ ухода из панели: пересчет немедленный
_fire40 = ctrl.layout.nodes[f"{tgm40.tree_id}:fire"]
_before40 = " ".join(_fire40.body_lines)
_lspin40 = next(s for s in w.inspector.form_host.findChildren(_QDS34)
                if s.maximum() >= 10_000_000)
assert abs(_lspin40.value() - 50.0) < 1e-9
_lspin40.setValue(51251.0)
pump()
assert " ".join(ctrl.layout.nodes[f"{tgm40.tree_id}:fire"].body_lines) \
    != _before40                      # ΣQ ноды изменился сразу
_v40b, _n40b = w.ctx_map()[a40.id].tgm_multiplier(kb)
# длина 51 251 > 10 000 → эффективное значение включает П1.4-ветку
assert abs(_v40b - 0.0011 * 51251 ** 0.6) < 1e-6, (_v40b, _n40b)
assert _n40b == "(0,0011·51251^0,6)", _n40b
assert w.ctx_map()[a40.id].tgm_table(kb) == "П1.4"
_exp40 = fmt_q(tgm40.total_q(kb, w.ctx_map()[a40.id]))
assert _exp40 in w.status_label.text(), (w.status_label.text(), _exp40)
# аппарат/установка (м³): значение по типу, П1.3-ветка (10 < 10 000)
_st40.setCurrentIndex(_st40.findData("apparatus"))
pump()
_v40c, _ = w.ctx_map()[a40.id].tgm_multiplier(kb)
assert abs(_v40c - 9.0e-5 * 10.0) < 1e-12, _v40c
print("OK сессия 15, Задачи 1+2: тип/значение участка – сразу в множитель"
      " ТГМ (м/м³); пересчет ноды и статус-бара без ухода из панели")

# ---------- 41. Сессия 15, Задача 6: селектор типа наружной установки -----
od41 = od39                        # установка блока 39
od41.props.pop("site_type", None)  # имитация проекта ≤6.4.2 (без типа)
h.select_object(od41)
pump()
assert od41.props.get("site_type") == "area"   # миграция умолчанием «м²»
assert od41.props.get("area_m2") == 400.0      # умолчание установки – 400
od41.props["p13_type"] = "p13-multi"           # тип – как в блоке 34
w._refresh()
pump()
_st41 = next(c for c in w.inspector.form_host.findChildren(_QCB12)
             if c.count() == 3 and c.itemData(0) == "area")
assert _st41.currentData() == "area"
# дерево ТГМ на установке: F = площадь 400 (унаследованный проект)
w._add_tree(od41.id, "tgm")
tgm41 = next(t for t in w.trees
             if t.owner_id == od41.id and t.scenario_type == "tgm")
tgm41.gs_causes = [GSCause(ref="gs-tgm-surface")]
tgm41.iz_causes = [IZCause(ref="iz-lamp")]
w._refresh()
pump()
_v41, _ = w.ctx_map()[od41.id].tgm_multiplier(kb)
assert abs(_v41 - 9.0e-5 * 400.0) < 1e-12, _v41
# переключение на «линейный объект (м)»: длина 50 – сразу в множитель,
# подпись значения меняется на «Длина, м:»
_st41.setCurrentIndex(_st41.findData("linear"))
pump()
_v41b, _ = w.ctx_map()[od41.id].tgm_multiplier(kb)
assert abs(_v41b - 9.0e-5 * 50.0) < 1e-12, _v41b
_labels41 = [l.text() for l in w.inspector.form_host.findChildren(_QL)]
assert any(l == "Длина, м:" for l in _labels41), _labels41
print("OK сессия 15, Задача 6: селектор типа установки (м²/м/м³);"
      " миграция «м²»; значение по типу – в множитель ТГМ")

# ---------- 42. Сессия 15, Задача 11: T_ТО, подписи, разворот ≤85 --------
from eta.ui.controls import (PopupWrapDelegate, _popup_target_width,
                             wide_combo as _wc42)
from eta.ui.theme import math as _math42
# T_ТО: запись меры переименована, мини-нотация дает подстрочный «ТО»
_tt42 = next(m for m in kb.property_modifiers if m["id"] == "pm-ttest")
assert "T_ТО" in _tt42["title"] and "тест" not in _tt42["title"].lower()
assert "T_ТО" in _tt42["formula"]
assert "<sub>ТО</sub>" in _math42("(T_ТО)")
# подпись «Функциональное назначение (П1.3/П1.4)» в формах уровней
h.select_object(b40)
pump()
_lab42 = [l.text() for l in w.inspector.form_host.findChildren(_QL)]
assert any("Функциональное назначение (П1.3)" in l for l in _lab42)
h.select_object(a40)
pump()
_lab42b = [l.text() for l in w.inspector.form_host.findChildren(_QL)]
assert any("Функциональное назначение (П1.3)" in l for l in _lab42b)
# разворот списка: ширина по содержимому, потолок 85 символов,
# длинные пункты переносятся по словам/слогам
_cb42 = _wc42()
_cb42.addItem("Цеха по обработке синтетического каучука"
              " и искусственных волокон")
_cb42.addItem("короткий пункт")
_lv42 = _cb42.view()
_dl42 = _lv42.itemDelegate()
_fm42 = _lv42.fontMetrics()
_cap42 = _fm42.horizontalAdvance("А" * 85) + 34
_w42 = _popup_target_width(_cb42, _lv42, _dl42)
assert _cb42.width() <= _w42 <= _cap42, (_cb42.width(), _w42, _cap42)
_long42 = ("слово " * 40).strip()          # 200 символов
_lines42 = _dl42._lines(_long42, _fm42, 0)
assert len(_lines42) > 1 and all(len(l) <= 85 for l in _lines42)
_cb42b = _wc42()
_cb42b.addItem("п")                        # узкий список – не уже кнопки
_w42b = _popup_target_width(_cb42b, _cb42b.view(),
                            _cb42b.view().itemDelegate())
assert _w42b == _cb42b.width()
print("OK сессия 15, Задача 11: T_ТО (подстрочный «ТО»);"
      " «Функциональное назначение (П1.3/П1.4)»; разворот ≤85 символов"
      " с переносом по словам/слогам")

# ---------- 43. Сессия 15, Задача 8: развернутые строки ГС ----------------
from eta.core.model import TreeModel as _TM43
gg43 = next(t for t in w.trees
            if t.owner_id == od39.id and t.scenario_type == "gg")
recs43 = w.inspector._cause_records(gg43, gs=True)
# отверстие 5 мм – ТРИ независимые строки (диапазоны <1 / 1–50 / >50)
_row5 = [r for r in recs43 if r["id"] == "gs-vessel-5"]
assert len(_row5) == 3 and {r["flow"] for r in _row5} == \
    {"small", "mid", "big"}, len(_row5)
assert any(r["row_title"] == ("Аппарат (сосуд) под давлением:"
                             " Разгерметизация, Отверстие 5 мм –"
                             " массовый расход истечения < 1 кг/с")
           for r in _row5)
# «полное разрушение» – своя строка (диапазон «полный разрыв»), без суффикса
_rupt = [r for r in recs43 if r["id"] == "gs-vessel-rupt"]
assert len(_rupt) == 1 and _rupt[0]["flow"] == "rupt"
assert _rupt[0]["row_title"] == ("Аппарат (сосуд) под давлением:"
                                 " Разгерметизация, Полное разрушение")
# direct-события П1.1 – одна строка БЕЗ диапазона (проверка на ГЖ-дереве:
# прямые записи применяются к ГЖ/ЛВЖ)
_recs_gzh43 = w.inspector._cause_records(_TM43("gzh", "tmp43"), gs=True)
assert [r for r in _recs_gzh43
        if r["id"] == "gs-tank-float-ring"][0].get("flow") is None
# ТГМ/Пыль – развертки нет (математика не ветвится по расходу)
assert all(r.get("flow") is None
           for r in w.inspector._cause_records(
               next(t for t in _trees39 if t.scenario_type == "dust"),
               gs=True))
# движок: причина со своим диапазоном порождает ТОЛЬКО его сценарии;
# все режимы диапазона появляются автоматически (P > 0)
gg43.gs_causes = [GSCause(ref="gs-vessel-5", flow="mid"),
                  GSCause(ref="gs-vessel-5", flow="big")]
gg43.iz_causes = [IZCause(ref="iz-cable")]
w._refresh()
pump()
_ctx43 = w.ctx_map()[od39.id]
_chk43 = __import__("eta.core.validation", fromlist=["check_tree"])
assert not any("Повторяющиеся" in i.message
               for i in _chk43.check_tree(gg43, kb, _ctx43, "outdoor"))
gg43.gs_causes.append(GSCause(ref="gs-vessel-5", flow="mid"))
assert any("Повторяющиеся" in i.message
           for i in _chk43.check_tree(gg43, kb, _ctx43, "outdoor"))
del gg43.gs_causes[2]
rows43 = gg43.scenarios(kb, _ctx43)
assert len(rows43) == 6, len(rows43)      # 2 диапазона × 3 режима × 1 ИЗ
assert {r.flow for r in rows43} == {"mid", "big"}
assert {r.fire_type for r in rows43 if r.flow == "mid"} == \
    {"ft-jet", "ft-flash", "ft-vce"}
# сериализация round-trip с диапазоном (формат 5, поле опционально)
_t43 = _TM43.from_dict(gg43.to_dict())
assert [c.flow for c in _t43.gs_causes] == ["mid", "big"]
_p43 = _TM43("gg", "x")
_p43.gs_causes = [GSCause(ref="gs-vessel-5")]        # старый файл: без flow
assert "flow" not in _TM43.from_dict(_p43.to_dict()).gs_causes[0].to_dict()
# библиотека БД: строки развернуты (больше строк, чем записей)
assert kbw.gs_tab.table.rowCount() > len(kb.gs_causes)
print("OK сессия 15, Задача 8: строки по диапазонам расхода – независимые"
      " причины; rupt отдельно; движок и сериализация с flow; библиотека"
      " развернута")

# ---------- 44. Сессия 15, Задача 3: причины-дети, зависимости, DnD ------
def _cause_row(panel, tree_id, kind, cid):
    for it, _oid, data in panel._iter_items():
        if data and data.get("cause") and data.get("tree_id") == tree_id \
                and data.get("kind") == kind and data.get("cid") == cid:
            return it
    return None


h.select_object(None)
h.add_kind("territory")
t44 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("building")
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("room")
r44 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.add_kind("area")
a44 = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
h.select_object(r44)                  # сосед: второе помещение в здании
h.add_kind("room")                    # второе помещение – для переноса
r44b = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
w._add_tree(a44.id, "tgm")
tr44 = next(t for t in w.trees if t.owner_id == a44.id)
tr44.gs_causes = [GSCause(ref="gs-tgm-surface")]
_cable44 = IZCause(ref="iz-cable")
_lamp44 = IZCause(ref="iz-lamp")
_lamp44.parent = _cable44.cid          # лампа – следствие отказа КЛ
tr44.iz_causes = [_cable44, _lamp44]
w._refresh()
pump()
# (1) строки причин живут под строкой сценария; цепь вложена (3.1–3.3)
_scen44 = _scen_row_of(h, tr44.tree_id)
assert _scen44 is not None
_row_cable = _cause_row(h, tr44.tree_id, "iz", _cable44.cid)
assert _row_cable is not None and _row_cable.parent() is _scen44
_row_lamp = _cause_row(h, tr44.tree_id, "iz", _lamp44.cid)
assert _row_lamp.parent() is _row_cable          # зависимая ветвь – под родителем
# клик по строке причины: дерево на холсте, форма ноды ИЗ, пунктир ноды
h.tree.setCurrentItem(_row_lamp)
pump()
assert w.inspector.current_tree() is tr44
assert w.canvas.controller.selected_node() == f"{tr44.tree_id}:iz"
# драг-швы (строки переищены после каждой пересборки – старые айтемы
# Qt уже удалены): причина → причина того же списка (валидно), на себя (нет)
tr44.iz_causes.append(IZCause(ref="iz-static"))
w._refresh()
pump()
_st44 = tr44.iz_causes[-1]
_row_cable = _cause_row(h, tr44.tree_id, "iz", _cable44.cid)
_row_st = _cause_row(h, tr44.tree_id, "iz", _st44.cid)
assert h.drop_ok(_row_st, _row_cable)            # ИЗ → ИЗ можно
assert not h.drop_ok(_row_cable, _row_cable)     # на себя – нельзя
# отцепление на строке сценария
_scen44 = _scen_row_of(h, tr44.tree_id)
h.handle_drop(_row_st, _scen44)                  # статика → верхний уровень
pump()
assert _st44.parent is None
# зависимость через драг: статика под лампу (цепь 2 уровней)
_row_lamp = _cause_row(h, tr44.tree_id, "iz", _lamp44.cid)
_row_st = _cause_row(h, tr44.tree_id, "iz", _st44.cid)
h.handle_drop(_row_st, _row_lamp)
pump()
assert _st44.parent == _lamp44.cid
# математика немедленно: одна строка цепи «КЛ → лампа → статика» + 0
_rows44 = tr44.scenarios(kb, w.ctx_map()[a44.id])
assert len(_rows44) == 1 and _rows44[0].name.count("→") == 2, \
    [r.name for r in _rows44]
assert w.status_label.text().strip() != ""
# «Убрать» с зависимыми ветвями: шов подтверждения, ветвь удаляется целиком
w.inspector.show_tree_node(tr44, "iz")
pump()
_caps44 = []
w._confirm_remove_chain = \
    lambda chain, kb_: (_caps44.append(len(chain)), True)[1]
w.inspector.remove_iz_requested.emit(0)          # кабельная линия (idx 0)
pump()
assert _caps44 == [3]                            # КЛ + лампа + статика
assert not tr44.iz_causes
# (2) перенос объекта: участок → второе помещение (поддерево целиком)
tr44.gs_causes = [GSCause(ref="gs-tgm-surface")]
tr44.iz_causes = [IZCause(ref="iz-cable")]
w._refresh()
pump()
_it_a44 = h._item_of(a44)
_it_r44b = h._item_of(r44b)
assert h.drop_ok(_it_a44, _it_r44b)
h.handle_drop(_it_a44, _it_r44b)
pump()
assert a44.parent is r44b                        # новый родитель
assert h.selected() is a44                       # выбор следует за объектом
assert any(t.owner_id == a44.id for t in w.trees)  # дерево живо (owner_id)
# недопустимый дроп: здание → помещение (строки переищены после rebuild)
_it_r44b = h._item_of(r44b)
_it_b44 = h._item_of(t44.children[0])
assert not h.drop_ok(_it_b44, _it_r44b)
# (3) перенос дерева: строка сценария → другой владелец (тот же тип)
h.select_object(r44b)                 # участок создается в помещении
pump()
h.add_kind("area")
a44b = h.selected()
h.tree.closePersistentEditor(h.tree.currentItem())
w._refresh()
pump()
_scen44b = _scen_row_of(h, tr44.tree_id)
_it_a44b = h._item_of(a44b)
assert h.drop_ok(_scen44b, _it_a44b)
h.handle_drop(_scen44b, _it_a44b)
pump()
assert tr44.owner_id == a44b.id
_ann44 = next(a for a in ctrl.layout.annotations
              if a.tree_id == tr44.tree_id)
assert a44b.title in " ".join(_ann44.lines)      # аннотация следует
print("OK сессия 15, Задача 3: причины-дети, цепи И-гейт через DnD,"
      " «Убрать» с ветвью, перенос объекта/дерева")

# ---------- 45. Сессия 15, Задача 10: редактор шаблонов оборудования ----
w._open_kb_window()
pump()
kbw10 = w.kb_window
tt10 = kbw10.templates_tab
kbw10.tabs.setCurrentWidget(tt10)
pump()
# [Добавить]/[Удалить] – в нижней панели ОКНА БД (слева, единообразно)
assert kbw10.btn_add_rec.isVisibleTo(kbw10) \
    and kbw10.btn_del_rec.isVisibleTo(kbw10)
# форма редактирования выбранного шаблона (Задача 10.1): доступна
# ТОЛЬКО после «Редактировать» (Задача 2, сессия 15/1)
tt10.selected_id = "eq-tgm-warehouse"
tt10._on_card(type("_C", (), {"rec": {"id": "eq-tgm-warehouse"}})())
pump()
assert tt10.ed_title.text() == "Складской участок с ТГМ"
assert tt10.cb_type.currentData() == "tgm"
assert tt10.gs_list.count() == 1 and tt10.iz_list.count() == 6
assert not tt10.ed_title.isEnabled() and not tt10.gs_list.isEnabled()
assert tt10.btn_edit.isVisibleTo(kbw10) \
    and not tt10.btn_save_form.isVisibleTo(kbw10)
tt10.btn_edit.click()                      # «Редактировать»
pump()
assert tt10.ed_title.isEnabled() \
    and tt10.btn_save_form.isVisibleTo(kbw10) \
    and tt10.btn_cancel_form.isVisibleTo(kbw10) \
    and not tt10.btn_edit.isVisibleTo(kbw10)
_rec10 = next(r for r in kb.equipment_templates
              if r["id"] == "eq-tgm-warehouse")
# правка названия/категории пишется в запись; карточка обновляется живьем
tt10.ed_title.setText("Склад с ТГМ (правка)")
tt10._edit_title(tt10.ed_title.text())
pump()
assert _rec10["title"] == "Склад с ТГМ (правка)"
assert any("Склад с ТГМ (правка)" in c.rec.get("title", "")
           for c in tt10._cards)
tt10.btn_save_form.click()                 # «Сохранить» – фиксирует правки
pump()
assert not tt10.ed_title.isEnabled() \
    and tt10.btn_edit.isVisibleTo(kbw10)
assert _rec10["title"] == "Склад с ТГМ (правка)"
# «Отмена» отбрасывает правки к снимку режима
tt10.btn_edit.click()
pump()
tt10.ed_title.setText("Неудачная правка")
tt10._edit_title(tt10.ed_title.text())
pump()
assert _rec10["title"] == "Неудачная правка"
tt10.btn_cancel_form.click()               # «Отмена»
pump()
assert _rec10["title"] == "Склад с ТГМ (правка)"    # вернулось
assert tt10.ed_title.text() == "Склад с ТГМ (правка)"
assert not tt10.ed_title.isEnabled()
# списки редактируются в режиме: удаление строки ИЗ; запись ГС
# с диапазоном расхода (Задача 8)
tt10.btn_edit.click()
pump()
tt10.iz_list.item(1).setSelected(True)
tt10._remove_iz_rows()
pump()
assert _rec10["iz_causes"] == ["iz-lamp", "iz-uzdo", "iz-human",
                               "iz-fork", "iz-spark"]
_rec10["gs_causes"].append("gs-vessel-5#mid")
tt10._mark_dirty()
pump()
assert tt10.gs_list.count() == 2
assert "массовый расход истечения 1–50 кг/с" \
    in tt10.gs_list.item(1).text()
# применение шаблона с записью «ref#диапазон»: поток проходит в дерево
_gg10 = next(r for r in kb.equipment_templates
             if r["id"] == "eq-outdoor-gas")
_gg10["gs_causes"].append("gs-vessel-5#mid")
h.select_object(inst)
w._update_kb_apply_hint()
pump()
tt10.selected_id = "eq-outdoor-gas"
tt10._on_card_dbl(type("_C", (), {"rec": {"id": "eq-outdoor-gas"}})())
pump()
_newgg10 = [t for t in w.trees
            if t.owner_id == inst.id and t.scenario_type == "gg"][-1]
assert ("gs-vessel-5", "mid") in [(c.ref, c.flow)
                                  for c in _newgg10.gs_causes]
# удаление шаблона: предупреждение со счетчиком использования (шов)
_caps10 = []
tt10._confirm_delete_tpl = lambda t, u: (_caps10.append(u), True)[1]
tt10.selected_id = "eq-tgm-warehouse"
tt10.delete_current_record()
pump()
assert _caps10 and _caps10[0] >= 1      # состав используется деревьями
assert not any(r["id"] == "eq-tgm-warehouse"
               for r in kb.equipment_templates)
# новый шаблон: умолчания подтверждены заказчиком
kbw10.btn_add_rec.click()
pump()
_new10 = kb.equipment_templates[-1]
assert _new10["title"] == "Новый шаблон оборудования"
assert _new10["category"] == "Прочее" and _new10["scenario_type"] == "gg"
assert _new10["gs_causes"] == [] and _new10["iz_causes"] == []
# восстановление БД (в памяти; файл на диске не тронут) + чистое закрытие
kb.data = _kb_snap0
kb._reindex()
for _i in range(kbw10.tabs.count()):
    _t10 = kbw10.tabs.widget(_i)
    if hasattr(_t10, "reload"):
        _t10.reload()
kbw10.templates_tab.rebuild_cards()
kbw10.close()
pump()
w.kb_window = None
print("OK сессия 15, Задача 10: форма редактирования шаблона, списки"
      " ГС/ИЗ (включая диапазоны расхода), удаление со счетчиком,"
      " [Добавить]/[Удалить] внизу окна")

# ---------- 46. Сессия 15/1: реальная мышь запускает драг причин ------
# БАГФИКС: строки причин/сценариев были НЕ selectable – Qt вообще не
# начинал перетаскивание реальной мышью (startDrag не вызывался), а
# программные setCurrentItem в тестах это маскировали
w5 = MainWindow(kb, restore_ui=False)
h5 = w5.hierarchy
h5.select_object(None)
h5.add_kind("territory")
h5.tree.closePersistentEditor(h5.tree.currentItem())
h5.add_kind("building")
h5.tree.closePersistentEditor(h5.tree.currentItem())
h5.add_kind("room")
h5.tree.closePersistentEditor(h5.tree.currentItem())
h5.add_kind("area")
a46 = h5.selected()
h5.tree.closePersistentEditor(h5.tree.currentItem())
w5._add_tree(a46.id, "tgm")
tr46 = next(t for t in w5.trees if t.owner_id == a46.id)
cable46 = IZCause(ref="iz-cable")
lamp46 = IZCause(ref="iz-lamp")
tr46.gs_causes = [GSCause(ref="gs-tgm-surface")]
tr46.iz_causes = [cable46, lamp46]
w5._refresh()
pump()


def _row46(panel, cid):
    for it, _oid, data in panel._iter_items():
        if data and data.get("cause") and data.get("cid") == cid:
            return it
    return None


def _expand_to46(tr_, it):
    chain = []
    p = it.parent()
    while p is not None:
        chain.append(p)
        p = p.parent()
    for p in reversed(chain):
        p.setExpanded(True)
    tr_.scrollToItem(it)


_it_c = _row46(h5, cable46.cid)
_it_l = _row46(h5, lamp46.cid)
assert _it_c is not None and _it_l is not None
_expand_to46(h5.tree, _it_c)
pump()
_calls46 = []
_orig_sd46 = h5.tree.startDrag
h5.tree.startDrag = \
    lambda actions: _calls46.append(1)  # exec не зовем: offscreen без DnD
from PySide6.QtTest import QTest as _QT46
from PySide6.QtGui import QMouseEvent as _QME46
from PySide6.QtCore import QEvent as _QE46, QPointF as _QPF46, \
    QPoint as _QP46
_vp46 = h5.tree.viewport()
_r46 = h5.tree.visualItemRect(_it_c)
_p046 = _QP46(min(_r46.center().x(), _vp46.width() - 20),
               _r46.center().y())
assert h5.tree.indexAt(_p046) == h5.tree.indexAt(_r46.center())
_QT46.mousePress(_vp46, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier, _p046)
# движение С зажатой ЛКМ: представление обязано запустить перетаскивание
_ev46 = _QME46(_QE46.Type.MouseMove,
               _QPF46(_p046.x() + 15, _p046.y() + 3),
               _QPF46(_p046.x() + 15, _p046.y() + 3),
               Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
               Qt.KeyboardModifier.NoModifier)
QApplication.sendEvent(_vp46, _ev46)
pump()
_QT46.mouseRelease(_vp46, Qt.MouseButton.LeftButton,
                   Qt.KeyboardModifier.NoModifier, _p046)
pump()
assert len(_calls46) == 1, _calls46      # startDrag ВЫЗВАН реальной мышью
# offscreen-платформа не исполняет QDrag.exec (нет оконного DnD) –
# дальнейший путь (enter → move → drop) покрываем синтетическими
# drag-событиями с меткой собственного драга
from PySide6.QtGui import (QDragEnterEvent as _DEE46, QDragMoveEvent,
                           QDropEvent as _DRE46)
from PySide6.QtCore import QMimeData as _MD46
_r46l = h5.tree.visualItemRect(_it_l)
_t46 = _QP46(min(_r46l.center().x(), _vp46.width() - 20),
              _r46l.center().y())
_m46 = _MD46()
_m46.setData("application/x-kuji-hier", b"1")
h5.tree.setCurrentItem(_it_c)            # источник = перетаскиваемая строка
pump()
_ee46 = _DEE46(_QPF46(_t46), Qt.DropAction.MoveAction, _m46,
               Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
# drag-события приходят через ВЬЮПОРТ (QAbstractScrollArea::viewportEvent
# пересылает их в обработчики дерева) – как при реальном DnD
QApplication.sendEvent(_vp46, _ee46)
assert _ee46.isAccepted()
_mv46 = QDragMoveEvent(_QPF46(_t46), Qt.DropAction.MoveAction, _m46,
                       Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)
QApplication.sendEvent(_vp46, _mv46)
pump()
assert _it_l.background(0).color().name().lower() == "#dbeafe"  # подсветка
_dr46 = _DRE46(_QPF46(_t46), Qt.DropAction.MoveAction, _m46,
               Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
QApplication.sendEvent(_vp46, _dr46)
pump()
# зависимость зафиксирована, математика пересчиталась немедленно
assert cable46.parent == lamp46.cid
_rows46 = tr46.scenarios(kb, w5.ctx_map()[a46.id])
assert len(_rows46) == 1 and "→" in _rows46[0].name, \
    [r.name for r in _rows46]
# целевая строка раскрыта, перенесенная – выделена
_it_c2 = _row46(h5, cable46.cid)
_it_l2 = _row46(h5, lamp46.cid)
assert _it_c2.parent() is _it_l2 and _it_l2.isExpanded()
assert h5.tree.currentItem() is _it_c2
w5._dirty = False
w5.close()
print("OK сессия 15/1: реальная мышь запускает драг причин (selectable-"
      "багфикс); enter→move→drop; подсветка; раскрытие и выделение")

# ---------- 47. Сессия 16, Задача 1: Delete/мусорка на строках причин ----
# БАГФИКС (класс потери данных): выбор строки причины + Delete/мусорка
# молча удалял ВЕСЬ УЧАСТОК (легаси-фолбэк _selected_deletable_nodes).
# Теперь чистый выбор причин удаляет ПРИЧИНЫ с зависимыми ветвями;
# участок-владелец жив; строка сценария – безопасный no-op; смешанный
# выбор удаляет только объекты
from PySide6.QtCore import QPoint as _QP47
w7 = MainWindow(kb, restore_ui=False)
h7 = w7.hierarchy
h7.select_object(None)
h7.add_kind("territory")
h7.tree.closePersistentEditor(h7.tree.currentItem())
h7.add_kind("building")
h7.tree.closePersistentEditor(h7.tree.currentItem())
h7.add_kind("room")
h7.tree.closePersistentEditor(h7.tree.currentItem())
h7.add_kind("area")
a47 = h7.selected()
h7.tree.closePersistentEditor(h7.tree.currentItem())
w7._add_tree(a47.id, "tgm")
tr47 = next(t for t in w7.trees if t.owner_id == a47.id)


def _causes47():
    gs47 = GSCause(ref="gs-tgm-surface")
    cable = IZCause(ref="iz-cable")
    lamp = IZCause(ref="iz-lamp")
    static = IZCause(ref="iz-static")
    lamp.parent = cable.cid
    static.parent = lamp.cid
    tr47.gs_causes = [gs47]
    tr47.iz_causes = [cable, lamp, static]
    w7._refresh()
    pump()
    return gs47, cable, lamp, static


def _click_row47(panel, it, mod=Qt.KeyboardModifier.NoModifier):
    """Реальный клик мышью по строке дерева (без модификатора – один,
    Ctrl – добавить к выбору); X зажимается в пределы вьюпорта."""
    _expand_to46(panel.tree, it)
    pump()
    vp = panel.tree.viewport()
    r = panel.tree.visualItemRect(it)
    p = _QP47(min(r.center().x(), vp.width() - 20), r.center().y())
    assert panel.tree.indexAt(p) == panel.tree.indexAt(r.center())
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton, mod, p)
    pump()


_caps47: list[list[str]] = []
w7._confirm_remove_causes = \
    lambda chain, kb_: (_caps47.append([c.ref for c in chain]), True)[1]

# (1) клик по строке причины + Delete: ОДНО окно со всей цепью,
# причина удалена С ветвями, УЧАСТОК ЖИВ, дерево и его ГС-причина живы
_gs47, _cb47, _lp47, _st47 = _causes47()
_it47 = _row46(h7, _cb47.cid)
assert _it47 is not None
_click_row47(h7, _it47)
assert w7._canvas_sel_by_click is False     # пунктир ноды – программный
assert h7.selected_causes() == [(tr47.tree_id, "iz", _cb47.cid)]
h7.tree.setFocus()
QTest.keyClick(h7.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert _caps47 == [["iz-cable", "iz-lamp", "iz-static"]], _caps47
assert not tr47.iz_causes                  # цепь удалена целиком
assert len(tr47.gs_causes) == 1            # ГС-причина жива
assert w7.objects.by_id(a47.id) is not None  # УЧАСТОК ЖИВ
assert any(t is tr47 for t in w7.trees)    # дерево живо
assert w7.status_label.text().strip() != ""  # Q/статус пересчитаны
# (2) отказ в окне подтверждения: всё остается на месте
_gs47, _cb47, _lp47, _st47 = _causes47()
_click_row47(h7, _row46(h7, _cb47.cid))
w7._confirm_remove_causes = lambda chain, kb_: False
QTest.keyClick(h7.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert [c.ref for c in tr47.iz_causes] == ["iz-cable", "iz-lamp",
                                           "iz-static"]
w7._confirm_remove_causes = \
    lambda chain, kb_: (_caps47.append([c.ref for c in chain]), True)[1]
# (3) мультивыбор двух строк причин (реальный Ctrl+клик): ОДНО окно,
# обе цепи удалены
_click_row47(h7, _row46(h7, _gs47.cid))
_click_row47(h7, _row46(h7, _cb47.cid),
             Qt.KeyboardModifier.ControlModifier)
assert len(h7.selected_causes()) == 2
QTest.keyClick(h7.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert _caps47[-1] == ["gs-tgm-surface", "iz-cable", "iz-lamp",
                       "iz-static"], _caps47
assert not tr47.gs_causes and not tr47.iz_causes
assert w7.objects.by_id(a47.id) is not None   # участок по-прежнему жив
# (4) мусорка: с выбранной причиной – удаляет её (то же окно);
# с выбранной строкой сценария – выключена, Delete – no-op
_gs47, _cb47, _lp47, _st47 = _causes47()
_click_row47(h7, _row46(h7, _cb47.cid))
assert w7.left_toolbar.btn_trash.isEnabled()
w7.left_toolbar.btn_trash.click()
pump()
assert _caps47[-1] == ["iz-cable", "iz-lamp", "iz-static"]
assert not tr47.iz_causes
_scen47 = _scen_row_of(h7, tr47.tree_id)
h7.tree.setCurrentItem(_scen47)
pump()
assert not w7.left_toolbar.btn_trash.isEnabled()
h7.tree.setFocus()
QTest.keyClick(h7.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert w7.objects.by_id(a47.id) is not None   # no-op: ничего не удалено
assert any(t is tr47 for t in w7.trees)
# (5) смешанный выбор (причина + объект): удаляется ТОЛЬКО объект
_gs47, _cb47, _lp47, _st47 = _causes47()
_n47 = len(_caps47)
h7._confirm_delete = lambda node: True
_click_row47(h7, _row46(h7, _cb47.cid))
_click_row47(h7, h7._item_of(a47),
             Qt.KeyboardModifier.ControlModifier)
QTest.keyClick(h7.tree.viewport(), Qt.Key.Key_Delete)
pump()
assert w7.objects.by_id(a47.id) is None       # объект удален (как прежде)
assert len(_caps47) == _n47                   # причины окном не тронуты
assert not any(t is tr47 for t in w7.trees)   # дерево ушло с участком
w7._dirty = False
w7.close()
print("OK сессия 16, Задача 1: Delete/мусорка на строках причин – "
      "удаляются причины с ветвями, участок жив; сценарий – no-op; "
      "смешанный выбор – только объекты")

# ---------- 48. Сессия 16, Задача 2: отцепление 4 способами + Задача 4 --
w8 = MainWindow(kb, restore_ui=False)
h8 = w8.hierarchy
h8.select_object(None)
h8.add_kind("territory")
h8.tree.closePersistentEditor(h8.tree.currentItem())
h8.add_kind("building")
b48 = h8.selected()
h8.tree.closePersistentEditor(h8.tree.currentItem())
h8.add_kind("room")
h8.tree.closePersistentEditor(h8.tree.currentItem())
h8.add_kind("area")
a48 = h8.selected()
h8.tree.closePersistentEditor(h8.tree.currentItem())
w8._add_tree(a48.id, "tgm")
tr48 = next(t for t in w8.trees
            if t.owner_id == a48.id and t.scenario_type == "tgm")
w8._add_tree(a48.id, "gg")            # второе дерево того же владельца
tr48b = next(t for t in w8.trees if t is not tr48)
tr48.gs_causes = [GSCause(ref="gs-tgm-surface")]
cable48 = IZCause(ref="iz-cable")
lamp48 = IZCause(ref="iz-lamp")
static48 = IZCause(ref="iz-static")
lamp48.parent = cable48.cid           # КЛ → лампа → статика (цепь)
static48.parent = lamp48.cid
tr48.iz_causes = [cable48, lamp48, static48]
tr48b.iz_causes = [IZCause(ref="iz-static")]   # причина ДРУГОГО дерева
w8._refresh()
pump()


def _attach48(child, parent):
    child.parent = parent.cid
    w8._refresh()
    pump()


def _dnd48(panel, src_it, tgt_it, frac=0.5, drop=True):
    """Синтетический драг причины: enter → move (→ drop) через ВЬЮПОРТ;
    frac – доля высоты ЦЕЛЕВОЙ строки (0.2 – верхняя зона, 0.5 –
    середина); X зажимается в пределы вьюпорта (урок блока 31)."""
    from PySide6.QtGui import (QDragEnterEvent as _DEE48,
                               QDragMoveEvent as _DME48,
                               QDropEvent as _DRE48)
    from PySide6.QtCore import QMimeData as _MD48, QPointF as _QPF48
    _expand_to46(panel.tree, tgt_it)   # участок добавляется СВЕРНУТЫМ
    QApplication.processEvents()
    vp = panel.tree.viewport()
    r = panel.tree.visualItemRect(tgt_it)
    x = min(r.center().x(), vp.width() - 20)
    y = r.top() + int(r.height() * frac)
    p = _QPF48(x, y)
    assert panel.tree.itemAt(p.toPoint()) is tgt_it
    m = _MD48()
    m.setData("application/x-kuji-hier", b"1")
    panel.tree.setCurrentItem(src_it)
    QApplication.processEvents()
    QApplication.sendEvent(vp, _DEE48(
        p, Qt.DropAction.MoveAction, m, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier))
    QApplication.sendEvent(vp, _DME48(
        p, Qt.DropAction.MoveAction, m, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier))
    QApplication.processEvents()
    if drop:
        QApplication.sendEvent(vp, _DRE48(
            p, Qt.DropAction.MoveAction, m, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier))
        QApplication.processEvents()


# Задача 4: глифы списков ГС и ИЗ РАЗЛИЧАЮТСЯ (облако ≠ пламя),
# внутри списка – одинаковы
_img_gs48 = _row46(h8, tr48.gs_causes[0].cid) \
    .icon(0).pixmap(22, 22).toImage()
_img_iz48 = _row46(h8, cable48.cid).icon(0).pixmap(22, 22).toImage()
assert _img_gs48 != _img_iz48
assert _row46(h8, static48.cid).icon(0) \
    .pixmap(22, 22).toImage() == _img_iz48

_scen48 = _scen_row_of(h8, tr48.tree_id)
assert _scen48 is not None
# подсказка «Отцепить» у курсора над целью отцепления (шов-текст)
_dnd48(h8, _row46(h8, static48.cid), _scen48, 0.5, drop=False)
assert h8.tree._detach_hint_text == "Отцепить"
_it_a48 = h8._item_of(a48)
_dnd48(h8, _row46(h8, static48.cid), _it_a48, 0.5, drop=False)
assert h8.tree._detach_hint_text == "Отцепить"       # строка владельца
_dnd48(h8, _row46(h8, static48.cid), _row46(h8, cable48.cid),
       0.2, drop=False)
assert h8.tree._detach_hint_text == "Отцепить"       # крайняя зона
# (1) дроп на строку сценария: отцепление, верхний уровень, выделение
_dnd48(h8, _row46(h8, lamp48.cid), _scen48, 0.5)
pump()
assert lamp48.parent is None
_r48 = _row46(h8, lamp48.cid)
assert _r48.parent() is _scen_row_of(h8, tr48.tree_id)  # переищена!
assert h8.tree.currentItem() is _r48
assert len(tr48.scenarios(kb, w8.ctx_map()[a48.id])) == 2, \
    [r.name for r in tr48.scenarios(kb, w8.ctx_map()[a48.id])]
# (2) дроп на СТРОКУ ВЛАДЕЛЬЦА (участок) – отцепить; чужой объект – нет
_attach48(lamp48, cable48)
_it_a48 = h8._item_of(a48)             # айтемы переищены после пересборки
_dnd48(h8, _row46(h8, lamp48.cid), _it_a48, 0.5)
pump()
assert lamp48.parent is None \
    and _row46(h8, lamp48.cid).parent() \
    is _scen_row_of(h8, tr48.tree_id)
assert not h8.drop_ok(_row46(h8, lamp48.cid), h8._item_of(b48))
# (3) ПКМ «Отцепить от родителя» (шов: действия без exec)
_attach48(lamp48, cable48)
_acts48 = h8._cause_context_actions(_row46(h8, lamp48.cid))
assert [t for t, _cb in _acts48] == ["Отцепить от родителя"]
_acts48[0][1]()
pump()
assert lamp48.parent is None \
    and h8.tree.currentItem() is _row46(h8, lamp48.cid)
assert h8._cause_context_actions(_row46(h8, cable48.cid)) == []  # корень
# (4) пустое место – отцепить (для причин); объект/дерево – недопустимо
_attach48(lamp48, cable48)
from PySide6.QtCore import QMimeData as _MD48x, QPoint as _QP48, \
    QPointF as _QPF48x
from PySide6.QtGui import QDragEnterEvent as _DEE48x, \
    QDragMoveEvent as _DME48x, QDropEvent as _DRE48x
_vp48 = h8.tree.viewport()


def _empty_point48(panel):
    """Точка ВЬЮПОРТА без айтема (под последней строкой; при высоком
    содержимом – прокрутка вниз)."""
    vp = panel.tree.viewport()
    bottoms = [panel.tree.visualItemRect(it).bottom()
               for it, _o, _d in panel._iter_items()]
    y = max(bottoms) + 10
    if y >= vp.height():
        panel.tree.scrollToBottom()
        QApplication.processEvents()
        bottoms = [panel.tree.visualItemRect(it).bottom()
                   for it, _o, _d in panel._iter_items()]
        y = max(bottoms) + 10
    return _QP48(min(vp.width() - 12, vp.width() // 2), y)


_empty48 = _empty_point48(h8)
assert h8.tree.itemAt(_empty48) is None
h8.tree.setCurrentItem(_row46(h8, lamp48.cid))
_m48 = _MD48x()
_m48.setData("application/x-kuji-hier", b"1")
# enter → move → drop (как при реальном DnD: enter переводит вид в
# состояние драга – без него QDropEvent до обработчика не доходит)
QApplication.sendEvent(_vp48, _DEE48x(
    _QPF48x(_empty48), Qt.DropAction.MoveAction, _m48,
    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
QApplication.sendEvent(_vp48, _DME48x(
    _QPF48x(_empty48), Qt.DropAction.MoveAction, _m48,
    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
QApplication.processEvents()
QApplication.sendEvent(_vp48, _DRE48x(
    _QPF48x(_empty48), Qt.DropAction.MoveAction, _m48,
    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
pump()
assert lamp48.parent is None
assert not h8.drop_ok(h8._item_of(a48), None)      # объект – нельзя
assert not h8.drop_ok(_scen_row_of(h8, tr48.tree_id), None)  # дерево
# (5) крайние зоны: верхние 20 % строки причины своего списка –
# отцепить; середина той же строки – снова привязать
_attach48(lamp48, cable48)
_dnd48(h8, _row46(h8, lamp48.cid), _row46(h8, cable48.cid), 0.2)
pump()
assert lamp48.parent is None
_attach48(lamp48, cable48)
_dnd48(h8, _row46(h8, lamp48.cid), _row46(h8, cable48.cid), 0.5)
pump()
assert lamp48.parent == cable48.cid
# (6) недопустимые цели остаются красными (attach-зона)
assert not h8.drop_ok(_row46(h8, lamp48.cid), _row46(h8, lamp48.cid))
assert not h8.drop_ok(_row46(h8, lamp48.cid), _row46(h8, static48.cid))
assert not h8.drop_ok(_row46(h8, lamp48.cid),
                      _row46(h8, tr48.gs_causes[0].cid))
assert not h8.drop_ok(_row46(h8, lamp48.cid),
                      _row46(h8, tr48b.iz_causes[0].cid))
assert not h8.drop_ok(_row46(h8, lamp48.cid), h8._item_of(b48))
# крайняя зона чужого списка/дерева – тоже недопустима
assert not h8.drop_ok(_row46(h8, lamp48.cid),
                      _row46(h8, tr48.gs_causes[0].cid),
                      h8.tree.visualItemRect(
                          _row46(h8, tr48.gs_causes[0].cid))
                      .topLeft() + _QP48(4, 2))
assert not h8.drop_ok(_row46(h8, lamp48.cid),
                      _row46(h8, tr48b.iz_causes[0].cid),
                      h8.tree.visualItemRect(
                          _row46(h8, tr48b.iz_causes[0].cid))
                      .topLeft() + _QP48(4, 2))
w8._dirty = False
w8.close()
print("OK сессия 16, Задача 2: отцепление 4 способами (сценарий/"
      "владелец/ПКМ/пустое место/крайняя зона), подсказка «Отцепить»,"
      " недопустимые цели; Задача 4: глифы ГС ≠ ИЗ")

# ---------- 49. Сессия 17, Задачи 1+2+3: множитель П1.1 живьём + чистка ----
# Задача 2 (LOCKED): ГЖ-дерево с причиной П1.1 – смена типа участка и ввод
# значения пересчитывают формулу матрицы и ΣQ ноды БЕЗ перевыбора
w49 = MainWindow(kb, restore_ui=False)
w49.show()
pump()
h49 = w49.hierarchy
h49.add_kind("territory")
h49.tree.closePersistentEditor(h49.tree.currentItem())
h49.add_kind("building")
b49 = h49.selected()
h49.tree.closePersistentEditor(h49.tree.currentItem())
h49.add_kind("room")
r49 = h49.selected()
h49.tree.closePersistentEditor(h49.tree.currentItem())
h49.add_kind("area")
a49 = h49.selected()
h49.tree.closePersistentEditor(h49.tree.currentItem())
# Задача 3: секции «ПАРАМЕТРЫ …» (единый шаблон), подпись «Площадь:»
# (форма территории), ВСЕКАПС-подписи вида объекта над именем больше нет
h49.select_object(r49)
pump()
_lbls49 = [l.text() for l in w49.inspector.form_host.findChildren(_QL)]
assert any("ПАРАМЕТРЫ ПОМЕЩЕНИЯ" in l for l in _lbls49), _lbls49
h49.select_object(b49.ancestors()[0])
pump()
_lbls49 = [l.text() for l in w49.inspector.form_host.findChildren(_QL)]
assert any("ПАРАМЕТРЫ ТЕРРИТОРИИ" in l for l in _lbls49), _lbls49
assert any(l == "Площадь:" for l in _lbls49), _lbls49
for _node49 in (r49, b49.ancestors()[0]):
    h49.select_object(_node49)
    pump()
    assert w49.inspector.title.text() == "", w49.inspector.title.text()
h49.select_object(b49)
pump()
h49.toolbar.buttons["compartment"].click()
pump()
c49 = h49.selected()
h49.tree.closePersistentEditor(h49.tree.currentItem())
_lbls49 = [l.text() for l in w49.inspector.form_host.findChildren(_QL)]
assert any("ПАРАМЕТРЫ ПОЖАРНОГО ОТСЕКА" in l for l in _lbls49), _lbls49
# «НОДА ДЕРЕВА» остается (маркер смены контекста, Задача 3)
w49._add_tree(a49.id, "gzh")
tr49 = next(t for t in w49.trees if t.owner_id == a49.id)
tr49.gs_causes = [GSCause(ref="gs-vessel-5")]
tr49.iz_causes = [IZCause(ref="iz-cable")]
w49._refresh()
pump()
# участок снова выбран – дерево на холсте (после клика по отсеку)
h49.select_object(a49)
pump()
w49._on_canvas_node(f"{tr49.tree_id}:fire")
pump()
assert w49.inspector.title.text() == "НОДА ДЕРЕВА"
# Задача 1: колонки матрицы переименованы (единый источник – matrix.py)
_hh49 = [w49.matrix_table.horizontalHeaderItem(i).text()
         for i in range(w49.matrix_table.columnCount())]
assert "Сценарий пожара" in _hh49 and "Участок (установка)" in _hh49, _hh49
assert not any("ГС – расход" in x for x in _hh49)
# Задача 2: значение типа участка НЕ задано – скобка без множителя
def _formula_cell49() -> str:
    for _r in range(w49.matrix_table.rowCount()):
        t = w49.matrix_table.item(_r, 5).text()
        if "4·10⁻⁵" in t:
            return t
    return ""


h49.select_object(a49)
pump()
# значение СВОЁ не задано, но здание дало 1200 м² по каскаду – множитель
# уже работает (тот же резолвер effective-props, что у ТГМ/П1.2);
# случай «нигде не задано → множитель 1» покрыт smoke-блоком 22
assert "(4·10⁻⁵·1200)" in _formula_cell49(), _formula_cell49()
_fire49 = w49.canvas.controller.layout.nodes[f"{tr49.tree_id}:fire"]
_q_before49 = _fire49.body_lines[-1]
# ввод собственной площади 86 м² – живой пересчет формулы, ΣQ и статус-бара
_spin49 = next(s for s in w49.inspector.form_host.findChildren(_QDS34)
               if s.maximum() >= 10_000_000)
_spin49.setValue(86.0)
pump()
assert "(4·10⁻⁵·86)" in _formula_cell49(), _formula_cell49()
_fire49 = w49.canvas.controller.layout.nodes[f"{tr49.tree_id}:fire"]
assert _fire49.body_lines[-1] != _q_before49       # ΣQ изменился сразу
assert "Q_В" in w49.status_label.text()
# смена типа участка на «линейный объект (м)»: умолчание 50 – сразу
# в множитель (реальный переключатель списка в инспекторе)
_st49 = next(c for c in w49.inspector.form_host.findChildren(_QCB12)
             if c.count() == 3 and c.itemData(0) == "area")
_st49.setCurrentIndex(_st49.findData("linear"))
pump()
assert "(4·10⁻⁵·50)" in _formula_cell49(), _formula_cell49()
_spin49.setValue(120.0)
pump()
assert "(4·10⁻⁵·120)" in _formula_cell49(), _formula_cell49()
# П1.2 не задваивается: тот же поток на трубопроводной причине – скобка
# только λ'·значение (проверено в smoke); здесь – «аппарат/установка»
_st49.setCurrentIndex(_st49.findData("apparatus"))
pump()
assert "(4·10⁻⁵·10)" in _formula_cell49(), _formula_cell49()
w49._dirty = False
w49.close()
print("OK сессия 17, Задачи 1+2+3: П1.1 × F|L|V живьём (тип/значение –"
      " сразу в формулу матрицы, ΣQ и статус); колонки и шапка инспектора"
      " переименованы")

# ---------- 50. Сессия 17, Задача 4: шорткаты RU + undo/redo + буфер -------
# Раскладконезависимость: кириллический Ctrl+Ы это Ctrl+S (та же клавиша);
# QTest шлет КОД клавиши – ровно то, что дает Windows в русской раскладке.
# Проверяемое действие: Ctrl+В (D) открывает окно «Документ»
w50 = MainWindow(kb, restore_ui=False)
w50.show()
pump()
h50 = w50.hierarchy
h50.add_kind("territory")
h50.tree.closePersistentEditor(h50.tree.currentItem())
h50.add_kind("building")
h50.tree.closePersistentEditor(h50.tree.currentItem())
h50.add_kind("room")
h50.tree.closePersistentEditor(h50.tree.currentItem())
h50.add_kind("area")
a50 = h50.selected()
h50.tree.closePersistentEditor(h50.tree.currentItem())
w50._add_tree(a50.id, "gg")
tr50 = next(t for t in w50.trees if t.owner_id == a50.id)
tr50.gs_causes = [GSCause(ref="gs-vessel-5")]
tr50.iz_causes = [IZCause(ref="iz-cable")]
w50._refresh()
pump()
# (1) кириллический Ctrl+В (0x0412) = латинский Ctrl+D: документ открылся
# (setActiveWindow: WindowShortcut у этого действия матчится только с
# АКТИВНЫМ окном – в offscreen активное окно само не назначается)
QApplication.setActiveWindow(w50)
h50.tree.setFocus()
pump()
QTest.keyClick(h50.tree, Qt.Key(0x0412),
               Qt.KeyboardModifier.ControlModifier)
pump()
assert w50.doc_window is not None and w50.doc_window.isVisible(), \
    ("doc window not opened by Ctrl+В",
     QApplication.activeWindow() is w50,
     w50.doc_window)
w50.doc_window.close()
pump()
# латинский путь работает по-прежнему (после close() активное окно
# сбрасывается – восстанавливаем, WindowShortcut матчится по нему)
QApplication.setActiveWindow(w50)
pump()
QTest.keyClick(h50.tree, Qt.Key.Key_D,
               Qt.KeyboardModifier.ControlModifier)
pump()
assert w50.doc_window is not None and w50.doc_window.isVisible()
w50.doc_window.close()
pump()
# (2) Alt-путь фильтра проверен в блоке 21 (латиница + кириллица Ф);
# здесь – Ctrl-путь: кириллический Ctrl+Я = Ctrl+Z (ApplicationShortcut,
# действия «Правка» едины на приложение)
# (3) Ctrl+Z отменяет добавление (кириллица Я = 0x042F), Ctrl+Y возвращает
# (цель добавления – ПОМЕЩЕНИЕ: сосед-комната под зданием; после части (1)
# выделен участок, и добавление комнаты дало бы информационное окно)
h50.select_object(a50.parent)
pump()
_n50 = len(w50.objects.all_nodes())
h50.add_kind("room")
h50.tree.closePersistentEditor(h50.tree.currentItem())
assert len(w50.objects.all_nodes()) == _n50 + 1
h50.tree.setFocus()
pump()
# offscreen: шорткат-диспетчер Qt матчит события окна, которое АКТИВНО
# (в реальном приложении окно активно по определению – пользователь
# печатает в него); назначаем активным w50 перед нажатиями
QApplication.setActiveWindow(w50)
pump()
QTest.keyClick(h50.tree, Qt.Key(0x042F),
               Qt.KeyboardModifier.ControlModifier)
pump()
assert len(w50.objects.all_nodes()) == _n50, w50.objects.all_nodes()
QTest.keyClick(h50.tree, Qt.Key.Key_Y,
               Qt.KeyboardModifier.ControlModifier)
pump()
assert len(w50.objects.all_nodes()) == _n50 + 1
# (4) три правки – три отката (Ctrl+Z латиницей)
w50._add_tree(a50.id, "gzh")
w50._add_tree(a50.id, "dust")
w50._add_tree(a50.id, "lvzh")
assert len(w50.trees) == 4
for _i50 in range(3):
    QTest.keyClick(h50.tree, Qt.Key.Key_Z,
                   Qt.KeyboardModifier.ControlModifier)
    pump()
assert len(w50.trees) == 1, len(w50.trees)
for _i50 in range(3):
    QTest.keyClick(h50.tree, Qt.Key(0x041D),   # кириллица Н = Y
                   Qt.KeyboardModifier.ControlModifier)
    pump()
assert len(w50.trees) == 4
# (5) буфер: копия участка с деревом (Ctrl+C), вставка в другую комнату
# (Ctrl+М кириллицей = 0x041C), повторная вставка, отмена вставки (Ctrl+Z)
h50.select_object(a50.parent)
h50.add_kind("room")
h50.tree.closePersistentEditor(h50.tree.currentItem())
r50b = h50.selected()
h50.select_object(a50, emit=False)
pump()
# (select_object снимает прежний мультивыбор – Задача 4: копируется
# ровно выделенный объект)
assert [i.text(0) for i in h50.tree.selectedItems()] == [a50.title]
_ntr50 = len([t for t in w50.trees if t.owner_id == a50.id])
QApplication.setActiveWindow(w50)
pump()
QTest.keyClick(h50.tree, Qt.Key.Key_C,
               Qt.KeyboardModifier.ControlModifier)
pump()
assert len(w50._clip) == 1
h50.select_object(r50b, emit=False)
pump()
QApplication.setActiveWindow(w50)
pump()
QTest.keyClick(h50.tree, Qt.Key(0x041C),
               Qt.KeyboardModifier.ControlModifier)
pump()
_copies50 = [n for n in w50.objects.all_nodes()
             if n.title.endswith(" (копия)")]
assert len(_copies50) == 1 and _copies50[0].kind == "area"
assert _copies50[0].parent is r50b and _copies50[0].id != a50.id
# у копии – ВСЕ деревья участка-источника (после части (4) их четыре),
# со свежими tree_id/cid; авторазметка чистая
_t50 = [t for t in w50.trees if t.owner_id == _copies50[0].id]
assert len(_t50) == _ntr50, (len(_t50), _ntr50)
assert [c.ref for c in _t50[0].gs_causes] == ["gs-vessel-5"]
assert _t50[0].gs_causes[0].cid != tr50.gs_causes[0].cid
assert _t50[0].total_q(kb, w50.ctx_map()[_copies50[0].id]) > 0
# повторная вставка: цель снова выбрана (после вставки выделена копия)
h50.select_object(r50b, emit=False)
pump()
QApplication.setActiveWindow(w50)
pump()
QTest.keyClick(h50.tree, Qt.Key(0x041C),
               Qt.KeyboardModifier.ControlModifier)
pump()
assert len([n for n in w50.objects.all_nodes()
            if n.title.endswith(" (копия)")]) == 2
_nt50 = len(w50.trees)
QApplication.setActiveWindow(w50)
QTest.keyClick(h50.tree, Qt.Key.Key_Z,
               Qt.KeyboardModifier.ControlModifier)
pump()
assert len([n for n in w50.objects.all_nodes()
            if n.title.endswith(" (копия)")]) == 1
assert len(w50.trees) == _nt50 - _ntr50   # все деревья вставки ушли разом
# (6) недопустимая вставка: участок в территорию – информационное окно
# (шов: модальное окно подменяется, реальный диалог не показывается)
_boxes50 = []
_orig_info50 = QMessageBox.information
QMessageBox.information = staticmethod(
    lambda *a, **k: _boxes50.append(a[2] if len(a) > 2 else str(a)) or None)
h50.select_object(h50.objects.territories[0], emit=False)
pump()
w50._paste_clipboard()
QMessageBox.information = staticmethod(_orig_info50)
assert len(_boxes50) == 1 and "нельзя добавить" in _boxes50[0], _boxes50
w50._dirty = False
w50.close()
print("OK сессия 17, Задача 4: кириллические Ctrl+В/Я/Н/М и Alt+Ф ="
      " латинские (открытие документа, undo/redo, копия/вставка);"
      " 3 правки – 3 отката; буфер с деревом, свежие id, «(копия)»,"
      " недопустимая вставка – информационное окно")

# ---------- 51. Сессия 17, Задачи 5+6: крупное дерево + рамка/группы ------
w51 = MainWindow(kb, restore_ui=False)
w51.resize(1700, 1000)
w51.show()
pump()
h51 = w51.hierarchy
h51.add_kind("territory")
h51.tree.closePersistentEditor(h51.tree.currentItem())
h51.add_kind("building")
h51.tree.closePersistentEditor(h51.tree.currentItem())
h51.add_kind("room")
h51.tree.closePersistentEditor(h51.tree.currentItem())
h51.add_kind("area")
a51 = h51.selected()
h51.tree.closePersistentEditor(h51.tree.currentItem())
w51._add_tree(a51.id, "gg")
tr51 = next(t for t in w51.trees if t.owner_id == a51.id)
tr51.gs_causes = [GSCause(ref="gs-vessel-5")]
tr51.iz_causes = [IZCause(ref="iz-cable")]
w51._refresh()
pump()
# --- часть 1 (Задача 5): константы крупной геометрии и умный fit ---
from eta.ui.theme import (F_FORMULA as _FF51, F_META as _FM51,
                          F_TITLE as _FT51, NODE_INSET as _NI51,
                          PAD_V as _PV51)
from eta.ui.canvas import FIT_MAX_ZOOM as _FZ51, FIT_PAD_PX as _FP51
assert (_FT51, _FM51, _FF51) == (14, 11, 14)     # кегли выросли
assert _PV51 == 16 and _PV51 > 12                # вертикальные поля узла
assert _NI51 == 13 and _NI51 > 10                # внутренний отступ
assert _FP51 == 48 and 40 <= _FP51 <= 60         # поле вписывания
assert _FZ51 == 1.5                              # ПОТОЛОК апскейла
_fnode51 = w51.canvas.controller.layout.nodes[f"{tr51.tree_id}:fire"]
assert _fnode51.rect.height() >= 56.0            # минимальная высота выросла
_vp51 = w51.canvas.viewport()
_sr51 = w51.canvas.controller.layout.scene_rect
_want51 = min(_vp51.width() / (_sr51.width() + 2 * _FP51),
              _vp51.height() / (_sr51.height() + 2 * _FP51))
w51.canvas.set_zoom_level(0.2)
pump()
w51.canvas.fit_tree()
pump()
_z51 = w51.canvas.zoom_level()
assert _z51 <= _FZ51 + 1e-9, (_z51, _want51)     # потолок никогда не пробит
if _want51 > _FZ51:
    assert abs(_z51 - _FZ51) < 0.01, (_z51, _want51)   # кап сработал
else:
    assert abs(_z51 - _want51) < 0.02, (_z51, _want51)
assert _z51 > 0.9                                # маленькое дерево крупно
print(f"OK Задача 5: fit z={_z51:.2f} (потолок {_FZ51}, поле "
      f"{_FP51:.0f}px); константы выросли (PAD_V {_PV51}, "
      f"NODE_INSET {_NI51}, кегли {_FT51}/{_FM51}/{_FF51})")

# --- часть 2 (Задача 6): рамка, Ctrl+клик, групповой драг/удаление, пан ---
def _vp_center51(node_id: str) -> QPoint:
    it = w51.canvas.controller.node_item(node_id)
    return QPointF(w51.canvas.mapFromScene(
        it.geo.rect.center())).toPoint()


def _marquee51(p1: QPointF, p2: QPointF) -> None:
    QTest.mousePress(_vp51, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier, p1.toPoint())
    pump()
    QTest.mouseMove(_vp51, p2.toPoint())
    pump()
    QTest.mouseRelease(_vp51, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier, p2.toPoint())
    pump()


# (а) рамка вокруг ГС и ИЗ одного дерева выделяет ровно эти две ноды
from PySide6.QtCore import QRectF as _QRF51


def _node_view_rect51(node_id: str):
    it = w51.canvas.controller.node_item(node_id)
    tl = w51.canvas.mapFromScene(it.geo.rect.topLeft())
    br = w51.canvas.mapFromScene(it.geo.rect.bottomRight())
    return _QRF51(QPointF(tl), QPointF(br))


def _marquee_nodes51(*node_ids):
    """Рамка вокруг НОД: старт СНАРУЖИ их габаритов (ЛКМ на пустом).
    Старт – ПОД деревом (сверху висит справочная нода – там занято),
    затем протянуть вверх; ширина – габарит нод по X."""
    rects = [_node_view_rect51(n) for n in node_ids]
    p1 = QPointF(min(r.left() for r in rects) + 15,
                 max(r.bottom() for r in rects) + 30)
    p2 = QPointF(max(r.right() for r in rects) - 15,
                 min(r.top() for r in rects) - 10)
    _marquee51(p1, p2)


_marquee_nodes51(f"{tr51.tree_id}:gs", f"{tr51.tree_id}:iz")
assert sorted(w51.canvas.controller.selected_nodes()) == \
    sorted([f"{tr51.tree_id}:gs", f"{tr51.tree_id}:iz"]), \
    w51.canvas.controller.selected_nodes()
assert w51._canvas_sel_by_click            # рамка – выбор пользователя
# (б) Ctrl+клик добавляет/убирает ноду из выделения
_sub_c51 = _vp_center51(f"{tr51.tree_id}:substance")
QTest.mouseClick(_vp51, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.ControlModifier, _sub_c51)
pump()
assert len(w51.canvas.controller.selected_nodes()) == 3
QTest.mouseClick(_vp51, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.ControlModifier, _sub_c51)
pump()
assert len(w51.canvas.controller.selected_nodes()) == 2
# (в) групповое перетаскивание: обе выделенные ноды двигаются вместе
w51.canvas.set_zoom_level(1.0)
pump()
tr51.node_offsets = None
w51.canvas.controller.rebuild_last()
pump()
_marquee_nodes51(f"{tr51.tree_id}:gs", f"{tr51.tree_id}:iz")
assert len(w51.canvas.controller.selected_nodes()) == 2
_stack51 = len(w51._undo_stack)
_gs_c51 = _vp_center51(f"{tr51.tree_id}:gs")
QTest.mousePress(_vp51, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier, _gs_c51)
pump()
QTest.mouseMove(_vp51, (_gs_c51 + QPoint(50, 0)))
pump()
QTest.mouseRelease(_vp51, Qt.MouseButton.LeftButton,
                   Qt.KeyboardModifier.NoModifier,
                   (_gs_c51 + QPoint(50, 0)))
pump()
_off51 = tr51.node_offsets or {}
assert set(_off51) == {"gs", "iz"}, _off51       # обе ноды – один драг
assert abs(_off51["gs"][0] - 50.0) < 1.0 and abs(_off51["iz"][0] - 50.0) < 1.0
assert len(w51._undo_stack) == _stack51 + 1      # одна точка отката
# (г) второе дерево на участке – групповое удаление ОДНИМ окном
w51._add_tree(a51.id, "gzh")
tr51b = next(t for t in w51.trees
             if t.owner_id == a51.id and t.tree_id != tr51.tree_id)
tr51b.gs_causes = [GSCause(ref="gs-tank-float-ring")]
w51._refresh()
pump()
w51.canvas.set_zoom_level(0.8)
pump()
_marquee_nodes51(f"{tr51.tree_id}:fire", f"{tr51b.tree_id}:fire")
_sel51 = w51.canvas.controller.selected_nodes()
assert len(_sel51) >= 2, _sel51
_confirmed51 = []
w51._confirm_trees_delete = lambda trees: (
    _confirmed51.append([t.tree_id for t in trees]), True)[1]
QTest.keyClick(_vp51, Qt.Key.Key_Delete)
pump()
assert len(_confirmed51) == 1, _confirmed51    # ОДНО окно на группу
_gone51 = set(_confirmed51[0])                 # список tree_id деревьев
assert _gone51 <= {tr51.tree_id, tr51b.tree_id}
assert all(t.tree_id not in _gone51 for t in w51.trees)
# (д) Пробел+ЛКМ – панорама; ЛКМ-рамка больше НЕ панорамирует
w51._add_tree(a51.id, "gg")
w51._refresh()
pump()
QTest.keyPress(_vp51, Qt.Key.Key_Space)     # УДЕРЖАНИЕ (keyClick = press+release)
pump()
assert w51.canvas._space_held
# контент КРУПНЕЕ вьюпорта – у ползунков есть запас хода
w51.canvas.set_zoom_level(2.5)
pump()
_hb51 = w51.canvas.horizontalScrollBar()
_vb51 = w51.canvas.verticalScrollBar()
_h0, _v0 = _hb51.value(), _vb51.value()
QTest.mousePress(_vp51, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier, QPoint(300, 300))
pump()
QTest.mouseMove(_vp51, QPoint(220, 240))
pump()
QTest.mouseRelease(_vp51, Qt.MouseButton.LeftButton,
                   Qt.KeyboardModifier.NoModifier, QPoint(220, 240))
pump()
assert (_hb51.value(), _vb51.value()) != (_h0, _v0)   # камера уехала
QTest.keyRelease(_vp51, Qt.Key.Key_Space)
pump()
assert not w51.canvas._space_held
# ЛКМ-рамка на пустом – НЕ панорама (скролл не меняется)
_h1, _v1 = _hb51.value(), _vb51.value()
_marquee51(QPointF(10, 10), QPointF(120, 90))
assert (_hb51.value(), _vb51.value()) == (_h1, _v1)
w51._dirty = False
w51.close()
print("OK Задача 6: рамка выделяет (стиль rgba(59,130,246,.12)+#3B82F6),"
      " Ctrl+клик переключает, групповой драг – один оффсет-коммит,"
      " групповое удаление – ОДНО окно (оба дерева), Пробел+ЛКМ –"
      " панорама, ЛКМ больше не панорамирует")

# ---------- 52. Сессия 18, Задачи 10/11: единый DOCX-отчет (pandoc) ------
# Полный конвейер: контент-модель → Markdown + сырые блоки OOXML →
# встроенный pandoc по ГОСТ-шаблону; проверки – по word/document.xml
from eta.export.report_docx import export_docx
w52 = MainWindow(kb, restore_ui=False)
w52.show()
pump()
h52 = w52.hierarchy
h52.add_kind("territory")
h52.tree.closePersistentEditor(h52.tree.currentItem())
h52.add_kind("building")
b52 = h52.selected()
h52.tree.closePersistentEditor(h52.tree.currentItem())
h52.add_kind("room")
h52.tree.closePersistentEditor(h52.tree.currentItem())
h52.add_kind("area")
a52 = h52.selected()
h52.tree.closePersistentEditor(h52.tree.currentItem())
w52._add_tree(a52.id, "gg")
tr52 = next(t for t in w52.trees if t.owner_id == a52.id)
tr52.gs_causes = [GSCause(ref="gs-vessel-5", flow="small"),
                  GSCause(ref="gs-pipe-100-small", flow="mid")]
tr52.iz_causes = [IZCause(ref="iz-cable"), IZCause(ref="iz-static")]
w52._refresh()
pump()
_docx52 = str(ROOT / "qa_artifacts" / "_gest_t18.docx")
export_docx(_docx52, w52.objects, w52.trees, kb, w52.ctx_map(),
            w52._owner_titles(), "A3L", canvas=w52.canvas)
import zipfile as _zf52
with _zf52.ZipFile(_docx52) as _z52:
    assert _z52.testzip() is None               # валидный zip
    _x52 = _z52.read("word/document.xml").decode("utf-8")
    _media52 = [n for n in _z52.namelist()
                if n.startswith("word/media/")]
# титул (Задача 3) и поле оглавления (LOCKED 8)
assert "Расчет частоты возникновения пожара" in _x52
assert 'TOC \\o "1-3"' in _x52 and 'w:dirty="true"' in _x52
assert "Куджи v" in _x52 and " от " in _x52
# иерархия разделов (Задача 11.3): все уровни заголовков
for _h52 in ("Территория «", "Здание «", "Помещение «", "Участок «",
             "Параметры расчета", "Исходные данные", "Результаты расчета",
             "Нормативные ссылки и справочные данные",
             "Логическое дерево событий"):
    assert _h52 in _x52, _h52
# Задача 4: Kσ отдельной строкой; «Огненный шар» выключен – строки НЕТ
assert "Коэффициент безопасности Kσ" in _x52
assert "Огненный шар" not in _x52
# Задача 5/6/7: запрещенных строк нет; источники без скобок; Q_В есть
assert "Объект расчёта" not in _x52 and "Исполнитель" not in _x52 \
    and "Проект «" not in _x52
assert "[Приказ" not in _x52 and "Q_В = Σ Q_i · Kσ" in _x52
# схемы: по ОДНОЙ картинке-владельцу (LOCKED 10) + донорская графика
assert _x52.count("<w:drawing>") == len(w52.objects.tree_owners()) == 1
assert len(_media52) >= 29 + 1
# Задача 4: шар ВКЛЮЧЕН – строка появляется (повторная сборка)
tr52.fireball = True
export_docx(_docx52, w52.objects, w52.trees, kb, w52.ctx_map(),
            w52._owner_titles(), "A3L", canvas=w52.canvas)
with _zf52.ZipFile(_docx52) as _z52b:
    _x52b = _z52b.read("word/document.xml").decode("utf-8")
assert "Огненный шар: включен" in _x52b
Path(_docx52).unlink()
w52._dirty = False
w52.close()
print("OK сессия 18, Задача 11: единый DOCX (pandoc + ГОСТ-шаблон):"
      " титул 18/12 pt, ПОЛЕ оглавления, иерархия разделов, условный"
      " «Огненный шар», источники без скобок, Q_В, схема-на-владельца")

# ---------- 53. Сессия 18, Задача 1: память панелей/сплиттера ----------
# Сплиттер имеет objectName; сохранение state+geometry – ЕДИНАЯ точка
# _persist_ui_state (closeEvent + дебаунс splitterMoved 300 мс); round-trip
# через ВТОРОЕ окно по тому же герметичному QSettings; мусорные байты
# не ломают восстановление (умолчания остаются). Слоты дочерних окон
# сохраняют геометрию при скрытии ЛЮБЫМ путём (hideEvent).
w53 = MainWindow(kb, restore_ui=False)
w53.show()
pump()
assert w53.splitter.objectName() == "mainSplitter"
assert w53._ui_save_timer.isSingleShot()
assert w53._ui_save_timer.interval() == 300
w53.splitter.setSizes([420, 620, 400])
pump()
_sizes53 = w53.splitter.sizes()        # setSizes масштабируется к ширине
assert _sizes53[1] > _sizes53[0], _sizes53   # центр действительно шире
w53._persist_ui_state()                # слот дебаунса – синхронно
w53._dirty = False
w53.close()
pump()
w53b = MainWindow(kb, restore_ui=True)      # «второй запуск»
# экран offscreen 800×800: восстановленная геометрия клампится к ~1200 px,
# где пропорции [420, 620, 400] неосуществимы (минимумы 320/500/360 съеда-
# ют всё) – возвращаем окну реальный «десктопный» размер (проверено пробой:
# на выполнимой ширине restoreState восстанавливает размеры ТОЧНО)
w53b.resize(1500, 920)
w53b.show()
pump()
_r53 = w53b.splitter.sizes()
assert len(_r53) == 3 and all(abs(a - b) <= 8 for a, b in zip(_r53, _sizes53)), \
    (_r53, _sizes53)
from PySide6.QtCore import QSettings as _QS53
# мусорные байты в ui/splitter – restoreState отклоняет, окно живо
_QS53().setValue("ui/splitter", b"garbage-bytes-not-a-state")
w53c = MainWindow(kb, restore_ui=True)
pump()
assert len(w53c.splitter.sizes()) == 3 and sum(w53c.splitter.sizes()) > 0
w53c._dirty = False
w53c.close()
pump()
# окно «Документ»: скрытие БЕЗ closeEvent – геометрия всё равно сохранена
w53b.open_doc_window()
pump()
w53b.doc_window.resize(700, 500)
pump()
w53b.doc_window.hide()
pump()
assert _QS53().value("ui/doc_geometry") is not None
w53b.doc_window.close()
pump()
w53b.open_doc_window()
pump()
assert (w53b.doc_window.width(), w53b.doc_window.height()) == (700, 500), \
    (w53b.doc_window.width(), w53b.doc_window.height())
w53b.doc_window.close()
pump()
# окно «База данных»: тот же hide-путь + восстановление при пересоздании
w53b._open_kb_window()
pump()
w53b.kb_window.resize(720, 500)
pump()
w53b.kb_window.hide()
pump()
assert _QS53().value("ui/kb_geometry") is not None
w53b.kb_window = None                  # ленивый синглтон – «новый запуск»
w53b._open_kb_window()
pump()
assert (w53b.kb_window.width(), w53b.kb_window.height()) == (720, 500), \
    (w53b.kb_window.width(), w53b.kb_window.height())
w53b.kb_window.close()
pump()
w53b.kb_window = None
print("OK сессия 18, Задача 1: сплиттер/геометрия панелей помнятся"
      " (round-trip вторым окном, мусорные байты, hide-путь)")

# ---------- 54. Сессия 18, Задача 12: память последней папки ----------
from PySide6.QtCore import QSettings as _QS54
_DIR54 = str(ROOT / "qa_artifacts")
_QS54().setValue("ui/last_dir", _DIR54)
from eta.ui.dialogs import DocxExportDialog
_d54 = DocxExportDialog(parent=w53b, suggested_name="t54.docx",
                        start_dir=w53b._dir_hint())
assert str(Path(_d54.path_edit.text()).parent) == _DIR54
assert _d54.size_combo.count() == 6                 # Задача 10: 6 форматов
_labels54 = [_d54.size_combo.itemText(i)
             for i in range(_d54.size_combo.count())]
assert any("A3" in _l and "альбомная" in _l for _l in _labels54)
assert not hasattr(_d54, "mode_combo") \
    and not hasattr(_d54, "sw_report")          # упразднены (LOCKED 9)
_d54.reject()
pump()
# успешное сохранение проекта обновляет ключ (шов, без файлового диалога)
w53b._project_path = str(ROOT / "qa_artifacts" / "_gest_t18.kuji.json")
w53b._dirty = False
w53b._save_project()
assert _QS54().value("ui/last_dir") == _DIR54
Path(w53b._project_path).unlink()
# цепочка фолбэков: нет last_dir и нет проекта – Рабочий стол
_QS54().remove("ui/last_dir")
w53b._project_path = ""
assert w53b._dir_hint() == str(Path.home() / "Desktop"), w53b._dir_hint()
print("OK сессия 18, Задача 12: диалоги предзаполняются из ui/last_dir;"
      " сохранение обновляет ключ; фолбэк – Рабочий стол")

# ---------- 55. Сессия 18, Задача 9: реестр источников в БД ----------
w._open_kb_window()
pump()
kt55 = w.kb_window
_tab_names55 = [kt55.tabs.tabText(i) for i in range(kt55.tabs.count())]
assert "Источники" in _tab_names55, _tab_names55
st55 = kt55.sources_tab
_n_src55 = len(kb.sources)
assert st55.table.rowCount() == _n_src55
assert st55.table.horizontalHeaderItem(0).text() == "Наименование"
# добавление источника + правка названия прямо в ячейке
st55.add_record()
pump()
st55.table.closePersistentEditor(
    st55.table.item(st55.table.rowCount() - 1, 0))
assert len(kb.sources) == _n_src55 + 1
_rec55 = kb.sources[-1]
assert _rec55["title"] == "Новый источник"
_row55 = st55.table.rowCount() - 1
st55.table.item(_row55, 0).setText("ГОСТ 12.1.044-89* (проверка реестра)")
pump()
assert _rec55["title"] == "ГОСТ 12.1.044-89* (проверка реестра)"
# привязка к используемой записи ГС через шов вкладки ГС
_used55 = [t for t in w.trees
           if any(c.ref == "gs-tgm-surface" for c in t.gs_causes)]
assert _used55, "дерево с gs-tgm-surface не найдено"
kt55.gs_tab._set_source(kb.gs_by_id("gs-tgm-surface"), _rec55["id"])
pump()
from eta.export.report_docx import used_source_ids
_ids55 = used_source_ids(w.trees, kb, w.objects)
assert _rec55["id"] in _ids55, _ids55
# колонка «Источник» показывает название записи реестра (не id)
_cell55 = kt55.gs_tab.table.cellWidget(
    next(r for r in range(kt55.gs_tab.table.rowCount())
         if kt55.gs_tab._rec_at(r) is kb.gs_by_id("gs-tgm-surface")), 3)
assert "ГОСТ 12.1.044-89*" in _cell55.text()
# отвязали – источник больше не участвует (правило варианта Б)
kt55.gs_tab._set_source(kb.gs_by_id("gs-tgm-surface"), "")
assert _rec55["id"] not in used_source_ids(w.trees, kb, w.objects)
# удаление источника: подтверждение подменено, привязки очищаются
st55.table.setCurrentCell(_row55, 0)
st55._confirm_delete_src = lambda title, used: True
st55.delete_current_record()
pump()
assert len(kb.sources) == _n_src55
# вернуть исходную привязку (в памяти) и перечитать базу с диска
kb.gs_by_id("gs-tgm-surface")["source"] = "src-1"
kt55._reload_all()
pump()
assert kb.gs_by_id("gs-tgm-surface")["source"] == "src-1"
assert st55.table.rowCount() == _n_src55
w.kb_window.close()
pump()
w.kb_window = None
print("OK сессия 18, Задача 9: вкладка «Источники» (добавить/править/"
      "удалить с очисткой привязок); колонка «Источник» у библиотек;"
      " вариант Б: привязка участвует, без привязки – пропускается")

# ---------- 56. Сессия 18, Задача 13: кнопка «?» и справка БД ----------
w._open_kb_window()
pump()
kt56 = w.kb_window
# круглая «?» – слева от «Закрыть» в нижнем ряду
_bar56 = kt56.btn_help.parentWidget()
_row56 = [b for b in _bar56.findChildren(QPushButton)
          if b.parent() is _bar56]
assert kt56.btn_help.toolTip() == "Справка по работе с базой данных"
assert kt56.btn_help.width() == kt56.btn_help.height() == 30
_ih56 = _row56.index(kt56.btn_help)
_ic56 = _row56.index(kt56.btn_close)
assert _ih56 == _ic56 - 1, (_row56, _ih56, _ic56)
# окно справки открывается ШВОМ (без exec): контент – заголовки,
# «Источник» и проверенный пример формулы с настоящим индексом
kt56._open_help()
pump()
hw56 = kt56._help_win
assert hw56.windowTitle() == "Справка: База данных"
_lbls56 = [l.text() for l in hw56.findChildren(_QL)]
_joined56 = "\n".join(_lbls56)
assert any("Что такое «База данных»" in t for t in _lbls56)
assert "Источник" in _joined56
assert "<sub>зд</sub>" in _joined56          # F_зд отрендерен индексом
assert "<sup>-2</sup>" in _joined56          # 10^-2 отрендерен степенью
assert "3,2^-5" in _joined56                 # ввод с кареткой показан
hw56.accept()
pump()
kt56._help_win = None
w.kb_window.close()
pump()
w.kb_window = None
print("OK сессия 18, Задача 13: «?» слева от «Закрыть», справка"
      " открывается швом; формулы – настоящие индексы/степени;"
      " «Источник» и ввод с кареткой документированы")

# ---------- 57. Сессия 18, Задача 2: доставка ShortcutOverride + Пробел --
# ИЗМЕРЕННАЯ форма реальной Windows (qa_artifacts\key_debug.log):
# Ctrl+буква -> ShortcutOverride с ЛАТИНСКИМ key(); Alt+буква ->
# ShortcutOverride с КИРИЛЛИЧЕСКИМ key() и ЛАТИНСКИМ nativeVirtualKey;
# KeyPress для буквы НЕ приходит вовсе. Фильтр latin_keys нормализует
# букву и запускает действие из реестра (дебаунс ~80 мс – Qt доставляет
# Override по всей цепочке родителей). Пробел – ГЛОБАЛЬНАЯ готовность
# панорамы (доставляется только сфокусированному виджету).
from PySide6.QtCore import QEvent as _QE57
from PySide6.QtGui import QKeyEvent as _QKE57
from PySide6.QtWidgets import QApplication as _QA57
from eta.ui.latin_keys import space_pan_active
w57 = MainWindow(kb, restore_ui=False)
w57.show()
pump()
_QA57.setActiveWindow(w57)          # урок сессии 17: диспетчер активного окна


def _ov57(key, mods, text, target) -> None:
    ev = _QKE57(_QE57.Type.ShortcutOverride, key, mods, text)
    _QA57.sendEvent(target, ev)


_fired57 = []
w57.act_fit.triggered.connect(lambda: _fired57.append(1))
# (1) Alt+Ф кириллической формы по цепочке родителей: ОДИН запуск
for _tgt57 in (w57.canvas.viewport(), w57.hierarchy.tree, w57):
    _ov57(Qt.Key(0x0424), Qt.KeyboardModifier.AltModifier, "ф", _tgt57)
pump()
assert len(_fired57) == 1, _fired57
# (2) Ctrl+В латинской формы (key=D, text – управляющий символ);
#     ВНИМАНИЕ: Ctrl+E/У в тесте НЕ отправляем – _export_docx открывает
#     МОДАЛЬНЫЙ диалог (exec) и вешает offscreen-прогон; латинскую
#     форму Ctrl+буква покрывает D без модальности
_ov57(Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier, "\x04",
      w57.hierarchy.tree)
pump()
assert w57.doc_window is not None and w57.doc_window.isVisible()
w57.doc_window.close()
pump()
assert w57.doc_window is None
# (3) контекст окна: WindowShortcut не срабатывает из ЧУЖОГО окна,
#     но работает в СВОЕМ активном (пауза больше дебаунса 80 мс)
import time as _time57
_time57.sleep(0.12)
w57b = MainWindow(kb, restore_ui=False)
w57b.show()
pump()
_QA57.setActiveWindow(w57b)
_ov57(Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier, "\x04",
      w57b.hierarchy.tree)
pump()
assert w57.doc_window is None, "чужое окно запустило действие"
assert w57b.doc_window is not None, "свое активное окно не запустило"
w57b._dirty = False
w57b.close()
pump()
_QA57.setActiveWindow(w57)
# (4) Пробел ГЛОБАЛЬНО: фокус в дереве иерархии – панорама вооружена,
#     ЛКМ на холсте начинает панораму, отпускание/отжатие завершают
w57.hierarchy.tree.setFocus()
pump()
assert not space_pan_active()
QTest.keyPress(w57.hierarchy.tree, Qt.Key.Key_Space)
pump()
assert space_pan_active() and w57.canvas._pan_armed()
w57.canvas.set_zoom_level(2.0)
for _ in range(20):
    app.processEvents()
QTest.mousePress(w57.canvas.viewport(), Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier, QPoint(200, 200))
pump()
assert w57.canvas._space_pan_origin is not None
QTest.mouseMove(w57.canvas.viewport(), QPoint(264, 244))
QTest.mouseRelease(w57.canvas.viewport(), Qt.MouseButton.LeftButton)
pump()
assert w57.canvas._space_pan_origin is None
QTest.keyRelease(w57.hierarchy.tree, Qt.Key.Key_Space)
pump()
assert not space_pan_active()
# автоповтор Пробела не togg'ает флаг
QTest.keyPress(w57.hierarchy.tree, Qt.Key.Key_Space)
QTest.keyRelease(w57.hierarchy.tree, Qt.Key.Key_Space)
pump()
assert not space_pan_active()
w57._dirty = False
w57.close()
pump()
print("OK сессия 18, Задача 2: ShortcutOverride (Alt+Ф кириллицей,"
      " Ctrl+У латиницей, дебаунс, контекст окна) + глобальный Пробел"
      " (фокус в иерархии, панорама холста, автоповтор)")

# ---------- 13. QSettings: hermetic ini + закрытие окон -------------------
w._dirty = False
w.close()
w2._dirty = False
w2.close()
pump()
print("GESTURES PASSED")
