# -*- coding: utf-8 -*-
"""Задача 4 (сессия 17, LOCKED): сквозная раскладко-независимость
буквенных шорткатов.

Приложение НЕ обязано знать, в какой раскладке печатает пользователь:
приложенческий фильтр событий переводит НАЖАТИЯ С Ctrl/Alt, чей key() –
кириллический код Qt.Key (Windows в русской раскладке дает именно их),
в ЛАТИНСКИЙ ПОЗИЦИОННЫЙ эквивалент полной таблицы ЙЦУКЕН и доставляет
синтетическое событие дальше. Каждый буквенный шорткат – текущие
(Ctrl+N/O/S/E/Q/D, Alt+A) и будущие – срабатывает в ОБЕИХ раскладках
без ручных «близнецов» (существующие пары-близнецы безвредны и остаются).

Функция latin_key – ЧИСТАЯ (тестируется без окна); сам фильтр ставится
на QApplication ОДИН раз и держится сильной ссылкой на уровне модуля
(ловушка GC PySide6: объект фильтра без ссылки молча умирает).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent

# =====================================================================
# Задача 2 (сессия 18): инструментировка РЕАЛЬНОЙ доставки клавиш.
# Windows-десктоп ≠ offscreen QTest: измеренные заказчиком факты –
# Alt+Ф не открывает меню «Файл», Ctrl+N/O работают в обеих раскладках,
# Alt+A / Ctrl+E(У) / Ctrl+D(В) НЕ работают в русской, Пробел+ЛКМ не
# панорамирует ни в одной. Форма доставки клавиш на реальной Windows
# обязана быть ИЗМЕРЕНОЙ до правки кода: при KUJI_DEBUG_KEYS=1 каждый
# KeyPress/KeyRelease (+ShortcutOverride – кандидат «съесть» Alt+букву),
# видимый приложенческому фильтру, пишется в qa_artifacts\key_debug.log.
# =====================================================================
_DEBUG_KEYS: bool | None = None      # ленивое кэширование env
_DEBUG_PATH = (Path(__file__).resolve().parents[2] / "qa_artifacts"
               / "key_debug.log")


def keys_debug_enabled() -> bool:
    """KUJI_DEBUG_KEYS=1 (читается лениво – переменную можно поставить
    и после старта процесса)."""
    global _DEBUG_KEYS
    if _DEBUG_KEYS is None:
        _DEBUG_KEYS = os.environ.get("KUJI_DEBUG_KEYS") == "1"
    return _DEBUG_KEYS


def _mods_text(mods) -> str:
    parts = []
    if mods & Qt.KeyboardModifier.ControlModifier:
        parts.append("Ctrl")
    if mods & Qt.KeyboardModifier.AltModifier:
        parts.append("Alt")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        parts.append("Shift")
    if mods & Qt.KeyboardModifier.MetaModifier:
        parts.append("Meta")
    if mods & Qt.KeyboardModifier.KeypadModifier:
        parts.append("Keypad")
    return "+".join(parts) if parts else "-"


def key_debug_log(tag: str, ev, obj=None, note: str = "") -> None:
    """Одна строка в qa_artifacts\\key_debug.log (KUJI_DEBUG_KEYS=1):
    кто (tag), какое окно-цель/класс, key()/nativeVirtualKey()/text(),
    модификаторы, авто-повтор, класс виджета в фокусе, примечание
    (конвертация фильтром, принятие фильтром холста и т.п.)."""
    if not keys_debug_enabled():
        return
    from PySide6.QtWidgets import QApplication
    try:
        kind = {QEvent.Type.KeyPress: "KeyPress",
                QEvent.Type.KeyRelease: "KeyRelease",
                QEvent.Type.ShortcutOverride: "ShortcutOverride"}.get(
                    ev.type(), str(ev.type()))
        focus = "-"
        app = QApplication.instance()
        if app is not None:
            fw = app.focusWidget()
            if fw is not None:
                focus = type(fw).__name__
        obj_s = "-"
        if obj is not None:
            obj_s = type(obj).__name__
        line = (f"[{time.strftime('%H:%M:%S')}."
                f"{int(time.time() * 1000) % 1000:03d}] {tag} {kind}"
                f" obj={obj_s} key={ev.key()}(0x{ev.key():04X})"
                f" native={ev.nativeVirtualKey()}"
                f" text={ev.text()!r} mods={_mods_text(ev.modifiers())}"
                f" auto={ev.isAutoRepeat()} focus={focus}"
                + (f" | {note}" if note else ""))
        _DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_DEBUG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:            # noqa: BLE001 – лог не должен ронять ввод
        pass

# Полная таблица ЙЦУКЕН: кириллический код Qt.Key → латинская клавиша
# ТОЙ ЖЕ физической позиции (верхний регистр 0x0410–0x042F; строчные
# 0x0430–0x044F нормализуются снятием бита 0x20)
_CYR_TO_LAT: dict[int, int] = {
    0x0419: 0x51,  # Й → Q
    0x0426: 0x57,  # Ц → W
    0x0423: 0x45,  # У → E
    0x041A: 0x52,  # К → R
    0x0415: 0x54,  # Е → T
    0x041D: 0x59,  # Н → Y
    0x0413: 0x55,  # Г → U
    0x0428: 0x49,  # Ш → I
    0x0429: 0x4F,  # Щ → O
    0x0417: 0x50,  # З → P
    0x0424: 0x41,  # Ф → A
    0x042B: 0x53,  # Ы → S
    0x0412: 0x44,  # В → D
    0x0410: 0x46,  # А → F
    0x041F: 0x47,  # П → G
    0x0420: 0x48,  # Р → H
    0x041E: 0x4A,  # О → J
    0x041B: 0x4B,  # Л → K
    0x0414: 0x4C,  # Д → L
    0x042F: 0x5A,  # Я → Z
    0x0427: 0x58,  # Ч → X
    0x0421: 0x43,  # С → C
    0x041C: 0x56,  # М → V
    0x0418: 0x42,  # И → B
    0x0422: 0x4E,  # Т → N
    0x042C: 0x4D,  # Ь → M
}


def latin_key(code: int | None) -> int | None:
    """Латинский позиционный эквивалент кириллического кода клавиши
    (ЙЦУКЕН → QWERTY) или None для не-кириллических кодов. Чистая
    функция без Qt-объектов – тестируется напрямую.

    Внимание: кириллический регистр – ЧИСЛОВОЕ смещение +0x20
    (0x0410–0x042F → 0x0430–0x044F), а не битовая маска: у букв
    вроде У (0x0423) бит 0x20 уже установлен, очистка бита дала бы
    0x0403 – мусор. Строчные нормализуются вычитанием."""
    if not isinstance(code, int):
        return None
    lat = _CYR_TO_LAT.get(code)
    if lat is None and 0x0430 <= code <= 0x044F:
        lat = _CYR_TO_LAT.get(code - 0x20)
    return lat


def latin_letter(ev) -> str | None:
    """Латинская буква физической клавиши события (A–Z) или None.

    Три канала разрешения (Задача 2, сессия 18; форма доставки
    ИЗМЕРЕНА на реальной Windows – qa_artifacts\\key_debug.log):
      1) key() уже латинская буква (Ctrl+буква в русской раскладке);
      2) key() кириллическая – таблица ЙЦУКЕН (Alt+буква);
      3) nativeVirtualKey() – виртуальный код Windows ВСЕГДА латинский
         по позиции (Alt+Ф: key=0x0424, native=65='A')."""
    k = ev.key()
    if 0x41 <= k <= 0x5A or 0x61 <= k <= 0x7A:
        return chr(k).upper()
    lat = latin_key(k)
    if lat is not None:
        return chr(lat)
    nv = ev.nativeVirtualKey()
    if 0x41 <= nv <= 0x5A:
        return chr(nv)
    return None


# =====================================================================
# Задача 2 (сессия 18): реестр буквенных шорткатов + доставка через
# ShortcutOverride. Измерено на реальной Windows (key_debug.log,
# 15.11.2026): нажатие Ctrl/Alt+буква ДОСТАВЛЯЕТСЯ ТОЛЬКО как
# ShortcutOverride (KeyPress для буквы не приходит вовсе), при этом
# карта шорткатов Qt активирует StandardKey (Ctrl+N/O), но НЕ
# активирует кастомные QKeySequence ни в латинской, ни в кириллической
# форме. Поэтому кастомные буквенные последовательности приложения
# срабатывают ПРЯМО из приложенческого фильтра: буква нормализуется
# (latin_letter), ищется в реестре, действие запускается с УЧЕТОМ
# контекста (ApplicationShortcut – из любого окна; WindowShortcut –
# только когда окно-владелец активно). Реестр ДЕБАЮНСИРОВАН (~80 мс):
# Qt доставляет ShortcutOverride по всей цепочке родителей (8 объектов
# в логе) – одно физическое нажатие = один запуск.
# =====================================================================
from PySide6.QtCore import QEvent  # noqa: E402

_LETTER_ACTIONS: dict[str, list] = {}       # "Ctrl+E" -> [(owner, action)]
_LAST_FIRED: dict[str, float] = {}          # seq -> monotonic-время
_IN_FLIGHT: set[str] = set()                # seq внутри action.trigger()
_FIRE_DEBOUNCE_S = 0.08


def register_letter_action(seq: str, owner, action) -> None:
    """Зарегистрировать буквенный шорткат для доставки через
    ShortcutOverride (вызывается из MainWindow._build_actions)."""
    lst = _LETTER_ACTIONS.setdefault(seq, [])
    if not any(o is owner and a is action for o, a in lst):
        lst.append((owner, action))


def _dispatch_letter(seq: str) -> bool:
    """Запустить действие реестра для последовательности. Возвращает
    True, если что-то запущено (событие нужно поглотить).

    Дебаунса 80 мс мало для МОДАЛЬНЫХ действий (замер живьём, заказчик
    17.11.2026: Ctrl+E открывал диалог экспорта дважды). Причина: Qt
    разносит ShortcutOverride по цепочке родителей синхронно, а фильтр
    вызывает action.trigger() прямо посреди этого обхода. Если действие
    запускает вложенный цикл событий (exec() модального диалога),
    продолжение обхода наступает уже ПОСЛЕ закрытия окна – штамп
    «последнего срабатывания» к тому времени устаревает, и следующий
    объект цепочки запускает то же действие ещё раз. Отсюда два guard'а:

      1) `_IN_FLIGHT` – одно физическое нажатие = один вход в действие
         (автоповтор клавиатуры, пришедший во время модалки, гасится);
      2) штамп `_LAST_FIRED` обновляется ПОСЛЕ возврата из действия,
         чтобы возобновившаяся цепочка родителей попала в дебаунс.
    """
    import time as _time
    now = _time.monotonic()
    if seq in _IN_FLIGHT:
        return True                   # действие ещё не вернулось (модалка)
    if now - _LAST_FIRED.get(seq, 0.0) < _FIRE_DEBOUNCE_S:
        return True                   # уже запущено этим нажатием
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    active = app.activeWindow() if app is not None else None
    fired = False
    for owner, action in list(_LETTER_ACTIONS.get(seq, [])):
        if action is None or not action.isEnabled():
            continue
        w = getattr(owner, "window", None)
        if w is not None and action.shortcutContext() \
                != Qt.ShortcutContext.ApplicationShortcut \
                and w() is not active:
            continue                  # окно-владелец не активно
        _LAST_FIRED[seq] = now
        _IN_FLIGHT.add(seq)
        try:
            action.trigger()
        finally:
            _IN_FLIGHT.discard(seq)
            # штамп после возврата – возобновившаяся цепочка родителей
            # обязана попасть в дебаунс, а не запускать диалог второй раз
            _LAST_FIRED[seq] = _time.monotonic()
        fired = True
    return fired


def _seq_of(mods, letter: str) -> str | None:
    """Каноническое имя последовательности для реестра. Shift – часть
    имени (Ctrl+Shift+S «Сохранить как…»), Meta игнорируется веткой
    вызова. Пара Ctrl+Alt не используется намеренно."""
    ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
    alt = bool(mods & Qt.KeyboardModifier.AltModifier)
    shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
    if ctrl and not alt:
        return ("Ctrl+Shift+" if shift else "Ctrl+") + letter
    if alt and not ctrl:
        return ("Alt+Shift+" if shift else "Alt+") + letter
    return None


# ---------- Пробел: панорама на уровне ПРИЛОЖЕНИЯ (Задача 2) ----------
_SPACE_PAN = {"held": False}
_SPACE_CONSUMERS: list = []


def space_pan_active() -> bool:
    """Пробел удерживается (панорама холста вооружена) – глобальный
    флаг приложения: клавиша доставляется только сфокусированному
    виджету, а фокус может стоять в иерархии/инспекторе."""
    return _SPACE_PAN["held"]


def add_space_pan_consumer(cb) -> None:
    """Подписка на смену флага (холст показывает курсор «рука»)."""
    if not any(cb is c for c in _SPACE_CONSUMERS):
        _SPACE_CONSUMERS.append(cb)


def _set_space_pan(on: bool) -> None:
    if _SPACE_PAN["held"] == on:
        return
    _SPACE_PAN["held"] = on
    for cb in list(_SPACE_CONSUMERS):
        try:
            cb(on)
        except Exception:  # noqa: BLE001 – мертвый потребитель отвязываем
            try:
                _SPACE_CONSUMERS.remove(cb)
            except ValueError:
                pass


def _editor_has_focus() -> bool:
    """Фокус в текстовом редакторе/спинбоксе – Пробел принадлежит ему."""
    from PySide6.QtWidgets import (QAbstractSpinBox, QApplication,
                                   QLineEdit, QPlainTextEdit, QTextEdit)
    w = QApplication.focusWidget()
    return isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit,
                          QAbstractSpinBox))


class LatinKeyFilter(QObject):
    """Фильтр приложения. Два механизма (сессия 17 + сессия 18):

    1) KeyPress с Ctrl/Alt и КИРИЛЛИЧЕСКИМ key() → синтетическое
       событие с латинским кодом той же физической клавиши (пути
       offscreen/QTest и платформ, где KeyPress приходит);
    2) ShortcutOverride с Ctrl/Alt+буква → нормализация буквы
       (latin_letter) и ПРЯМОЙ запуск действия из реестра (форма
       доставки реальной Windows: KeyPress нет вовсе);
    3) Пробел на уровне ПРИЛОЖЕНИЯ: press/release вне текстовых
       редакторов переключает глобальный флаг панорамы (isAutoRepeat
       не togg'ает); события не поглощаются – штатная активация
       кнопок клавишей Пробел сохраняется."""

    def eventFilter(self, obj, ev) -> bool:  # noqa: N802
        # Задача 2 (сессия 18): инструментировка – каждый KeyPress/
        # KeyRelease (+ShortcutOverride) на пути ПРИЛОЖЕНЧЕСКОГО фильтра
        if ev.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease,
                         QEvent.Type.ShortcutOverride):
            key_debug_log("app", ev, obj)
        if ev.type() == QEvent.Type.ShortcutOverride:
            mods = ev.modifiers()
            # Shift ДОПУЩЕН (сессия 19): «Сохранить как…» = Ctrl+Shift+S;
            # в реестре ищется точное имя последовательности, поэтому
            # незарегистрированные комбинации (в т. ч. Alt+Shift –
            # переключатель раскладки Windows, у Shift нет буквы key())
            # остаются нетронутыми. Meta (Win) по-прежнему исключаем.
            if mods & (Qt.KeyboardModifier.ControlModifier
                       | Qt.KeyboardModifier.AltModifier) \
                    and not mods & Qt.KeyboardModifier.MetaModifier:
                letter = latin_letter(ev)
                if letter is not None:
                    seq = _seq_of(mods, letter)
                    if seq is not None and _dispatch_letter(seq):
                        key_debug_log(
                            "app", ev, obj,
                            note=f"override dispatch: {seq}")
                        return True      # запущено – событие поглощено
        if ev.type() == QEvent.Type.KeyPress:
            mods = ev.modifiers()
            if mods & (Qt.KeyboardModifier.ControlModifier
                       | Qt.KeyboardModifier.AltModifier):
                lat = latin_key(ev.key())
                if lat is None:
                    # запасной канал: латинская позиция по nativeVirtualKey
                    # или кириллическому text() (Задача 2, ожидаемая форма)
                    nv = ev.nativeVirtualKey()
                    if 0x41 <= nv <= 0x5A:
                        lat = nv
                    elif ev.text():
                        lat = latin_key(ord(ev.text()[0]))
                if lat is not None and not (0x41 <= ev.key() <= 0x5A
                                            or 0x61 <= ev.key() <= 0x7A):
                    text = chr(lat).lower() if not mods & \
                        Qt.KeyboardModifier.ShiftModifier else chr(lat)
                    synthetic = QKeyEvent(QEvent.Type.KeyPress, lat, mods,
                                          text, ev.isAutoRepeat(),
                                          ev.count())
                    from PySide6.QtWidgets import QApplication
                    QApplication.sendEvent(obj, synthetic)
                    key_debug_log(
                        "app", ev, obj,
                        note=f"converted: key()={ev.key()}"
                             f"(0x{ev.key():04X}) -> Latin {lat}"
                             f"(0x{lat:04X})")
                    return True          # исходное кириллическое поглощено
            # Пробел вне редакторов: глобальная готовность панорамы
            if ev.key() == Qt.Key.Key_Space and not ev.isAutoRepeat():
                _set_space_pan(not _editor_has_focus())
        elif ev.type() == QEvent.Type.KeyRelease:
            if ev.key() == Qt.Key.Key_Space and not ev.isAutoRepeat():
                _set_space_pan(False)
        return super().eventFilter(obj, ev)


# сильная ссылка на уровне модуля (PySide6 GC: фильтр без ссылки умирает)
_installed: LatinKeyFilter | None = None


def install_latin_key_filter(app=None) -> LatinKeyFilter | None:
    """Поставить фильтр на QApplication (идемпотентно; сильная ссылка
    хранится в модуле). Вызывается из MainWindow.__init__ – окна тестов
    получают механизм автоматически."""
    global _installed
    from PySide6.QtWidgets import QApplication
    app = app or QApplication.instance()
    if app is None:
        return None
    if _installed is None:
        _installed = LatinKeyFilter()
        app.installEventFilter(_installed)
        if keys_debug_enabled():
            # заголовок сессии – прогоны разделяются в общем логе
            _DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_DEBUG_PATH, "a", encoding="utf-8") as fh:
                fh.write(
                    f"\n=== session {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    f" platform="
                    f"{os.environ.get('QT_QPA_PLATFORM', 'windows')}"
                    f" ===\n")
    return _installed
