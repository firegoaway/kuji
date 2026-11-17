# -*- coding: utf-8 -*-
"""Диалог экспорта в DOCX (Задачи 10/11, сессия 18, LOCKED).

Формат листа (ровно шесть позиций: A4/A3/A2 × книжная/альбомная)
задает размер растра СХЕМ в документе; сам файл – один DOCX
(A4 книжный по шаблону ГОСТ Р 21.101, колонки-штампы донца).
Настройки «Содержимое» и отчетный переключатель упразднены вместе
с PDF-экспортом (Задача 11: один проект = один DOCX)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout)

from ..export.report_docx import FORMAT_LABELS, export_docx


class DocxExportDialog(QDialog):
    def __init__(self, parent=None, suggested_name: str = "отчет.docx",
                 start_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Экспорт отчета в DOCX")
        self.setMinimumWidth(520)
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

    def _do_export(self) -> None:
        path = self.path_edit.text().strip()
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
            self.path_edit.setText(path)
        try:
            export_docx(path, self._objects, self._trees, self._kb,
                        self._ctx_map, self._owner_titles,
                        self.size_combo.currentData(), canvas=self._canvas)
        except Exception as exc:  # noqa: BLE001 – русская диагностика
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Экспорт DOCX", str(exc))
            return
        self.accept()
