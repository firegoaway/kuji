# -*- coding: utf-8 -*-
"""Хранилище настроек приложения (сессия 19, замечание заказчика п.3).

ПРОБЛЕМА. Qt писал настройки в реестр Windows (NativeFormat,
`HKCU\\Software\\GraphiczD\\Kuji ETA 533`). На машине заказчика это
хранилище перестало обновляться: в ветке лежат только ключи старых
сборок (`ui/geometry`, `ui/split_h`, `ui/split_v`, `ui/doc_scale`,
`ui/threshold`, `ui/inspector_tab`, `ui/palette_groups`,
`ui/viewport_mode`, `ui/migrated_from`), а всё введённое с сессии 17
(`ui/migrated`, `ui/splitter`, `ui/doc_geometry`, `ui/kb_geometry`,
`ui/last_dir`, `export/last_dir`) – ОТСУТСТВУЕТ. Заказчик проверил:
перезапуск не помнит ни размеров окон, ни последней папки экспорта.
Права на ветку полные (FullControl у пользователя), значит теряется
сама запись – политика/антивирус/виртуализация реестра. Спорить с чужой
политикой мы не можем, поэтому настройки переведены на ЯВНЫЙ INI-файл в
%APPDATA%\\GraphiczD\\: его видно глазами, он переносим и удаляется без
regedit, и его выбор больше не зависит от того, какой бэкенд Qt счёл бы
умолчательным на данной машине.

ЧТО ОТВЕЧАЕТ ЗА ЧТО:

  * `install_ini_backend()` вызывается ОДИН раз из `main.py` (до первого
    окна). Меняет формат по умолчанию на IniFormat, поэтому ВСЕ
    существующие вызовы `QSettings()` в коде продолжают работать без
    правок и попадают в INI (`%APPDATA%\\GraphiczD\\Kuji ETA 533.ini`).
  * `write_value()` – единственная правильная запись: `setValue` +
    `sync()`. Без `sync()` Qt держит изменение в кэше до разрушения
    последнего объекта QSettings, а убитый «сверху» процесс терял память
    папок и пропорций панелей.
  * `migrate_from_registry()` – однократный перенос старых значений из
    реестра в INI, чтобы ничего не потерять при смене хранилища.
    Вызывается ТОЛЬКО из `main.py`: тесты вызывают свои миграции сами и
    обязаны оставаться герметичными (они переопределяют формат и путь
    на временный ini, и `QSettings.setPath` действует и на явные
    конструкторы).
  * `diagnostics()` – путь файла, статус записи и снимок реестра для
    лога запуска (`run_app_debug.cmd`) и для отчётов.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QSettings

ORG = "GraphiczD"
APP = "Kuji ETA 533"

# Ключи, переносимые из реестра в INI при первом запуске новой схемы
# (исторические имена сессий 8–19; несуществующие просто пропускаются)
_MIGRATE_KEYS = (
    "ui/geometry", "ui/splitter", "ui/split_h", "ui/split_v",
    "ui/doc_geometry", "ui/kb_geometry", "ui/last_dir", "ui/doc_scale",
    "ui/threshold", "ui/palette_groups", "ui/inspector_tab",
    "ui/viewport_mode", "export/last_dir",
)

_installed: bool = False
_store_dir: tuple = ()


def installed() -> bool:
    """True, если INI-бэкенд установлен этим процессом."""
    return _installed


def app_root() -> Path:
    """Корень программы – каталог с `main.py` и `run_app.cmd`."""
    return Path(__file__).resolve().parents[2]


def _writable(dir_path: str) -> bool:
    """Проверить, что в каталог РЕАЛЬНО можно писать (создать и удалить
    пробный файл). Без такой проверки выбор хранилища – гадание: на машине
    заказчика не создавалось НИЧЕГО – ни новых ключей в реестре, ни файла в
    `%APPDATA%\\GraphiczD` (каталога просто не существовало после запусков)."""
    try:
        os.makedirs(dir_path, exist_ok=True)
        fd, probe = tempfile.mkstemp(prefix="kuji_probe_", dir=dir_path)
        os.close(fd)
        os.unlink(probe)
        return True
    except OSError:
        return False


def choose_store_dir() -> tuple:
    """Куда положить файл настроек: (каталог, пояснение для лога).

    Порядок: (1) ПЕРЕНОСИМОЕ хранилище рядом с программой –
    `<корень>\\settings`: оно заведомо доступно на запись там, где программа
    вообще запускается, и его видно глазами вместе с проектом; (2) штатный
    для IniFormat каталог `%APPDATA%\\GraphiczD`. Переносимое идёт первым
    именно потому, что проверяется на запись до выбора."""
    portable = str(app_root() / "settings")
    if _writable(portable):
        return portable, "portable (рядом с программой)"
    roaming = os.path.join(os.environ.get("APPDATA") or str(Path.home()), ORG)
    if _writable(roaming):
        return roaming, "roaming (%APPDATA%)"
    return roaming, "fallback (запись недоступна, взят %APPDATA%)"


def install_ini_backend(store_dir: str | None = None) -> str:
    """Перевести QSettings на явный INI-файл и вернуть его путь.

    `store_dir=None` (боевой запуск из `main.py`) – каталог выбирает
    `choose_store_dir()`; явный каталог нужен тестам, чтобы хранилище
    осталось герметичным. Идемпотентно. ВАЖНО: вызывать ПОСЛЕ
    `setOrganizationName`/`setApplicationName` и ДО первого окна."""
    global _installed, _store_dir
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    if store_dir is None:
        store_dir, why = choose_store_dir()
    else:
        why = "задан явно (тесты)"
    _store_dir = (str(store_dir), why)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      str(store_dir))
    _installed = True
    return settings_file()


def store_info() -> tuple:
    """(каталог хранилища, пояснение выбора) – для стартовой диагностики."""
    return _store_dir or ("", "бэкенд не установлен")


def settings() -> QSettings:
    """Объект настроек приложения (та же схема, что у `QSettings()`)."""
    return QSettings()


def settings_file() -> str:
    """Путь фактического файла/ключа настроек, как его видит Qt."""
    return settings().fileName()


def write_value(key: str, value) -> None:
    """Записать настройку и немедленно столкнуть её на диск."""
    st = settings()
    st.setValue(key, value)
    st.sync()


def read_value(key: str, default=None):
    """Прочитать настройку (строка/байты/число – как лежит)."""
    return settings().value(key, default)


def registry_settings() -> QSettings:
    """Реестровое хранилище старых сборок – для миграции и диагностики."""
    return QSettings(QSettings.Format.NativeFormat,
                     QSettings.Scope.UserScope, ORG, APP)


def diagnostics() -> dict:
    """Снимок состояния хранилища для лога запуска и отчётов.

    Поля различаются сборками PySide (часть методов статические), поэтому
    всё читается осторожно и при непонимании остаётся None."""
    st = settings()
    out: dict = {"store": None, "format": None, "scope": None,
                 "writable": None, "status": None,
                 "registry_store": None, "registry_keys": None}
    try:
        out["store"] = st.fileName()
    except Exception:  # noqa: BLE001
        pass
    try:
        out["format"] = repr(st.format())
        out["scope"] = repr(st.scope())
    except Exception:  # noqa: BLE001
        pass
    try:
        out["writable"] = bool(st.isWritable())
    except Exception:  # noqa: BLE001
        try:
            out["writable"] = bool(QSettings.isWritable())
        except Exception:  # noqa: BLE001
            pass
    try:
        out["status"] = int(st.status())
    except Exception:  # noqa: BLE001
        pass
    try:
        reg = registry_settings()
        out["registry_store"] = reg.fileName()
        out["registry_keys"] = len(reg.allKeys())
    except Exception:  # noqa: BLE001
        pass
    return out


def log_diagnostics() -> dict:
    """Собрать diagnostics() и, если включён отладочный лог
    (KUJI_DEBUG_KEYS=1 / run_app_debug.cmd), записать туда состояние
    хранилища. Это ответ на вопрос «куда Qt реально пишет и разрешена ли
    запись» без расспросов пользователя."""
    info = diagnostics()
    try:
        from .latin_keys import debug_line
        debug_line("settings | " + " | ".join(f"{k}={v}"
                                              for k, v in info.items()))
    except Exception:  # noqa: BLE001 – диагностика не ломает запуск
        pass
    return info


def log_startup() -> str:
    """Одна строка старта в `<корень>\\qa_artifacts\\startup.log` – ВСЕГДА,
    а не только при KUJI_DEBUG_KEYS.

    Зачем: три раунда подряд заказчик сообщал, что настройки не помнятся, а
    прочитать состояние его хранилища из-за пределов его процесса было
    нечем. Строка содержит путь файла настроек, причину выбора каталога,
    признак записи, статус Qt, снимок реестра и фактическое наличие
    ключей – этого достаточно, чтобы отличить «не пишем» от «пишем не туда».
    Файл держит последние 200 строк и не растёт вечно."""
    import time

    from .. import __version__
    info = diagnostics()
    st_dir, why = store_info()
    st = settings()
    marks = {k: (st.value(k) is not None) for k in
             ("ui/geometry", "ui/splitter", "ui/last_dir",
              "export/last_dir", "ui/kb_geometry", "ui/doc_geometry")}
    line = (f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] v{__version__} "
            f"store={info.get('store')} why={why} "
            f"writable={info.get('writable')} status={info.get('status')} "
            f"registry={info.get('registry_store')} "
            f"reg_keys={info.get('registry_keys')} keys={marks}")
    path = app_root() / "qa_artifacts" / "startup.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tail: list[str] = []
        if path.exists():
            tail = path.read_text(encoding="utf-8",
                                  errors="replace").splitlines()[-199:]
        path.write_text("\n".join(tail + [line]) + "\n", encoding="utf-8")
    except OSError:
        pass                      # диагностика не имеет права ломать запуск
    return line


def migrate_from_registry() -> int:
    """Однократно перенести старые значения из реестра в INI.

    Возвращает число перенесённых ключей. Отметка `ui/settings_ini`
    больше не повторяет перенос; уже имеющееся в INI значение НЕ
    перезаписывается (вдруг пользователь уже выбрал другую папку)."""
    st = settings()
    if st.value("ui/settings_ini", False):
        return 0
    reg = registry_settings()
    try:
        keys = set(reg.allKeys())
    except Exception:  # noqa: BLE001 – недоступный куст не беда
        keys = set()
    moved = 0
    for key in _MIGRATE_KEYS:
        if key not in keys:
            continue
        if st.value(key, None) not in (None, ""):
            continue
        try:
            val = reg.value(key)
        except Exception:  # noqa: BLE001
            continue
        if val in (None, ""):
            continue
        st.setValue(key, val)
        moved += 1
    st.setValue("ui/settings_ini", True)
    st.sync()
    return moved
