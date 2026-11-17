#!/usr/bin/env python
"""Точка входа: Kuji (Куджи) – конструктор логических деревьев событий
(FTA + ETA) по Методике МЧС России № 533.

Запуск:  runtime\\python\\python.exe main.py   (или run_app.cmd)
"""

from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from eta.core.kb import KnowledgeBase
    from eta.ui.icons import app_icon
    from eta.ui.main_window import MainWindow, migrate_qsettings
    from eta.ui.modern_tooltip import install_modern_tooltips
    from eta.ui.scroll import install_scroll_wide
    from eta.ui.theme import QSS

    app = QApplication(sys.argv)
    app.setOrganizationName("GraphiczD")
    app.setOrganizationDomain("graphiczd.local")
    app.setApplicationName("Kuji ETA 533")
    app.setApplicationDisplayName("Kuji (Куджи)")
    app.setWindowIcon(app_icon())
    app.setStyleSheet(QSS)
    # скролл колесом/Shift+колесом во всех окнах, кроме зумящихся вьюпортов
    install_scroll_wide(app)
    # современные анимированные подсказки (сессия 9, Задача 2): единая
    # панель на всё приложение, системные QToolTip подавляются фильтром;
    # мгновенный режим – offscreen/KUJI_NO_ANIMATION (шов тестов)
    install_modern_tooltips(app)
    # одноразовая миграция настроек старого «Freq ETA 533» → «Kuji ETA 533»
    migrate_qsettings()
    kb = KnowledgeBase()
    win = MainWindow(kb)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
