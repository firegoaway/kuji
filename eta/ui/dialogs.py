# -*- coding: utf-8 -*-
"""Диалог экспорта в DOCX (Задачи 10/11, сессия 18, LOCKED).

Формат листа (ровно шесть позиций: A4/A3/A2 × книжная/альбомная)
задает размер растра СХЕМ в документе; сам файл – один DOCX
(A4 книжный по шаблону ГОСТ Р 21.101, колонки-штампы донца).
Настройки «Содержимое» и отчетный переключатель упразднены вместе
с PDF-экспортом (Задача 11: один проект = один DOCX).

Сессия 19, Задачи 1 и 3: путь предзаполняется умным именем
«Отчет-РЧП-…», выбор папки в «Обзор…» запоминается сразу (шов
`remember_dir`), а успешный экспорт публикует фактический абсолютный
путь в `exported_path` – по нему окно спрашивает, открыть ли отчет."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QVBoxLayout)

from ..export.report_docx import FORMAT_LABELS, export_docx


def _pump(times: int = 3) -> None:
    """Дать окну перерисоваться (экспорт идёт в GUI-потоке)."""
    app = QApplication.instance()
    for _ in range(max(1, int(times))):
        if app is None:
            return
        app.processEvents()


class ReportProgress(QDialog):
    """Ход формирования отчёта (сессия 20, просьба заказчика): полоса
    прогресса и текущий этап.

    Показывается НЕ модально (`show()`, не `exec()`): сам экспорт выполняется
    в этом же потоке и между этапами крутит события через `_pump()`, а
    модальный `exec()` внутри обработчика «Экспортировать» повесил бы и
    экспорт, и окно (тот же урок, что и с модалками в offscreen-прогонах)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Формирование отчета DOCX")
        self.setModal(False)
        self.setMinimumWidth(440)
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(10)
        self.info = QLabel("Подготовка документа")
        self.info.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFormat("%p%")
        box.addWidget(self.info)
        box.addWidget(self.bar)

    def show_progress(self) -> None:
        self.show()
        _pump()

    def stage(self, value: float, message: str = "") -> None:
        """Один этап конвейера: доля 0..1 и русская подпись."""
        try:
            done = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return
        self.bar.setValue(int(round(done * 100)))
        if message:
            self.info.setText(str(message))
        _pump()

    def close_progress(self) -> None:
        self.close()
        _pump(1)


class DocxExportDialog(QDialog):
    def __init__(self, parent=None, suggested_name: str = "отчет.docx",
                 start_dir: str = "",
                 remember_dir: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        self.setWindowTitle("Экспорт отчета в DOCX")
        self.setMinimumWidth(520)
        # Задача 1 (сессия 19): вызывается при выборе пути в «Обзор…»
        # (даже если диалог затем отменен) – MainWindow пишет export/last_dir
        self._remember_dir = remember_dir
        # Задача 3 (сессия 19): фактический абсолютный путь успешного
        # экспорта (пусто, пока экспорт не удался)
        self.exported_path: str = ""
        # данные экспорта (заполняет MainWindow перед exec)
        self._objects = None
        self._trees: list = []
        self._kb = None
        self._ctx_map: dict = {}
        self._owner_titles: dict = {}
        self._canvas = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        form = QFormLayout()
        # Задача 10 (LOCKED): шесть форматов – размер листа СХЕМ
        self.size_combo = QComboBox()
        for fid, label in FORMAT_LABELS.items():
            self.size_combo.addItem(label, fid)
        form.addRow("Формат листа:", self.size_combo)
        root.addLayout(form)

        path_row = QHBoxLayout()
        initial = (Path(start_dir) / suggested_name if start_dir
                   else Path.home() / "Desktop" / suggested_name)
        self.path_edit = QLineEdit(str(initial))
        browse = QPushButton("Обзор…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        root.addLayout(path_row)

        self.preview = QLabel("")
        self.preview.setWordWrap(True)
        root.addWidget(self.preview)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Экспортировать")
        ok.setObjectName("primary")
        ok.clicked.connect(self._do_export)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        root.addLayout(btns)
        self._update_preview()

    def set_project_data(self, objects, trees: list, kb, ctx_map: dict,
                         owner_titles: dict, canvas) -> None:
        """Данные отчета: иерархия, деревья, база, контексты, холст."""
        self._objects = objects
        self._trees = trees
        self._kb = kb
        self._ctx_map = ctx_map
        self._owner_titles = owner_titles
        self._canvas = canvas
        self._update_preview()

    def _update_preview(self) -> None:
        owners = sum(1 for o in self._objects.all_nodes()
                     if o.kind in ("area", "outdoor")
                     and any(t.owner_id == o.id for t in self._trees)) \
            if self._objects is not None else len(self._trees)
        self.preview.setText(
            f"Расчетных участков и установок: {owners}."
            " Один файл DOCX: титул, оглавление, нормативные ссылки,"
            " расчет, схемы деревьев и матрицы.")

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Файл DOCX", self.path_edit.text(),
            "Документ Word (*.docx)")
        if path:
            self.path_edit.setText(path)
            # Задача 1 (сессия 19, LOCKED): выбранная папка запоминается
            # СРАЗУ – даже если пользователь затем отменит диалог
            if self._remember_dir is not None:
                self._remember_dir(path)

    def _make_progress(self):
        """ШОВ: окно хода формирования отчета. Тесты подменяют метод,
        возвращая None – тогда экспорт идёт вообще без второго окна
        (в offscreen любые модалки невозможны по определению)."""
        dlg = ReportProgress(self)
        dlg.show_progress()
        return dlg

    def _do_export(self) -> None:
        path = self.path_edit.text().strip()
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        # Задача 3 (сессия 18, §8): export_docx требует АБСОЛЮТНЫЙ путь
        # (pandoc работает во временном каталоге) – нормализуем поле
        path = os.path.abspath(path)
        self.path_edit.setText(path)
        # Сессия 20 (просьба заказчика): видно, на каком этапе сейчас
        # формирование – схемы, текст, конвертация, зачистка, проверка
        prog = self._make_progress()
        try:
            export_docx(path, self._objects, self._trees, self._kb,
                        self._ctx_map, self._owner_titles,
                        self.size_combo.currentData(), canvas=self._canvas,
                        progress=(prog.stage if prog is not None else None))
        except Exception as exc:  # noqa: BLE001 – русская диагностика
            if prog is not None:
                prog.close_progress()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Экспорт DOCX", str(exc))
            return
        if prog is not None:
            prog.close_progress()
        # Задача 3 (сессия 19): публикуем фактический путь успешного
        # экспорта – по нему MainWindow покажет вопрос об открытии отчета
        self.exported_path = path
        self.accept()
