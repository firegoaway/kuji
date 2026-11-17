"""Нативное pop-out окно «ДОКУМЕНТ – ТАБЛИЦА / ЛИСТ ДЛЯ PDF» (сессия 8).

Панель документа (шапка с переключателем «Матричный вид» /
«Схематический вид», кнопка «Вписать по ширине», таблица сценариев
и лист для PDF) вынесена из главного окна в ОТДЕЛЬНОЕ нативное окно ОС:
системный заголовок, перетаскивание между мониторами, свободное
изменение размеров (края/углы), разворот и сворачивание. Внутри –
ТЕ ЖЕ САМЫЕ виджеты, что раньше жили в верхней панели (reparent), а не
их копия: синхронизация с деревом, вероятностями, видом и формулами
мгновенная и двусторонняя – матрица и лист слушают model.changed,
правки идут через общий DiagramController.

Жизненный цикл (владение панелью остаётся у MainWindow):
  * панель строится один раз и хранится в скрытом хосте главного окна;
  * open  → панель перекладывается в layout этого окна (reparent);
  * close (крестик) → сигнал closed → MainWindow забирает панель
    обратно в скрытый хост и удаляет окно; кнопка-триггер на левой
    панели инструментов гаснет (синее выделение снимается).

Масштабирование листа для PDF: колесо мыши – плавный зум к курсору
(как в рабочем вьюпорте), «+»/«–» (в т.ч. с Ctrl) – зум от центра,
Ctrl+0 – «Вписать по ширине»; в режиме «fit» лист сам переписывается
по ширине при изменении размера окна (DocumentView.resizeEvent).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .. import APP_TITLE
from .icons import app_icon
from .theme import APP_BG


class DocumentWindow(QWidget):
    """Отдельное нативное окно ОС (системный chrome) с панелью документа.

    Флаг Qt.Window даёт настоящее окно платформы: собственная строка
    заголовка с кнопками свернуть/развернуть/закрыть, свободный drag
    по рабочему столу (в т.ч. на второй монитор), resize за края.
    """

    closed = Signal()              # окно закрыто – вернуть панель в хост
    shown = Signal()               # окно показано – можно переписать лист
    zoom_requested = Signal(int)   # +1 – крупнее, −1 – мельче
    fit_requested = Signal()       # Ctrl+0 – «Вписать по ширине»

    def __init__(self, panel: QWidget):
        super().__init__(None, Qt.WindowType.Window)
        self.setObjectName("docWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#docWindow {{ background: {APP_BG}; border: none; }}")
        self.setWindowTitle(f"ДОКУМЕНТ – ТАБЛИЦА / ЛИСТ ДЛЯ PDF – {APP_TITLE}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(520, 320)
        self.resize(1060, 660)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(panel)        # reparent: панель теперь в этом окне

        self._add_zoom_shortcuts()

    # ---------- масштабирование: «+»/«–» и Ctrl+0 ----------
    def _add_zoom_shortcuts(self) -> None:
        """Действует при фокусе в окне; слоты подключает MainWindow."""

        def shortcut(seq, slot) -> None:
            act = QAction(self)
            act.setShortcut(seq)
            act.triggered.connect(slot)
            self.addAction(act)

        shortcut(QKeySequence.StandardKey.ZoomIn,       # Ctrl+(+)
                 lambda: self.zoom_requested.emit(1))
        shortcut(QKeySequence("+"), lambda: self.zoom_requested.emit(1))
        shortcut(QKeySequence("="), lambda: self.zoom_requested.emit(1))
        shortcut(QKeySequence.StandardKey.ZoomOut,      # Ctrl+(−)
                 lambda: self.zoom_requested.emit(-1))
        shortcut(QKeySequence("-"), lambda: self.zoom_requested.emit(-1))
        shortcut(QKeySequence("Ctrl+0"), self.fit_requested.emit)

    # ---------- события ----------
    def showEvent(self, e) -> None:
        super().showEvent(e)
        self.shown.emit()

    def hideEvent(self, e) -> None:
        # Задача 1 (сессия 18): размер/положение запоминаются при скрытии
        # ЛЮБЫМ путём (close, скрытие родителем, teardown приложения) –
        # closeEvent главного окна и сигнал closed покрывают не всё
        from PySide6.QtCore import QSettings
        QSettings().setValue("ui/doc_geometry", self.saveGeometry())
        super().hideEvent(e)

    def closeEvent(self, e) -> None:
        # сначала отдаём панель (MainWindow), только потом окно умирает
        self.closed.emit()
        super().closeEvent(e)
