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
    from eta.ui import app_settings
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
    # Сессия 19 (п.3): настройки приложения лежат в ЯВНОМ INI-файле
    # (%APPDATA%\GraphiczD\Kuji ETA 533.ini), а не в реестре: на машине
    # заказчика записи в ветку реестра терялись, и перезапуск не помнил ни
    # размеров окон, ни последней папки экспорта. Делается до первого окна
    # и до любого QSettings – весь остальной код работает прежним вызовом.
    store = app_settings.install_ini_backend()
    app.setWindowIcon(app_icon())
    app.setStyleSheet(QSS)
    # скролл колесом/Shift+колесом во всех окнах, кроме зумящихся вьюпортов
    install_scroll_wide(app)
    # современные анимированные подсказки (сессия 9, Задача 2): единая
    # панель на всё приложение, системные QToolTip подавляются фильтром;
    # мгновенный режим – offscreen/KUJI_NO_ANIMATION (шов тестов)
    install_modern_tooltips(app)
    # перенос старых значений из реестра в INI (один раз), затем –
    # одноразовая миграция настроек старого «Freq ETA 533» → «Kuji ETA 533»
    moved = app_settings.migrate_from_registry()
    migrate_qsettings()
    app_settings.log_diagnostics()      # в key_debug.log при KUJI_DEBUG_KEYS
    app_settings.log_startup()          # всегда: qa_artifacts\startup.log
    if moved:
        print(f"[kuji] настройки перенесены из реестра в {store}"
              f" (ключей: {moved})")
    kb = KnowledgeBase()
    win = MainWindow(kb)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
