# -*- coding: utf-8 -*-
"""Сериализация проектов (формат 5, сессия 10 – ЧИСТЫЙ РАЗРЫВ).

Парадигма «пяти инвариантных типов сценариев» несовместима с деревьями
форматов 1–4 (левое крыло с И/ИЛИ/НЕ, правое крыло с барьерами,
терминалы «Сценарий N»): при открытии такого файла возбуждается
UnsupportedFormatError, и приложение показывает понятное сообщение
«Формат проекта устарел» БЕЗ попыток конвертации (решение заказчика).

Файл формата 5:
    {"format": 5, "name": …, "threshold": …,
     "objects": [территория…], "trees": [TreeModel…], "ui": {…}}
"""

from __future__ import annotations

import json

from .model import TreeModel
from .objects import ObjectTree

FORMAT_VERSION = 5


class UnsupportedFormatError(Exception):
    """Формат файла проекта не поддерживается (устарел)."""


def save_project(path: str, object_tree: ObjectTree,
                 trees: list[TreeModel], project_name: str = "",
                 threshold: float = 1e-8, ui: dict | None = None) -> None:
    data = {
        "format": FORMAT_VERSION,
        "name": project_name,
        "threshold": float(threshold),
        "objects": object_tree.to_dict(),
        "trees": [t.to_dict() for t in trees],
    }
    if ui:
        data["ui"] = ui
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def load_project(path: str) -> dict:
    """Прочитать проект формата 5. Возвращает словарь с ключами
    objects (list), trees (list[TreeModel]), name, threshold, ui."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    fmt = data.get("format")
    if fmt != FORMAT_VERSION:
        raise UnsupportedFormatError(
            f"Формат проекта устарел (обнаружен формат {fmt});"
            " файлы сессий 1–9 несовместимы с новой моделью"
            " «пяти типов сценариев» – постройте дерево заново.")
    return {
        "objects": data.get("objects", []),
        "trees": [TreeModel.from_dict(t) for t in data.get("trees", [])],
        "name": data.get("name", ""),
        "threshold": float(data.get("threshold", 1e-8)),
        "ui": data.get("ui", {}) or {},
    }
