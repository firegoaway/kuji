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


def installed() -> bool:
    """True, если INI-бэкенд установлен этим процессом."""
    return _installed


def install_ini_backend() -> str:
    """Перевести QSettings на INI (IniFormat + привычный путь %APPDATA%).

    Возвращает путь файла настроек. Идемпотентно. ВАЖНО: вызывать
    ПОСЛЕ `setOrganizationName`/`setApplicationName` и ДО первого окна.
    """
    global _installed
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    if not _installed:
        _installed = True
    return settings_file()


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
