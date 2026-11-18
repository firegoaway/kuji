# -*- coding: utf-8 -*-
"""Всегда включённая трасса потока «экспорт → вопрос → открытие
отчёта» (сессия 20, задачи 1 и 2; разрешение заказчика от 18.11.2026).

Зачем. Дефекты сессии 19 невозможно было разделить по причинам, потому
что ни один факт о РЕАЛЬНОМ прохождении потока не фиксировался:
launch-цепочка молча деградирует `cmd start` → powershell → explorer →
`os.startfile` (неудача возвращает False, исключений нет), а повторное
открытие диалога экспорта не оставляет следов – видно только окно.
Настройки были разгаданы в один раунд именно безусловным логом
(`app_settings.log_startup` → qa_artifacts\\startup.log); здесь тот же
приём для модального потока.

Формат: одна строка на событие,
`[ГГГГ-ММ-ДД ЧЧ:ММ:СС] <событие> key=value …` в
qa_artifacts\\launch_trace.log. События:

  * `dlg-open source=<shortcut|menu|…> project=<база|UID> t=<monotonic>`
    – диалог экспорта ОТКРЫТ; `source` различает маршрут: shortcut –
    диспетчер latin_keys (ShortcutOverride-фильтр), menu – собственная
    механика Qt (пункт меню или нативный шорткат, маршрут, которого
    `_IN_FLIGHT` не видит вовсе);
  * `dlg-open-blocked reason=<belt> source=…` – повторный вход отвергнут
    поясом `_export_running` (второй диалог НЕ открыт);
  * `dlg-export-start path=<файл>` / `dlg-export-done ms=<мс>` /
    `dlg-export-fail err=<…>` – сборка отчёта внутри диалога;
  * `overwrite-ask path=<файл>` / `overwrite-answer=<yes|no>` – вопрос
    о перезаписи существующего файла (сессия 20, требование заказчика);
  * `dlg-accepted` / `dlg-rejected` – чем закончился диалог;
  * `question-shown` / `question-answer=<yes|no>` – вопрос об открытии;
  * `launch-attempt way=<cmd|powershell|explorer|explorer-select|
    startfile|qt|winword> rc=<ok|spawned pid=…|fail err=…>` – КАЖДАЯ
    попытка открыть отчёт: по этим строкам видно, какой способ реально
    исполнился на машине заказчика (фолбэк-цепочка больше не «молчит»;
    explorer – открытие САМОГО файла процессом Проводника, сессия 20;
    explorer-select – запасной показ папки с выделением).

Файл держит последние `_MAX_LINES` строк (не растёт вечно). Запись
никогда не роняет приложение: любая ошибка диска проглатывается.
Трасса НЕ заменяет `latin_keys.debug_line` (посмотр-key-level
детали остаются в key_debug.log при KUJI_DEBUG_KEYS=1) – она отвечает
на вопрос «каким путём прошло событие», а не «какая клавиша пришла».

Герметичность тестов: путь вычисляет `trace_file()`; offscreen-блоки
подменяют её на свой подкаталог, чтобы не трогать общий файл.
"""

from __future__ import annotations

import time
from pathlib import Path

from .app_settings import app_root

# Ёмкость файла трассы (строк) – как у startup.log
_MAX_LINES = 200


def trace_file() -> Path:
    """Путь файла трассы (по умолчанию – общий qa_artifacts). Шов для
    тестов: подменяется на собственный подкаталог."""
    return app_root() / "qa_artifacts" / "launch_trace.log"


def trace_line(event: str, **fields: object) -> str:
    """Дописать одну строку события и вернуть её (для тестов).

    Перечитывает и обрезает файл до `_MAX_LINES - 1` строк, затем
    дописывает новую: событие редкое, файл короткий, цена копии
    пренебрежима – зато ёмкость гарантируется без внешних утилит."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {event}"
    if fields:
        line += " " + " ".join(f"{k}={v}" for k, v in fields.items())
    path = trace_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tail: list[str] = []
        if path.exists():
            tail = path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()[-(_MAX_LINES - 1):]
        path.write_text("\n".join(tail + [line]) + "\n", encoding="utf-8")
    except OSError:
        pass                      # трасса не имеет права ломать экспорт
    return line
