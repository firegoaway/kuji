# -*- coding: utf-8 -*-
r"""Имена файлов отчета DOCX (Задача 1, сессия 19; LOCKED).

Правило: «Отчет-РЧП-<идентификатор>.docx», где идентификатор –

  * имя сохраненного файла проекта без расширения, например
    `D:\Проекты\ФОК Донецк.kuji.json` → `Отчет-РЧП-ФОК Донецк.docx`
    (`.kuji.json` отсекается ОДНИМ движком, `.json` – тоже);
  * либо UID несохраненного проекта – ровно 6 символов `[a-z0-9]`
    (`a4f91c`). UID живет в памяти одного документа (атрибут
    `MainWindow._report_uid`), поэтому одинаков при каждом открытии
    диалога в этой сессии и перегенерируется командой «Новый проект»
    и при перезапуске приложения.

Санитизация (детерминированная, пункт 1 правила LOCKED):

  1. каждый недопустимый в именах файлов Windows символ
     `\ / : * ? " < > |` (плюс управляющие `0x00–0x1F`) заменяется
     дефисом «-»;
  2. серии дефисов схлопываются в один;
  3. ведущие/завершающие пробелы, точки и дефисы удаляются (Windows
     не принимает завершающие точку и пробел).

Если после санитизации база пуста – используется UID-вариант.

Модуль ЧИСТЫЙ: без Qt и без обращения к файловой системе, поэтому
проверяется smoke-блоками напрямую.
"""

from __future__ import annotations

import re
import secrets
from pathlib import PureWindowsPath

# Префикс имени отчета (текст интерфейса, §5 канона: дефисы, без пробелов)
PREFIX = "Отчет-РЧП"
EXT = ".docx"

# Формат UID несохраненного проекта: 6 строчных латинских букв и цифр
UID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
UID_LENGTH = 6
UID_RE = re.compile(r"\A[a-z0-9]{6}\Z")

# Недопустимые символы Windows-имени (+ управляющие символы)
_ILLEGAL_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_DASH_RUN_RE = re.compile(r"-{2,}")


def new_session_uid() -> str:
    """Новый UID документной сессии: 6 символов `[a-z0-9]`."""
    return "".join(secrets.choice(UID_ALPHABET) for _ in range(UID_LENGTH))


def sanitize_filename(name: str) -> str:
    """Имя, законное для Windows (правила докстринга модуля, п. 1–3)."""
    s = _ILLEGAL_RE.sub("-", str(name or ""))
    s = _DASH_RUN_RE.sub("-", s)
    return s.strip().strip("-.").strip()


def project_basename(project_path: str) -> str:
    """База имени файла проекта: `ФОК Донецк.kuji.json` → `ФОК Донецк`.

    Путь разбирается как windows-путь (проектные файлы – только Windows
    сборка); расширения нет – имя возвращается как есть."""
    name = PureWindowsPath(str(project_path or "")).name
    if name.lower().endswith(".kuji.json"):
        return name[: -len(".kuji.json")]
    return PureWindowsPath(name).stem


def report_docx_name(project_path: str | None, session_uid: str) -> str:
    """Полное имя файла отчета по правилу «Отчет-РЧП-<база|UID>.docx».

    `session_uid` используется только для несохраненного проекта; если
    он пуст или не формата UID – генерируется новый (гарантия формата
    на выходе)."""
    base = sanitize_filename(project_basename(project_path or ""))
    if not base:
        uid = str(session_uid or "").strip().lower()
        base = uid if UID_RE.match(uid) else new_session_uid()
    return f"{PREFIX}-{base}{EXT}"
