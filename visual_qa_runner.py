# -*- coding: utf-8 -*-
"""Headless Visual QA (сессии 10–12): сборка демо-проекта новой
парадигмы и снимки окон/холста/инспектора/КБ/PDF в qa_artifacts.

Запуск: run_qa.cmd (QT_QPA_PLATFORM=offscreen, встроенный Python).
Артефакты: qa_window, qa_canvas, qa_hierarchy (+ qa_hierarchy2 –
прокрутка вправо), qa_tooltip, qa_combo, qa_matrix, qa_docview,
qa_sheet, qa_switches, qa_inspector_fire, qa_inspector_building,
qa_kb_*, qa_pdf_*, qa_stats.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "qa_artifacts"
OUT.mkdir(exist_ok=True)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def build_demo(kb, win) -> None:
    """Демо-проект: здание со складом ТГМ + наружная газовая установка."""
    from eta.core.model import GSCause, IZCause
    h = win.hierarchy
    h.add_kind("territory")
    h.add_kind("building")
    bld = h.selected()
    bld.props.update({"area_m2": 2400.0, "p13_type": "p13-multi",
                      "p14_type": "p14-food", "bln_S": 60.0, "bln_L": 40.0,
                      "bln_H": 12.0})
    h.add_kind("room")
    h.add_kind("area")
    area = h.selected()
    area.props.update({"site_type": "area", "area_m2": 2400.0})
    win._add_tree(area.id, "tgm")
    tgm = next(t for t in win.trees if t.scenario_type == "tgm")
    tgm.gs_causes = [GSCause(ref="gs-tgm-surface")]
    tgm.iz_causes = [IZCause(ref=r) for r in
                     ("iz-lamp", "iz-cable", "iz-uzdo", "iz-human",
                      "iz-fork", "iz-spark")]
    # Задача 4 (сессия 13): справочная нода ТГМ-дерева привязана к ноде
    # «Возникновение» (следует за ней), у ГГ-дерева – свободная
    # (позиция по умолчанию над деревом)
    tgm.annotation = {"attached": "fire", "offset": [-110.0, -70.0]}
    # наружная установка с ГГ-деревом; длинное имя – проверка задач 1/8
    # (сессия 12: глифы крупнее, полного имени – с горизонтальным
    # ползунком, без усечения по буквам)
    h.select_object(None)
    h.add_kind("territory")
    h.add_kind("outdoor")
    inst = h.selected()
    inst.title = "Одностенный изотермический резервуар хранения СУГ № 1"
    inst.props.update({"area_m2": 600.0})
    win._add_tree(inst.id, "gg")
    gg = next(t for t in win.trees if t.scenario_type == "gg")
    gg.gs_causes = [GSCause(ref="gs-vessel-12.5"),
                    GSCause(ref="gs-vessel-25")]
    gg.iz_causes = [IZCause(ref="iz-static"), IZCause(ref="iz-cable")]
    gg.k_sigma = 1.2
    # Задача 6 (сессия 14): вторая установка с деревом БЕЗ причин –
    # смешанные состояния на холсте: «задано» (синие ГС/ИЗ + фиолетовое
    # «Возникновение») у заполненных деревьев и «не задано» (янтарь/
    # красный + серые строки, красное «Возникновение») у пустого
    h.select_object(inst.parent)          # территория второй установки
    h.add_kind("outdoor")                 # соседняя установка
    inst2 = h.selected()
    inst2.title = "Печь обжига № 2 (без причин)"
    win._add_tree(inst2.id, "gzh")
    win._mark_dirty()


def main() -> int:
    from PySide6.QtCore import QSize, QTimer
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import QRectF

    from eta.core.kb import KnowledgeBase
    from eta.ui.icons import app_icon
    from eta.ui.main_window import MainWindow
    from eta.ui.scroll import install_scroll_wide
    from eta.ui.theme import QSS

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      str(OUT / "_settings"))

    app = QApplication(sys.argv)
    app.setOrganizationName("GraphiczD")
    app.setApplicationName("Kuji ETA 533")
    app.setWindowIcon(app_icon())
    app.setStyleSheet(QSS)
    install_scroll_wide(app)
    from eta.ui.modern_tooltip import install_modern_tooltips
    install_modern_tooltips(app)

    for old in list(OUT.glob("qa_pdf_*.png")) + list(OUT.glob("qa_export_*.pdf")) + list(OUT.glob("qa_docx_com_skipped.txt")):
        old.unlink()

    kb = KnowledgeBase()
    win = MainWindow(kb, restore_ui=False)
    win.resize(1560, 940)
    build_demo(kb, win)
    for _ in range(8):
        app.processEvents()
    win.hierarchy.select_object(None)
    win._refresh()
    for _ in range(6):
        app.processEvents()
    win.canvas.fit_tree()

    # 1. окно целиком
    win.grab().save(str(OUT / "qa_window.png"))

    # 2. холст (все деревья)
    win.canvas.grab().save(str(OUT / "qa_canvas.png"))

    # 3. инспекторы: нода «Возникновение пожара» + здание
    gg = next(t for t in win.trees if t.scenario_type == "gg")
    win.inspector.show_tree_node(gg, "fire")
    for _ in range(4):
        app.processEvents()
    win.inspector.grab().save(str(OUT / "qa_inspector_fire.png"))
    bld = next(o for o in win.objects.all_nodes() if o.kind == "building")
    win.hierarchy.select_object(bld)
    for _ in range(4):
        app.processEvents()
    win.inspector.grab().save(str(OUT / "qa_inspector_building.png"))
    # Задача 12 (сессия 13): форма территории – «Площадь территории»
    # с переключателем км²|м² рядом со значением
    terr = next(o for o in win.objects.all_nodes() if o.kind == "territory")
    win.hierarchy.select_object(terr)
    for _ in range(4):
        app.processEvents()
    win.inspector.grab().save(str(OUT / "qa_inspector_territory.png"))

    # 3a. панель иерархии крупно (сессия 12, Задачи 1/8): длинные имена
    # без усечений + горизонтальный ползунок внизу; второй снимок –
    # прокрученный вправо: полный текст длинного имени достижим.
    # Сессия 15 (Задача 3): для снимка участок РАСКРЫТ – видны строка
    # сценария и причины-дети («Образование ГС: …», ИЗ; вложенность
    # зависимых ветвей); после снимка возвращаем свернутость
    _own_it = win.hierarchy._item_of(area_node) \
        if (area_node := next(
            (o for o in win.objects.all_nodes() if o.kind == "area"),
            None)) is not None else None
    if _own_it is not None:
        _own_it.setExpanded(True)
        for _ in range(2):
            app.processEvents()
    win.hierarchy.grab().save(str(OUT / "qa_hierarchy.png"))
    if _own_it is not None:
        _own_it.setExpanded(False)
        for _ in range(2):
            app.processEvents()
    hbar = win.hierarchy.tree.horizontalScrollBar()
    if hbar.maximum() > 0:
        hbar.setValue(hbar.maximum())
        for _ in range(4):
            app.processEvents()
        win.hierarchy.grab().save(str(OUT / "qa_hierarchy2.png"))
        hbar.setValue(0)
        for _ in range(4):
            app.processEvents()
    # Задача 2 (сессия 14): РЕАЛЬНЫЙ мультивыбор – две территории
    # выделены одновременно (программная установка без сигналов –
    # только ради снимка; клик-механика проверена gesture-блоком 31)
    _ters = win.hierarchy.objects.territories
    if len(_ters) >= 2:
        _t = win.hierarchy.tree
        _t.blockSignals(True)
        _t.clearSelection()
        for _tt in _ters[:2]:
            _it = win.hierarchy._item_of(_tt)
            if _it is not None:
                _it.setSelected(True)
        _t.blockSignals(False)
        for _ in range(4):
            app.processEvents()
        win.hierarchy.grab().save(str(OUT / "qa_hierarchy3.png"))
        _t.blockSignals(True)
        _t.clearSelection()
        _t.setCurrentItem(None)
        _t.blockSignals(False)
        for _ in range(4):
            app.processEvents()

    # 3b. подсказки-«сноски» (Задача 3): короткая – компактный пузырь,
    # длинная – перенос по словам ≤85 символов
    from eta.ui.modern_tooltip import ModernTooltip
    t_short = ModernTooltip()
    t_short.set_content("<b>Приблизить</b> – увеличить масштаб вьюпорта")
    t_long = ModernTooltip()
    t_long.set_content(
        "При включении аварийной вентиляции условная вероятность"
        " сохранения взрывоопасной концентрации снижается"
        " до P_ост = 1/(A·T + 1). Делитель массы – по"
        " ГОСТ Р 12.3.047-98, прил. А, п. А.2.5. Кратность воздухообмена"
        " A задается в свойствах помещения, ч; T – продолжительность"
        " поступления, ч.")
    t_short.show_instantly()
    t_long.show_instantly()
    for _ in range(4):
        app.processEvents()
    g1, g2 = t_short.grab(), t_long.grab()
    tip_img = QImage(QSize(max(g1.width(), g2.width()) + 8,
                           g1.height() + g2.height() + 16),
                     QImage.Format.Format_ARGB32)
    tip_img.fill(0xFFE2E8F0)
    tp = QPainter(tip_img)
    tp.drawPixmap(4, 4, g1)
    tp.drawPixmap(4, g1.height() + 12, g2)
    tp.end()
    t_short.hide()
    t_long.hide()
    tip_img.save(str(OUT / "qa_tooltip.png"))

    # 3c. разворот списка (Задачи 5/6): кнопка + всплывший список
    # («Категория защиты» здания) – пункты во всю высоту, ширина
    # адаптивна (не шире 2× кнопки)
    from PySide6.QtWidgets import QComboBox
    from eta.ui.switch import ToggleSwitch as _TS
    lp_sw = next((s for s in win.inspector.form_host.findChildren(_TS)
                  if s.text() == "Молниезащита"), None)
    if lp_sw is not None and not lp_sw.isChecked():
        lp_sw.setChecked(True)         # «Категория защиты» видима
        for _ in range(4):
            app.processEvents()
    cat = next((c for c in win.inspector.form_host.findChildren(QComboBox)
                if c.count() == 4 and "0,98" in c.itemText(0)), None)
    if cat is not None:
        cat.showPopup()
        for _ in range(6):
            app.processEvents()
        btn_pm = cat.grab()
        view_pm = cat.view().window().grab()
        combo_img = QImage(
            QSize(max(btn_pm.width(), view_pm.width()) + 8,
                  btn_pm.height() + view_pm.height() + 12),
            QImage.Format.Format_ARGB32)
        combo_img.fill(0xFFE2E8F0)
        cp2 = QPainter(combo_img)
        cp2.drawPixmap(4, 4, btn_pm)
        cp2.drawPixmap(4, btn_pm.height() + 8, view_pm)
        cp2.end()
        combo_img.save(str(OUT / "qa_combo.png"))
        cat.hidePopup()

    # 4. матрица (pop-out окно документа). Задача 1 (сессия 13):
    # снимок делается ПОВТОРНОГО открытия – цикл close → open проверяет,
    # что панель не остается скрытой (пустое окно)
    win.open_doc_window()
    win.doc_window.close()
    for _ in range(4):
        app.processEvents()
    win.open_doc_window()
    win.set_doc_view_mode("matrix")
    for _ in range(6):
        app.processEvents()
    win.doc_window.grab().save(str(OUT / "qa_matrix.png"))
    # Сессия 17: колонка «Формула» шире вьюпорта (горизонтальный скролл,
    # как в дереве иерархии) – дополнительный снимок ПРОКРУЧЕННОЙ вправо
    # матрицы: подставленные числа (множитель П1.1 × F/L/V) видны целиком
    mhbar = win.matrix_table.horizontalScrollBar()
    if mhbar.maximum() > 0:
        mhbar.setValue(mhbar.maximum())
        for _ in range(4):
            app.processEvents()
        win.doc_window.grab().save(str(OUT / "qa_matrix2.png"))
        mhbar.setValue(0)
        for _ in range(4):
            app.processEvents()

    # 5. схематический лист
    win.set_doc_view_mode("schematic")
    win.doc_view.fit_width()
    for _ in range(6):
        app.processEvents()
    win.doc_view.grab().save(str(OUT / "qa_docview.png"))
    win.doc_window.close()

    # 6. полный лист 2x (сцена = PDF)
    src = win.canvas.controller.layout.scene_rect
    img = QImage(QSize(int(src.width() * 2), int(src.height() * 2)),
                 QImage.Format.Format_ARGB32)
    img.fill(0xFFFFFFFF)
    p = QPainter(img)
    p.setRenderHints(QPainter.RenderHint.Antialiasing
                     | QPainter.RenderHint.TextAntialiasing)
    win.canvas.controller.doc_scene.render(p, QRectF(img.rect()), src)
    p.end()
    img.save(str(OUT / "qa_sheet.png"))

    # 7. переключатели-«свитчи» крупно
    from eta.ui.switch import ToggleSwitch
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
    host = QWidget()
    lay = QVBoxLayout(host)
    lay.setContentsMargins(24, 24, 24, 24)
    lay.setSpacing(14)
    lay.addWidget(QLabel("Переключатели (крупно, состояние ×3):"))
    for text, on, dis in (("Вытяжная / аварийная вентиляция", True, False),
                          ("ПАЗ по уровню полноты безопасности (SIL)", True, False),
                          ("Молниезащита здания", False, False),
                          ("Износ (превышен срок службы)", False, False),
                          ("Резервирование противоаварийной защиты", True, True)):
        sw = ToggleSwitch(text)
        sw.setChecked(on)
        sw.setEnabled(not dis)
        lay.addWidget(sw)
    host.adjustSize()
    host.show()
    for _ in range(4):
        app.processEvents()
    host.grab().scaled(host.width() * 3, host.height() * 3,
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.FastTransformation
                       ).save(str(OUT / "qa_switches.png"))
    host.close()

    # 7a. Сессия 16, Задача 3: образцы КАРТОЧКИ ПЕРЕНОСА (глиф 16 +
    # заголовок, рамка 1 px, elide по пикселям) на нейтральном фоне –
    # растер _drag_pixmap в 2× (физические пиксели 1:1, без размытия)
    from eta.ui.hierarchy_panel import _drag_pixmap as _dp_qa
    from eta.ui.icons import (GLYPH_AREA as _GA_qa, GLYPH_GS_CAUSE,
                              GLYPH_IZ_CAUSE)
    _cards_qa = [
        _dp_qa(GLYPH_GS_CAUSE,
               "Образование ГС: Пожар по поверхности", 2.0),
        _dp_qa(GLYPH_IZ_CAUSE, "Отказ кабельных линий", 2.0),
        _dp_qa(_GA_qa,
               "Одностенный изотермический резервуар хранения СУГ"
               " № 1 с очень длинным названием – проверка усечения"
               " по пикселям", 2.0),
    ]
    _gap_qa = 24
    _wmax_qa = max(pm.deviceIndependentSize().width()
                   for pm, _ in _cards_qa)
    _hsum_qa = sum(pm.deviceIndependentSize().height()
                   for pm, _ in _cards_qa) \
        + _gap_qa * (len(_cards_qa) + 1)
    _img_qa = QImage(int(_wmax_qa) * 2 + _gap_qa * 4,
                     int(_hsum_qa) * 2, QImage.Format.Format_ARGB32)
    _img_qa.fill(0xFFE2E8F0)
    _pq_qa = QPainter(_img_qa)
    _y_qa = _gap_qa
    for _pmq, _ in _cards_qa:
        _pq_qa.drawImage(_gap_qa * 2, _y_qa * 2, _pmq.toImage())
        _y_qa += int(_pmq.deviceIndependentSize().height()) + _gap_qa
    _pq_qa.end()
    _img_qa.save(str(OUT / "qa_drag_card.png"))

    # 8. окно БД: шаблоны оборудования (с выбранной целью – плашка;
    #    сессия 11: выбрана карточка с «<» в названии – проверка Задачи 4
    #    (подсветка выбора) и Задачи 5 (жирный только заголовок))
    area_node = next(o for o in win.objects.all_nodes()
                     if o.kind == "area")
    win.hierarchy.select_object(area_node)
    win._update_kb_apply_hint()
    win._open_kb_window()
    win.kb_window.templates_tab.selected_id = "eq-tank-small"
    win.kb_window.templates_tab._mark_selected()
    win.kb_window.templates_tab.scroll_to_selected()
    # Задача 10 (сессия 15): панель справа – ФОРМА РЕДАКТИРОВАНИЯ шаблона
    win.kb_window.templates_tab._load_form()
    win.kb_window.templates_tab._sync_apply()
    for _ in range(6):
        app.processEvents()
    win.kb_window.grab().save(str(OUT / "qa_kb_templates.png"))
    # вкладки «Защитные средства» и «Таблицы типовых частот» (сессия 11:
    # под-вкладки П1.3/П1.4/П2.1 – снимки под-вкладок 1 и 2)
    tabs = win.kb_window.tabs

    def _hscroll_right(table) -> None:
        # Задача 9 (сессия 18): таблицы стали шире (колонка «Источник») –
        # снимок с горизонтальной прокруткой ДО КРАЯ показывает её
        bar = table.horizontalScrollBar()
        bar.setValue(bar.maximum())
        for _ in range(4):
            app.processEvents()

    for i in range(tabs.count()):
        title = tabs.tabText(i)
        if title == "Защитные средства":
            tabs.setCurrentIndex(i)
            for _ in range(4):
                app.processEvents()
            win.kb_window.grab().save(str(OUT / "qa_kb_measures.png"))
            _hscroll_right(tabs.currentWidget().table)
            win.kb_window.grab().save(str(OUT / "qa_kb_measures2.png"))
        # Задачи 9/10 (сессия 13): редактируемые библиотеки ИЗ/ГС –
        # снимки ЦЕЛОГО ОКНА (внизу слева – «Добавить/Удалить запись»,
        # справа – «Сохранить»/«Закрыть»); в ГС прокручиваем таблицу к
        # трубопроводной строке П1.2 («× L» в колонке частоты)
        if title == "Источники зажигания (ИЗ)":
            tabs.setCurrentIndex(i)
            for _ in range(4):
                app.processEvents()
            win.kb_window.grab().save(str(OUT / "qa_kb_iz.png"))
            _hscroll_right(tabs.currentWidget().table)
            win.kb_window.grab().save(str(OUT / "qa_kb_iz2.png"))
        if title == "Горючие среды (ГС)":
            tabs.setCurrentIndex(i)
            for _ in range(4):
                app.processEvents()
            gst = tabs.currentWidget()
            for r in range(gst.table.rowCount()):
                it = gst.table.item(r, 0)
                if it and "Трубопровод" in it.text():
                    gst.table.scrollToItem(
                        it, getattr(__import__("PySide6.QtWidgets",
                                               fromlist=["QAbstractItemView"]),
                                    "QAbstractItemView").ScrollHint
                        .PositionAtCenter)
                    break
            for _ in range(4):
                app.processEvents()
            win.kb_window.grab().save(str(OUT / "qa_kb_gs.png"))
            _hscroll_right(gst.table)
            win.kb_window.grab().save(str(OUT / "qa_kb_gs2.png"))
        # Задача 9 (сессия 18): реестр источников «Базы данных»
        if title == "Источники":
            tabs.setCurrentIndex(i)
            for _ in range(4):
                app.processEvents()
            win.kb_window.grab().save(str(OUT / "qa_kb_sources.png"))
        # Задача 8 (сессия 13): справочник «Таблица типовых режимов
        # пожара» (только чтение)
        if title == "Таблица типовых режимов пожара":
            tabs.setCurrentIndex(i)
            for _ in range(4):
                app.processEvents()
            tabs.grab().save(str(OUT / "qa_kb_fire_modes.png"))
        if title == "Таблицы типовых частот":
            tabs.setCurrentIndex(i)
            for _ in range(4):
                app.processEvents()
            sub = tabs.currentWidget().sub
            sub.setCurrentIndex(0)
            for _ in range(4):
                app.processEvents()
            tabs.grab().save(str(OUT / "qa_kb_tables.png"))
            sub.setCurrentIndex(1)
            for _ in range(4):
                app.processEvents()
            tabs.grab().save(str(OUT / "qa_kb_tables2.png"))
    # Задача 13 (сессия 18): окно справки «?» (формулы – индексы/степени).
    # Для снимка окно выше обычного (контент ~экран); плюс второй снимок
    # прокрученный вниз – разделы 3 (ввод чисел) и 4 видны целиком
    win.kb_window._open_help()
    hw = win.kb_window._help_win
    hw.resize(620, 780)
    for _ in range(6):
        app.processEvents()
    hw.grab().save(str(OUT / "qa_kb_help.png"))
    _scr = hw.findChildren(__import__("PySide6.QtWidgets",
                                      fromlist=["QScrollArea"])
                           .QScrollArea)[0]
    _bar = _scr.verticalScrollBar()
    _bar.setValue(_bar.maximum())
    for _ in range(4):
        app.processEvents()
    hw.grab().save(str(OUT / "qa_kb_help2.png"))
    hw.accept()
    win.kb_window._help_win = None
    win.kb_window.close()
    # (окно БД закрыто – после снимка справки «?»)

    # 9. экспорт DOCX (Задача 11): pandoc + ГОСТ-шаблон; визуальные
    #    страницы – Word COM (docx→pdf) + WinRT-рендер (QtPdf рисует
    #    Word-PDF черным – замер сессии 18)
    from eta.export.report_docx import export_docx
    docx_path = OUT / "qa_report.docx"
    pdf_rendered = False
    report_pages = 0

    def _docx_to_pdf_com(docx: str, pdf: str) -> bool:
        """Word COM (headless): docx -> pdf. Требует интерактивный сеанс;
        при недоступности COM – False (шаг пропускается)."""
        ps = ("$w = New-Object -ComObject Word.Application; "
              "$w.Visible = $false; "
              "try { $d = $w.Documents.Open('{d}', $false, $true); "
              "$d.ExportAsFixedFormat('{p}', 17); "
              "$d.Close($false); Write-Output OK } "
              "finally { $w.Quit() }").format(
                  d=str(docx).replace("'", "''"),
                  p=str(pdf).replace("'", "''"))
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-Command", ps], capture_output=True, text=True,
                timeout=300)
            return "OK" in r.stdout
        except Exception:  # noqa: BLE001 – COM может отсутствовать
            return False

    def _render_pdf_pages(pdf: str, prefix: str, pages: list) -> int:
        """Страницы PDF -> PNG через Windows.Data.Pdf
        (render_pdf_pages.ps1; QtPdf рисует Word-PDF черным – замер
        сессии 18). Номера страниц – от нуля. Возвращает число PNG."""
        pages_arg = "@(" + ",".join(str(p) for p in pages) + ")"
        script = (ROOT / "render_pdf_pages.ps1").resolve()
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-Command",
                 "& '{s}' -Pdf '{p}' -OutPrefix '{o}' -Pages {n}".format(
                     s=script, p=str(pdf).replace("'", "''"),
                     o=prefix, n=pages_arg)],
                capture_output=True, text=True, timeout=300)
        except Exception:  # noqa: BLE001
            return 0
        return sum(1 for i in pages
                   if (OUT / f"{prefix}{i + 1}.png").exists())

    try:
        export_docx(str(docx_path), win.objects, win.trees, kb,
                    win.ctx_map(), win._owner_titles(), "A3L",
                    canvas=win.canvas)
        assert docx_path.exists() and docx_path.stat().st_size > 100_000
        pdf_out = OUT / "qa_report.pdf"
        if _docx_to_pdf_com(str(docx_path), str(pdf_out)):
            # страницы: титул, оглавление, расчет + последняя (схемы)
            n = _render_pdf_pages(str(pdf_out), "qa_docx_page", [0, 1, 2])
            n_last = _render_pdf_pages(str(pdf_out), "qa_docx_last", [-1])
            pdf_rendered = n >= 1
            report_pages = n + n_last
        else:
            (OUT / "qa_docx_com_skipped.txt").write_text(
                "Word COM недоступен – конвертация в PDF пропущена",
                encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        pdf_rendered = False
        report_pages = 0
        (OUT / "qa_docx_error.txt").write_text(str(exc), encoding="utf-8")

    totals = []
    cmap = win.ctx_map()
    for t in win.trees:
        totals.append(t.total_q(kb, cmap.get(t.owner_id)))
    stats = {
        "trees": len(win.trees),
        "matrix_rows": win.matrix_table.rowCount(),
        "total_q": totals,
        "pdf_rendered": pdf_rendered,
        "report_pages": report_pages,
        "kb_version": kb.meta.get("version"),
        "app_version": __import__("eta").__version__,
        "artifacts": [p.name for p in sorted(OUT.iterdir())
                      if p.suffix in (".png", ".json")],
    }
    (OUT / "qa_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    win._dirty = False
    win.close()
    QTimer.singleShot(0, app.quit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
